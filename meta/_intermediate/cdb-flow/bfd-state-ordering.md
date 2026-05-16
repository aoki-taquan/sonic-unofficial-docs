# BFD_SESSION_TABLE (STATE_DB) — Phase B 書込み順依存スキャンノート

対象テーブル: STATE_DB `BFD_SESSION_TABLE`
Writer: `BfdOrch::create_bfd_session()` / `BfdOrch::doTask(NotificationConsumer&)` (`sonic-swss/orchagent/bfdorch.cpp`)
スキャン範囲: L49-88 (コンストラクタ/クリーンアップ), L111-218 (doTask Consumer), L220-268 (doTask NotificationConsumer), L305-574 (create_bfd_session), L609-634 (remove_bfd_session), L683-704 (handleTsaStateChange) を精読

---

## 検出した順序依存・タイミング依存

### 1. SAI セッション作成が STATE_DB 書込みより先行する（セッション作成経路）

- `create_bfd_session()` L544-565: `fvVector` に `state = "Down"` を最後に追加した**後**、`sai_bfd_api->create_bfd_session()` を呼び、成功した場合のみ `m_stateBfdSessionTable.set(state_db_key, fvVector)` する。
- → STATE_DB への初期書込みは SAI create の成否に依存する。SAI create が失敗（3 回リトライ後も）した場合、STATE_DB に一切書き込まれない。
- フィールド書込み順（fvVector 追加順）:
  1. `type` (L418)
  2. `local_discriminator` (L424)
  3. `local_addr` (L445)
  4. `tx_interval` (L454)
  5. `rx_interval` (L459)
  6. `multiplier` (L464)
  7. `multihop` (L475 or L479)
  8. `state = "Down"` (L544) ← **最後に追加**
- その後 `m_stateBfdSessionTable.set(state_db_key, fvVector)` で全フィールドを**一括書込み** (L565)。中間状態は見えない。
- evidence: `bfdorch.cpp:418-544, 565`

### 2. SAI 通知受信による `state` 単独更新（通知経路）

- `doTask(NotificationConsumer&)` L252: SAI `bfd_session_state_change` 通知を受信すると `m_stateBfdSessionTable.hset(key, "state", ...)` で `state` フィールド**のみ**を上書きする。
- 他の静的フィールド（`type`, `local_discriminator`, `tx_interval` 等）は変更しない。
- 前提条件: `bfd_session_lookup[id]` が存在すること（= `create_bfd_session()` 完了後）。`id` が未登録なら `bfd_session_lookup[id].state` は `std::map` のデフォルト値 (0 = `SAI_BFD_SESSION_STATE_ADMIN_DOWN` 相当) を返すため、誤通知を受けても `state != bfd_session_lookup[id].state` の比較が成立すれば誤書込みが発生する可能性がある。
- evidence: `bfdorch.cpp:249-262`

### 3. orchagent 再起動時のクリーンアップが先行する

- コンストラクタ (L74-84): `m_stateBfdSessionTable.getKeys(keys)` で既存エントリを全列挙し、`m_stateBfdSessionTable.del(alias)` で**全削除**してから通常処理を開始する。
- → orchagent 起動時は STATE_DB `BFD_SESSION_TABLE` が一時的に空になる。`vnetorch` 等の consumer が同タイミングで参照すると、全セッションが Down 扱いになる瞬間がある。
- evidence: `bfdorch.cpp:74-84`

### 4. TSA enter 時の STATE_DB エントリ削除順序

- `handleTsaStateChange(true)` L688-694: `bfd_session_cache` 全件走査で `bfd_session_map` に存在するセッションを `notify_session_state_down(key)` → `remove_bfd_session(key)` の順で処理する。
- `notify_session_state_down()` (L658-681) は STATE_DB を書き換えず、`Subject::notify(SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE, ...)` で内部 observer へ Down 通知を送るのみ（STATE_DB の `state` フィールドは変更しない）。
- `remove_bfd_session()` (L629): `m_stateBfdSessionTable.del(state_db_key)` でエントリを削除。
- → TSA enter 時の STATE_DB 上の変化は「Down 通知なしでエントリが消える」ではなく、「内部 observer への Down 通知 → STATE_DB エントリ削除」の順。STATE_DB を polling する外部 consumer は `state = "Down"` を経由せずエントリが消える点に注意。
- evidence: `bfdorch.cpp:688-694, 629, 658-681`

### 5. TSA exit 時の再作成順序（辞書順）

- `handleTsaStateChange(false)` L697-703: `bfd_session_cache`（`std::map<string, ...>`）のキー辞書順で `create_bfd_session()` を再呼び出しする。
- 各 `create_bfd_session()` は STATE_DB に一括書込みするため、辞書順での順次再出現となる。
- evidence: `bfdorch.cpp:686, 697-703`

### 6. DEL 時の STATE_DB 削除は SAI remove 成功後

- `remove_bfd_session()` (L618-633): `sai_bfd_api->remove_bfd_session(bfd_session_id)` が成功した場合のみ `m_stateBfdSessionTable.del(...)` を呼ぶ。SAI remove 失敗時は STATE_DB エントリが残存する（`return false` で `doTask` の `it++` 再試行ループへ）。
- evidence: `bfdorch.cpp:618-631`

---

## 書込み順序サマリ

| フェーズ | STATE_DB 操作 | 前提条件 | evidence |
|---|---|---|---|
| orchagent 起動 | 全エントリ削除（クリーンアップ） | なし | bfdorch.cpp:74-84 |
| SET 受信（hardware BFD）| SAI create 成功後、全フィールド一括 `set` | SAI capability, PORT/VRF 解決済み | bfdorch.cpp:547-565 |
| SET 受信（software BFD）| `BFD_SOFTWARE_SESSION_TABLE` に転記のみ（本テーブルには書かない）| BgpGlobalStateOrch 起動済み | bfdorch.cpp:136 |
| SAI 通知受信 | `hset(key, "state", ...)` で state のみ更新 | create 完了済み | bfdorch.cpp:252 |
| TSA enter | notify_session_state_down（内部通知）→ del（エントリ削除）| shutdown_bfd_during_tsa==true のセッションのみ | bfdorch.cpp:692-693 |
| TSA exit | `create_bfd_session` 再投入（辞書順、全フィールド一括 set）| SAI capability, PORT/VRF 再解決 | bfdorch.cpp:700 |
| DEL 受信 | SAI remove 成功後 `del` | セッション存在確認済み | bfdorch.cpp:618-629 |
