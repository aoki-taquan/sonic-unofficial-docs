# VLAN_MEMBER テーブル — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (chore/q67-f-phaseD-vlan-member)

ソース: `sonic-net/sonic-swss/cfgmgr/vlanmgr.cpp`

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-swss/cfgmgr/vlanmgr.cpp`

### 1. 即時破棄 (no retry)

以下の条件ではエントリを `m_toSync` から即座に削除し、リトライしない。

| 失敗条件 | 検出箇所 | 結果 | ログ出力 |
|---------|---------|------|---------|
| `VLAN_MEMBER` キーに `Vlan` プレフィクスなし | `doVlanMemberTask` L605-609 | `erase(it)` で即破棄 | `SWSS_LOG_ERROR("Invalid key format. No 'Vlan' prefix: %s")` |
| `VLAN_MEMBER` キーにメンバーポート部分がない | `doVlanMemberTask` L621-625 | `erase(it)` で即破棄 | `SWSS_LOG_ERROR("Invalid key format. No member port is presented: %s")` |
| `tagging_mode` が `untagged`/`tagged`/`priority_tagged` 以外 | `doVlanMemberTask` L658-665 | `erase(it)` で即破棄 | `SWSS_LOG_ERROR("Wrong tagging_mode '%s' for key: %s")` |
| 不明な `operation type` | `doVlanMemberTask` L709 | `erase(it)` で即破棄 | `SWSS_LOG_ERROR("Unknown operation type %s")` |
| consumer pipe 内の重複キー | `processUntaggedVlanMembers` L584 | 当該キーをスキップ | `SWSS_LOG_WARN("Duplicate key %s found in table:%s")` |

これらは不正入力であり、リトライしても解決しない。破棄後は CONFIG_DB 側に誤エントリが残留するが
`vlanmgrd` は再通知しない（silent drop）。

### 2. 遅延リトライ (iterator increment のみ)

以下の条件では `it++; continue;` のみ行い、エントリを `m_toSync` に残す。
次回 `doTask()` 呼び出し時に再試行される。

| 失敗条件 | 検出箇所 | 結果 | ログ出力 |
|---------|---------|------|---------|
| メンバーポート (PORT/LAG) が STATE_DB に未登録 | `isMemberStateOk()` L491-514 → `doVlanMemberTask` L642-645 | `it++; continue;` で retry | `SWSS_LOG_DEBUG("%s not ready, delaying")` |
| VLAN が STATE_VLAN_TABLE に未登録 | `isVlanStateOk()` L517-531 → `doVlanMemberTask` L642-645 | `it++; continue;` で retry | `SWSS_LOG_DEBUG("%s not ready, delaying")` |
| `addHostVlanMember()` が PortChannel (LAG) レースで `false` を返す | `addHostVlanMember` L258-265 → `doVlanMemberTask` L683-686 | `it++; continue;` で retry | `SWSS_LOG_INFO("Netdevice for %s not ready, delaying")` |
| PAC 経路 (`doVlanPacVlanMemberTask`) でポート/VLAN が未 ready | `doVlanPacVlanMemberTask` L866-870 | `it++; continue;` で retry | `SWSS_LOG_DEBUG("%s not ready, delaying")` |

**`isMemberStateOk()` 判定詳細:**
- `PortChannel*` 前置の場合: `m_stateLagTable.get(alias, ...)` が成功すれば ready
- その他 (Ethernet 等): `m_statePortTable.get(alias, ...)` で `state` フィールドが存在すれば ready

**`isVlanStateOk()` 判定詳細:**
- `Vlan` 前置の場合のみ `m_stateVlanTable.get(alias, ...)` を確認。
  `Vlan` プレフィクスがなければ即 `false` (デバッグログのみ)。

### 3. kernel bridge コマンド失敗

`addHostVlanMember()` は以下のシェルコマンド列を実行する:

```
/sbin/ip link set <port> master Bridge &&
/sbin/bridge vlan del vid 1 dev <port> &&
/sbin/bridge vlan add vid <vlan_id> dev <port> [pvid untagged]
```

| 失敗ケース | コード | 挙動 |
|---------|------|------|
| PortChannel (`PortChannel*`) で `EXEC_WITH_ERROR_THROW` 例外 | `addHostVlanMember` L258-265 | `return false` → 呼び出し元で `it++` retry（LAG 削除レースを想定した意図的設計） |
| Ethernet ポートで `EXEC_WITH_ERROR_THROW` 例外 | `addHostVlanMember` L267-269 | 例外を再スロー → `vlanmgrd` プロセスクラッシュ → supervisor が再起動 |
| `removeHostVlanMember()` での `bridge vlan del` 失敗 | `removeHostVlanMember` (例外伝播) | 例外伝播 → `vlanmgrd` クラッシュ → supervisor 再起動 |

**PortChannel と Ethernet で挙動が非対称**な点に注意。
PortChannel は race condition（LAG 削除が STATE_DB 更新前に完了する場合）を想定して `return false`
にしてあり、リトライで自然解消する設計。Ethernet の場合はハードエラー扱い。

### 4. SAI 失敗（orchagent / VlanOrch 側）

`vlanmgr.cpp` は直接 SAI を呼ばない。SAI 処理は orchagent の `VlanOrch` / `PortsOrch` が
APP_DB の `VLAN_MEMBER_TABLE` を購読して実行する。
`vlanmgrd` の観点では APP_DB への書き込みが成功した時点で処理完了とみなす。

SAI 側の失敗挙動（`portsorch.cpp` / `vlanorch.cpp`）:

| 失敗ケース | 挙動 |
|---------|------|
| `sai_vlan_api->create_vlan_member()` 失敗 | `handleSaiCreateStatus(SAI_API_VLAN, status)` でリトライ可否を分類。retryable なら `it++`、非 retryable なら `erase(it)` |
| `sai_bridge_api->create_bridge_port()` 失敗（ポートの bridge port 化） | 同上 (`SAI_API_BRIDGE` 経由) |
| PORT/VLAN が orchagent 側で未解決 | `getPort()` 失敗 → `it++; continue;` で保留 |
| 不正 `tagging_mode` (orchagent 再チェック) | `SWSS_LOG_ERROR` + `erase(it)` で即破棄（vlanmgrd 通過後の二重ガード） |

### 5. warm-restart 時のリカバリ

- 起動時、`m_vlanMemberReplay` に CONFIG_DB の全 VLAN_MEMBER キーをキャッシュ
- 各エントリ処理完了時に `m_vlanMemberReplay.erase(kfvKey(t))` で消化
- `m_vlanMemberReplay` が空になったとき（`m_vlanReplay` も空であれば）:
  `WarmStart::setWarmStartState("vlanmgrd", WarmStart::REPLAYED)` → `RECONCILED` へ遷移 (L714-719)
- STATE_DB に既存の VLAN_MEMBER は `isVlanMemberStateOk()` ガードで `m_vlanMemberReplay` から削除のみ（bridge 再操作しない）

### 6. 回復シナリオまとめ

| 失敗ケース | 回復方法 | 自動か手動か |
|---------|---------|-----------|
| PORT/LAG が STATE_DB に未登録 | ポート初期化完了後に自動再試行 | 自動 |
| VLAN が STATE_VLAN_TABLE に未登録 | VLAN 作成完了後に自動再試行 | 自動 |
| PortChannel bridge コマンド失敗 (LAG レース) | 次ポーリングで自動再試行 | 自動 |
| キー形式不正 / 不正 tagging_mode | CLI で正しいエントリを再投入 | 手動 |
| Ethernet bridge コマンド失敗 | `vlanmgrd` 再起動 (supervisor) | 自動 (プロセス再起動) |
| SAI retryable 失敗 | orchagent が自動再試行 | 自動 |
| SAI 非 retryable 失敗 | エントリ破棄。APP_DB から VLAN_MEMBER を再投入 | 手動 |

<!-- /failure -->

[^src]: `sonic-swss/cfgmgr/vlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vlanmgr.cpp>
