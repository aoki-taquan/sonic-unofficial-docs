# AS_PATH_SET — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/as-path-set.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `bgpcfgd` (`sonic-bgpcfgd`) |
| 2. CFG→APPL 翻訳 | なし (FRR vtysh コマンドで直接 BGP デーモンに注入) |
| 3. APPL→SAI | なし (SAI 非経由 — FRR プロセス内部で AS-path フィルタとして使用) |
| 4. タイミング+副作用 | CONFIG_DB 変化を `bgpcfgd` が検知後、FRR `vtysh -c` コマンドを発行。FRR BGP デーモンは即時反映。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` (`sonic-bgpcfgd`) が CONFIG_DB の `AS_PATH_SET` テーブルを購読する。

`bgpcfgd` は `ConfigDBConnector.listen()` で `BGP_PEER_RANGE`/`BGP_GLOBALS` 等と合わせて購読。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh コマンドで直接 BGP デーモンに注入)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — FRR プロセス内部で AS-path フィルタとして使用)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `bgpcfgd` が検知後、FRR `vtysh -c` コマンドを発行。FRR BGP デーモンは即時反映。

**副作用**: FRR プロセスへの設定注入のみ。既存 BGP セッションには次回 UPDATE 送信時または policy soft-clear 実施時に適用。
<!-- /runtime-trace -->
```
