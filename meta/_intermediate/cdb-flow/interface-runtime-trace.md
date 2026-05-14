# INTERFACE — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/interface.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `intfmgrd` → `IntfsOrch` (APPL_DB 経由) |
| 2. CFG→APPL 翻訳 | `APP_INTF_TABLE` に書き込み (IP address 付き router interface) |
| 3. APPL→SAI | `sai_router_intf_api` — router interface を作成/更新 + `sai_neighbor_api` で ネイバー設定 |
| 4. タイミング+副作用 | CONFIG_DB 変化を `intfmgrd` が検知後 `APP_INTF_TABLE` に書き込み。`IntfsOrch` が APPL_DB を購読して... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`intfmgrd` → `IntfsOrch` (APPL_DB 経由) が CONFIG_DB の `INTERFACE` テーブルを購読する。

`INTERFACE` の key は `<intf_name>|<ip_prefix>` または `<intf_name>` (intf 属性のみ)。physical port の L3 設定。

### 段階 2 — CFG→APPL 翻訳

`APP_INTF_TABLE` に書き込み (IP address 付き router interface)

### 段階 3 — APPL→SAI

`sai_router_intf_api` — router interface を作成/更新 + `sai_neighbor_api` で ネイバー設定

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を `intfmgrd` が検知後 `APP_INTF_TABLE` に書き込み。`IntfsOrch` が APPL_DB を購読して SAI router interface を作成/更新。IP address 追加は即時反映。

**副作用**: IP address 追加は ARP/NDP 送信を開始。IP address 削除は関連する ARP エントリと neighbor を削除。MTU 変更は PMTUD に影響。
<!-- /runtime-trace -->
```
