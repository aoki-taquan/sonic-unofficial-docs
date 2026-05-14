# SNMP — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`snmp-config` サービスが `SNMP` グローバルテーブルを読み、snmpd の設定ファイルを生成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| snmpd community 文字列 | `SNMP_COMMUNITY` エントリ存在 | `rocommunity` / `rwcommunity` 行を生成 | `snmp_config` |
| snmpd `sysName` | `DEVICE_METADATA.hostname` 参照 | システム名を snmpd に設定 | `snmp_config` |
| snmpd `sysLocation` | `SNMP.sysLocation` あり | `sysLocation` を設定 | `snmp_config` |
| snmpd `sysContact` | `SNMP.sysContact` あり | `sysContact` を設定 | `snmp_config` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `sonic-snmpagent` サービスが有効 | `SNMP` テーブルを購読する snmp-config が動作 | systemd service |
| `SNMP.traps==enabled` | snmpd の trap 送信を有効化 | `snmp_config` |
| `SNMP.traps==disabled` | snmpd の trap 送信を無効化 | `snmp_config` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `snmp-config` | `traps==enabled` | snmpd に `trap2sink` 設定を生成 | `snmp_config` |
| `snmp-config` | `traps==disabled` | `trap2sink` 行を生成しない | `snmp_config` |
| `snmp-config` | `sysLocation` フィールドあり | `syslocation <value>` を snmpd.conf に追加 | `snmp_config` |
| `snmp-config` | `sysContact` フィールドあり | `syscontact <value>` を snmpd.conf に追加 | `snmp_config` |
| `snmp-config` | `SNMP_COMMUNITY` テーブルエントリ変化 | snmpd 設定ファイルを再生成して reload | `snmp_config` |

> **スキャン証跡**: `SNMP` テーブルはグローバル SNMP 設定。`traps` フィールドで trap 設定の有無を分岐。CONFIG_DB 内フィールド間の自動派生なし。
