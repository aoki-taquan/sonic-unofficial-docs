# SNMP_AGENT_ADDRESS_CONFIG — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

- `agent_ip` (key): `inet:ip-address`（IPv4 / IPv6）
- `port` (key): `inet:port-number` または空文字（デフォルト 161）
- `vrf_name` (key): 文字列（空文字 / `mgmt` / `Vrf[a-zA-Z0-9_-]+`）

## Phase 2: per-value 挙動

### `port` 値別挙動
| 値 | 挙動 |
|----|------|
| 空文字 `""` | YANG `pattern ''` 許容。snmpd.conf では `udp:<ip>:161` のデフォルトポートで展開（テンプレート側が処理）。 |
| `161` | 標準 SNMP ポート。 |
| 他の port-number | 非標準ポートで snmpd がリッスン。ファイアウォール設定の調整が必要。 |

### `vrf_name` 値別挙動
| 値 | 挙動 |
|----|------|
| 空文字 `""` | default VRF。全インタフェースでリッスン。 |
| `mgmt` | 管理 VRF でリッスン。snmpd.conf の `agentaddress` に `@mgmt` が付与。 |
| `Vrf<name>` | 指定 VRF でリッスン。VRF が実際に存在しない場合は snmpd 起動後にリッスン失敗（CONFIG_DB では検知不可）。 |

### エントリなしの場合
| 条件 | 挙動 |
|------|------|
| SNMP_AGENT_ADDRESS_CONFIG が空 | テンプレートが `agentAddress udp:161` / `agentAddress udp6:161` をデフォルト出力。 |

## Phase 3: ソース確認

- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2:29-33`: エントリがある場合はループで `agentAddress {{ protocol(agentip) }}:[{{ agentip }}]{% if vrf %}@{{ vrf }}{% endif %}{% if port %}:{{ port }}{% endif %}`。エントリなしは `udp:161` / `udp6:161`。
- 変更反映: `docker-snmp` コンテナ再起動時のみ。

## enum 有無

- `port`: enum なし（`inet:port-number` または空文字）
- `vrf_name`: enum なし（文字列パターン制約）
