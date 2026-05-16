# BFD STATE_DB — Phase B 書込み順依存スキャンノート

対象ページ: `docs/reference/config-db/bfd-state.md`
対象テーブル: `STATE_DB`
  - `BFD_SESSION_TABLE`
  - `BFD_SOFTWARE_SESSION_TABLE`
Producer: `BfdOrch` (`sonic-swss/orchagent/bfdorch.cpp`)
スキャン範囲: `BfdOrch::BfdOrch()` / `doTask(Consumer)` / `doTask(NotificationConsumer)` / `register_bfd_state_change_notification()` / `create_bfd_session()` / `retry_create_bfd_session()` / `remove_bfd_session()` / `notify_session_state_down()` / `handleTsaStateChange()` / `createSoftwareBfdSession()` / `removeAllSoftwareBfdSessions()` の全行精読

---

## 検出した順序依存・タイミング依存

### 1. constructor 起動時の STATE_DB クリア — notifier 登録より先行

- `BfdOrch::BfdOrch()` 冒頭 (`bfdorch.cpp:74-85`) で `m_stateBfdSessionTable.getKeys()` 経由で旧キーを列挙し全削除、続けて `m_stateSoftBfdSessionTable->del()` で `BFD_SOFTWARE_SESSION_TABLE` も全削除する。
- 削除完了**後** (`bfdorch.cpp:86`) に `Orch::addExecutor(bfdStateNotificatier)` で BFD 状態変化通知 (`ASIC_DB NOTIFICATIONS`) consumer を登録する。
- **順序依存（強制先行）**: 通知 consumer が動き出す前に旧 STATE_DB は確実に空となる。これにより orchagent 再起動直後の `BFD_SESSION_TABLE` には**必ず**新規セッションのみが残り、stale な `state=Up` が他の orch (vnetorch / BfdMonitorOrch) に拾われない。
- evidence: `bfdorch.cpp:74-86`

### 2. SAI BFD 通知ハンドラ登録は初回 create 時に遅延実行

- `register_state_change_notif` フラグは constructor で `false` で初期化される (`bfdorch.cpp:87`)。
- 初回 `create_bfd_session()` 呼出時 (`bfdorch.cpp:307-315`) に `register_bfd_state_change_notification()` を試行し、成功時のみフラグが `true` に立つ。失敗時はセッション作成自体が中断される (`return false`)。
- **順序依存（遅延）**: STATE_DB への初期書込み (`state=Down`) は SAI 通知ハンドラ登録**後**にしか発生しない。登録失敗時は STATE_DB に何も書かれず、bfd_session_map にも入らない。
- evidence: `bfdorch.cpp:307-315`, `bfdorch.cpp:270-303`, `bfdorch.cpp:87`

### 3. SAI BFD create 成功後にのみ STATE_DB 書込み — fvVector の組み立て順が重要

- `create_bfd_session()` は `fvVector` を `type` → `local_discriminator` → `local_addr` → `tx_interval` → `rx_interval` → `multiplier` → `multihop` の順で組み立てる (`bfdorch.cpp:418-480`)。
- `state="Down"` は最後に追加される (`bfdorch.cpp:544`)。
- その**直後** (`bfdorch.cpp:547`) で `sai_bfd_api->create_bfd_session()` を呼び、SAI 成功（または `retry_create_bfd_session()` 経由のリトライ成功）した場合に限り `bfdorch.cpp:565` で `m_stateBfdSessionTable.set(state_db_key, fvVector)` を実行する。
- **順序依存（強制）**: SAI BFD session 作成（`bfd_session_id` 取得）→ `bfd_session_map[key] = bfd_session_id` 登録 → `bfd_session_lookup` 登録 の前に **STATE_DB へ書く**。すなわち consumer は **session_map に存在しない** が `BFD_SESSION_TABLE` には現れる、という極小窓を理論上観測しうるが、orchagent はシングルスレッドのため次の event loop までは外部から見えない。
- evidence: `bfdorch.cpp:415-480`, `bfdorch.cpp:544`, `bfdorch.cpp:547-567`

### 4. SAI create 失敗 + handleSaiCreateStatus 不成功 → STATE_DB 未書込み

- `sai_bfd_api->create_bfd_session()` 失敗時は `retry_create_bfd_session()` を呼び (`bfdorch.cpp:551`)、それでも失敗の場合 `handleSaiCreateStatus(SAI_API_BFD, status)` の戻り値で挙動分岐 (`bfdorch.cpp:554-562`)。
- `handle_status != task_success` の場合は `parseHandleSaiStatusFailure()` の値を関数の戻り値として返し、`m_stateBfdSessionTable.set()` には到達しない。
- **順序依存（負の制約）**: SAI 失敗時は STATE_DB に何も書かない。CONFIG_DB から `BFD_SESSION` を投入したのに STATE_DB に現れない場合は SAI レイヤの失敗を疑う。
- evidence: `bfdorch.cpp:549-562`

### 5. SAI 通知 → `state` 書込みは事前条件（bfd_session_lookup 登録済み）に依存

- `doTask(NotificationConsumer)` は受信した `bfd_session_id` を `bfd_session_lookup[id]` で逆引きし (`bfdorch.cpp:244-251`)、その `peer` (STATE_DB キー) に対して `m_stateBfdSessionTable.hset(key, "state", ...)` を発行する (`bfdorch.cpp:252`)。
- `bfd_session_lookup[id]` の登録は `create_bfd_session()` の `bfdorch.cpp:567` で行われる。
- **順序依存（強制先行）**: SAI から「Up」通知が届く前に `create_bfd_session()` が `bfd_session_lookup` 登録まで完走している必要がある。仮に SAI 側で create 完了通知が極めて早く返った場合でも、`bfdorch.cpp:565-567` まで実行されていなければ `bfd_session_lookup[id]` が未登録となり、`session_state_lookup.at(bfd_session_lookup[id].state)` のロギング (`bfdorch.cpp:255`) で例外が出る潜在的レース余地がある（実際は orchagent シングルスレッド + NotificationConsumer も同 select loop で逐次処理のため発火しない）。
- evidence: `bfdorch.cpp:242-263`, `bfdorch.cpp:565-567`

### 6. state 変化フィルタ — 同値受信時は STATE_DB を書かない

- `doTask(NotificationConsumer)` は `state != bfd_session_lookup[id].state` のときのみ `hset` する (`bfdorch.cpp:249-263`)。
- **順序依存（冪等保証）**: SAI が同じ状態を繰り返し通知しても STATE_DB の `state` フィールドは無駄に書き直されず、`bfd_session_lookup[id].state` も更新されない。consumer (vnetorch 等) は `SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE` notify を**変化時のみ**受け取る。
- evidence: `bfdorch.cpp:249-263`

### 7. TSA 有効化 → `notify_session_state_down()` → `remove_bfd_session()` の順序

- `handleTsaStateChange(true)` (`bfdorch.cpp:683-704`) は `bfd_session_cache` を走査し、各セッションについて先に `notify_session_state_down(key)` を呼んでから `remove_bfd_session(key)` を呼ぶ。
- `notify_session_state_down()` は STATE_DB を直接更新せず、`SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE` を `SAI_BFD_SESSION_STATE_DOWN` で観測者に伝播する (`bfdorch.cpp:677-680`)。
- `remove_bfd_session()` (`bfdorch.cpp:609-634`) は SAI 側 remove 成功後に `m_stateBfdSessionTable.del(bfd_session_lookup[bfd_session_id].peer)` で STATE_DB から削除する。
- **順序依存（強制）**: consumer は「**先に Down 通知** を受け取り、**その後で** STATE_DB エントリが消える」順で観測する。先に STATE_DB エントリを消してから Down notify するのではない。これにより consumer が `state=Up` のスナップショットを保持した状態でエントリが消える「孤立 Up」を防ぐ。
- evidence: `bfdorch.cpp:683-704`, `bfdorch.cpp:609-634`, `bfdorch.cpp:658-681`

### 8. TSA 解除 → `create_bfd_session()` の replay は cache 順

- `handleTsaStateChange(false)` (`bfdorch.cpp:696-702`) は `bfd_session_cache` の iteration 順で `create_bfd_session()` を再実行する。
- **順序依存（非決定）**: `bfd_session_cache` は unordered map の場合がある（`bfdorch.h` 定義依存）。consumer から見ると TSA 解除後の `local_discriminator` 連番は**元の作成順とは異なる**可能性がある (`bfd_gen_id()` は静的カウンタなので、再 create のたびに新規 ID が振られる)。
- evidence: `bfdorch.cpp:696-702`, `bfdorch.cpp:641-645`

### 9. software BFD と SAI BFD は同一 key で共存しない — 経路は `use_software_bfd` で固定

- `doTask(Consumer)` の冒頭 (`bfdorch.cpp:116-120`) で `bgp_global_state_orch->getSoftwareBfd()` を取得し、`true` のときは `createSoftwareBfdSession()` 経路 (`bfdorch.cpp:706-710`)、`false` のときは `create_bfd_session()` 経路に流す。
- **順序依存**: 同一 BFD key について `BFD_SESSION_TABLE` と `BFD_SOFTWARE_SESSION_TABLE` の両方が同時に書かれることはない。`use_software_bfd` の途中切替が起きた場合も、constructor のクリーンアップが次回起動時に効くため stale なエントリは残らない。
- evidence: `bfdorch.cpp:74-85`, `bfdorch.cpp:114-122`, `bfdorch.cpp:706-710`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | constructor の STATE_DB 全削除 → notifier 登録 | 強制先行 | 起動直後の stale state を consumer が拾わない |
| 2 | 初回 create での SAI 通知ハンドラ登録 → STATE_DB 書込み | 遅延（初回のみ） | 登録失敗時は STATE_DB 未書込み |
| 3 | SAI BFD create 成功 → STATE_DB `state=Down` set → session_map / session_lookup 登録 | 強制先行（STATE_DB が先） | orchagent シングルスレッドのため外部観測窓なし |
| 4 | SAI create 失敗 → STATE_DB 未書込み | 負の制約 | エラー時は `BFD_SESSION_TABLE` に現れない |
| 5 | `bfd_session_lookup` 登録 → SAI 通知 → `hset(state)` | 強制先行 | シングルスレッド select loop で保証 |
| 6 | 同一 state 通知 → STATE_DB 書込みスキップ | 冪等 | consumer は変化時のみ notify を受信 |
| 7 | TSA 有効化: Down notify → STATE_DB del | 強制（notify が先） | 孤立 Up 状態を防ぐ |
| 8 | TSA 解除での replay: cache iteration 順 | 非決定 | `local_discriminator` は新規連番に置換 |
| 9 | `use_software_bfd` フラグで経路固定 | 排他 | 同 key 二重書込みなし |

---

## ページ反映方針

- `<!-- ordering -->` ブロックを `<!-- value-behavior -->` の直後・`<!-- defaults -->` の直前に挿入する。
- サマリ表 + 主要制約の散文（依存 #1 / #3 / #5 / #7 を主軸）を含める。
- 既存の `<!-- cdb-mermaid -->` / `<!-- value-behavior -->` / `<!-- defaults -->` / `<!-- cdb-exceptions -->` / `<!-- ref-triangle -->` / `<!-- ops-hint -->` ブロックは触らない。
- frontmatter は `last_verified: 2026-05-16` に更新。
