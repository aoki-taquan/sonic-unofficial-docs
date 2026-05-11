---
title: QoS / Buffer の運用
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
---

# QoS / Buffer の運用

「アプリが詰まる」「PFC で止まった」「キューが捨てている」と言われたときに、どのコマンドをどの順番で叩くか、を整理します。

## まず叩く 4 コマンド

| コマンド | 何を見るのか | 出典 |
|---------|------------|------|
| `show queue counters` | キュー単位の packets / bytes / drops | [show-queue](../../reference/cli/show-queue.md) |
| `show priority-group counters` | ingress PG 単位の drop / xoff time | [show-priority-group](../../reference/cli/show-priority-group.md) |
| `show pfc counters` | ポート単位の PFC Rx/Tx | [show-pfc](../../reference/cli/show-pfc.md) |
| `show buffer pool persistent-watermark` | プール peak | [show-buffer](../../reference/cli/show-buffer.md) |

この 4 つで「どの queue / PG / ポートで何が起きているか」がだいたい分かります。

## 「ドロップしている」と言われたとき

1. `show interfaces counters` で port 全体の drop を確認。
2. `show queue counters` で egress 側 queue の drop が立っているか。立っていればその queue を持つ flow（DSCP / TC）を [`DSCP_TO_TC_MAP`](../../reference/config-db/dscp-to-tc-map.md) と [`TC_TO_QUEUE_MAP`](../../reference/config-db/tc-to-queue-map.md) から逆引き。
3. 立っていなければ ingress 側を疑い、[port buffer drop counters](../../acl-qos/port-buffer-drop-counters-in-sonic.md) の系列カウンタ（`SAI_PORT_STAT_IN_DROPPED_PKTS` 系 / `SAI_PORT_STAT_PFC_*_RX_PKTS` など）を `portstat -j` 系で取り、ingress PG drop かどうかを切り分け。
4. WRED / ECN が動いている経路なら [WRED and ECN statistics](../../acl-qos/wred-and-ecn-statistics.md) のカウンタで、drop と mark の比率を見る。

## 「PFC で止まる」と言われたとき

1. `show pfc counters` で Rx PFC が増えているか、Tx PFC を出しているかを判断。
2. Rx PFC が多い → 相手側が止めている。自分は被害者なので相手の queue / buffer を見てもらう。
3. Tx PFC が多い → 自分の ingress PG が `xoff` を超えている。`show priority-group watermark` でピークを確認し、profile の `xoff` / `dynamic_th` を見直す。
4. PFC が異常に長く続く場合は PFCWD が止めているはず（`show pfcwd stats` / `show pfcwd config`）。
5. 履歴で振り返りたい場合は [PFC historical statistics](../../acl-qos/pfc-historical-statistics.md) を使う。

## Watermark の見方と落とし穴

Watermark は `show queue persistent-watermark`、`show priority-group persistent-watermark`、`show buffer pool persistent-watermark` の 3 系統と、それぞれの `clear` コマンドがあります。

- `watermark` と `persistent-watermark` は別系統で、前者は短期、後者はクリアするまで保持。
- 観測対象は「ConfigDB 上で有効なポート/queue/PG だけ」に限定されるように改善されており、port を削除した直後に幽霊オブジェクトの古い値が残らないようになっています（[align watermark flow with port configuration](../../acl-qos/align-watermark-flow-with-port-configuration-hld.md)）。
- テストで効果を確認する観点は [test plan](../../acl-qos/test-plan-for-align-watermark-flow-with-port-configuration.md) を参照。

## `show buffer` 系の使い分け

- `show buffer pool` — プールの使用量と peak。
- `show buffer profile` — どの profile があるか、サイズ・閾値・参照プール。
- `show priority-group` — PG ごとの shared / headroom の使用と xoff/xon time。
- `show queue` — queue ごとの bytes、packets、drops、WRED drop / ECN mark。

具体的なオプションは [show-buffer](../../reference/cli/show-buffer.md) / [show-queue](../../reference/cli/show-queue.md) / [show-priority-group](../../reference/cli/show-priority-group.md) を参照。

## telemetry / counter の収集間隔

FlexCounter のポーリング間隔は CONFIG_DB の `FLEX_COUNTER_TABLE` で変えられます。queue / PG / pool / PFCWD ごとに独立しているので、短くしたいものだけ短くすれば SAI 側の負荷も抑えられます。観測値の単位や意味は [watermark counters in SONiC](../../acl-qos/watermark-counters-in-sonic.md) の表が一次資料です。
