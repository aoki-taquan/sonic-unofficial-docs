# LOOPBACK_INTERFACE — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/loopback-interface.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `intfmgrd` → `IntfsOrch` (APPL_DB 経由) |
| 2. CFG→APPL 翻訳 | `APP_INTF_TABLE` に書き込み (loopback interface の IP address) |
| 3. APPL→SAI | `sai_router_intf_api` — loopback router interface を作成/更新 |
| 4. タイミング+副作用 | CONFIG_DB 変化を `intfmgrd` が検知後 `APP_INTF_TABLE` に書き込み。`IntfsOrch` が SAI loopback ... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`intfmgrd` → `IntfsOrch` (APPL_DB 経由) が CONFIG_DB の `LOOPBACK_INTERFACE` テーブルを購読する。

`LOOPBACK_INTERFACE` の key は `<lo_name>|<ip_prefix>` または `<lo_name>`。`Loopback0` が BGP router-id として使用される。

### 段階 2 — CFG→APPL 翻訳

`APP_INTF_TABLE` に書き込み (loopback interface の IP address)

### 段階 3 — APPL→SAI

`sai_router_intf_api` — loopback router interface を作成/更新

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `intfmgrd` が検知後 `APP_INTF_TABLE` に書き込み。`IntfsOrch` が SAI loopback router interface を更新。即時反映。

**副作用**: Loopback IP address は BGP の Router ID / peering source として使用される。削除すると BGP session に影響する可能性がある。
<!-- /runtime-trace -->
```
