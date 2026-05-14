# NTP_KEY — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

NTP_KEY はセキュリティ上の理由から自動生成されない。管理者が CLI で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### hostcfgd — NtpCfg (NTP_KEY 購読)

`NtpCfg` が NTP_KEY を購読 (hostcfgd:1282 付近の `__init__` 内)。常時登録、条件なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### NtpCfg — NTP_KEY ハンドラ分岐

| 操作 | 処理 |
|------|------|
| SET | `/etc/ntp.keys` にキー行追記 + `ntpd` リロード |
| DEL | `ntp.keys` から該当行削除 + `ntpd` リロード |

early return: `key_id` が数値でない / `key_type` が `md5`/`sha1` 以外 → エラーログして return。

<!-- /handler-branching -->
