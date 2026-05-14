# LOSSLESS_TRAFFIC_PATTERN — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/lossless-traffic-pattern.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `buffermgrdyn` (動的バッファ管理) |
| 2. CFG→APPL 翻訳 | なし (内部計算パラメータ) |
| 3. APPL→SAI | なし (直接 SAI 呼び出しなし — 計算結果が BUFFER_PROFILE 経由で SAI に到達) |
| 4. タイミング+副作用 | CONFIG_DB 変化を `buffermgrdyn` が検知後、lossless バッファプロファイルを再計算。再計算結果が APPL_DB の BUFFE... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`buffermgrdyn` (動的バッファ管理) が CONFIG_DB の `LOSSLESS_TRAFFIC_PATTERN` テーブルを購読する。

`LOSSLESS_TRAFFIC_PATTERN` の key は `AZURE` 等のパターン名。`mtu` / `small_packet_percentage` 等のパラメータを保持。

### 段階 2 — CFG→APPL 翻訳

なし (内部計算パラメータ)

### 段階 3 — APPL→SAI

なし (直接 SAI 呼び出しなし — 計算結果が BUFFER_PROFILE 経由で SAI に到達)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `buffermgrdyn` が検知後、lossless バッファプロファイルを再計算。再計算結果が APPL_DB の BUFFER_PROFILE_TABLE に書き込まれる。

**副作用**: PFC lossless traffic パターン変更は lossless バッファ量の再計算を引き起こす。すべての lossless ポートのバッファプロファイルが再生成される。
<!-- /runtime-trace -->
```
