---
title: QoS / Buffer の運用
description: QoS / Buffer の運用 — 「アプリが詰まる」「PFC で止まった」「キューが捨てている」と言われたときに、どのコマンドをどの順番で叩くか、を整理します。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/show-buffer.md
- docs/reference/cli/show-queue.md
- docs/reference/cli/show-pfc.md
- docs/reference/cli/show-priority-group.md
- docs/acl-qos/port-buffer-drop-counters-in-sonic.md
- docs/acl-qos/watermark-counters-in-sonic.md
- docs/acl-qos/pfc-historical-statistics.md
- docs/acl-qos/wred-and-ecn-statistics.md
- docs/acl-qos/align-watermark-flow-with-port-configuration-hld.md
- docs/acl-qos/test-plan-for-align-watermark-flow-with-port-configuration.md
related:
  cli:
  - show queue
  - show buffer_pool
  - show pfc
  - show buffer
  - show interfaces
  - config qos
  - config buffer
  config_db:
  - DSCP_TO_TC_MAP
  - TC_TO_QUEUE_MAP
  - BUFFER_PROFILE
  - BUFFER_POOL
  - FLEX_COUNTER_TABLE
  - WRED_PROFILE
  - BUFFER_QUEUE
  yang:
  - sonic-buffer-queue
  - sonic-buffer-profile
  - sonic-buffer-pool
  - sonic-buffer-pg
  - sonic-pfc-priority-queue-map
  - sonic-pfc-priority-priority-group-map
  - sonic-wred-profile
---

# QoS / Buffer の運用

「アプリが詰まる」「[PFC](../../reference/glossary.md#term-pfc) で止まった」「キューが捨てている」と言われたときに、どのコマンドをどの順番で叩くか、を整理します。

## まず叩く 4 コマンド

| コマンド | 何を見るのか | 出典 |
|---------|------------|------|
| `show queue counters` | キュー単位の packets / bytes / drops | [show-queue](../../reference/cli/show-queue.md) |
| `show priority-group counters` | ingress PG 単位の drop / xoff time | [show-priority-group](../../reference/cli/show-priority-group.md) |
| `show pfc counters` | ポート単位の PFC Rx/Tx | [show-pfc](../../reference/cli/show-pfc.md) |
| `show buffer_pool persistent-watermark` | プール peak | [show-buffer](../../reference/cli/show-buffer.md) |

この 4 つで「どの queue / PG / ポートで何が起きているか」がだいたい分かります。

```text
admin@sonic:~$ show queue counters Ethernet0
       Port    TxQ    Counter/pkts    Counter/bytes    Drop/pkts    Drop/bytes
-----------  -----  --------------  ---------------  -----------  ------------
  Ethernet0   UC0          1.2M           1.5G              0             0
  Ethernet0   UC1            42K           63M              0             0
  Ethernet0   UC3           890K          1.3G          12.3K          18M
  Ethernet0   UC4              0             0              0             0

admin@sonic:~$ show pfc counters Ethernet0
       Port    PFC0    PFC1    PFC2    PFC3    PFC4    PFC5    PFC6    PFC7
-----------  ------  ------  ------  ------  ------  ------  ------  ------
Ethernet0 Rx     0       0       0     12K     0       0       0       0
Ethernet0 Tx     0       0       0       0     0       0       0       0
```

`UC3` で drop が伸び、同じ port の `PFC3 Rx` が増えていれば、上流が PFC で止めているのに自分側の egress も同じ TC で詰まっている、というよくある絵です。

## 「ドロップしている」と言われたとき

1. `show interfaces counters` で port 全体の drop を確認。
2. `show queue counters` で egress 側 queue の drop が立っているか。立っていればその queue を持つ flow（[DSCP](../../reference/glossary.md#term-dscp) / TC）を [`DSCP_TO_TC_MAP`](../../reference/config-db/dscp-to-tc-map.md) と [`TC_TO_QUEUE_MAP`](../../reference/config-db/tc-to-queue-map.md) から逆引き。
3. 立っていなければ ingress 側を疑い、[port buffer drop counters](../../acl-qos/port-buffer-drop-counters-in-sonic.md) の系列カウンタ（`SAI_PORT_STAT_IN_DROPPED_PKTS` 系 / `SAI_PORT_STAT_PFC_*_RX_PKTS` など）を `portstat -j` 系で取り、ingress PG drop かどうかを切り分け。
4. [WRED](../../reference/glossary.md#term-wred) / ECN が動いている経路なら [WRED and ECN statistics](../../acl-qos/wred-and-ecn-statistics.md) のカウンタで、drop と mark の比率を見る。

切り分けは「どの DB に何が出ているか」を意識すると速いです:

| 観点 | 主な DB / Table | 取り方 |
|------|------------------|--------|
| port 全体 | `COUNTERS_DB` `COUNTERS:Ethernet0` | `portstat -j` |
| egress queue | `COUNTERS_DB` `COUNTERS_QUEUE_NAME_MAP` | `show queue counters` |
| ingress PG | `COUNTERS_DB` `COUNTERS_PG_NAME_MAP` | `show priority-group counters` |
| WRED / ECN | `COUNTERS_DB` `SAI_QUEUE_STAT_WRED_*` | [WRED counters](../../acl-qos/wred-and-ecn-statistics.md) |
| buffer pool | `COUNTERS_DB` `COUNTERS_BUFFER_POOL_NAME_MAP` | `show buffer pool persistent-watermark` |
| 設定マップ | `CONFIG_DB` `DSCP_TO_TC_MAP` / `TC_TO_QUEUE_MAP` / `BUFFER_PROFILE` | `redis-cli -n 4` |

### ログサンプル (PFC storm 検出)

```text
Apr 30 12:34:01 sw01 INFO pfc_wd: storm detected on Ethernet24 queue 3
Apr 30 12:34:01 sw01 INFO pfc_wd: action=drop, restore_time=200ms, detect_time=200ms
Apr 30 12:34:02 sw01 INFO pfc_wd: storm restored on Ethernet24 queue 3
```

このログが頻発する場合は、Tx PFC を出している ingress 側 (相手) を疑い、自装置側は WRED / ECN しきい値の調整、または該当 TC の buffer profile (`xoff`) を増やす方向を検討します。

## 「PFC で止まる」と言われたとき

1. `show pfc counters` で Rx PFC が増えているか、Tx PFC を出しているかを判断。
2. Rx PFC が多い → 相手側が止めている。自分は被害者なので相手の queue / buffer を見てもらう。
3. Tx PFC が多い → 自分の ingress PG が `xoff` を超えている。`show priority-group watermark` でピークを確認し、profile の `xoff` / `dynamic_th` を見直す。
4. PFC が異常に長く続く場合は PFCWD が止めているはず（`show pfcwd stats` / `show pfcwd config`）。
5. 履歴で振り返りたい場合は [PFC historical statistics](../../acl-qos/pfc-historical-statistics.md) を使う。

```text
admin@sonic:~$ show pfcwd stats
                     QUEUE    STATUS    STORM DETECTED    TX OK    TX DROP    RX OK    RX DROP
-------------------------    ------    --------------    -----    -------    -----    -------
Ethernet24:3                operational             3        0       12.3K        0      8.5K
Ethernet48:3                operational             0        0           0        0         0

admin@sonic:~$ show pfcwd config
       PORT    ACTION    DETECTION TIME    RESTORATION TIME
-----------  --------  ----------------  ------------------
Ethernet24      drop               200                 200
```

`STORM DETECTED` の累計が秒〜分のオーダーで増え続けるなら、PFC を出している側を直さない限り収束しません。応急で PFCWD `action: forward` にすると drop を止められますが、ingress 側の buffer 圧迫が他 PG に飛び火するので恒久対応にはしません。

## Buffer pool の枯渇を見つける

`show buffer_pool persistent-watermark` で、ingress / egress / lossless / lossy pool の peak バイトを見ます。

```text
admin@sonic:~$ show buffer_pool persistent-watermark
       Pool                   Bytes
-----------  ----------------------
ingress_lossless_pool        12345600
ingress_lossy_pool             450000
egress_lossless_pool          9876500
egress_lossy_pool              780000
```

pool size に近い値が peak で出ている場合、burst 時に shared pool が頭打ちになっていた可能性が高いです。`show buffer_pool watermark` (現在値) と差を取り、常時忙しいのか瞬間 burst かを判別します。

`BUFFER_POOL` テーブルの `size` と `xoff` (lossless のみ) が一次的なつまみで、`BUFFER_PROFILE` の `dynamic_th` / `static_th` がポートごとの shared 割当 ratio になります。

```text
admin@sonic:~$ redis-cli -n 4 hgetall "BUFFER_PROFILE|pg_lossless_100000_5m_profile"
1) "pool"
2) "ingress_lossless_pool"
3) "size"
4) "1248"
5) "xon"
6) "19456"
7) "xoff"
8) "165888"
9) "dynamic_th"
10) "0"
```

`xoff` (PFC 発火閾値) と `xon` (停止解除閾値) は cable length / link speed 依存で計算されるため、手で書き換える前に [buffer profile スキーマ](../../reference/config-db/buffer-profile.md) と shared headroom pool の有無を確認します。

## Watermark の見方と落とし穴

Watermark は `show queue persistent-watermark`、`show priority-group persistent-watermark`、`show buffer_pool persistent-watermark` の 3 系統と、それぞれの `clear` コマンドがあります。

- `watermark` と `persistent-watermark` は別系統で、前者は短期、後者はクリアするまで保持。
- 観測対象は「ConfigDB 上で有効なポート/queue/PG だけ」に限定されるように改善されており、port を削除した直後に幽霊オブジェクトの古い値が残らないようになっています（[align watermark flow with port configuration](../../acl-qos/align-watermark-flow-with-port-configuration-hld.md)）。
- テストで効果を確認する観点は [test plan](../../acl-qos/test-plan-for-align-watermark-flow-with-port-configuration.md) を参照。

## `show buffer` 系の使い分け

- `show buffer_pool` — プールの使用量と peak。
- `show buffer profile` — どの profile があるか、サイズ・閾値・参照プール。
- `show priority-group` — PG ごとの shared / headroom の使用と xoff/xon time。
- `show queue` — queue ごとの bytes、packets、drops、WRED drop / ECN mark。

具体的なオプションは [show-buffer](../../reference/cli/show-buffer.md) / [show-queue](../../reference/cli/show-queue.md) / [show-priority-group](../../reference/cli/show-priority-group.md) を参照。

```text
admin@sonic:~$ show priority-group watermark headroom
        Port      PG0    PG1    PG2    PG3       PG4    PG5    PG6    PG7
------------  ------  -----  -----  -----  --------  -----  -----  -----
   Ethernet0       0      0      0      0    123456      0      0      0
  Ethernet24       0      0      0      0     12000      0      0      0
```

`headroom` 系の watermark が 0 でない PG が、lossless で xoff を消費した瞬間値です。常時 0 ではないが小さい、なら設計範囲内です。0 から急に大きな値になっているなら burst の発生時刻を syslog と照合します。

## telemetry / counter の収集間隔

[FlexCounter](../../reference/glossary.md#term-flexcounter) のポーリング間隔は [CONFIG_DB](../../reference/glossary.md#term-config_db) の `FLEX_COUNTER_TABLE` で変えられます。queue / PG / pool / PFCWD ごとに独立しているので、短くしたいものだけ短くすれば [SAI](../../reference/glossary.md#term-sai) 側の負荷も抑えられます。観測値の単位や意味は [watermark counters in SONiC](../../acl-qos/watermark-counters-in-sonic.md) の表が一次資料です。

```text
admin@sonic:~$ counterpoll show
Type                     Interval (in ms)    Status
-----------------------  ------------------  --------
QUEUE_STAT               10000               enable
PG_WATERMARK_STAT        10000               enable
PORT_STAT                1000                enable
BUFFER_POOL_WATERMARK    10000               enable
PFCWD_STAT               default (10000)     enable
ACL_STAT                 5000                enable
```

検証時に細粒度で見たいときは `counterpoll queue interval 1000` のように短くし、終わったら 10000ms 程度に戻します。常時 1s polling は CPU と SAI 負荷を上げるので避けます。

## 対応コマンド早見表

| 症状 | 入口 | 詳細 |
|------|------|------|
| 特定アプリだけ遅い | `show queue counters` | 該当 queue の drop / PFC |
| 全体的に遅い・bursty | `show buffer_pool persistent-watermark` | shared pool 枯渇 |
| PFC が止まらない | `show pfc counters` + `show pfcwd stats` | Rx/Tx の向き、PFCWD |
| ECN mark が立たない | `show queue counters` (WRED 系) | `WRED_PROFILE` 設定 |
| 設定したのに反映されない | `redis-cli -n 4 hgetall BUFFER_PROFILE\|...` | CONFIG_DB と [STATE_DB](../../reference/glossary.md#term-state_db) |
| port 削除直後の幽霊 watermark | `show queue persistent-watermark` | [align watermark flow](../../acl-qos/align-watermark-flow-with-port-configuration-hld.md) |

## 関連章

- 章 [07 ACL / CoPP / mirror](../07-acl-copp-mirror/operations.md) — drop の入口の切り分け
- 章 [09 telemetry / SNMP / observability](../09-telemetry-snmp/operations.md) — counter を [gNMI](../../reference/glossary.md#term-gnmi) で取る
- 章 [10 gNMI / OpenConfig](../10-gnmi-openconfig/operations.md) — [QoS](../../reference/glossary.md#term-qos) / Buffer の宣言的設定
- [Buffer Pool / Profile スキーマ](../../reference/config-db/buffer-pool.md)

<!-- glossary-links-injected: e1fd4940b990 -->
