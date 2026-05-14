# LDAP_SERVER — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/ldap-server.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `hostcfgd` の `LdapHandler` |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — `nslcd` / LDAP クライアント設定を更新) |
| 4. タイミング+副作用 | CONFIG_DB 変化を検知後、LDAP クライアント設定ファイルを更新して `nslcd` を再起動。次回 LDAP 認証から新設定が有効。... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`hostcfgd` の `LdapHandler` が CONFIG_DB の `LDAP_SERVER` テーブルを購読する。

`LDAP_SERVER` の key は LDAP server の IP アドレス。複数サーバをリストで指定可能。`AAA` テーブルで `login` に `ldap` を含む場合に有効。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — `nslcd` / LDAP クライアント設定を更新)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を検知後、LDAP クライアント設定ファイルを更新して `nslcd` を再起動。次回 LDAP 認証から新設定が有効。

**副作用**: `nslcd` 再起動中は LDAP 認証が一時中断。既存 SSH session は影響なし (PAM session は認証完了済み)。
<!-- /runtime-trace -->
```
