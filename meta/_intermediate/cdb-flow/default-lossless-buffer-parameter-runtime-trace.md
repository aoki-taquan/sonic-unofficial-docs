# DEFAULT_LOSSLESS_BUFFER_PARAMETER — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/default-lossless-buffer-parameter.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `buffermgrdyn` (動的バッファ管理デーモン) |
| 2. CFG→APPL 翻訳 | なし (内部計算パラメータとして使用) |
| 3. APPL→SAI | なし (直接 SAI 呼び出しなし — 計算結果が `BUFFER_PROFILE` に反映されて SAI に到達) |
| 4. タイミング+副作用 | CONFIG_DB 変化を `buffermgrdyn` が検知後、すべての lossless バッファプロファイルを再計算。再計算された値が `APPL_DB... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`buffermgrdyn` (動的バッファ管理デーモン) が CONFIG_DB の `DEFAULT_LOSSLESS_BUFFER_PARAMETER` テーブルを購読する。

`DEFAULT_LOSSLESS_BUFFER_PARAMETER` は静的バッファモード (`buffermgrd`) では使用されない。

### 段階 2 — CFG→APPL 翻訳

なし (内部計算パラメータとして使用)

### 段階 3 — APPL→SAI

なし (直接 SAI 呼び出しなし — 計算結果が `BUFFER_PROFILE` に反映されて SAI に到達)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `buffermgrdyn` が検知後、すべての lossless バッファプロファイルを再計算。再計算された値が `APPL_DB` の `BUFFER_PROFILE_TABLE` に書き込まれ `BufferOrch` が SAI を更新。

**副作用**: パラメータ変更はすべての lossless ポートのバッファプロファイルを再生成する。一時的な traffic 影響が発生する可能性。
<!-- /runtime-trace -->
```
