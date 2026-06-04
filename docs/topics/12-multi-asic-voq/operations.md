---
title: 運用
description: 運用 — Multi-ASIC / VOQ chassis の運用調査は、pizza-box と比べて「どこから見るか」が増えます。supervisor
  から見るか、line card から見るか、ASIC namespace から見るか。ここでは典型的な確認順を整理します。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show queue
  - show platform
  - show interfaces
  - show ip
  - clear
  - config bgp
  - show bgp
  config_db:
  - SNMP
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_AGGREGATE_ADDRESS
  - BGP_PEER_GROUP
  - BGP_NEIGHBOR_AF
  yang:
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
  - sonic-bgp-aggregate-address
  - sonic-bgp-sentinel
---

# 運用

[Multi-ASIC](../../reference/glossary.md#term-multi-asic) / [VOQ](../../reference/glossary.md#term-voq) chassis の運用調査は、pizza-box と比べて「どこから見るか」が増えます。supervisor から見るか、line card から見るか、[ASIC](../../reference/glossary.md#term-asic) namespace から見るか。ここでは典型的な確認順を整理します。

## どこから見るかの判定

| 観点 | 入口 |
|------|------|
| 物理 inventory（line card / fabric / PSU / fan） | supervisor の PMON / Entity MIB |
| line card 個別の port up/down、route、neighbor | line card host の `show` に `--namespace asic0` など |
| ASIC 内部 counter（queue、buffer、PG） | line card の ASIC namespace |
| VOQ counter（ingress 側 per-system-port queue） | line card の [COUNTERS_DB](../../reference/glossary.md#term-counters_db) を aggregate |
| chassis 全体の system port、line card 状態 | supervisor の Chassis DB |

CLI 上は `show platform inventory` / `show chassis modules` などが supervisor で chassis 全体を見せ、line card 内では従来の `show interfaces` 系が namespace を集約して見せます。

### supervisor からの典型 show 出力

```bash
admin@sup0:~$ show chassis modules status
       Name         Description    Physical-Slot   Oper-Status     Admin-Status
-----------  ------------------  ---------------  ------------  ---------------
LINE-CARD0   Cisco-8800-LC-48H            1            Online              up
LINE-CARD1   Cisco-8800-LC-48H            2            Online              up
LINE-CARD2   Cisco-8800-LC-48H            3        Offline (boot)            up
FABRIC-CARD0 Cisco-8800-FC                4            Online              up
FABRIC-CARD1 Cisco-8800-FC                5            Online              up
SUPERVISOR0  Cisco-8800-RP                0            Online              up

admin@sup0:~$ show chassis system-ports | head -8
              System Port Name      Port Id   Switch Id   Core   Core Port  Speed
-----------------------------------  --------  ----------  -----  ---------  -------
LINE-CARD0|asic0|Ethernet0                256          0      0          1     400G
LINE-CARD0|asic0|Ethernet8                257          0      0          2     400G
LINE-CARD1|asic1|Ethernet0                512          2      0          1     400G
...
```

`Oper-Status` が `Offline` のまま戻らない line card は、まず supervisor `/var/log/syslog` の `chassisd` / `chassis_db_init` のエラーを追います。`Online (boot)` で長時間止まる場合は line card 側 `bgpd`/`swss` 起動が [SAI](../../reference/glossary.md#term-sai) 初期化で詰まっている可能性があり、line card にログインして `docker ps` と `journalctl -u swss@asic0` を見ます。

### line card からの典型 show 出力

```bash
admin@lc0:~$ show interfaces status --namespace asic0 | head -5
Interface       Lanes        Speed   MTU  FEC   Alias    Vlan    Oper    Admin    Type
-----------  ------------  -------  ----  ----  -------  ------  ------  -------  ------
Ethernet0    8,9,10,11      400G   9100  rs    etp1     routed     up       up    QSFP-DD
Ethernet8    12,13,14,15    400G   9100  rs    etp2     routed     up       up    QSFP-DD

admin@lc0:~$ show ip bgp summary --namespace asic0
BGP router identifier 10.0.0.1, local AS number 65100
...
Neighbor        V    AS  MsgRcvd  MsgSent  Up/Down   State/PfxRcd
10.0.0.0        4 65100      120      118  00:55:12  256
```

`--namespace` 省略時は line card 上の全 ASIC namespace を集約してくれますが、特定 ASIC の問題を切り分けるときは `--namespace asicN` で個別に当たります。

## Aggregate VOQ Counter

`aggregate-voq-counters-in-sonic` [HLD](../../reference/glossary.md#term-hld) は、VOQ counter が ASIC namespace ごとに分散している問題を解決します。VOQ は ingress 側で egress system port ごとに存在するため、「ある egress system port の輻輳」を知りたいときに、全 ingress line card の COUNTERS_DB を横断する必要があります。

集約は以下の流れで行います。

1. 各 line card の COUNTERS_DB が per-sys-port VOQ counter を持つ。
2. supervisor 側の aggregator が全 line card の COUNTERS_DB を購読する。
3. egress system port 単位での合計値を Chassis DB 側に書き込む。
4. CLI `show queue` 系が、aggregator 出力を整形して提示する。

運用者が押さえるのは「単一 line card の counter だけ見ても egress 系の輻輳は見えない」「supervisor 側の aggregate 値が遅延を持つ可能性がある」の 2 点です。

### VOQ counter の確認コマンド

```bash
admin@sup0:~$ show queue counters --voq 'LINE-CARD1|asic0|Ethernet0'
For system port LINE-CARD1|asic0|Ethernet0:
   Queue    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
--------  --------------  ---------------  -----------  ------------
   UC0          1,204,500    62,308,000             0             0
   UC1                  0             0             0             0
   ...
   UC7             18,402         945,000         1,230        62,000

admin@sup0:~$ show queue watermark --voq 'LINE-CARD1|asic0|Ethernet0'
   Queue    Current (bytes)    Peak (bytes)
--------  -----------------  --------------
   UC0              0             1,572,864
   UC7              0               294,912
```

`Drop/pkts` が UC7 のみで増える場合は、ingress 側のどの line card から流れているかを `show queue counters --json` の per-ingress 内訳で特定します。aggregator が止まると counter が古いまま固まるため、supervisor 側 `docker logs chassisd` と Chassis DB の `SYSTEM_PORT_TABLE` 更新時刻を `redis-cli -h <chassisdb> -p 6380 -n 13 hget SYSTEM_PORT_TABLE:... last_update` で確認します。

### DB 参照

| DB | キー例 | 役割 |
|---|---|---|
| `COUNTERS_DB` (line card) | `COUNTERS:oid:0x15...` | per-sys-port VOQ の生 counter |
| `CHASSIS_APP_DB` (supervisor) | `SYSTEM_PORT_TABLE:LINE-CARD1\|asic0\|Ethernet0` | aggregator 出力 |
| `CHASSIS_STATE_DB` (supervisor) | `CHASSIS_MODULE_TABLE:LINE-CARD0` | module up/down 状態 |

DB スキーマは原典の [Aggregate VOQ Counters HLD](../../internals/aggregate-voq-counters-in-sonic.md) と各 line card の `redis-cli -n 2 keys 'COUNTERS:*'` 出力で確認します。

## PMON for Multi-ASIC / Chassis

`platform-monitor-design-for-multi-asic-platforms` および `platform-monitor-requirement-for-chassis-subsystem` は、PMON が複数 ASIC / 複数 line card 環境でどう動くかを定義します。

- Multi-ASIC pizza-box では PMON は 1 つの host で動き、ASIC それぞれの transceiver / DOM / thermal を集約します。
- VOQ chassis では PMON は supervisor と各 line card に独立して存在し、supervisor PMON が fabric / chassis 共通の sensor を、line card PMON が自分の transceiver / 内部 sensor を担当します。
- chassis subsystem 要件として、line card 抜き差し、PSU、fan tray、fabric card の hotswap 検出が PMON 経由で `STATE_DB` および Chassis DB に反映されます。

## Entity MIB / Entity Sensor MIB

`sonic-entity-mib-and-entity-sensor-mib-extension` は、chassis を含む物理コンポーネントツリーを [SNMP](../../reference/glossary.md#term-snmp) で公開するための entityPhysical / entitySensor 拡張を定義します。

- chassis -> linecard -> ASIC -> port のような階層を `entPhysicalTable` で表現します。
- thermal / voltage / current / fan speed を `entSensorTable` 系で提供します。

運用上、NMS から chassis 全体を 1 つの SNMP target として見たいときに必要な仕組みで、line card 個別の SNMP target を増やさずに済みます。

### PMON / chassis 状態の確認コマンド

```bash
admin@sup0:~$ show platform inventory
Name          Product ID         Serial Number       Part Number    Software Version
------------  -----------------  ------------------  -------------  -----------------
Chassis       8808                FCH2334V0AB         800-110000-01  ...
LINE-CARD0    8800-LC-48H         FCH2336V0CD        800-110001-01  20250408.49
FABRIC-CARD0  8800-FC             FCH2336V0EF        800-110002-01  20250408.49
PSU0          ...

admin@lc0:~$ show platform temperature
        Sensor              Temperature    High TH    Low TH    Crit High TH    Crit Low TH    Warning
------------------------  -------------  ---------  --------  --------------  -------------  ---------
CPU On-board                       42.0       85.0       N/A            95.0           N/A          False
ASIC0 Temp                         63.5       95.0       N/A           105.0           N/A          False
Optics Module 1                    52.0       75.0       N/A            85.0           N/A          False
```

`Warning=True` が継続する thermal は、`thermalctld` ログ（`docker logs pmon` の `thermalctld` プレフィクス）で fan speed override 履歴を追います。chassis では fan が supervisor 側 PSU/fan tray にしかないケースが多く、line card 上の `show platform fan` が `N/A` でも異常ではありません。

### Entity MIB の SNMP walk 例

```bash
$ snmpwalk -v2c -c public sup0 entPhysicalDescr | head
SNMPv2-SMI::mib-2.47.1.1.1.1.2.1 = STRING: "Cisco 8808 Chassis"
SNMPv2-SMI::mib-2.47.1.1.1.1.2.2 = STRING: "Linecard slot 1: 8800-LC-48H"
SNMPv2-SMI::mib-2.47.1.1.1.1.2.3 = STRING: "Linecard slot 2: 8800-LC-48H"
SNMPv2-SMI::mib-2.47.1.1.1.1.2.10 = STRING: "ASIC 0 on Linecard slot 1"
```

`entPhysicalContainedIn` で chassis -> linecard -> ASIC -> port の親子関係が辿れます。NMS で「どの port がどの ASIC に属するか」を機械的に列挙したいときの入口です。

## 典型的な調査フロー

問題タイプ別の入口の例:

1. **特定の egress port で drop が見える**: line card 側 `show interfaces counters` で drop 種別を確認し、ingress 側全 line card の VOQ counter を aggregate で確認、fabric port の link monitoring を見る。
2. **route が片方向しか上がっていない**: line card ごとの [BGP](../../reference/glossary.md#term-bgp) namespace で neighbor 状態確認、Chassis DB の system port presence、`show ip route --namespace` で各 ASIC namespace を順に見る。
3. **新しい line card が立ち上がらない**: supervisor PMON で module 検出ログ、Chassis DB の line card 登録、line card 起動ログ（sub_role / hwsku 取得失敗を検索）。
4. **fabric link error**: supervisor PMON で fabric card 状態、`show fabric` 系コマンド、line card 側 fabric port counter。

### 異常検出と典型ログ

`/var/log/syslog` で頻出する文字列の意味:

| ログ片 | 意味 | 一次対応 |
|---|---|---|
| `chassisd: ... module LINE-CARDx state transition: Online -> Offline` | line card が落ちた | line card host にログイン、`journalctl -b -1` で再起動原因 |
| `swss#orchagent: ... Failed to create system port` | system port 作成失敗 | Chassis DB の `SYSTEM_PORT_TABLE` 重複、`asic_id` 衝突を疑う |
| `syncd#syncd: ... SAI_STATUS_TABLE_FULL` | per-ASIC リソース枯渇 | 別 ASIC に分散、`crm` で table 利用率確認 |
| `pmon#xcvrd: ... SFP <N> not present` | port presence GPIO 反転 | 該当 ASIC namespace で `show interfaces transceiver presence` |
| `fabricmgrd: ... fabric port <N> down` | fabric port エラー | supervisor `show fabric reachability`、両側 ASIC の link counter |

### 復旧コマンドの目安

| 状況 | コマンド | 注意 |
|---|---|---|
| line card 再起動 | supervisor で `sudo config chassis modules shutdown LINE-CARDx` → `startup` | shutdown 中はトラフィック転送停止 |
| ASIC namespace のサービス再起動 | line card で `sudo systemctl restart swss@asicN` | 該当 ASIC 配下の port が一時 down |
| PMON 単独再起動 | `sudo systemctl restart pmon` | sensor 値が一時的に N/A になる |
| VOQ counter のクリア | `sonic-clear queuecounters` を全 line card で実行 | aggregator 側は再収集まで時差あり |

破壊的操作（`config chassis modules shutdown` を本番中に）は HA ペアの片側に限定して順次行うのが定石です。

### よくある事故パターン

1. **全 line card 同時 reboot** — supervisor で `config reload -y` を流すと全 line card 側 [SONiC](../../reference/glossary.md#term-sonic) が再展開されることがあり、chassis 全断になる。事前にメンテナンス窓を取り、必要なら line card ごとに区切って流す。
2. **fabric card の片系抜き差し時の輻輳** — 片系 fabric だけで sustain できないトラフィック量で fabric を抜くと VOQ ingress 側で詰まる。`show queue counters` の上昇を見ながら段階的に行う。
3. **namespace を間違えた `config save`** — line card 側で `config save` を `--namespace` 指定せずに流すと、host config のみ更新され ASIC namespace の差分が消える。
4. **Chassis DB の port-channel ID 衝突** — 大規模 chassis で port-channel ID を line card で独立して採番すると衝突する。supervisor 側の chassis-wide 採番ポリシーを使う。
5. **PMON の sensor poll 周期と alert ストーム** — 短い poll 周期と低い threshold の組合せで、過渡的 spike で大量 alert が流れる。`thermal_policy.json` の hysteresis 設定を確認する。

### 監視メトリクスのおすすめ

| メトリクス | 取得元 | しきい値の目安 |
|---|---|---|
| line card oper-status | `CHASSIS_STATE_DB` `CHASSIS_MODULE_TABLE` | `Offline` が 60 秒以上継続 |
| system port VOQ drop | aggregator 出力 (`CHASSIS_APP_DB`) | per-queue で 1pps 以上が継続 |
| fabric port utilization | line card `show fabric counters` | 80% 以上で警告 |
| ASIC temperature | `STATE_DB` `TEMPERATURE_INFO` | センサー仕様の High TH の 90% |
| PSU input voltage | `STATE_DB` `PSU_INFO` | 公称値の ±10% |

### 他章への誘導

- VOQ chassis のアーキテクチャや fabric の仕組みは [architecture](./architecture.md) と [advanced](./advanced.md) を参照。
- PMON / SNMP の細部は [Platform / Port / Optics の運用](../14-platform-port-optics/operations.md) と重複する部分があり、装置 health 全般は同章を入口にすると整理しやすいです。
- 初期セットアップ手順は [setup](./setup.md) を参照。

## 関連ページ

- [Aggregate VOQ Counters](../../internals/aggregate-voq-counters-in-sonic.md)
- [PMON for Multi-ASIC Platforms](../../system/platform-monitor-design-for-multi-asic-platforms.md)
- [PMON for Chassis Subsystem](../../system/platform-monitor-requirement-for-chassis-subsystem.md)
- [Entity MIB / Entity Sensor MIB 拡張](../../system/sonic-entity-mib-and-entity-sensor-mib-extension.md)

<!-- glossary-links-injected: 5c9b3765d470 -->
