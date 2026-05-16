# SNMP テーブル — Phase H: プラットフォーム差分

## 調査対象ソース

- `sonic-net/sonic-buildimage` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
  - `dockers/docker-snmp/supervisord.conf.j2` — snmp-subagent 起動コマンド分岐
  - `dockers/docker-snmp/snmpd.conf.j2` — agentAddress コメント (multi-asic / single-asic)
  - `dockers/docker-snmp/sysDescription.j2` — hwsku 埋め込み
- `sonic-net/sonic-snmpagent` (HEAD)
  - `src/sonic_ax_impl/__main__.py` — `--enable_dynamic_frequency` フラグ処理
  - `src/sonic_ax_impl/mibs/ietf/rfc4292.py` — multi-asic 経路テーブルフィルタ
  - `src/sonic_ax_impl/mibs/ietf/rfc1213.py` — multi-asic ARP テーブル取得
  - `src/sonic_ax_impl/mibs/vendor/cisco/` — Cisco 固有 MIB 実装
  - `src/sonic_ax_impl/mibs/vendor/dell/force10.py` — Dell Force10 固有 MIB 実装

## プラットフォーム識別方法

SNMP スタック (`docker-snmp` + `sonic-snmpagent`) のプラットフォーム差分は  
**DEVICE_METADATA.localhost.switch_type** (CONFIG_DB) と  
**multi-ASIC / single-ASIC 構成** (sonic_py_common.multi_asic 判定) の 2 軸で決まる。

ACL/SWSS と異なり、`platform` 環境変数（ASIC ベンダー文字列）による静的分岐は SNMP スタックに存在しない。

---

## 差異 1: snmp-subagent 起動コマンド (switch_type == 'chassis-packet')

`supervisord.conf.j2` L53–57

| 条件 | snmp-subagent 起動コマンド | 効果 |
|------|--------------------------|------|
| `DEVICE_METADATA.localhost.switch_type == 'chassis-packet'` | `python3 -m sonic_ax_impl --enable_dynamic_frequency` | MIB 更新頻度の動的調整を有効化 |
| それ以外 (npu / voq / fabric / dpu 等) | `python3 -m sonic_ax_impl` | 固定頻度 (`DEFAULT_UPDATE_FREQUENCY`) で更新 |

`--enable_dynamic_frequency` フラグが有効の場合、`MIBTable` は MIB updater のアイドル時間を監視し、  
更新負荷に応じてポーリング周期を動的に変化させる (`ax_interface/mib.py` L69)。  
chassis-packet スイッチでは ASIC 数・IF 数が多くなるため、このフラグで CPU 使用率を抑制する。

`DEVICE_METADATA.localhost` が CONFIG_DB に存在しない場合、`supervisord.conf.j2` のテンプレート展開が  
KeyError で失敗し、docker-snmp コンテナが起動しない（全プラットフォーム共通の前提条件）。

---

## 差異 2: multi-ASIC プラットフォームでの agentAddress バインド先コメント

`snmpd.conf.j2` L16–17

```
# Listen for connections on all ip addresses, including eth0, ipv4 lo for multi-asic platform
# Listen on managment and loopback0 ips for single asic platform
```

コードとしての分岐はなく、`SNMP_AGENT_ADDRESS_CONFIG` の内容に従う（差異 3 参照）。  
multi-ASIC 構成では全 IP（eth0 含む）にバインドする運用が推奨されるが、強制ではない。

---

## 差異 3: multi-ASIC での snmp-subagent 経路テーブルフィルタ (rfc4292)

`src/sonic_ax_impl/mibs/ietf/rfc4292.py` L56–93

| 構成 | inetCidrRouteTable の動作 |
|------|--------------------------|
| single-ASIC | `front_ns` が空リスト → 全 namespace (デフォルト namespace のみ) の APP_DB から経路取得 |
| multi-ASIC | `multi_asic.get_all_namespaces()['front_ns']` でフロントエンド ASIC namespace を取得し、BackEnd ASIC の namespace をスキップ。内部ポートチャネル (`INTERNAL_PORT` role) を MIB から除外 |

multi-ASIC 構成では BackEnd ASIC の内部経路が inetCidrRouteTable に混入しないよう  
`is_port_channel_internal()` / `PORT_ROLE == INTERNAL_PORT` チェックで除外する。  
single-ASIC では `front_ns` が空のため、このフィルタは実質ノーオペレーション。

---

## 差異 4: multi-ASIC での ARP テーブル取得 (rfc1213)

`src/sonic_ax_impl/mibs/ietf/rfc1213.py` L113–115

| 構成 | atTable (ARP) の取得元 |
|------|----------------------|
| single-ASIC | デフォルト namespace の NEIGH_TABLE のみ参照 |
| multi-ASIC | ホスト kernel の ARP テーブルと各 namespace の NEIGH_TABLE を合算。eth0 (management) は namespace ごとに除外 (`L88` で名前付き条件) |

---

## 差異 5: sysDescr — hwsku 埋め込み (全プラットフォーム共通だが機器依存)

`sysDescription.j2`

```
SONiC Software Version: SONiC.{{ build_version }} - HwSku: {{ DEVICE_METADATA['localhost']['hwsku'] }} - Distribution: Debian {{ debian_version }} - Kernel: {{ kernel_version }}
```

`DEVICE_METADATA.localhost.hwsku` が CONFIG_DB に存在しない場合は `sysDescr` が KeyError で空になる可能性がある。  
hwsku の値は機器固有で、プラットフォーム (ASIC ベンダー) によって異なる文字列が入る。

---

## 差異 6: ベンダー固有 MIB サブエージェント (sonic-snmpagent)

sonic-snmpagent は `SonicMIB` を `ax_interface.Agent` に登録するが、以下のベンダー固有 MIB は  
すべての sonic デプロイメントで一律登録される（プラットフォーム条件なし）。

| MIB モジュール | OID prefix | 対象ベンダー表記 | 実装 |
|--------------|------------|---------------|------|
| `ciscoPfcExtMIB` | (Cisco enterprise) | Cisco PFC 統計 | `mibs/vendor/cisco/ciscoPfcExtMIB.py` |
| `ciscoSwitchQosMIB` | (Cisco enterprise) | Cisco QoS キューカウンタ | `mibs/vendor/cisco/ciscoSwitchQosMIB.py` |
| `ciscoEntityFruControlMIB` | (Cisco enterprise) | PSU/電源管理 | `mibs/vendor/cisco/ciscoEntityFruControlMIB.py` |
| `bgp4` (Cisco) | (Cisco enterprise) | BGP4 MIB | `mibs/vendor/cisco/bgp4.py` |
| `SSeriesMIB` (Dell Force10) | `.1.3.6.1.4.1.6027.3.10.1.2.9` | CPU/メモリ利用率 | `mibs/vendor/dell/force10.py` |

これらは YANG / CONFIG_DB の `SNMP` テーブルとは直接連携しない。  
snmpd に AgentX サブエージェントとして接続し、各 MIB OID に対応する値を STATE_DB / COUNTERS_DB から提供する。  
**hardware プラットフォームに関係なく全デプロイメントで登録される** — Cisco 機器以外でも Cisco MIB が応答可能な状態になる点に注意。

---

## 差異 5: MGMT_VRF 環境での agentAddress / trapsink VRF バインド

### agentAddress

`snmpd.conf.j2` L28–29 に基づき、`SNMP_AGENT_ADDRESS_CONFIG` の `vrf` フィールドが設定されている場合:

```
agentAddress <protocol>:[<ip>]@<vrf>:<port>
```

| `vrf` フィールド値 | 生成結果 | 効果 |
|------------------|---------|------|
| 空 / 未設定 | `agentAddress udp:[<ip>]:<port>` | グローバルルーティングテーブルでバインド |
| `"mgmt"` | `agentAddress udp:[<ip>]@mgmt:<port>` | MGMT_VRF の netns でバインド。管理 IF 専用 |

MGMT_VRF が有効な環境 (`MGMT_VRF_CONFIG.mgmtVrfEnabled=true`) での推奨構成。SNMP アクセスをデータプレーンから分離可能。

### trapsink の VRF バインド

`snmpd.conf.j2` L148–170 に基づき、`SNMP_TRAP_CONFIG.<version>TrapDest.vrf` が `"None"` 以外の場合:

```
trapsink <ip>:<port>%<vrf> <community>
```

| `vrf` フィールド値 | 生成結果 |
|------------------|---------|
| `"None"` (文字列) | `trapsink <ip>:<port> <community>` (VRF なし) |
| `"mgmt"` など | `trapsink <ip>:<port>%mgmt <community>` |

---

## 差異 6: SmartSwitch DPU (switch_type == 'dpu') の挙動

`supervisord.conf.j2` L53–57

DPU ノードは `switch_type = 'dpu'` で識別される。`chassis-packet` 分岐に該当しないため、snmp-subagent は `--enable_dynamic_frequency` なしの固定頻度で起動する。

| `switch_type` | 動作 |
|---------------|------|
| `dpu` | 固定頻度 (`DEFAULT_UPDATE_FREQUENCY`) |
| `chassis-packet` | 動的頻度 (`--enable_dynamic_frequency`) |
| `npu` / `voq` / `fabric` | 固定頻度 |

DPU でも `DEVICE_METADATA.localhost` の存在が必須。欠如時は KeyError でコンテナ起動失敗。

---

## スキャン証跡

- `supervisord.conf.j2` 全行精読 (2026-05-15)
- `snmpd.conf.j2` L1–34, L140–175 精読 (multi-asic コメント・VRF バインド確認)
- `sysDescription.j2` 全行精読
- `sonic_ax_impl/__main__.py` `arg_parser.py` `main.py` 精読
- `mibs/ietf/rfc4292.py` L1–95 精読
- `mibs/ietf/rfc1213.py` L55–135 精読
- `mibs/vendor/cisco/*.py` 全ファイル確認
- `mibs/vendor/dell/force10.py` 確認
- `ax_interface/mib.py` L30–340 (enable_dynamic_frequency ロジック) 確認
- `hostcfgd` SNMP 関連ハンドラ確認 (2026-05-16)
