---
title: QoS / Buffer の設定
description: QoS / Buffer の設定 — 設定は「pool / profile を作る → port に classification を当てる
  → queue に scheduler / WRED を当てる → 必要なら PFC / PFCWD を有効化」の順で組むのが筋が良いです。
area: topics
verification: code-verified
last_verified: 2026-06-04
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-utilities
    path: pfcwd/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-buildimage
    path: device/common/profiles/th/gen/RDMA-CENTRIC/buffers_defaults_t0.j2
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: device/common/profiles/th/gen/RDMA-CENTRIC/pg_profile_lookup.ini
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
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

- [`config interface buffer`](../../reference/cli/config-buffer.md) — buffer profile を port の priority group / queue にバインドする操作。実装は `config interface buffer` 配下の `priority_group lossless add|set|remove` / `queue add|set|remove` で、いずれも **dynamic buffer 有効環境専用** (`is_dynamic_buffer_enabled` チェックで弾かれる)[^cli-buffer]。
- [`config qos`](../../reference/cli/config-qos.md) — `qos reload` でテンプレを再展開、`qos clear` で BUFFER_* / QUEUE / SCHEDULER / *_MAP 系を一掃する。
- [`config pfcwd`](../../reference/cli/config-pfcwd.md) — PFCWD の start/start_default/stop/interval/counter_poll/big_red_switch を扱う。`start` の detection-time / restoration-time は **100〜60000ms** に validate される[^cli-pfcwd]。

[^cli-buffer]: `sonic-net/sonic-utilities` `config/main.py` の `buffer` group は `@interface.group` 直下に定義されており、`is_dynamic_buffer_enabled(config_db)` が False のときは `ctx.fail("This command can only be executed on a system with dynamic buffer enabled")` で終了する (commit `39732bc`, lines 6201-6209)。`priority_group lossless add|set|remove` は同ファイル 6225-6267 行。
[^cli-pfcwd]: `sonic-net/sonic-utilities` `pfcwd/main.py` の `start` コマンドは `--restoration-time` を `click.IntRange(100, 60000)`、位置引数 `detection-time` を `click.IntRange(100, 5000)` で受け取る (commit `39732bc`, lines 506-527)。デフォルト値は同ファイル 37-41 行で `DEFAULT_DETECTION_TIME = 200` / `DEFAULT_RESTORATION_TIME = 200` / `DEFAULT_POLL_INTERVAL = 200` / `DEFAULT_ACTION = 'drop'`。

[CONFIG_DB](../../reference/glossary.md#term-config_db) を直接編集する場合は次のテーブル群です。

| 目的 | テーブル | [YANG](../../reference/glossary.md#term-yang) |
|------|----------|------|
| Buffer pool 定義 | [`BUFFER_POOL`](../../reference/config-db/buffer-pool.md) | [sonic-buffer-pool](../../reference/yang/sonic-buffer-pool.md) |
| Buffer profile | [`BUFFER_PROFILE`](../../reference/config-db/buffer-profile.md) | [sonic-buffer-profile](../../reference/yang/sonic-buffer-profile.md) |
| Ingress PG 割当 | [`BUFFER_PG`](../../reference/config-db/buffer-pg.md) | [sonic-buffer-pg](../../reference/yang/sonic-buffer-pg.md) |
| Egress queue 割当 | [`BUFFER_QUEUE`](../../reference/config-db/buffer-queue.md) | [sonic-buffer-queue](../../reference/yang/sonic-buffer-queue.md) |
| Queue × scheduler/WRED | [`QUEUE`](../../reference/config-db/queue.md) | [sonic-queue](../../reference/yang/sonic-queue.md) |
| [Scheduler](../../reference/glossary.md#term-scheduler) / shaping | [`SCHEDULER`](../../reference/config-db/scheduler.md) | [sonic-scheduler](../../reference/yang/sonic-scheduler.md) |
| WRED / [ECN](../../reference/glossary.md#term-ecn) | [`WRED_PROFILE`](../../reference/config-db/wred-profile.md) | [sonic-wred-profile](../../reference/yang/sonic-wred-profile.md) |
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

最初の boot で `qos.json.j2` / `buffers.json.j2` が展開されるため、上記 5 オブジェクトのほとんどはテンプレ起源で埋まる。手作業で組むのは「テンプレ非対応 SKU」や「BUFFER_PROFILE をカスタム差し替え」など限定ケースで、その場合は `BUFFER_POOL` / `BUFFER_PROFILE` を CONFIG_DB に直接 set し、`BUFFER_PG` / `BUFFER_QUEUE` / `QUEUE` の参照を再配線する。dynamic-buffer 有効環境であれば PG / queue 側のバインドのみ `config interface buffer priority_group lossless` / `config interface buffer queue` で操作できる。

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

lossless profile の `size` / `xon` / `xoff` は **port speed と cable length から `pg_profile_lookup.ini` で逆引き** される。例えば `sonic-buildimage` の Tomahawk RDMA-CENTRIC テンプレでは 100G / 5m なら `size=1248, xon=2288, xoff=165568`、25G / 40m なら `size=1248, xon=2288, xoff=53248` といった離散テーブルが配布されている[^pg-lookup]。下記サンプルは「100G / 短距離想定」の概算値であって、本番では必ず SKU 同梱の `pg_profile_lookup.ini` の該当行を使う。

```bash
# 1. lossless pool (xoff 領域を含む) と profile を CONFIG_DB に直接書き込む
#    (BUFFER_POOL / BUFFER_PROFILE の直接 add CLI は無いため redis-cli を使う)
redis-cli -n 4 HSET 'BUFFER_POOL|ingress_lossless_pool' type ingress mode dynamic size 10875072 xoff 4194112
redis-cli -n 4 HSET 'BUFFER_PROFILE|ingress_lossless_profile' \
  pool ingress_lossless_pool size 1248 xon 2288 xoff 165568 dynamic_th 0
# dynamic-buffer 有効環境のみ: profile を PG3 にバインド
config interface buffer priority_group lossless add Ethernet0 3 ingress_lossless_profile

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

[^pg-lookup]: `sonic-net/sonic-buildimage` `device/common/profiles/th/gen/RDMA-CENTRIC/pg_profile_lookup.ini` (commit `9ea932e`)。同 RDMA-CENTRIC テンプレの `buffers_defaults_t0.j2` も `ingress_lossless_pool.size=10875072 / xoff=4194112`、`egress_lossless_pool.size=15982720` といった具体値を持つ。

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
# (DEVICE_METADATA.localhost.default_pfcwd_status = "enable" が前提。未設定だと何もしないで戻る)
config pfcwd start_default

# ポート単位で個別チューニング
# 構文: pfcwd start [--action <drop|forward|alert>] [--restoration-time N] <ports...> <detection-time>
# detection-time は 100〜5000ms、restoration-time は 100〜60000ms
sudo pfcwd start --action drop --restoration-time 200 Ethernet0 Ethernet1 200

# polling interval を変える (デフォルト 200ms、最小 100ms)
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

`Storm detected` が立ち上がるのは実際に PFC storm が起きたとき。CLI の validation は `detection-time` を 100ms 以上に強制するので、100ms 直下まで攻めると正常 micro-burst を storm と誤検知することがあるため、デフォルトの 200ms を出発点に運用負荷を見て調整します。詳細は [`config pfcwd`](../../reference/cli/config-pfcwd.md) と [`PFC_WD`](../../reference/config-db/pfc-wd.md) を参照。

## QoS テンプレートの再展開

設定を初期テンプレートに戻したいときは `config qos reload`、map 系だけクリアしたいときは `config qos clear` です。プラットフォーム固有テンプレートは `device/<vendor>/<sku>/qos.json.j2` にあり、interface speed / cable length / mode を入力にして展開されます。

```bash
# 全体再展開 (BUFFER_*, QUEUE, SCHEDULER, *_TO_*_MAP 系を含む)
config qos reload --no-dynamic-buffer

# 特定ポートだけテンプレ再適用
config qos reload --ports Ethernet0,Ethernet4
```

`--no-dynamic-buffer` を付けるとテンプレ依存の dynamic buffer calculator を起動しません (mellanox / barefoot 向けのフックがスキップされる)。手で BUFFER 系を細かく調整しているスイッチでは付けておくと、起動時の自動再計算で踏まれるのを防げます。multi-ASIC 環境では `config qos reload` が内部で全 namespace を順に処理するため、namespace 指定 option は無く、特定 namespace だけ再展開したい場合は `--ports` でその ASIC 配下のポートを列挙する形になります[^qos-reload]。

[^qos-reload]: `sonic-net/sonic-utilities` `config/main.py` の `qos reload` (commit `39732bc`, lines 3652-3709)。`--ports` / `--no-dynamic-buffer` / `--no-delay` / `--verbose` / `--json-data` / `--dry_run` の各 option を持ち、`multi_asic.get_num_asics() > 1` のときは `multi_asic.get_namespaces_from_linux()` で得た namespace を for ループで処理する。

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
| PFCWD が `start_default` で何も起動しない | `DEVICE_METADATA.localhost.default_pfcwd_status` が `enable` でない、または `DEVICE_NEIGHBOR` が空で対象ポートが特定できない | `redis-cli -n 4 HSET 'DEVICE_METADATA|localhost' default_pfcwd_status enable` を入れて再実行。[BGP](../../reference/glossary.md#term-bgp) 隣接のないラボでは `DEVICE_NEIGHBOR` を疑似的に埋めるか、`pfcwd start` で明示的にポートを指定する |
| dynamic buffer 環境で `BUFFER_PROFILE.size` が無視される | `buffermgrd` が dynamic mode で再計算 | `DEVICE_METADATA.localhost.buffer_model` を `traditional` に切替、または `--no-dynamic-buffer` で reload |

## 関連リファレンス

- [`config buffer`](../../reference/cli/config-buffer.md)、[`config qos`](../../reference/cli/config-qos.md)、[`config pfcwd`](../../reference/cli/config-pfcwd.md)
- CONFIG_DB: [`BUFFER_POOL`](../../reference/config-db/buffer-pool.md) / [`BUFFER_PROFILE`](../../reference/config-db/buffer-profile.md) / [`SCHEDULER`](../../reference/config-db/scheduler.md) / [`PORT_QOS_MAP`](../../reference/config-db/port-qos-map.md)
- YANG: [sonic-buffer-pool](../../reference/yang/sonic-buffer-pool.md) / [sonic-buffer-profile](../../reference/yang/sonic-buffer-profile.md) / [sonic-pfcwd](../../reference/yang/sonic-pfcwd.md)
- 同章の [concept](concept.md) / [architecture](architecture.md) / [operations](operations.md)

<!-- glossary-links-injected: 1c59d90c07b4 -->
