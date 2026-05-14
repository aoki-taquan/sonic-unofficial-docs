# FABRIC_PORT — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/fabric-port.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `fabricmgrd` → `FabricPortsOrch` (APPL_DB 経由) |
| 2. CFG→APPL 翻訳 | `APP_FABRIC_MONITOR_PORT_TABLE` に書き込み |
| 3. APPL→SAI | fabric 固有 SAI (fabric port enable/isolate) |
| 4. タイミング+副作用 | CONFIG_DB 変化を `fabricmgrd` が検知後 APPL_DB に書き込み。`FabricPortsOrch` が SAI fabric por... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`fabricmgrd` → `FabricPortsOrch` (APPL_DB 経由) が CONFIG_DB の `FABRIC_PORT` テーブルを購読する。

`FABRIC_PORT` は Chassis の fabric ASIC ポートを管理。通常の ToR では使用しない。

### 段階 2 — CFG→APPL 翻訳

`APP_FABRIC_MONITOR_PORT_TABLE` に書き込み

### 段階 3 — APPL→SAI

fabric 固有 SAI (fabric port enable/isolate)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `fabricmgrd` が検知後 APPL_DB に書き込み。`FabricPortsOrch` が SAI fabric port attribute を更新。

**副作用**: `admin_status` 変更は fabric link の up/down に直結。isolate 設定は traffic の再ルーティングを引き起こす。
<!-- /runtime-trace -->
```
