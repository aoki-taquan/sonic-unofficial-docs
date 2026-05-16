# FG_NHG — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-fg-nhg)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/fgnhgorch.cpp`

### NEXTHOP 未解決 → retry（return false）

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `FG_NHG_MEMBER` 投入時に nexthop がまだ neighOrch に存在しない（ARP/NDP 未解決） | `doTaskFgNhgMember()` L2071–2073 | `SWSS_LOG_INFO` のみ、Consumer キューに残り retry | `"Nexthop %s is not resolved yet"` | `fgnhgorch.cpp:2071-2074` |
| `FG_NHG_PREFIX` 投入時に親 `FG_NHG` エントリが未受信 | `doTaskFgNhgPrefix()` L1821–1824 | `return false` → retry | `"FG_NHG entry not received yet, continue"` | `fgnhgorch.cpp:1821-1824` |
| `FG_NHG_MEMBER` 投入時に親 `FG_NHG` エントリが未受信 | `doTaskFgNhgMember()` L2004–2008 | `return false` → retry | `"FG_NHG entry not received yet, continue"` | `fgnhgorch.cpp:2004-2008` |
| prefix 移行中（APP_DB delete 後に routeorch の削除完了待ち） | `doTaskFgNhgPrefix()` L1883–1885 | `return false` → retry | `"Route(%s) ADD exists in routeorch, and APP_DB route was deleted, waiting for routeorch delete to complete"` | `fgnhgorch.cpp:1883-1885` |
| アクティブ bank がゼロ（全 bank 空で bucket 割り当て不能） | `createFgNhg()` L1067–1071 | `return false` → retry 期待 | `"Found no next-hops to add, skipping"` | `fgnhgorch.cpp:1067-1071` |

### SAI fg_nhg 操作失敗

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `createFineGrainedNextHopGroup` が失敗（SAI NHG 生成エラー） | `createFgNhg()` L275–279 | `return false`（エントリ破棄） | `"Failed to create next hop group %s"` | `fgnhgorch.cpp:275-279` |
| `SAI_NEXT_HOP_GROUP_ATTR_REAL_SIZE` クエリ失敗後クリーンアップ失敗 | `createFgNhg()` L296–305 | `return false`、NHG 削除も失敗時は追加 SWSS_LOG_ERROR | `"Failed to query next hop group %s SAI_NEXT_HOP_GROUP_ATTR_REAL_SIZE"` / `"Failed to clean-up after next hop group real_size query failure"` | `fgnhgorch.cpp:294-306` |
| SAI next hop group member 作成失敗（`create_next_hop_group_member`） | `setNewNhgMembers()` L1174–1187 | NHG 全体をロールバック（`removeFineGrainedNextHopGroup`）後 `return false` | `"Failed to create next hop group %s member %s: %d"` / `"Failed to clean-up after next-hop member creation failure"` | `fgnhgorch.cpp:1174-1187` |
| `validNextHopInNextHopGroup` 失敗（nexthop の SAI 登録失敗） | `doTaskFgNhgMember()` L2078–2084 | メンバー情報を全ロールバック、`return false` | `"Failing validNextHopInNextHopGroup for %s"` | `fgnhgorch.cpp:2078-2084` |
| Fine Grained NHG 削除失敗（`removeFineGrainedNextHopGroup`） | 複数箇所 | `return false` | `"Failed to remove nhgid %"` | `fgnhgorch.cpp:343-345` |
| SAI route 設定（packet action forward）失敗 | `setRouteDestMac()` L367–371 | `return false` | `"Failed to set route %s with packet action forward, %d"` | `fgnhgorch.cpp:367-371` |
| SAI next_hop_group_member の set（bucket 割り当て）失敗 | L241–243 | 処理継続（エラーログのみ） | `"Failed to set next hop oid %s member %s: %d"` | `fgnhgorch.cpp:241-244` |
| `removeFineGrainedNextHopGroup` 内で member 削除失敗 | `removeFineGrainedNextHopGroup()` L328–335 | `parseHandleSaiStatusFailure` に委譲（`false` の場合あり） | `"Failed to remove next hop group member %s, rv:%d"` | `fgnhgorch.cpp:328-336` |

### 不正 bucket_size

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `bucket_size == 0`（未指定または明示的に 0） | `doTaskFgNhg()` L1722–1726 | `SWSS_LOG_ERROR` → `return true`（エントリ破棄、Consumer キューに戻らず） | `"Received bucket_size which is 0 for key %s"` | `fgnhgorch.cpp:1722-1726` |
| `match_mode==prefix-based` かつ `max_next_hops==0` | `doTaskFgNhg()` L1719 | `SWSS_LOG_ERROR`（処理は継続するが SAI 動作不定） | `"Received match_mode==prefix_based with max_next_hops 0, not a supported combination"` | `fgnhgorch.cpp:1719-1721` |
| `FG_NHG_MEMBER` を `prefix-based` グループに投入 | `doTaskFgNhgMember()` L2011–2014 | `SWSS_LOG_ERROR` → `return true`（エントリ破棄） | `"Received FG_NHG member for prefix-based match_mode, not a supported operation"` | `fgnhgorch.cpp:2011-2014` |
| `FG_NHG` エントリ空名（`fg_nhg_name` が空文字） | `doTaskFgNhg()` L1816 / `doTaskFgNhgMember()` L2000 | `SWSS_LOG_ERROR` → `return true`（破棄） | `"Received FG_NHG with empty name for key %s"` | `fgnhgorch.cpp:1816,2000` |

<!-- /failure -->
