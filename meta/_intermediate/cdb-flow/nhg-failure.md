# NEXTHOP_GROUP_TABLE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-nexthop-group)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/nhgorch.cpp`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `nexthop_group` と `nexthop`/`ifname` が共存（再帰 NHG と通常 NHG のフィールド混在） | `doTask()` L98-103 | `m_toSync.erase(it)` でエントリ破棄。retry なし | `SWSS_LOG_ERROR("Nexthop group %s has both regular(ip/alias) and recursive fields")` | `nhgorch.cpp:98-103` |
| SRv6 NHG で `nexthop` 数と `seg_src` 数が不一致 | `doTask()` L209-214 | `m_toSync.erase(it)` でエントリ破棄。retry なし | `SWSS_LOG_ERROR("inconsistent number of endpoints and srv6_srcs.")` | `nhgorch.cpp:209-214` |
| 再帰 NHG のメンバー NHG が recursive または temporary な NHG | `doTask()` L139-157 | `m_toSync.erase(it)` でエントリ破棄。retry なし | `SWSS_LOG_ERROR("Invalid member nexthop group %s in parent nhg %s")` | `nhgorch.cpp:139-157` |
| 再帰 NHG で異なる型（SRv6 と非 SRv6、overlay と非 overlay）のメンバーが混在 | `doTask()` L175-198 | `m_toSync.erase(it)` でエントリ破棄。retry なし | `SWSS_LOG_ERROR("Inconsistent nexthop group type between %s and %s")` | `nhgorch.cpp:175-198` |
| 再帰 NHG の全メンバー NHG が未登録（`m_syncdNextHopGroups` に存在しない） | `doTask()` L160-164 | `++it` でスキップ。メンバー登録後に自動 retry | ログなし（silent retry） | `nhgorch.cpp:160-164` |
| NHG 数上限到達時、SRv6 NHG を新規作成しようとした | `doTask()` L257-260 | `++it` でスキップ（temp NHG も作成しない）。リソース解放後に自動 retry | `SWSS_LOG_DEBUG("Next hop group count reached its limit.")` | `nhgorch.cpp:252-260` |
| NHG 数上限到達時、非 SRv6 NHG の temporary group sync 失敗 | `doTask()` L271-275 | temporary NHG 未登録のまま `++it` でスキップ。retry | `SWSS_LOG_INFO("Failed to sync temporary NHG %s with %s")` | `nhgorch.cpp:271-275` |
| NHG 数上限到達時、createTempNhg で有効な NH が 1 つも存在しない | `createTempNhg()` L844-849 | `std::logic_error` を throw。呼び出し元が catch して `SWSS_LOG_INFO` → エントリはスキップ | `SWSS_LOG_INFO("Got exception: ... while adding temp group %s")` | `nhgorch.cpp:277-282, 844-849` |
| SAI `create_next_hop_group` 失敗（ECMP グループ作成失敗） | `NextHopGroup::sync()` L782-791 | `handleSaiCreateStatus()` 経由で `parseHandleSaiStatusFailure()`。`task_need_retry` なら retry、それ以外は false 返却 | `SWSS_LOG_ERROR("Failed to create next hop group %s, rv:%d")` | `nhgorch.cpp:782-791` |
| `syncMembers()` でいずれかのメンバーの SAI ID が NULL | `NextHopGroup::syncMembers()` L937-944 | `success = false`。`sync()` は false を返す → `doTask()` で `++it` retry | `SWSS_LOG_WARN("Failed to get next hop %s in group %s")` | `nhgorch.cpp:937-944` |
| `syncMembers()` でメンバー作成後に返った SAI ID が NULL（bulk create 失敗） | `NextHopGroup::syncMembers()` L973-977 | `success = false`。sync 済み他メンバーは SAI に残るが部分適用状態 | `SWSS_LOG_ERROR("Failed to create next hop group %s's member %s")` | `nhgorch.cpp:973-977` |
| 単一メンバー NHG（非再帰）で NH ID が SAI_NULL_OBJECT_ID | `NextHopGroup::sync()` L746-749 | `return false` → `doTask()` で retry | `SWSS_LOG_WARN("Next hop %s is not synced")` | `nhgorch.cpp:746-749` |
| 未解決ネイバー（NH ID 未登録、ラベル付き NH の IP NHG が未作成） | `NextHopGroupMember::getNhId()` L583-586 | `gNeighOrch->resolveNeighbor()` を呼び出して解決を要求。SAI_NULL_OBJECT_ID を返す | `SWSS_LOG_INFO("Failed to get next hop %s, resolving neighbor")` | `nhgorch.cpp:583-586` |
| SRv6 Nexthop 作成失敗（`createSrv6NexthopWithoutVpn` 失敗） | `NextHopGroupMember::getNhId()` L551-553, L576-578 | SAI_NULL_OBJECT_ID を返す。上位でメンバー sync 失敗として処理 | `SWSS_LOG_ERROR("Failed to create SRv6 nexthop %s")` | `nhgorch.cpp:551-553` |
| メンバーの weight 更新失敗（SAI `set_next_hop_group_member_attribute` 失敗） | `NextHopGroupMember::updateWeight()` L614-615 | `false` を返す → `update()` が `false` 返却 | ログなし（`success = status == SAI_STATUS_SUCCESS` のみ） | `nhgorch.cpp:614-615` |
| NHG update でメンバー重み更新失敗 | `NextHopGroup::update()` L1042-1045 | `return false` → `doTask()` で retry | `SWSS_LOG_WARN("Failed to update member %s weight")` | `nhgorch.cpp:1042-1045` |
| NHG update で古いメンバー削除失敗 | `NextHopGroup::update()` L1057-1060 | `return false` → `doTask()` で retry。削除済み SAI メンバーは部分的に残る可能性あり | `SWSS_LOG_WARN("Failed to remove members from group %s")` | `nhgorch.cpp:1057-1060` |
| NHG update で新メンバー sync 失敗 | `NextHopGroup::update()` L1080-1083 | `return false` → `doTask()` で retry | `SWSS_LOG_WARN("Failed to sync new members for group %s")` | `nhgorch.cpp:1080-1083` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| DEL 対象 NHG が参照元（RouteOrch 等）から参照中（ref_count > 0） | `doTask()` L413-417 | `success = false` → `m_toSync` に残り retry。参照解除まで削除不可 | `SWSS_LOG_INFO("Unable to remove group %s which is referenced")` | `nhgorch.cpp:413-417` |
| DEL 対象 NHG が存在しない（`m_syncdNextHopGroups` 未登録） | `doTask()` L407-411 | `success = true` で消費（冪等）。retry なし | `SWSS_LOG_INFO("Unable to find group with key %s to remove")` | `nhgorch.cpp:407-411` |
| DEL で `nhg->remove()` が失敗（SAI remove 失敗） | `doTask()` L421-429 | `success = false` → `m_toSync` に残り retry。`m_syncdNextHopGroups` からは erase されない | ログなし（`NhgCommon::remove()` 内部で処理） | `nhgorch.cpp:421-429` |
| DEL と同一キーに pending SET が存在 | `doTask()` L401-405 | DEL をスキップして SET を適用（正しい最終状態への収束のため） | ログなし | `nhgorch.cpp:401-405` |

### retry 挙動まとめ

| シナリオ | retry 上限 | 間隔 | 上限超過時 |
|---|---|---|---|
| 再帰 NHG メンバー未登録 | なし（`m_toSync` に残留） | 次 doTask() 呼び出し時 | ネイバー解決後に自動解消 |
| NHG 数上限到達（SRv6） | なし（`m_toSync` に残留） | 次 doTask() 呼び出し時 | リソース解放後に自動解消 |
| SAI create / sync 失敗 | なし（retry を繰り返す） | 次 doTask() 呼び出し時 | 永続的 SAI エラーの場合は無限 retry |
| DEL 参照中ブロック | なし（`m_toSync` に残留） | 次 doTask() 呼び出し時 | 参照元ルート削除後に自動解消 |
| フィールド不正（混在・不一致・invalid type） | **0 回**（erase） | — | エントリ破棄。CONFIG の修正が必要 |

### 部分適用の注意

- `syncMembers()` は bulk create を使用する (`ObjectBulker`)。bulk flush 後に個別 SAI ID を確認するため、一部成功・一部失敗の部分適用が発生しうる。失敗したメンバーのみ NULL ID が残り、成功メンバーは SAI に登録済みになる。
- NHG update 時に古いメンバー削除後・新しいメンバー追加前の間、NHG は縮退した状態で ASIC に存在する。この間にパケット転送が行われた場合、旧メンバーに基づく ECMP が継続される。
- `validateNextHop` / `invalidateNextHop` は NhgOrch が NeighOrch から呼び出される。失敗時は即 `return false` で後続 NHG への適用を中断する（`nhgorch.cpp:477-483, 513-519`）。

### ECMP リソース枯渇時の暫定動作

NHG 数が上限 (`getMaxNhgCount()`) に達した場合、非 SRv6 NHG は `createTempNhg()` で代表 1 NH のみの temporary group を SAI に登録する。これにより：

1. RouteOrch はルート解決を継続できる（ECMP なしの単一 NH ルート）
2. ECMP 動作は一時的に失われる（トラフィックは 1 NH に集中）
3. リソース解放後に `doTask()` が temp NHG を完全 NHG に昇格させる

SRv6 NHG はこの暫定措置を持たないため、リソース枯渇時はルート解決そのものが保留される。

<!-- /failure -->
