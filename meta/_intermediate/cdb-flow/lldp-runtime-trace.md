# LLDP — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/lldp.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `lldpmgrd` |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — `lldpd` デーモンのグローバル設定) |
| 4. タイミング+副作用 | CONFIG_DB 変化を `lldpmgrd` が検知後、`lldpcli` でグローバル設定を注入。即時反映。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`lldpmgrd` が CONFIG_DB の `LLDP` テーブルを購読する。

`LLDP` の key は `GLOBAL` (単一エントリ)。system description / hello timer 等のグローバルパラメータ。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — `lldpd` デーモンのグローバル設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `lldpmgrd` が検知後、`lldpcli` でグローバル設定を注入。即時反映。

**副作用**: global LLDP 設定変更 (system description / chassis ID 等) は次回 LLDP PDU 送信から反映。隣接機器の LLDP テーブルが更新されるまで時間がかかる。
<!-- /runtime-trace -->
```
