---
title: QoS / Buffer の設定
description: QoS / Buffer の設定 — 設定は「pool / profile を作る → port に classification を当てる
  → queue に scheduler / WRED を当てる → 必要なら PFC / PFCWD を有効化」の順で組むのが筋が良いです。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/config-buffer.md
- docs/reference/cli/config-qos.md
- docs/reference/cli/config-pfcwd.md
- docs/reference/config-db/buffer-pool.md
- docs/reference/config-db/buffer-profile.md
- docs/reference/config-db/buffer-pg.md
- docs/reference/config-db/buffer-queue.md
- docs/reference/config-db/queue.md
- docs/reference/config-db/scheduler.md
- docs/reference/config-db/wred-profile.md
- docs/reference/config-db/dscp-to-tc-map.md
- docs/reference/config-db/tc-to-queue-map.md
- docs/reference/config-db/port-qos-map.md
- docs/reference/config-db/pfc-priority-to-priority-group-map.md
- docs/reference/config-db/pfc-wd.md
- docs/reference/yang/sonic-buffer-pool.md
- docs/reference/yang/sonic-buffer-profile.md
- docs/reference/yang/sonic-buffer-pg.md
- docs/reference/yang/sonic-buffer-queue.md
- docs/reference/yang/sonic-queue.md
- docs/reference/yang/sonic-scheduler.md
- docs/reference/yang/sonic-pfcwd.md
- docs/reference/yang/sonic-port-qos-map.md
- docs/reference/yang/sonic-tc-queue-map.md
- docs/reference/yang/sonic-wred-profile.md
- docs/reference/yang/sonic-dscp-tc-map.md
- docs/reference/yang/sonic-pfc-priority-priority-group-map.md
related:
  cli:
  - config buffer
  - config qos
  - config pfcwd
  - show queue
  - show pfc
  - config interface
  - show interfaces
  config_db:
  - SCHEDULER
  - PORT_QOS_MAP
  - BUFFER_POOL
  - BUFFER_PROFILE
  - QUEUE
  - DSCP_TO_TC_MAP
  - TC_TO_QUEUE_MAP
  yang:
  - sonic-buffer-profile
  - sonic-buffer-pool
  - sonic-pfcwd
  - sonic-buffer-pg
  - sonic-buffer-queue
  - sonic-queue
  - sonic-scheduler
---

# QoS / Buffer の設定

設定は「pool / profile を作る → port に classification を当てる → queue に scheduler / [WRED](../../reference/glossary.md#term-wred) を当てる → 必要なら [PFC](../../reference/glossary.md#term-pfc) / PFCWD を有効化」の順で組むのが筋が良いです。テンプレートは多くのプラットフォームで `buffers.json.j2` / `qos.json.j2` として配布されていて、まずはそれを読み、必要なところだけ patch するのが現実解です。

## CLI から触れる範囲

- [`config buffer`](../../reference/cli/config-buffer.md) — buffer pool / profile / PG / queue の追加・削除と、shared headroom などの switch 全体属性。
- [`config qos`](../../reference/cli/config-qos.md) — `qos reload` で `/etc/sonic/qos.json` の再展開、`qos clear`、map 系の操作。
- [`config pfcwd`](../../reference/cli/config-pfcwd.md) — PFCWD の start/stop/interval/action とポーリング設定。

[CONFIG_DB](../../reference/glossary.md#term-config_db) を直接編集する場合は次のテーブル群です。

| 目的 | テーブル | [YANG](../../reference/glossary.md#term-yang) |
|------|----------|------|
| Buffer pool 定義 | [`BUFFER_POOL`](../../reference/config-db/buffer-pool.md) | [sonic-buffer-pool](../../reference/yang/sonic-buffer-pool.md) |
| Buffer profile | [`BUFFER_PROFILE`](../../reference/config-db/buffer-profile.md) | [sonic-buffer-profile](../../reference/yang/sonic-buffer-profile.md) |
| Ingress PG 割当 | [`BUFFER_PG`](../../reference/config-db/buffer-pg.md) | [sonic-buffer-pg](../../reference/yang/sonic-buffer-pg.md) |
| Egress queue 割当 | [`BUFFER_QUEUE`](../../reference/config-db/buffer-queue.md) | [sonic-buffer-queue](../../reference/yang/sonic-buffer-queue.md) |
| Queue × scheduler/WRED | [`QUEUE`](../../reference/config-db/queue.md) | [sonic-queue](../../reference/yang/sonic-queue.md) |
| [Scheduler](../../reference/glossary.md#term-scheduler) / shaping | [`SCHEDULER`](../../reference/config-db/scheduler.md) | [sonic-scheduler](../../reference/yang/sonic-scheduler.md) |
| WRED / ECN | [`WRED_PROFILE`](../../reference/config-db/wred-profile.md) | [sonic-wred-profile](../../reference/yang/sonic-wred-profile.md) |
| [DSCP](../../reference/glossary.md#term-dscp)→TC | [`DSCP_TO_TC_MAP`](../../reference/config-db/dscp-to-tc-map.md) | [sonic-dscp-tc-map](../../reference/yang/sonic-dscp-tc-map.md) |
| TC→queue | [`TC_TO_QUEUE_MAP`](../../reference/config-db/tc-to-queue-map.md) | [sonic-tc-queue-map](../../reference/yang/sonic-tc-queue-map.md) |
| ポート単位の map 適用 | [`PORT_QOS_MAP`](../../reference/config-db/port-qos-map.md) | [sonic-port-qos-map](../../reference/yang/sonic-port-qos-map.md) |
| PFC priority→PG | [`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP`](../../reference/config-db/pfc-priority-to-priority-group-map.md) | [sonic-pfc-priority-priority-group-map](../../reference/yang/sonic-pfc-priority-priority-group-map.md) |
| PFCWD | [`PFC_WD`](../../reference/config-db/pfc-wd.md) | [sonic-pfcwd](../../reference/yang/sonic-pfcwd.md) |

## シナリオ 1: 最小構成 — lossy のみ ToR

「100G lossy だけのアクセス ToR」を想定して、queue 0 を strict、queue 1–7 を [DWRR](../../reference/glossary.md#term-dwrr) (weight 15) で並べる例です。テンプレ展開を待たずに最低限手で組むなら、pool / profile / scheduler / port_qos_map の 4 つを作って 1 ポートに当てるところまでが必要最小限です。

操作の順番は次のとおり。

1. `BUFFER_POOL` を ingress / egress で 1 本ずつ定義する。
2. profile を 2 種（ingress lossy / egress lossy）作って pool を指す。
3. PG 0、queue 0–7 にそれぞれ profile を当てる。
4. `SCHEDULER` を 2 種（STRICT / DWRR）作って `QUEUE` から指す。
5. `PORT_QOS_MAP` でポートに DSCP→TC、TC→queue を当てる。

`config` CLI を使う場合の組み立て例です。

```bash
config buffer profile add ingress_lossy_profile --pool ingress_lossy_pool --xon 0 --xoff 0 --size 0 --dynamic_th 3
config buffer profile add q_lossy_profile       --pool egress_lossy_pool  --size 0 --dynamic_th 3
config buffer priority-group lossy add  Ethernet0 0    ingress_lossy_profile
config buffer queue add                 Ethernet0 0-7  q_lossy_profile
```

CONFIG_DB に直接書くなら次のような構造になります。

```json
{
  "BUFFER_POOL": {
    "ingress_lossy_pool": {"type":"ingress","mode":"static","size":"10485760"},
    "egress_lossy_pool":  {"type":"egress","mode":"static","size":"10485760"}
  },
  "BUFFER_PROFILE": {
    "ingress_lossy_profile": {"pool":"ingress_lossy_pool","size":"0","dynamic_th":"3"},
    "q_lossy_profile":       {"pool":"egress_lossy_pool","size":"0","dynamic_th":"3"}
  },
  "BUFFER_PG":   {"Ethernet0|0":   {"profile":"ingress_lossy_profile"}},
  "BUFFER_QUEUE":{"Ethernet0|0-7": {"profile":"q_lossy_profile"}},
  "SCHEDULER": {
    "scheduler.0":{"type":"STRICT"},
    "scheduler.1":{"type":"DWRR","weight":"15"}
  },
  "QUEUE": {
    "Ethernet0|0":  {"scheduler":"scheduler.0"},
    "Ethernet0|1-7":{"scheduler":"scheduler.1"}
  },
  "PORT_QOS_MAP": {
    "Ethernet0": {"dscp_to_tc_map":"AZURE","tc_to_queue_map":"AZURE"}
  }
}
```

`AZURE` は [SONiC](../../reference/glossary.md#term-sonic) の標準サンプル map 名で、テンプレ展開後にこの名前で参照されるのが慣例です。別名で揃えても動きますが、`config qos reload` の再展開で踏み直されるので、長期運用なら `AZURE` を残して同名で上書きする方が安全です。

確認は次の通り。

```bash
$ show queue counters Ethernet0
       Port    TxQ    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
-----------  -----  -------------    -------------   ----------   -----------
  Ethernet0    UC0       1,234,567      987,654,321            0             0
  Ethernet0    UC1         234,567      198,765,432            0             0
  ...

$ show priority-group persistent-watermark headroom
        Port    PG0    PG1    PG2    PG3    PG4    PG5    PG6    PG7
-----------  -----  -----  -----  -----  -----  -----  -----  -----
  Ethernet0      0      0      0      0      0      0      0      0
```

`show queue counters` の `Drop/pkts` が常に増えていれば queue 容量不足、あるいは scheduler weight の不均衡を疑います。

## シナリオ 2: RoCEv2 用 lossless (TC3) を追加する

既存の lossy ToR に「RoCEv2 だけ lossless で運ぶ」要件を被せるパターンです。lossless は DSCP 26（IEEE 802.1 で RoCEv2 の慣例）を TC3 にマップし、PG3 / queue 3 を PFC headroom 付き profile にし、ECN を入れる流れです。

```bash
# 1. lossless pool (xoff 領域を含む) と profile
config buffer profile add ingress_lossless_profile \
  --pool ingress_lossless_pool --xon 19456 --xoff 36352 --size 55808 --dynamic_th 0
config buffer priority-group lossless add Ethernet0 3 ingress_lossless_profile

# 2. PFC を priority 3 で enable
config interface pfc asymmetric off Ethernet0
redis-cli -n 4 HSET 'PORT_QOS_MAP|Ethernet0' pfc_enable '3'

# 3. PFC priority -> PG マップ
redis-cli -n 4 HSET 'PFC_PRIORITY_TO_PRIORITY_GROUP_MAP|AZURE' 3 3

# 4. ECN/WRED を queue 3 に当てる
config ecn -profile AZURE_LOSSLESS -rmax 2097152 -rmin 1048576 -gmax 5242880 -gmin 2621440
redis-cli -n 4 HSET 'QUEUE|Ethernet0|3' wred_profile 'AZURE_LOSSLESS'

# 5. DSCP 26 -> TC3 を確実に
redis-cli -n 4 HSET 'DSCP_TO_TC_MAP|AZURE' 26 3
```

確認:

```bash
$ show pfc priority Ethernet0
Interface    Lossless priorities
-----------  ---------------------
Ethernet0    3

$ show queue watermark unicast
        Port    UC0    UC1    UC2    UC3    UC4    UC5    UC6    UC7
-----------  -----  -----  -----  -----  -----  -----  -----  -----
  Ethernet0      0      0      0   8192      0      0      0      0

$ show interfaces counters --period 5 | grep Ethernet0
Ethernet0    U     12.50 MB/s    ...    0 RX_DRP    0 RX_OVR    0 TX_ERR
```

`show queue watermark unicast` の UC3 が増えるが drop が出ない、`show pfc counters` で peer に向けて PFC pause が送られている、`show priority-group persistent-watermark headroom` で PG3 の headroom が xoff 領域内に収まっている、の 3 つが揃っていれば lossless が機能しています。

## シナリオ 3: PFCWD を有効化して queue を保護する

PFCWD は「PFC pause が長時間止まったままになり、[ASIC](../../reference/glossary.md#term-asic) の buffer が消費され続ける状態」を検出して queue を強制 drop または forward に切り替える運用安全装置です。lossless を有効にした以上は必須と考えて差し支えありません。

```bash
# 推奨デフォルトでまとめて enable
config pfcwd start_default

# ポート単位で個別 chunk チューニング
config pfcwd start --action drop ports Ethernet0,Ethernet1 \
  detection-time 200 --restoration-time 200

# polling interval を変える (デフォルト 200ms)
config pfcwd interval 100
```

確認:

```bash
$ show pfcwd config
       Port    Action    Detection time    Restoration time
-----------  --------  ----------------  ------------------
  Ethernet0      drop               200                 200
  Ethernet1      drop               200                 200

$ show pfcwd stats
       Queue    Storm detected    Restored    Tx OK    Rx OK
------------  ----------------  ----------  -------  -------
Ethernet0:3                  0           0        0        0
```

`Storm detected` が立ち上がるのは実際に PFC storm が起きたとき。`detection-time` を 100ms 未満にすると正常 micro-burst を storm と誤検知することがあるため、200ms を出発点に運用負荷を見て調整します。詳細は [`config pfcwd`](../../reference/cli/config-pfcwd.md) と [`PFC_WD`](../../reference/config-db/pfc-wd.md) を参照。

## QoS テンプレートの再展開

設定を初期テンプレートに戻したいときは `config qos reload`、map 系だけクリアしたいときは `config qos clear` です。プラットフォーム固有テンプレートは `device/<vendor>/<sku>/qos.json.j2` にあり、interface speed / cable length / mode を入力にして展開されます。

```bash
# 全体再展開 (BUFFER_*, QUEUE, SCHEDULER, *_TO_*_MAP 系を含む)
config qos reload --no-dynamic-buffer

# 特定 namespace だけ
config qos reload -n asic0
```

`--no-dynamic-buffer` を付けるとテンプレ依存の dynamic buffer calculator (`buffermgrd`) を起動しません。手で BUFFER 系を細かく調整しているスイッチでは付けておくと、起動時の自動再計算で踏まれるのを防げます。

## YANG / gNMI から触る場合

OpenConfig には [QoS](../../reference/glossary.md#term-qos) 系もありますが、SONiC の native YANG では上表の `sonic-*` YANG が一次情報です。[gNMI](../../reference/glossary.md#term-gnmi) から `BUFFER_PROFILE` / `QUEUE` / `SCHEDULER` を操作するときは map 整合（参照される profile が存在するか）を YANG validation が見ているので、profile 削除前に PG / queue の参照を外す手順を踏みます。

```bash
gnmi_set --replace='/sonic-buffer-profile:sonic-buffer-profile/BUFFER_PROFILE/BUFFER_PROFILE_LIST[name=q_lossy_profile]:::JSON_IETF:::@/tmp/q_lossy_profile.json' \
  -target_addr localhost:8080 -insecure
```

## よくある設定エラーと対処

| 症状 | 典型的な原因 | 対処 |
|---|---|---|
| `config buffer profile add` が `pool does not exist` で失敗 | テンプレ非展開状態で profile 先に作った | `config qos reload` で pool を含むテンプレを展開してから profile を上書き |
| lossless 設定後に link は up だが PFC pause が流れない | `PORT_QOS_MAP.pfc_enable` が `3` を含まない、または `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` 未設定 | `redis-cli -n 4 HGETALL 'PORT_QOS_MAP|Ethernet0'` と `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP|*` を両方確認 |
| `show queue counters` で全ての queue が UC0 に偏る | `DSCP_TO_TC_MAP` または `TC_TO_QUEUE_MAP` が `PORT_QOS_MAP` から参照されていない | `PORT_QOS_MAP|Ethernet0` に `dscp_to_tc_map` / `tc_to_queue_map` が設定されているか確認 |
| `Drop/pkts` が増え続ける | queue size 不足、または scheduler の極端な weight 差 | `BUFFER_PROFILE.size` 増、または DWRR weight を再配分 |
| 再起動後に設定が消える | `config save` 忘れ、または `config qos reload` で上書きされた | `config save -y` を実行、テンプレと衝突する場合は Golden Config 側に反映 |
| PFCWD が `start_default` で何も起動しない | lossless priority 未定義（`PORT_QOS_MAP.pfc_enable` 空） | 先に PFC 有効化、その後 `start_default` を再実行 |
| dynamic buffer 環境で `BUFFER_PROFILE.size` が無視される | `buffermgrd` が dynamic mode で再計算 | `DEVICE_METADATA.localhost.buffer_model` を `traditional` に切替、または `--no-dynamic-buffer` で reload |

## 関連リファレンス

- [`config buffer`](../../reference/cli/config-buffer.md)、[`config qos`](../../reference/cli/config-qos.md)、[`config pfcwd`](../../reference/cli/config-pfcwd.md)
- CONFIG_DB: [`BUFFER_POOL`](../../reference/config-db/buffer-pool.md) / [`BUFFER_PROFILE`](../../reference/config-db/buffer-profile.md) / [`SCHEDULER`](../../reference/config-db/scheduler.md) / [`PORT_QOS_MAP`](../../reference/config-db/port-qos-map.md)
- YANG: [sonic-buffer-pool](../../reference/yang/sonic-buffer-pool.md) / [sonic-buffer-profile](../../reference/yang/sonic-buffer-profile.md) / [sonic-pfcwd](../../reference/yang/sonic-pfcwd.md)
- 同章の [concept](concept.md) / [architecture](architecture.md) / [operations](operations.md)

<!-- glossary-links-injected: ec18b66e3507 -->
