# COPP_GROUP — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/copp-group.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `coppmgrd` → `CoppOrch` (APPL_DB 経由) |
| 2. CFG→APPL 翻訳 | `APP_COPP_TABLE` に書き込み (`COPP_TABLE`) |
| 3. APPL→SAI | `sai_hostif_api` — `sai_create_hostif_trap_group` でトラップグループ (policer 込み) を作成/更新 |
| 4. タイミング+副作用 | CONFIG_DB 変化を `coppmgrd` が検知後 `APP_COPP_TABLE` に書き込み。`CoppOrch` が SAI trap group... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`coppmgrd` → `CoppOrch` (APPL_DB 経由) が CONFIG_DB の `COPP_GROUP` テーブルを購読する。

`COPP_GROUP` の key はグループ名 (例: `default`, `queue4_group1`)。policer の `cir`/`cbs` を含む。

### 段階 2 — CFG→APPL 翻訳

`APP_COPP_TABLE` に書き込み (`COPP_TABLE`)

### 段階 3 — APPL→SAI

`sai_hostif_api` — `sai_create_hostif_trap_group` でトラップグループ (policer 込み) を作成/更新

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `coppmgrd` が検知後 `APP_COPP_TABLE` に書き込み。`CoppOrch` が SAI trap group を更新。既存トラップのグループ再割り当ては即時反映。

**副作用**: policer (rate/burst) 変更は CPU 宛て control plane traffic の制限に即座に影響。誤設定により制御プレーンへの過剰 traffic が発生する可能性。
<!-- /runtime-trace -->
```
