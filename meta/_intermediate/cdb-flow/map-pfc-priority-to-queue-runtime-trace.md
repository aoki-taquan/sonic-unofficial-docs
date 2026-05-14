# MAP_PFC_PRIORITY_TO_QUEUE — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/map-pfc-priority-to-queue.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `QosOrch` (orchagent 直接 CFG 購読) |
| 2. CFG→APPL 翻訳 | なし (orchagent が直接 CONFIG_DB を購読) |
| 3. APPL→SAI | `sai_qos_map_api` — PFC priority → Queue マッピングテーブルを作成 |
| 4. タイミング+副作用 | orchagent が CONFIG_DB 変化を検知後即座に SAI QoS map を作成/更新。ポートへの割り当ては `PORT_QOS_MAP` で行う... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`QosOrch` (orchagent 直接 CFG 購読) が CONFIG_DB の `MAP_PFC_PRIORITY_TO_QUEUE` テーブルを購読する。

`MAP_PFC_PRIORITY_TO_QUEUE` の key はマップ名。PFC priority (0-7) → Queue (0-7) のマッピング。

### 段階 2 — CFG→APPL 翻訳

なし (orchagent が直接 CONFIG_DB を購読)

### 段階 3 — APPL→SAI

`sai_qos_map_api` — PFC priority → Queue マッピングテーブルを作成

### 段階 4 — タイミングと副作用

**適用タイミング**: orchagent が CONFIG_DB 変化を検知後即座に SAI QoS map を作成/更新。ポートへの割り当ては `PORT_QOS_MAP` で行う。

**副作用**: PFC priority → Queue マッピング変更は PFC フロー制御の動作に直接影響。誤設定で lossless traffic が loss になる可能性がある。
<!-- /runtime-trace -->
```
