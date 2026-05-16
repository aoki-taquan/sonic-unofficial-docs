# NEIGH — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-neighbor)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/neighorch.cpp`

### SET 処理における失敗経路（addNeighbor）

| 失敗条件 | 検出箇所 | 結果 | retry | evidence |
|---|---|---|---|---|
| INTERFACE が未解決（`getRouterIntfsId` が `SAI_NULL_OBJECT_ID` を返す） | `addNeighbor()` L1204-1208 | `return false` → Consumer が `it++` でエントリを保留し次 tick で再試行 | あり（自動再試行） | `neighorch.cpp:1205-1208` |
| MAC アドレスがゼロ（`!mac_address`）かつ既存 neighbor の場合 | `doTask()` L986-992 | エントリを `m_toSync` から erase（silent drop、再試行なし）。カーネルに「削除後に zero MAC 更新が来ることを期待」との設計コメント | なし | `neighorch.cpp:986-991` |
| 同一 IP が別 VLAN に存在し `removeNeighbor` 失敗 | `addNeighbor()` L1300-1304 | `return false` → Consumer が保留・再試行 | あり | `neighorch.cpp:1300-1304` |
| `sai_neighbor_api->create_neighbor_entry` が `SAI_STATUS_ITEM_ALREADY_EXISTS` | `addNeighbor()` L1337-1342 | エラーログ出力後 `return true`（retry をスキップ、重複は正常扱い） | なし（skip） | `neighorch.cpp:1337-1342` |
| `sai_neighbor_api->create_neighbor_entry` がその他 SAI エラー | `addNeighbor()` L1346-1352 | `handleSaiCreateStatus` → `task_success` 以外なら `parseHandleSaiStatusFailure` で `return false` | SAI ポリシー依存 | `neighorch.cpp:1346-1352` |
| `addNextHop` 失敗（next hop 作成失敗）後の neighbor ロールバック | `addNeighbor()` L1370-1394 | `sai_neighbor_api->remove_neighbor_entry` でロールバック試行。ロールバックも失敗すれば `return false` | なし（`addNextHop` 失敗時は `return false`） | `neighorch.cpp:1370-1395` |
| prefix route 追加 (`addPrefixRouteForNeighbor`) 失敗 | `addNeighbor()` L1401-1404 | `return false` → Consumer 再試行 | あり | `neighorch.cpp:1401-1404` |
| SAI `set_neighbor_entry_attribute` 失敗（既存 neighbor の属性更新） | `addNeighbor()` L1413-1422 | `handleSaiSetStatus` → 失敗時 `return false` | SAI ポリシー依存 | `neighorch.cpp:1413-1422` |

### DEL 処理における失敗経路（removeNeighbor）

| 失敗条件 | 検出箇所 | 結果 | retry | evidence |
|---|---|---|---|---|
| next hop の ref_count > 0（参照中の neighbor を削除しようとした） | `removeNeighbor()` L1483-1488 | `return false` → Consumer が `it++` で保留・再試行 | あり | `neighorch.cpp:1483-1488` |
| `sai_next_hop_api->remove_next_hop` が `SAI_STATUS_ITEM_NOT_FOUND` | `removeNeighbor()` L1520-1524 | NOTICE ログのみ → neighbor entry の削除処理を継続（next hop 欠如は許容） | なし（継続） | `neighorch.cpp:1520-1524` |
| `sai_next_hop_api->remove_next_hop` がその他 SAI エラー | `removeNeighbor()` L1527-1533 | `handleSaiRemoveStatus` → 失敗時 `return false` | SAI ポリシー依存 | `neighorch.cpp:1527-1533` |
| `sai_neighbor_api->remove_neighbor_entry` が `SAI_STATUS_ITEM_NOT_FOUND` | `removeNeighbor()` L1555-1559 | NOTICE ログのみ（既に削除済み扱い）→ CRM デクリメントなし | なし（継続） | `neighorch.cpp:1555-1559` |
| `sai_neighbor_api->remove_neighbor_entry` がその他 SAI エラー | `removeNeighbor()` L1562-1568 | `handleSaiRemoveStatus` → 失敗時 `return false` | SAI ポリシー依存 | `neighorch.cpp:1562-1568` |
| DEL 操作で `m_syncdNeighbors` に対象エントリが存在しない | `doTask()` L1034-1036 | `m_toSync` から erase（silent drop、カーネル neighbor は既に削除済みと判断） | なし | `neighorch.cpp:1034-1036` |

### 特殊挙動補足

- **INTERFACE 未解決 → retry**: `rif_id == SAI_NULL_OBJECT_ID` は一時的状態（インターフェイス初期化中）。Consumer ループが `it++` で保留し次の SELECT_TIMEOUT サイクルで再処理する設計。
- **MAC 不正（ゼロ MAC + 既存 neighbor）**: 既に `m_syncdNeighbors` に存在する neighbor に対してゼロ MAC の SET が来た場合、削除なしで即 erase。これは「削除→再学習」の順序保証を前提とした設計上の制約（コメント: `neighorch.cpp:986-988`）。
- **SAI 失敗のロールバック原則**: `addNeighbor` は SAI neighbor 作成後に `addNextHop` が失敗した場合のみロールバックを行う。他の失敗ケースではロールバックなし（べき等性は SAI 側に依存）。
- **参照中 DEL のペンディング**: `removeNeighbor` が ref_count > 0 で `false` を返した後、Consumer は `it++` で同エントリを m_toSync に残す。参照が解放されるまで無限に再試行される（タイムアウトなし）。
- **SET 後の pending DEL 消去**: SET 操作成功後、`doTask` は同 key の pending DEL 操作を `m_toSync` から逆順に除去する（`neighorch.cpp:1010-1019`）。これは過去に失敗した DEL が誤って再実行されるのを防ぐ設計。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `SWSS_LOG_ERROR` (addNeighbor 関連) | 5 | `neighorch.cpp:1207, 1279, 1283, 1302, 1339, 1346, 1375, 1416` |
| `SWSS_LOG_ERROR` (removeNeighbor 関連) | 3 | `neighorch.cpp:1475, 1527, 1562` |
| `handleSaiCreateStatus` (NEIGHBOR) | 1 | `neighorch.cpp:1348` |
| `handleSaiRemoveStatus` (NEIGHBOR) | 1 | `neighorch.cpp:1564` |
| `handleSaiSetStatus` (NEIGHBOR) | 1 | `neighorch.cpp:1418` |
| `return false` (retry 起点) | 8 | `neighorch.cpp:1208, 1304, 1351, 1394, 1403, 1421, 1487, 1532, 1567` |

<!-- /failure -->
