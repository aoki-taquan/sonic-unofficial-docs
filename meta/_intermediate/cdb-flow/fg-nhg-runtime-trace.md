# FG_NHG — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/fg-nhg.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `FgNhgOrch` (orchagent 直接 CFG 購読) |
| 2. CFG→APPL 翻訳 | なし (orchagent が直接 CONFIG_DB を購読) |
| 3. APPL→SAI | `sai_next_hop_group_api` — Fine Grained ECMP next hop group を作成/更新 |
| 4. タイミング+副作用 | orchagent が CONFIG_DB 変化を検知後即座に SAI next hop group を作成/更新。`FG_NHG_PREFIX` で対象プレフ... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`FgNhgOrch` (orchagent 直接 CFG 購読) が CONFIG_DB の `FG_NHG` テーブルを購読する。

`FG_NHG` / `FG_NHG_PREFIX` / `FG_NHG_MEMBER` の 3 テーブルがセット。通常の ECMP とは別のコードパスを使用。

### 段階 2 — CFG→APPL 翻訳

なし (orchagent が直接 CONFIG_DB を購読)

### 段階 3 — APPL→SAI

`sai_next_hop_group_api` — Fine Grained ECMP next hop group を作成/更新

### 段階 4 — タイミングと副作用

**適用タイミング**: orchagent が CONFIG_DB 変化を検知後即座に SAI next hop group を作成/更新。`FG_NHG_PREFIX` で対象プレフィクスを、`FG_NHG_MEMBER` でメンバーを指定。

**副作用**: Fine Grained ECMP の hash 制御に影響。traffic の分散方法が変化。メンバー変更は既存フローのリハッシュを引き起こす可能性。
<!-- /runtime-trace -->
```
