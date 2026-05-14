# LLDP_PORT — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/lldp-port.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `lldpmgrd` |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — `lldpd` デーモンの設定を更新) |
| 4. タイミング+副作用 | CONFIG_DB 変化を `lldpmgrd` が検知後、`lldpcli` コマンドで `lldpd` に設定を注入。即時反映。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`lldpmgrd` が CONFIG_DB の `LLDP_PORT` テーブルを購読する。

`LLDP_PORT` の key は `<port>` (例: `Ethernet0`)。ポート毎の LLDP 動作 (rx/tx/rxtx/disabled) を設定。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — `lldpd` デーモンの設定を更新)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `lldpmgrd` が検知後、`lldpcli` コマンドで `lldpd` に設定を注入。即時反映。

**副作用**: LLDP port 設定変更は次回 LLDP PDU 送受信から反映。`lldp_enable` 変更でポート毎に LLDP を有効/無効化可能。
<!-- /runtime-trace -->
```
