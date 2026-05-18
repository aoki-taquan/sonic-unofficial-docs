# Phase B — dot1p-to-pg-map 書き込み順調査

調査日: 2026-05-18

## 対象

`DOT1P_TO_PG_MAP` テーブルは存在しないため、実際の 2 段マッピングチェーン
（`DOT1P_TO_TC_MAP` → `TC_TO_PRIORITY_GROUP_MAP` → `PORT_QOS_MAP`）の
書き込み順依存を調査する。

## 調査コード

- `sonic-swss/orchagent/qosorch.cpp`
- `handlePortQosMapTable()`: L2046-2134
- `doTask(Consumer&)`: L2254-2299
- 汎用マップハンドラ (Dot1pToTcMapHandler 等): L130-196

## 調査結論

### SET 順序（必須）

1. `DOT1P_TO_TC_MAP|<name>` を先に SET する
2. `TC_TO_PRIORITY_GROUP_MAP|<name>` を先に SET する
3. 両マップ作成後に `PORT_QOS_MAP|<port>` で `dot1p_to_tc_map=<name>` および `tc_to_pg_map=<name>` を SET する

根拠: `handlePortQosMapTable()` L2124-2130 の `resolveFieldRefValue()` — 参照先マップが未作成の場合は `task_need_retry` を返す。orchagent のループで自動リトライされるが、マップが存在するまで PORT_QOS_MAP への SAI 反映はブロックされる。

### DEL 順序（必須）

1. `PORT_QOS_MAP|<port>` を先に DEL し参照を解除する
2. その後 `DOT1P_TO_TC_MAP|<name>` および `TC_TO_PRIORITY_GROUP_MAP|<name>` を DEL する

根拠: 汎用ハンドラ L181-186 — `isObjectBeingReferenced()` が true の間は DEL が `m_pendingRemove=true` を立て `task_need_retry` を返す。参照が解除されるまで SAI 削除は実行されない。

### allPortsReady() ブロック

`doTask()` L2258-2261 — `gPortsOrch->allPortsReady()` が false の間は全 QosOrch タスクが即 return でスキップされる。PortsOrch 初期化完了（通常は orchdaemon 起動数秒後）まで `DOT1P_TO_TC_MAP` 等のいかなる SET/DEL も処理されない。

## 依存関係サマリ

| 依存関係 | 方向 | 緩和策 |
|---------|------|-------|
| allPortsReady() 完了 → 全 QosOrch 処理 | 強制先行 | orchdaemon が自動管理 |
| DOT1P_TO_TC_MAP SET → PORT_QOS_MAP SET (dot1p_to_tc_map) | 必須先行 | task_need_retry で自動リトライ |
| TC_TO_PRIORITY_GROUP_MAP SET → PORT_QOS_MAP SET (tc_to_pg_map) | 必須先行 | task_need_retry で自動リトライ |
| PORT_QOS_MAP DEL → DOT1P_TO_TC_MAP DEL | 必須先行 | m_pendingRemove + task_need_retry |
| PORT_QOS_MAP DEL → TC_TO_PRIORITY_GROUP_MAP DEL | 必須先行 | m_pendingRemove + task_need_retry |
