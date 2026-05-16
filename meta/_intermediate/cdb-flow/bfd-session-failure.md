# BFD_SESSION — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-bfd-session)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/bfdorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

### SET 処理における失敗経路 (`create_bfd_session()` / `doTask()`)

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 影響 | evidence |
|---|---|---|---|---|
| BFD state change 通知 capability `get_implemented=false` または `sai_query_attribute_capability` 失敗 | `register_bfd_state_change_notification()` L280-289 | ERROR ログ → `return false` → 親 `create_bfd_session()` も `return false` → `doTask()` で `it++` 次周回再試行 | `BFD_SESSION_TABLE` 未作成 | `bfdorch.cpp:274-289, 307-313` |
| BFD 通知ハンドラ登録 SAI 失敗 (`sai_switch_api->set_switch_attribute`) | `register_bfd_state_change_notification()` L297-301 | ERROR ログ → `return false` → 次周回再試行 | 未作成 | `bfdorch.cpp:294-301` |
| 同一キーのセッションが既に `bfd_session_map` 内に存在 | `create_bfd_session()` L316-320 | ERROR ログ → `return true` (冪等扱い、no-op スキップ) | 既存エントリ維持 | `bfdorch.cpp:316-320` |
| key パース失敗: VRF デリミタなし | `create_bfd_session()` L322-327 | ERROR ログ → `return true` (恒久スキップ) | 未作成 | `bfdorch.cpp:322-327` |
| key パース失敗: interface デリミタなし | `create_bfd_session()` L329-334 | ERROR ログ → `return true` (恒久スキップ) | 未作成 | `bfdorch.cpp:329-334` |
| `type` フィールドに不正な enum 値 | `create_bfd_session()` L383-387 | ERROR ログ → 当該 attribute スキップ (他は継続) | 未作成 (致命でない場合は継続) | `bfdorch.cpp:383-387` |
| 未知/サポート外のフィールド名 | `create_bfd_session()` L404-407 | ERROR ログ → 当該 attribute スキップ | 未作成 or 部分作成 | `bfdorch.cpp:404-407` |
| `local_addr` (`src_ip_provided`) 未指定 | `create_bfd_session()` L409-413 | ERROR ログ → `return true` (恒久スキップ、再試行なし) | 未作成 | `bfdorch.cpp:409-413` |
| `interface != "default"` で PORT 未登録 (`gPortsOrch->getPort()` false) | `create_bfd_session()` L485-489 | ERROR ログ → `return false` → `doTask()` で `it++` 次周回再試行 (PORT 後追い作成で自動追従) | 未作成 | `bfdorch.cpp:485-489` |
| `interface != "default"` かつ `dst_mac` 未指定 | `create_bfd_session()` L491-496 | ERROR ログ → `return true` (恒久スキップ、不整合設定) | 未作成 | `bfdorch.cpp:491-496` |
| `interface != "default"` かつ `vrf != "default"` 併用 (hardware lookup 矛盾) | `create_bfd_session()` L498-503 | ERROR ログ → `return true` (恒久スキップ、再試行なし) | 未作成 | `bfdorch.cpp:498-503` |
| `interface == "default"` かつ `dst_mac` 指定 (hardware lookup 矛盾) | `create_bfd_session()` L523-528 | ERROR ログ → `return true` (恒久スキップ) | 未作成 | `bfdorch.cpp:523-528` |
| `vrf != "default"` で VRF 未登録 (`vrf_orch->getVRFid()` が `SAI_NULL_OBJECT_ID`) | `create_bfd_session()` L530-541 経由 SAI create | SAI 側で `SAI_STATUS_INVALID_PARAMETER` → 後段の retry/handleSaiCreateStatus 経路 | 未作成 | `bfdorch.cpp:530-541` |
| SAI `create_bfd_session` 失敗 (1 回目) — UDP src port 衝突含む | `create_bfd_session()` L547-551 | WARN ログ → `retry_create_bfd_session()` で UDP src port を変えて最大 `NUM_BFD_SRCPORT_RETRIES=3` 回再投入 | 未作成 (retry 成功時は作成) | `bfdorch.cpp:547-551, 581-588, 596-606` |
| SAI `create_bfd_session` 全 retry 失敗 (4 回連続失敗) | `create_bfd_session()` L554-562 | ERROR ログ → `handleSaiCreateStatus(SAI_API_BFD, status)` → `parseHandleSaiStatusFailure()` の戻り値で `return false` 等 → `doTask()` で `it++` または `erase` (`handleSaiCreateStatus` の判断に依存) | 未作成 | `bfdorch.cpp:554-562, 592-606` |
| `doTask()` で未知の op 文字列 (SET/DEL 以外) | `doTask()` L211-214 | ERROR ログ → `erase(it)` 次 entry へ continue (恒久スキップ) | 未作成 | `bfdorch.cpp:211-214` |

### DEL 処理における失敗経路 (`remove_bfd_session()`)

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 影響 | evidence |
|---|---|---|---|---|
| 削除対象 key が `bfd_session_map` に存在しない | `remove_bfd_session()` L611-615 | ERROR ログ → `return true` (冪等扱い、no-op スキップ) | 既に削除済み | `bfdorch.cpp:611-615` |
| SAI `remove_bfd_session` 失敗 | `remove_bfd_session()` L619-628 | ERROR ログ → `handleSaiRemoveStatus(SAI_API_BFD, status)` → `parseHandleSaiStatusFailure()` の戻り値で `return false` 等 → `doTask()` で `it++` 次周回再試行 | エントリ残存 | `bfdorch.cpp:619-628` |
| DEL key パース失敗 (VRF / ifname デリミタなし) | `remove_bfd_session()` L662-672 | ERROR ログ → `return true` (恒久スキップ) | エントリ残存 | `bfdorch.cpp:662-672` |
| `doTask()` で DEL op に `DEL on key ... is not expected` (BgpGlobalStateOrch 側) | `BgpGlobalStateOrch::doTask` L830-836 | ERROR ログ → `erase(it)` 次 entry へ continue | — | `bfdorch.cpp:830-836` |

### capability / 起動時失敗 (`BgpGlobalStateOrch`)

| 失敗条件 | 検出箇所 | 結果 | 経路への影響 | evidence |
|---|---|---|---|---|
| `SAI_SWITCH_ATTR_SUPPORTED_IPV4/IPV6_BFD_SESSION_OFFLOAD_TYPE` の `sai_query_attribute_capability` 失敗 | `checkBfdSwOrchHwSupport()` L767-772 | ERROR ログ → `return false` → `bfd_offload=false` 確定 → software BFD 経路強制 | hardware 経由不可 | `bfdorch.cpp:759-772` |
| capability `get_implemented=false` (BFD offload 未実装) | 同上 L774-777 | NOTICE ログ → `return false` → software BFD 経路強制 | 同上 | `bfdorch.cpp:774-777` |
| capability 取得後 `OFFLOAD_TYPE` 値取得失敗 | 同上 L789-790 | ERROR ログ → `return false` → software BFD 経路強制 | 同上 | `bfdorch.cpp:789-790` |

### retry / 自動追従の整理

- **UDP src port retry**: `NUM_BFD_SRCPORT_RETRIES = 3` (`bfdorch.cpp:23`)。SAI create が失敗するたびに `update_port_number()` で `bfd_src_port()` (範囲 49152–65535) から新ポートを引き直して再投入。最大 4 回 (初回 + 3 retry) 試行する。
- **doTask 周回再試行 (`return false`)**: `register_bfd_state_change_notification` 失敗、PORT 未準備、SAI create 全 retry 失敗、SAI remove 失敗 — いずれも `it++` で次イベントループ周回まで保留され、依存リソース (PORT/VRF/SAI capability) の確定後に自動成功。ログノイズに注意。
- **恒久スキップ (`return true`)**: key パース失敗、`local_addr` 未指定、`interface`/`dst_mac`/`vrf` の不整合設定、既存セッション重複 — いずれも `doTask()` で `it = consumer.m_toSync.erase(it)` 相当の処理に進み再試行されない。`local_addr` 等を後から SET し直すには DEL → SET の明示再投入が必要。

### 検出ロジック補足

- `return false` (再試行) と `return true` (確定処理) の使い分けが Phase D の中核。前者はリソース未確定 (PORT/VRF/SAI capability)、後者は設定不整合 (ユーザ入力エラー) と SAI 致命失敗に分かれる。
- `handleSaiCreateStatus` / `handleSaiRemoveStatus` は OrchAgent 共通のリトライ判断 (`parseHandleSaiStatusFailure`) を経由するため、SAI ベンダー実装による戻り値 (`SAI_STATUS_*`) によって最終挙動 (再試行 vs 恒久スキップ) が変わる。
- STATE_DB `BFD_SESSION_TABLE` への書き込みは SAI create 完了後 (`bfdorch.cpp:564-565`) なので、失敗経路では state エントリは一切作成されない。

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `SWSS_LOG_ERROR` (失敗ログ) | 19 | `bfdorch.cpp:213, 282, 288, 299, 311, 318, 325, 332, 385, 406, 411, 487, 493, 500, 525, 556, 613, 621, 664, 671, 789, 832, 836` |
| `SWSS_LOG_WARN` (retry ログ) | 1 | `bfdorch.cpp:585` |
| `return false` (再試行誘発) | 7 | `bfdorch.cpp:283, 289, 300, 312, 488, 772, 777, 790` |
| `return true` (恒久スキップ/冪等) | 7+ | `bfdorch.cpp:319, 326, 333, 412, 495, 502, 527, 574, 614, 633` |
| `SAI_STATUS_SUCCESS` 比較 | 5 | `bfdorch.cpp:280, 297, 549, 554, 601, 619, 769` |
| `NUM_BFD_SRCPORT_RETRIES` | 2 | `bfdorch.cpp:23, 596` |
| `retry_create_bfd_session` | 2 | `bfdorch.cpp:551, 592` |
| `register_bfd_state_change_notification` | 2 | `bfdorch.cpp:274, 309` |
| `sai_query_attribute_capability` | 2 | `bfdorch.cpp:276, 767` |

<!-- /failure -->
