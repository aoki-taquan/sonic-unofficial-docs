# SNMP_AGENT_ADDRESS_CONFIG — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`snmp-config` サービス (`sonic-snmpagent`) が `SNMP_AGENT_ADDRESS_CONFIG` テーブルを読み、snmpd の設定ファイルを生成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| snmpd `agentAddress` 設定 | `ip` + `port` + `interface` 組み合わせ | `agentAddress udp:<ip>:<port>` または VRF 対応形式 | `snmp_config` |
| VRF バインド | `interface` フィールドが mgmt VRF 名 | `agentAddress udp:<ip>:<port>@<vrf>` 形式で生成 | `snmp_config` |

**CONFIG_DB 内フィールド間の自動付与なし**: テーブル内フィールドは snmpd agentAddress 行の直接マッピング。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `sonic-snmpagent` サービスが有効 | `SNMP_AGENT_ADDRESS_CONFIG` を購読する snmp-config が動作 | systemd service |
| `SNMP_AGENT_ADDRESS_CONFIG` エントリなし | snmpd はデフォルトの agentAddress を使用 | snmpd デフォルト |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `snmp-config` | `interface` フィールドあり | VRF バインド形式の agentAddress 生成 | `snmp_config` |
| `snmp-config` | `interface` フィールドなし | シンプルな `udp:<ip>:<port>` 形式 | `snmp_config` |
| `snmp-config` | `port` フィールドあり | カスタムポート使用 (デフォルト 161) | `snmp_config` |
| `snmp-config` | エントリ削除時 | snmpd 設定から対応 agentAddress 行を削除して reload | `snmp_config` |

> **スキャン証跡**: `SNMP_AGENT_ADDRESS_CONFIG` は snmpd のリッスンアドレス/ポート/VRF を設定するシンプルテーブル。CONFIG_DB 内の自動派生なし。
