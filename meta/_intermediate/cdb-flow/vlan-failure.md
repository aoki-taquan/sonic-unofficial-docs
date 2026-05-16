# VLAN テーブル — 失敗挙動・リトライ・リカバリ (Phase D)

source: `sonic-swss/cfgmgr/vlanmgr.cpp`

## 概要

`vlanmgrd` は CONFIG_DB の `VLAN` / `VLAN_MEMBER` テーブルを購読し、
Linux カーネルブリッジと APP_DB を整合させる。
失敗時の挙動は「即時破棄」「遅延リトライ」「例外スロー」の 3 パターンに分類される。

---

## 1. 即時破棄 (no retry)

以下の条件ではエントリを `m_toSync` から即座に削除し、リトライしない。

| 条件 | ログ | コード箇所 |
|------|------|-----------|
| `VLAN` キーに `Vlan` プレフィクスなし | `SWSS_LOG_ERROR("Invalid key format. No 'Vlan' prefix: %s")` | `doVlanTask` L334-337 |
| `Vlan` 以降が数値でない | `SWSS_LOG_ERROR("Invalid key format. Not a number after 'Vlan' prefix: %s")` | `doVlanTask` L346-349 |
| `VLAN_MEMBER` キーにメンバーポート部分がない | `SWSS_LOG_ERROR("Invalid key format. No member port is presented")` | `doVlanMemberTask` L621-625 |
| `tagging_mode` が `untagged`/`tagged`/`priority_tagged` 以外 | `SWSS_LOG_ERROR("Wrong tagging_mode '%s' for key: %s")` | `doVlanMemberTask` L662-665 |
| 不明な operation type | `SWSS_LOG_ERROR("Unknown operation type %s")` | `doVlanTask` L474-477 |

- これらは不正入力であり、リトライしても解決しない。エントリを破棄することで無限ループを防ぐ。
- `VLAN` の `DEL` 操作で対象が存在しない場合も `SWSS_LOG_ERROR("%s doesn't exist")` を出力して即時削除する。

---

## 2. 遅延リトライ (iterator increment のみ、次のポーリングサイクルで再試行)

以下の条件では `it++` のみ行い、エントリを `m_toSync` に残す。次回 `doTask` 呼び出し時に再試行される。

### 2-1. MAC アドレス未確定

```
if (!isVlanMacOk()) {
    SWSS_LOG_DEBUG("VLAN mac not ready, delaying VLAN task");
    return;  // Consumer 全体を遅延
}
```

`gMacAddress` がまだ確定していない間は `doVlanTask` 全体を早期 return する。
MAC が確定次第（スイッチ起動シーケンスで設定される）自動的に処理が再開する。

### 2-2. VLAN_MEMBER: メンバーポート/VLAN がまだ ready でない

```
if (!isMemberStateOk(port_alias) || !isVlanStateOk(vlan_alias)) {
    SWSS_LOG_DEBUG("%s not ready, delaying", kfvKey(t).c_str());
    it++;
    continue;
}
```

- `isMemberStateOk`: STATE_PORT_TABLE または STATE_LAG_TABLE に対象ポートが存在するか確認
- `isVlanStateOk`: STATE_VLAN_TABLE に対象 VLAN が存在するか確認
- 条件が揃い次第（ポート初期化完了 or VLAN 作成完了後）自動的に処理される

### 2-3. PortChannel の VLAN_MEMBER 追加失敗

```cpp
// addHostVlanMember 内 (L254-269)
catch (const std::runtime_error& e) {
    if (!port_alias.compare(0, strlen(LAG_PREFIX), LAG_PREFIX))
        return false;  // PortChannel の場合は false を返す
    else
        EXEC_WITH_ERROR_THROW(cmds.str(), res);  // Ethernet は再度実行 (例外スロー)
}
```

- `addHostVlanMember` が `false` を返した場合、`doVlanMemberTask` は `it++` してリトライ待ちにする
  (`SWSS_LOG_INFO("Netdevice for %s not ready, delaying")`)
- PortChannel 削除とのレースコンディション（STATE_DB 更新前に削除が完了する場合）を想定した設計
- Ethernet ポートは例外再スローなのでリトライしない（ハードエラー扱い）

### 2-4. FDB 静的エントリ: VLAN 未作成

```cpp
if (!m_vlans.count(keys[0])) {
    SWSS_LOG_NOTICE("Vlan %s not available yet, mac %s", keys[0].c_str(), keys[1].c_str());
    it++;
    continue;
}
```

対象 VLAN が `m_vlans` に登録されるまで FDB エントリを遅延する。

---

## 3. 例外スロー (EXEC_WITH_ERROR_THROW)

以下の操作は失敗すると `std::runtime_error` をスローする。
`vlanmgrd` プロセスがクラッシュし、supervisor が再起動する。

| 操作 | コマンド例 |
|------|-----------|
| Linux bridge 初期化 (`VlanMgr::VlanMgr` コンストラクタ) | `ip link add Bridge up type bridge` など |
| `addHostVlan`: カーネル VLAN 追加 | `bridge vlan add vid <N> dev Bridge self` |
| `removeHostVlan`: カーネル VLAN 削除 | `ip link del Vlan<N>` |
| `setHostVlanAdminState`: admin_status 適用 | `ip link set Vlan<N> up/down` |
| `setHostVlanMac`: MAC 変更 | `ip link set Bridge down` → MAC 変更 → `ip link set Bridge up` |
| `removeHostVlanMember`: メンバー削除 | `bridge vlan del vid <N> dev <port>` |
| Ethernet の `addHostVlanMember` 失敗 | 2 回目の `EXEC_WITH_ERROR_THROW` 呼び出し |

- `EXEC_WITH_ERROR_THROW` は実行コマンドの終了コードが非ゼロの場合に例外をスロー
- `setHostVlanMtu` のみ例外をスローせず `false` を返す（MTU はホスト側 TODO 扱い）

---

## 4. warm-restart 時のリカバリ

- 起動時、`m_vlanReplay` / `m_vlanMemberReplay` に CONFIG_DB の全キーをキャッシュ
- 各エントリ処理完了時に `m_vlanReplay.erase(key)` で消化
- `m_vlanReplay` と `m_vlanMemberReplay` が両方空になったとき:
  `WarmStart::setWarmStartState("vlanmgrd", WarmStart::REPLAYED)` → `RECONCILED` へ遷移
- STATE_DB に既存の VLAN は `m_vlans` に登録するだけで Linux bridge を再作成しない（disruption 防止）

---

## 5. 回復シナリオまとめ

| 失敗ケース | 回復方法 | 自動か手動か |
|-----------|---------|------------|
| MAC 未確定 | MAC 確定後に自動再試行 | 自動 |
| ポート未 ready | STATE_DB 更新後に自動再試行 | 自動 |
| PortChannel レースコンディション | 次ポーリングで自動再試行 | 自動 |
| キー形式不正 | CLI で正しいキーを再投入 | 手動 |
| `ip link` 失敗 (bridge 操作) | vlanmgrd 再起動 (supervisor) | 自動 (プロセス再起動) |
| YANG `must` 違反 | 正しい値を再投入 | 手動 |

---

[^src]: `sonic-swss/cfgmgr/vlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vlanmgr.cpp>
