# ERSPAN (MIRROR_SESSION) — Phase D 失敗挙動調査

調査日: 2026-05-18  
対象: `sonic-swss/orchagent/mirrororch.cpp` (master)

## createEntry 失敗パス

| 行番号 | 失敗条件 | 戻り値 | ログ |
|--------|---------|--------|------|
| 391-392 | セッション名が既に `m_syncdMirrors` に存在 | `task_duplicated` | NOTICE "Failed to create session %s: object already exists" |
| 428-429 | `queue` 値が `m_maxNumTC` 以上 | `task_invalid_entry` | ERROR "Failed to get valid queue %s" |
| 436-438 | `policer` 名が PolicerOrch に未登録 | `task_need_retry` | ERROR "Failed to get policer %s" |
| 447-449 | `src_port` のポートが PortsOrch に存在しない / PHY・LAG 以外 | `task_invalid_entry` | ERROR "Failed to locate Port/LAG %s" / "Not supported port type %d" |
| 455-458 | `dst_port` のポートが存在しない / PHY 以外 | `task_invalid_entry` | ERROR "Not supported port %s type %d" |
| 466-468 | `direction` が RX/TX/BOTH 以外 | `task_invalid_entry` | ERROR "Failed to get valid direction %s" |
| 477-479 | 不明フィールド名 | `task_invalid_entry` | ERROR "Failed to parse session %s configuration. Unknown attribute %s" |
| 483-485 | フィールド値の数値変換で std::exception | `task_invalid_entry` | ERROR "Failed to parse session %s attribute %s error: %s." |
| 488-490 | フィールド値の数値変換で不明例外 | `task_failed` | ERROR "Failed to parse session %s attribute %s. Unknown error has been occurred" |
| 494-497 | src_ip / dst_ip のアドレスファミリ不一致 | `task_invalid_entry` | ERROR "Address family of source and destination IPs is different" |
| 500-503 | isHwResourcesAvailable() が false | `task_failed` | ERROR "Failed to create session %s: HW resources are not available" |

## deleteEntry 失敗パス

| 行番号 | 失敗条件 | 戻り値 | ログ |
|--------|---------|--------|------|
| 532-534 | 存在しないセッション名を DEL | `task_invalid_entry` | ERROR "Failed to remove non-existent mirror session %s" |
| 541-543 | refCount > 0 (ACL_RULE 等から参照中) | `task_need_retry` | WARN "Failed to remove still referenced mirror session %s, retry..." |
| 549-551 | deactivateSession() が false | `task_failed` | ERROR "Failed to remove mirror session %s" |

## activateSession 失敗パス (ERSPAN 固有)

| 行番号 | 失敗条件 | 結果 |
|--------|---------|------|
| 656-664 | getNeighborInfo() が false (ARP/ND 未解決) | false 返却 → INACTIVE 維持（非同期回復） |
| 966-967 | VoQ スイッチで recirc ポート取得失敗 | false 返却 |
| 1052-1060 | policer OID 取得失敗 | false 返却 → INACTIVE 維持 |
| 1070-1077 | sai_mirror_api->create_mirror_session() エラー | INACTIVE / SAI エラー |

## doTask ループの retry 設計

`mirrororch.cpp:1599-1604`: `task_need_retry` の場合のみ `it++`（キューに残す）。それ以外は `consumer.m_toSync.erase(it++)`（キューから除去）。

## allPortsReady ガード

`mirrororch.cpp:1571-1574`: doTask() 冒頭で `gPortsOrch->allPortsReady()` が false の間は即 return。エラーログなし。
