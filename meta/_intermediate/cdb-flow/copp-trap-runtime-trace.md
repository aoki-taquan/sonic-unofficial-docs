# COPP_TRAP — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/copp-trap.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `coppmgrd` → `CoppOrch` (APPL_DB 経由) |
| 2. CFG→APPL 翻訳 | `APP_COPP_TABLE` に書き込み |
| 3. APPL→SAI | `sai_hostif_api` — `sai_create_hostif_trap` でトラップ (BGP/ARP/OSPF 等) を作成/更新 |
| 4. タイミング+副作用 | CONFIG_DB 変化を `coppmgrd` が検知後 APPL_DB に書き込み。`CoppOrch` が SAI hostif trap を更新。`FE... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`coppmgrd` → `CoppOrch` (APPL_DB 経由) が CONFIG_DB の `COPP_TRAP` テーブルを購読する。

`COPP_TRAP` の key はトラップ名 (例: `bgp`, `arp_req`, `lldp`)。`COPP_GROUP` を `trap_group` フィールドで参照。

### 段階 2 — CFG→APPL 翻訳

`APP_COPP_TABLE` に書き込み

### 段階 3 — APPL→SAI

`sai_hostif_api` — `sai_create_hostif_trap` でトラップ (BGP/ARP/OSPF 等) を作成/更新

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `coppmgrd` が検知後 APPL_DB に書き込み。`CoppOrch` が SAI hostif trap を更新。`FEATURE` テーブルの state により一部トラップが有効化される。

**副作用**: トラップの `trap_action` 変更 (`drop`/`trap`/`copy`) は直ちに該当プロトコルの CPU 転送動作に影響。`OSPF` トラップ無効化で routing protocol が停止する可能性。
<!-- /runtime-trace -->
```
