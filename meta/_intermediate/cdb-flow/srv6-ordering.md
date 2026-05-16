# srv6-orch — Phase B 順序依存調査メモ

## 調査対象ファイル

- `sonic-swss/orchagent/srv6orch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/srv6orch.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

---

## 1. SRV6_SID_LIST_TABLE (SID リスト) の依存関係

### 作成時の依存なし
`doTaskSidTable` (srv6orch.cpp:1146) は外部テーブルへの依存チェックなしで SAI に直接書き込む。

### 削除時の参照カウントガード
`deleteSidList` (srv6orch.cpp:1119–1143):
```cpp
if (sid_table_[sid_name].nexthops.size() > 0)
{
    return task_process_status::task_need_retry;  // 行 1133
}
```
SID リストを参照中の nexthop が存在する場合は `task_need_retry` を返す。
すなわち **SRV6_SID_LIST の DEL は、参照中の MY_SID_TABLE/nexthop を先に削除しないと失敗し続ける**。

---

## 2. SRV6_MY_SID_TABLE の依存関係

### 作成時の VRF 依存
`createUpdateMysidEntry` (srv6orch.cpp:1431–):
- `mySidVrfRequired()` (行 1384–1397) が `end.t` / `end.dt*` / `udt*` 系アクションに対して VRF チェックを要求。
- VRF が存在しない場合 (行 1500): `SWSS_LOG_ERROR("VRF %s doesn't exist in DB")` → `return false`。
  つまり **カスタム VRF を使う MySID は VRF テーブルが先に存在する必要がある**。ペンディング機構なし（即時失敗）。

### 作成時の Neighbor/Nexthop 依存
- `mySidNextHopRequired()` (行 1399–1415) が `end.x` / `end.dx*` / `udx*` / `end.b6*` / `ua` に Nexthop を要求。
- Nexthop 未解決時 (行 1524–1543):
  ```cpp
  m_pendingSRv6MySIDEntries[nexthop].insert(pending_mysid_entry);
  return false;
  ```
  **ペンディングリストに登録し、NeighOrch から neighbor ADD 通知を受けた時点で自動再インストール**。

### 作成時の IPinIP トンネル自動生成
`mySidTunnelRequired()` (行 1417–1429):
- `un` / `udt46` アクション かつ CONFIG_DB の `decap_dscp_mode` が設定されている場合にのみトンネルを生成。
- DSCP mode 未設定時はトンネル生成をスキップ（`boost::none` 判定）。
- `decap_dscp_mode` は APP_DB `SRV6_MY_SID_TABLE` ではなく CONFIG_DB `SRV6_MY_SIDS` のキャッシュ
  (`m_mysidCfgTable`) から取得する (doTaskCfgMySidTable → addMySidCfgCacheEntry)。

### 削除時の依存なし
`doTaskMySidTable` DEL は依存チェックなし。即時削除。ただし先に関連 nexthop を削除することを推奨
（参照先 SID リストの削除ブロック解除のため）。

---

## 3. bgpcfgd (CONFIG_DB → FRR) 側の順序制御

### SRV6_MY_SIDS の保留機構
`managers_srv6.py:62–68` (`sids_set_handler`):
```python
if not self.directory.path_exist(self.db_name, "SRV6_MY_LOCATORS", locator_name):
    self.deps.add((self.db_name, "SRV6_MY_LOCATORS", locator_name))
    self.directory.subscribe([...], self.on_deps_change)
    return False
```
**SRV6_MY_LOCATORS にロケータが存在しない場合、SID エントリを保留 (False 返却) し、
ロケータ登録後に `on_deps_change` コールバックで自動再試行する**。

### SID のロケータ範囲チェック
`managers_srv6.py:74–76`:
```python
if not locator_prefix.supernet_of(sid_prefix):
    log_err(...)
    return False
```
SID の IPv6 プレフィックスがロケータプレフィックスのサブネットでなければ即時エラー（リトライなし）。

### 削除時の順序
ロケータ削除 (`locators_del_handler`) は依存の SID エントリを先に削除せずに実行される。
FRR 側でロケータ削除時に SID が孤立することを防ぐため、
**SID を先に削除してからロケータを削除する**ことが推奨される。

---

## 4. PIC_CONTEXT_TABLE の参照カウント保護

`doTaskPicContextTable` (srv6orch.cpp:2272–):
- DEL 時 `it->second.ref_count != 0` の場合 `task_need_retry` (行 2328)。
- `routeorch` から `increasePicContextIdRefCount()`/`decreasePicContextIdRefCount()` で管理。
- **PIC_CONTEXT エントリの削除は、参照するルートエントリが先に削除されるまでブロックされる**。

---

## 5. Warm-reboot サポート状況

`srv6orch.cpp` / `srv6orch.h` に `WarmStart` / `reconcil` の実装は存在しない。
**Srv6Orch は warm-reboot のリコンサイル非対応**。
warm-reboot 後は swss の再起動時に APP_DB から全エントリを再読み込みし、
SAI を再プログラムすることで状態を復元する（cold-recovery と同等の動作）。

---

## 6. 処理順序まとめ (推奨設定投入順)

### 投入 (SET) 推奨順序
```
1. VRF テーブル (VRF が必要な action を使う場合)
2. SRV6_MY_LOCATORS (bgpcfgd 経由で FRR に locator を通知)
3. SRV6_SID_LIST_TABLE / SRV6_MY_SIDS (bgpcfgd がロケータ確認後に FRR 反映)
4. SRV6_MY_SID_TABLE (Srv6Orch が VRF・Nexthop 確認後に SAI へ投入)
5. PIC_CONTEXT_TABLE (VPN 経路が確立した後)
```

### 削除 (DEL) 推奨順序
```
1. PIC_CONTEXT_TABLE 参照ルート (ref_count を 0 にする)
2. PIC_CONTEXT_TABLE エントリ
3. SRV6_MY_SID_TABLE エントリ (SID リストへの nexthop 参照を解除)
4. SRV6_SID_LIST_TABLE エントリ (nexthops.size() == 0 の確認後)
5. SRV6_MY_SIDS / SRV6_MY_LOCATORS (FRR 側 SID → ロケータの順)
```
