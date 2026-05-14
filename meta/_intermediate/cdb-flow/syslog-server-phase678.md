# SYSLOG_SERVER — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`hostcfgd` が `SYSLOG_SERVER` テーブルを読み、rsyslog のリモートサーバー設定を生成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| rsyslog forwarding ルール | `port` フィールド未設定 | デフォルトポート UDP/514 を使用 | `hostcfgd.py` |
| rsyslog プロトコル | `protocol==udp` | `@<server>:<port>` 形式 (rsyslog UDP) | `hostcfgd.py` |
| rsyslog プロトコル | `protocol==tcp` | `@@<server>:<port>` 形式 (rsyslog TCP) | `hostcfgd.py` |
| VRF 設定 | `vrf==mgmt` | VRF バインドの rsyslog 設定を生成 | `hostcfgd.py` |
| ソースインターフェース | `source_interface` フィールドあり | rsyslog の source 設定を追加 | `hostcfgd.py` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `hostcfgd` は常時起動 | `SYSLOG_SERVER` テーブルは無条件購読 | `hostcfgd.py` |
| `DEVICE_METADATA.hostname` が必要 | hostname ベースのフィルタ設定に使用 | `hostcfgd.py` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `hostcfgd` | `protocol==udp` | rsyslog `@<host>` 形式 | `hostcfgd.py` |
| `hostcfgd` | `protocol==tcp` | rsyslog `@@<host>` 形式 | `hostcfgd.py` |
| `hostcfgd` | `vrf==mgmt` | VRF バインド設定を追加 | `hostcfgd.py` |
| `hostcfgd` | `vrf==default` または未設定 | デフォルト VRF で転送 | `hostcfgd.py` |
| `hostcfgd` | `source_interface` フィールドあり | rsyslog source IP 設定 | `hostcfgd.py` |
| `hostcfgd` | サーバー削除 | 対応 rsyslog 設定を削除して reload | `hostcfgd.py` |

> **スキャン証跡**: `SYSLOG_SERVER` はリモート syslog 転送先の設定。`protocol` フィールドと `vrf` フィールドの組み合わせが主要分岐。ポートデフォルト値の補完が Phase 6 相当。
