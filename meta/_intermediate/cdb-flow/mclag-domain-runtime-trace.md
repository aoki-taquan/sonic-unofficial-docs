# MCLAG_DOMAIN — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/mclag-domain.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `MlagOrch` (orchagent 直接 CFG 購読) + `mclagsyncd` |
| 2. CFG→APPL 翻訳 | なし (orchagent が直接 CONFIG_DB を購読) |
| 3. APPL→SAI | `sai_fdb_api` (FDB 同期) + `mclagsyncd` が MCLAG ピアとの制御接続を管理 |
| 4. タイミング+副作用 | orchagent が CONFIG_DB 変化を検知後、MCLAG セッションのネゴシエーションを開始。`mclagsyncd` が ICCP (Inter-... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`MlagOrch` (orchagent 直接 CFG 購読) + `mclagsyncd` が CONFIG_DB の `MCLAG_DOMAIN` テーブルを購読する。

`MCLAG_DOMAIN` の key は domain ID (例: `1`)。`peer_link` / `peer_ip` / `source_ip` / `session_timeout` 等を保持。

### 段階 2 — CFG→APPL 翻訳

なし (orchagent が直接 CONFIG_DB を購読)

### 段階 3 — APPL→SAI

`sai_fdb_api` (FDB 同期) + `mclagsyncd` が MCLAG ピアとの制御接続を管理

### 段階 4 — タイミングと副作用

**適用タイミング**: orchagent が CONFIG_DB 変化を検知後、MCLAG セッションのネゴシエーションを開始。`mclagsyncd` が ICCP (Inter-Chassis Control Protocol) 接続を確立。非同期で完了。

**副作用**: MCLAG domain の peer IP/source IP 変更は ICCP session reset を引き起こす。ICCP session reset 中は MCLAG で同期していた FDB/ARP が失われる可能性がある。
<!-- /runtime-trace -->
```
