# SRV6_MY_SIDS — Phase B 書込み順依存スキャンノート

対象テーブル: `SRV6_MY_SIDS|<locator_name>|<ip_prefix>`
Consumer (bgpcfgd): `SRv6Mgr` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py`)
Consumer (orchagent): `Srv6Orch` (`sonic-swss/orchagent/srv6orch.cpp`)
スキャン範囲:
  - `managers_srv6.py:55-101` (`sids_set_handler`)
  - `srv6orch.cpp:1440-1660` (`createUpdateMysidEntry`)
  - `srv6orch.cpp:1200-1350` (`update()` — neighborhoodUpdate)
  - `srv6orch.cpp:2250-2270` (`doTaskCfgMySidTable`)
Evidence: sonic-buildimage sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`, sonic-swss sha `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 検出した順序依存・タイミング依存

### 1. SRV6_MY_LOCATORS が先行必須（bgpcfgd 経路）

- `sids_set_handler()` L62-68: `self.directory.path_exist(self.db_name, "SRV6_MY_LOCATORS", locator_name)` が false の場合、`self.deps.add()` で購読を登録して `return False`（処理中断）。
- bgpcfgd は `on_deps_change` コールバックにより、対応ロケータが登録された時点で自動的に SID エントリを再処理する。
- エントリは失われないが、**ロケータが登録されるまで FRR への通知が遅延**する。
- evidence: `managers_srv6.py:62-68`

**推奨順序（bgpcfgd 経路）**:
```
SET SRV6_MY_LOCATORS|<locator_name>   prefix=... block_len=... node_len=...
--- ロケータ登録確認後 ---
SET SRV6_MY_SIDS|<locator_name>|<ip_prefix>   action=uN
```

### 2. SID プレフィックスはロケータプレフィックスのサブネットである必要がある

- `sids_set_handler()` L71-75: `locator_prefix.supernet_of(sid_prefix)` が false の場合、`log_err` を出力して `return False`（恒久的失敗）。
- SID のIPv6プレフィックスは対応ロケータの `prefix` + `block_len + node_len` ビット長 の範囲内にあること。
- これは単純な再試行では解消しない。設定値を修正して再度 SET する必要がある。
- evidence: `managers_srv6.py:71-75`

### 3. VRF が先行必須（action=uDT46 等 VRF 要求行動 / Srv6Orch 経路）

- `createUpdateMysidEntry()` L1484-1502: `dt_vrf != "default"` かつ VRF が `m_vrfOrch->isVRFexists(dt_vrf)` で存在しない場合、`SWSS_LOG_ERROR("VRF %s doesn't exist in DB", ...)` を出力して `return false`。
- orchagent は VRF の存在を前提とし、不在時は SAI エントリ作成を試みずエラー終了（自動再試行なし）。
- `dt_vrf = "default"` の場合は `gVirtualRouterId` に直接解決されるため VRF エントリ不要。
- evidence: `srv6orch.cpp:1484-1502`

### 4. NeighborOrch (Nexthop) が先行必須（action=end.x / ua 等 Adj 要求行動 / Srv6Orch 経路）

- `createUpdateMysidEntry()` L1511-1541: `mySidNextHopRequired(end_behavior)` が true の場合、`m_neighOrch->hasNextHop(nexthop)` の結果を確認。
  - nexthop が存在しない場合: `m_pendingSRv6MySIDEntries[nexthop].insert(...)` に追加して `return false`（保留）。
  - nexthop が存在するが `getNextHopId() == SAI_NULL_OBJECT_ID` の場合も同様に保留。
- `update()` (neighborhoodUpdate) L1224-1260: Neighbor ADD イベント受信時に `m_pendingSRv6MySIDEntries` を走査して保留 SID を再試行インストール。
- Neighbor DEL イベント時 L1266-1341: インストール済み MySID が削除された Neighbor を参照している場合も pending に戻す。
- evidence: `srv6orch.cpp:1511-1541`, `srv6orch.cpp:1224-1260`

### 5. 先行 SRV6_MY_SID_TABLE (APPL_DB) の書込み（fpmsyncd / Srv6Orch 経路）

- `Srv6Orch` が APPL_DB の `SRV6_MY_SID_TABLE` を消費してSAIエントリを生成する経路（`doTaskMySidTable` L2204）。
- CONFIG_DB の `SRV6_MY_SIDS` は `doTaskCfgMySidTable` L2250 が処理してDSCPモードキャッシュ(`my_sid_dscp_cfg_cache_`)に保存するのみで、SAI 直接操作はしない。
- SAI への MySID 書き込みは APPL_DB 経路 (`SRV6_MY_SID_TABLE` → `doTaskMySidTable`) に依存している。
- evidence: `srv6orch.cpp:2204-2270`, `srv6orch.cpp:2352-2390`

---

## SET 操作の推奨順序

```
# 1. ロケータを先に登録
SET SRV6_MY_LOCATORS|<locator_name>  prefix=fcbb:bbbb:20:: block_len=32 node_len=16 func_len=16 arg_len=0

# 2. カスタム VRF を使う場合のみ（action=uDT46 等）
SET VRF|<vrf_name>  ...

# 3. SRV6_MY_SIDS エントリ本体（ロケータ登録確認後）
SET SRV6_MY_SIDS|MAIN|FCBB:BBBB:20::/48   action=uN
SET SRV6_MY_SIDS|MAIN|FCBB:BBBB:20:F1::/64  action=uDT46 decap_vrf=Vrf_Customer1
```

---

## DEL 操作の安全順序

```
# 1. SRV6_MY_SIDS エントリを先に削除（bgpcfgd が FRR から通知を外す）
DEL SRV6_MY_SIDS|<locator_name>|<ip_prefix>

# 2. その後ロケータを削除（削除しても SID エントリが残ると孤立）
DEL SRV6_MY_LOCATORS|<locator_name>
```

- `locators_del_handler()` L106-114: ロケータ削除時にbgpcfgdは依存購読を解除するが、対応SIDエントリを自動削除しない。ロケータより先にSIDを削除すること。
- evidence: `managers_srv6.py:106-115`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SRV6_MY_LOCATORS SET → SRV6_MY_SIDS SET（bgpcfgd 経路） | 論理的先行（deps購読で自動再試行） | `on_deps_change` でロケータ登録後に再処理 |
| 2 | SID プレフィックスがロケータのサブネット内 | 恒久的制約（エラー時再試行不可） | 設定値修正後に再 SET |
| 3 | VRF SET → SRV6_MY_SIDS SET（VRF 要求行動、Srv6Orch 経路） | 必須先行（自動再試行なし、エラー終了） | VRF 登録後に再 SET |
| 4 | Neighbor/Nexthop → SRV6_MY_SIDS（Adj 要求行動、Srv6Orch 経路） | 保留キューで自動調停 | Neighbor ADD イベントで自動再インストール |
| 5 | SRV6_MY_SIDS DEL → SRV6_MY_LOCATORS DEL | 推奨順序（強制ではないが孤立エントリを防ぐ） | ロケータ先行削除でも SID は残留（bgpcfgd は自動削除しない） |
