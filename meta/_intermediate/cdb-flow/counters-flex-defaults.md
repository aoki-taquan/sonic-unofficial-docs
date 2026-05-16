# counters-flex Phase A — implicit defaults (code-derived)

Generated: 2026-05-14  
Target doc: docs/reference/config-db/counters-flex.md

## 概要

`FLEX_COUNTER_DB` に書き込まれる per-OID エントリの `*_COUNTER_ID_LIST` / `*_ATTR_ID_LIST` フィールドのコード由来デフォルト分析。CONFIG_DB `FLEX_COUNTER_TABLE` のグループ設定とは異なり、orchagent が SAI オブジェクトごとに自動生成するフィールド。

## Field-by-field analysis

### PORT_COUNTER_ID_LIST (FLEX_COUNTER_DB)

| 検出種類 | 詳細 |
|---------|------|
| ハードコードリスト | `portsorch.cpp:242-381` の `port_stat_ids[]` で固定。変更不可 (CONFIG_DB 非公開)。 |
| 自動生成トリガー | `FLEX_COUNTER_STATUS = enable` を `PORT` グループで受信 → `gPortsOrch->generatePortCounterMap()` 呼び出し。 |
| PHY ポートのみ | `m_type != Port::PHY` はスキップ。LAG / VLAN / CPU ポートには設定されない。 |
| 一度きり生成 | `m_isPortCounterMapGenerated = true` フラグ。既に生成済みなら再呼び出しは no-op。`disable` しても既存エントリは残る可能性あり（`clearPortCounterMap()` は呼ばれない）。 |
| デフォルト SAI stat 一覧 | `SAI_PORT_STAT_IF_IN_OCTETS`, `SAI_PORT_STAT_IF_IN_UCAST_PKTS`, `SAI_PORT_STAT_IF_IN_NON_UCAST_PKTS`, `SAI_PORT_STAT_IF_IN_DISCARDS`, `SAI_PORT_STAT_IF_IN_ERRORS`, `SAI_PORT_STAT_IF_IN_UNKNOWN_PROTOS`, `SAI_PORT_STAT_IF_OUT_OCTETS`, `SAI_PORT_STAT_IF_OUT_UCAST_PKTS`, `SAI_PORT_STAT_IF_OUT_NON_UCAST_PKTS`, `SAI_PORT_STAT_IF_OUT_DISCARDS`, `SAI_PORT_STAT_IF_OUT_ERRORS`, `SAI_PORT_STAT_IF_OUT_QLEN`, `SAI_PORT_STAT_IF_IN_MULTICAST_PKTS`, `SAI_PORT_STAT_IF_IN_BROADCAST_PKTS`, `SAI_PORT_STAT_IF_OUT_MULTICAST_PKTS`, `SAI_PORT_STAT_IF_OUT_BROADCAST_PKTS` 他 frame-size bucket (64, 65-127, ...) 合計 ~60 stat。 |

### PORT_BUFFER_DROP_STAT (FLEX_COUNTER_DB)

| 検出種類 | 詳細 |
|---------|------|
| ハードコードリスト | `portsorch.cpp:383-387` `port_buffer_drop_stat_ids[]`: `SAI_PORT_STAT_IN_DROPPED_PKTS`, `SAI_PORT_STAT_OUT_DROPPED_PKTS` の 2 stat のみ。 |
| ポーリング間隔固定値 | `PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS = 60000` (portsorch.cpp:88) がハードコード。CONFIG_DB の `POLL_INTERVAL` で変更可能だが、stat_manager の初期化値は 60000ms。 |
| 生成フラグ | `m_isPortBufferDropCounterMapGenerated` フラグで一度きり生成。|

### QUEUE_COUNTER_ID_LIST (FLEX_COUNTER_DB)

| 検出種類 | 詳細 |
|---------|------|
| ハードコードリスト | `portsorch.cpp:389-398` `queue_stat_ids[]`: `SAI_QUEUE_STAT_PACKETS`, `SAI_QUEUE_STAT_BYTES`, `SAI_QUEUE_STAT_DROPPED_PACKETS`, `SAI_QUEUE_STAT_DROPPED_BYTES`, `SAI_QUEUE_STAT_TRIM_PACKETS`, `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS`, `SAI_QUEUE_STAT_TX_TRIM_PACKETS`。 |
| VoQ 追加 stat | VoQ (Virtual Output Queue) 対応時は `voq_stat_ids[]` = `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` が追加される。 |
| ポーリング間隔固定値 | `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 10000` (portsorch.cpp:90) がハードコード初期値。 |

### QUEUE_WATERMARK (FLEX_COUNTER_DB)

| 検出種類 | 詳細 |
|---------|------|
| ハードコードリスト | `portsorch.cpp:405-408` `queueWatermarkStatIds[]`: `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` 1 stat のみ。 |

### PG_COUNTER_ID_LIST (FLEX_COUNTER_DB)

| 検出種類 | 詳細 |
|---------|------|
| watermark stat | `ingressPriorityGroupWatermarkStatIds[]` (portsorch.cpp:410-414): `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES`, `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES`。 |
| drop stat | `ingressPriorityGroupDropStatIds[]` (portsorch.cpp:416-419): `SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS` 1 stat。 |

### WRED_ECN_PORT_STAT / WRED_ECN_QUEUE_STAT (FLEX_COUNTER_DB)

| 検出種類 | 詳細 |
|---------|------|
| WRED port stat | `wred_port_stat_ids[]` (portsorch.cpp:421-427): `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS`, `SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS`, `SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS`, `SAI_PORT_STAT_WRED_DROPPED_PACKETS`。 |
| WRED queue stat | `wred_queue_stat_ids[]` (portsorch.cpp:429-435): `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS`, `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES`, `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS`, `SAI_QUEUE_STAT_WRED_DROPPED_BYTES`。 |
| 能力チェック | WRED 統計は `sai_query_object_stage_capability` で ASIC サポートを確認してから登録。未対応 ASIC では stat は空（FLEX_COUNTER_DB にエントリなし）。 |

### COUNTER_ID_LIST の共通特性

| 検出種類 | 詳細 |
|---------|------|
| FLEX_COUNTER_DB 書き込み | `COUNTER_ID_LIST` は CONFIG_DB ではなく `FLEX_COUNTER_DB` に書き込まれる。`setCounterIdList()` → FlexCounter ライブラリ経由。 |
| ユーザー設定不可 | これらのフィールドは orchagent が自動生成する。CONFIG_DB から直接設定する手段はない（YANG 定義なし）。 |
| グループ初期化 polling interval | `FlexCounterManager` / `FlexCounter` クラスのコンストラクタ引数でハードコード初期値が渡される。CONFIG_DB の POLL_INTERVAL で後から上書き可能。 |

## 検出された discrepancy / 暗黙挙動まとめ

1. **COUNTER_ID_LIST は CONFIG_DB 非公開**: ユーザーが変更できるのは FLEX_COUNTER_TABLE のグループ設定（enable/disable, interval）のみ。個別 stat の追加・削除は orchagent コード変更が必要。
2. **PORT stat 一覧の隠れ拡張**: gearbox 対応時は `gbport_stat_ids` が別途登録される。通常ポートとは異なる stat セットになるが CONFIG_DB 上で識別不能。
3. **WRED stat の能力依存 silent skip**: ASIC が WRED stat をサポートしない場合、FLEX_COUNTER_DB へのエントリ書き込み自体が行われない。`counterpoll show` では STATUS が enable に見えても実際のカウンタはゼロのまま。
4. **VoQ 追加 stat**: VoQ 対応ビルドでは `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` が暗黙追加。ドキュメントに未記載。
5. **初期 polling interval とのずれ**: portsorch.cpp のハードコード値（PORT: 1000ms, QUEUE: 10000ms, PORT_BUFFER_DROP: 60000ms）が FlexCounter グループ初期値。CONFIG_DB で変更されるまでこの値が使われる。
