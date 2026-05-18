# HEARTBEAT — Phase C 暗黙参照テーブルスキャンノート

対象ページ: `docs/reference/config-db/heartbeat.md`
対象テーブル: `CONFIG_DB.HEARTBEAT`
Consumer: `supervisor-proc-exit-listener` (Python: `sonic-buildimage/src/sonic-supervisord-utilities/scripts/supervisor-proc-exit-listener`、Rust: `sonic-buildimage/src/sonic-supervisord-utilities-rs/src/proc_exit_listener.rs`)
スキャン範囲: `sonic-heartbeat.yang` 全体、`supervisor-proc-exit-listener` 全体、`proc_exit_listener.rs` 全体

---

## 検出した暗黙参照・外部依存

### 1. YANG leafref なし — 外部テーブル参照ゼロ

`sonic-heartbeat.yang` の `HEARTBEAT_LIST` 定義に `leafref` は一切存在しない。
`name`（string, 1–32 文字）、`heartbeat_interval`（uint32）、`alert_interval`（uint32）の 3 leaf のみ。
外部 CONFIG_DB テーブルへのキー参照はない。

- evidence: `sonic-heartbeat.yang` 全文（leafref キーワードなし）

### 2. consumer 側の暗黙依存 — FEATURE テーブル（別読み込み）

`supervisor-proc-exit-listener` は `get_autorestart_state()` で `FEATURE` テーブルも参照するが、これは HEARTBEAT テーブルの SET/DEL 処理とは別パス。HEARTBEAT エントリの key/フィールド値が FEATURE テーブルを参照することはない。

- evidence: `supervisor-proc-exit-listener:100-122`（`get_autorestart_state` 関数）

### 3. eventd 側の依存 — ZMQ / CONFIG_DB 接続のみ

`eventd.cpp` の heartbeat 関連コードは CONFIG_DB を直接参照せず、ZeroMQ の `GLOBAL_OPTION_HEARTBEAT` JSON RPC チャンネル経由で heartbeat_interval を受け取る。CONFIG_DB の `HEARTBEAT` テーブルとは別系統。

- evidence: `eventd.cpp:638-646`（`GLOBAL_OPTION_HEARTBEAT` の JSON パース）

### 4. 被参照なし — 他テーブルから HEARTBEAT を参照するテーブルなし

CONFIG_DB の他テーブル（FEATURE、PORT、DEVICE_METADATA 等）から `HEARTBEAT|<name>` への leafref / 外部キー参照は存在しない。

---

## 暗黙参照サマリ

| 参照方向 | 参照元 | 参照先 | 依存内容 | evidence |
|---------|--------|--------|---------|---------|
| なし | — | — | HEARTBEAT テーブルは外部テーブルを参照しない（leafref ゼロ） | `sonic-heartbeat.yang` 全文 |
| 被参照なし | — | HEARTBEAT | 他の CONFIG_DB テーブルから HEARTBEAT への leafref なし | 全 YANG 検索結果 |

---

## ページ反映方針

- `<!-- cross-refs -->` ブロックを `<!-- /ordering -->` 直後に挿入する。
- 参照なしという事実を明示する簡潔な表とし、eventd の別系統 (`GLOBAL_OPTION_HEARTBEAT` ZMQ RPC) と consumer 側 FEATURE 参照を補足として記す。
