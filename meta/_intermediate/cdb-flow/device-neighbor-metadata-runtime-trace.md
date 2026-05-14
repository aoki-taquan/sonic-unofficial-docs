# DEVICE_NEIGHBOR_METADATA — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/device-neighbor-metadata.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `lldpmgrd` / `intfmgrd` / neighbor discovery |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — LLDP / neighbor テーブルのメタデータとして参照) |
| 4. タイミング+副作用 | CONFIG_DB に書き込まれると即時に参照可能。lldpmgrd が LLDP neighbor との照合に使用。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`lldpmgrd` / `intfmgrd` / neighbor discovery が CONFIG_DB の `DEVICE_NEIGHBOR_METADATA` テーブルを購読する。

`DEVICE_NEIGHBOR_METADATA` は `<device_name>` の key で hwsku / type 情報を保持。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — LLDP / neighbor テーブルのメタデータとして参照)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB に書き込まれると即時に参照可能。lldpmgrd が LLDP neighbor との照合に使用。

**副作用**: neighbor metadata の変更は LLDP 情報の表示 / 解釈に影響。ネットワーク動作への直接影響なし。
<!-- /runtime-trace -->
```
