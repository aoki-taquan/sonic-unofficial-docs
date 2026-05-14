# BGP_DEVICE_GLOBAL — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/bgp-device-global.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `BgpGlobalStateOrch` (orchagent 直接 CFG 購読) |
| 2. CFG→APPL 翻訳 | なし (orchagent が直接 SAI を呼び出す) |
| 3. APPL→SAI | `sai_switch_api` (TCP MD5 等のヒント設定、ECMP hash seed 等) |
| 4. タイミング+副作用 | orchagent 起動時および CONFIG_DB 変化時に即時反映。SAI call は同期的。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`BgpGlobalStateOrch` (orchagent 直接 CFG 購読) が CONFIG_DB の `BGP_DEVICE_GLOBAL` テーブルを購読する。

`BGP_DEVICE_GLOBAL` は `BgpGlobalStateOrch` が `TableConsumer` で購読。

### 段階 2 — CFG→APPL 翻訳

なし (orchagent が直接 SAI を呼び出す)

### 段階 3 — APPL→SAI

`sai_switch_api` (TCP MD5 等のヒント設定、ECMP hash seed 等)

### 段階 4 — タイミングと副作用

**適用タイミング**: orchagent 起動時および CONFIG_DB 変化時に即時反映。SAI call は同期的。

**副作用**: Switch-global な BGP 関連パラメータ (ECMP) の変更は全 BGP ネクストホップに影響する。
<!-- /runtime-trace -->
```
