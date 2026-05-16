# NEXTHOP_GROUP / CBF_NHG / NHG_MAP — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-nhg-orch-next2)
ソース: `sonic-net/sonic-swss/orchagent/nhgorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

### NhgOrch — SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `nexthop_group` と `nexthop`/`ifname` が共存（再帰 NHG と通常 NHG フィールド混在） | `doTask()` | erase（永久破棄） | `SWSS_LOG_ERROR("Nexthop group %s has both regular(ip/alias) and recursive fields")` | `nhgorch.cpp:98–103` |
| SRv6 NHG で `nexthop` 数と `seg_src` 数が不一致 | `doTask()` | erase（永久破棄） | `SWSS_LOG_ERROR("inconsistent number of endpoints and srv6_srcs.")` | `nhgorch.cpp:209–214` |
| 再帰 NHG のメンバー NHG が recursive または temporary | `doTask()` | erase（永久破棄） | `SWSS_LOG_ERROR("Invalid member nexthop group %s in parent nhg %s")` | `nhgorch.cpp:139–157` |
| 再帰 NHG で異なる型（SRv6 と非 SRv6、overlay と非 overlay）が混在 | `doTask()` | erase（永久破棄） | `SWSS_LOG_ERROR("Inconsistent nexthop group type between %s and %s")` | `nhgorch.cpp:175–198` |
| 再帰 NHG の全メンバー NHG が未登録 | `doTask()` | `++it` silent retry | ログなし | `nhgorch.cpp:160–164` |
| NHG 数上限到達時、SRv6 NHG を作成しようとした | `doTask()` | `++it` retry（temp NHG も作成しない） | `SWSS_LOG_DEBUG("Next hop group count reached its limit.")` | `nhgorch.cpp:252–260` |
| NHG 数上限到達時、temp NHG sync 失敗 | `doTask()` | `++it` retry | `SWSS_LOG_INFO("Failed to sync temporary NHG %s with %s")` | `nhgorch.cpp:271–275` |
| NHG 数上限到達時、createTempNhg に有効 NH が 0 | `createTempNhg()` | `std::logic_error` throw → 呼び出し元 catch → `++it` retry | `SWSS_LOG_INFO("Got exception: ... while adding temp group %s")` | `nhgorch.cpp:277–282, 844–849` |
| SAI `create_next_hop_group` 失敗 | `NextHopGroup::sync()` | `handleSaiCreateStatus()` → `parseHandleSaiStatusFailure()` — `task_need_retry` なら retry | `SWSS_LOG_ERROR("Failed to create next hop group %s, rv:%d")` | `nhgorch.cpp:782–791` |
| `syncMembers()` でメンバーの NH ID が NULL | `syncMembers()` | `success=false` → sync() が false → `++it` retry | `SWSS_LOG_WARN("Failed to get next hop %s in group %s")` | `nhgorch.cpp:937–944` |
| bulk create 後に返った SAI メンバー ID が NULL（部分失敗） | `syncMembers()` | `success=false` 部分適用状態で retry | `SWSS_LOG_ERROR("Failed to create next hop group %s's member %s")` | `nhgorch.cpp:973–977` |
| 単一メンバー NHG（非再帰）で NH ID が NULL | `NextHopGroup::sync()` | `return false` → retry | `SWSS_LOG_WARN("Next hop %s is not synced")` | `nhgorch.cpp:746–749` |
| 未解決ネイバー（IP NHG 未作成・ラベル付き NH） | `NextHopGroupMember::getNhId()` | `gNeighOrch->resolveNeighbor()` 呼び出し + SAI_NULL_OBJECT_ID 返却 | `SWSS_LOG_INFO("Failed to get next hop %s, resolving neighbor")` | `nhgorch.cpp:583–586` |
| SRv6 Nexthop 作成失敗 | `NextHopGroupMember::getNhId()` | SAI_NULL_OBJECT_ID 返却 → メンバー sync 失敗として処理 | `SWSS_LOG_ERROR("Failed to create SRv6 nexthop %s")` | `nhgorch.cpp:551–553` |
| weight 更新失敗（update 時） | `NextHopGroup::update()` | `return false` → retry | `SWSS_LOG_WARN("Failed to update member %s weight")` | `nhgorch.cpp:1042–1045` |
| 旧メンバー削除失敗（update 時） | `NextHopGroup::update()` | `return false` → retry（削除済み SAI メンバーは部分的に残る可能性あり） | `SWSS_LOG_WARN("Failed to remove members from group %s")` | `nhgorch.cpp:1057–1060` |
| 新メンバー sync 失敗（update 時） | `NextHopGroup::update()` | `return false` → retry | `SWSS_LOG_WARN("Failed to sync new members for group %s")` | `nhgorch.cpp:1080–1083` |

### NhgOrch — DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| DEL 対象 NHG が参照中（ref_count > 0） | `doTask()` | `success=false` → retry（参照解除まで削除不可） | `SWSS_LOG_INFO("Unable to remove group %s which is referenced")` | `nhgorch.cpp:413–417` |
| DEL 対象 NHG が未登録 | `doTask()` | erase（冪等、retry なし） | `SWSS_LOG_INFO("Unable to find group with key %s to remove")` | `nhgorch.cpp:407–411` |
| 同一キーに pending SET が存在 | `doTask()` | DEL スキップ → SET を適用（正しい最終状態への収束） | ログなし | `nhgorch.cpp:401–405` |

### CbfNhgOrch — 失敗経路

| 失敗条件 | 結果 | ログ出力 | evidence |
|---|---|---|---|
| `members` が空または重複あり | erase（永久破棄） | `SWSS_LOG_ERROR("CBF next hop group members list is empty/not unique.")` | `cbfnhgorch.cpp:225–233` |
| NHG 数上限到達 | `++it` retry | `SWSS_LOG_WARN("Reached next hop group limit. Postponing creation.")` | `cbfnhgorch.cpp:102` |
| `selection_map` が未登録または最大インデックス >= メンバー数 | `return false` → retry | `SWSS_LOG_ERROR("FC to NHG map index %s does not exist")` 等 | `cbfnhgorch.cpp:323–330` |
| メンバー NHG が未 sync / temporary | `return false` → retry | `SWSS_LOG_WARN("CBF NHG member %s is not yet synced")` | `cbfnhgorch.cpp:637–638` |
| SAI `create_next_hop_group` (CBF) 失敗 | `handleSaiCreateStatus()` → `parseHandleSaiStatusFailure()` | `SWSS_LOG_ERROR("Failed to create CBF next hop group %s, rv %d")` | `cbfnhgorch.cpp:343–346` |

### retry 挙動まとめ

| シナリオ | retry 上限 | 備考 |
|---|---|---|
| フィールド不正（混在・不一致・invalid type） | **0 回**（erase） | CONFIG の修正が必要 |
| 再帰 NHG メンバー未登録 | なし（`m_toSync` に残留） | メンバー NHG 登録後に自動解消 |
| NHG 数上限到達（SRv6 含む） | なし（`m_toSync` に残留） | リソース解放後に自動解消 |
| SAI create / sync 失敗 | なし（retry を繰り返す） | 永続的 SAI エラーの場合は無限 retry |
| DEL — 参照中ブロック | なし（`m_toSync` に残留） | 参照元ルート削除後に自動解消 |

### 部分適用の注意

`syncMembers()` は `ObjectBulker` で bulk create を行うため、flush 後に個別 SAI ID を確認する。一部成功・一部失敗の**部分適用**が発生しうる。失敗メンバーのみ NULL ID が残り、成功メンバーは SAI に登録済みになる。

NHG update 時は旧メンバー削除後・新メンバー追加前の間、NHG は縮退状態で ASIC に存在する。この間のパケット転送は旧メンバーに基づく ECMP で継続される。

`validateNextHop` / `invalidateNextHop` は NeighOrch からコールバックで呼び出される。失敗時は即 `return false` で後続 NHG への適用を中断する。

### ECMP リソース枯渇時の暫定動作

NHG 数が上限 (`getMaxNhgCount()`) に達した場合、非 SRv6 NHG は `createTempNhg()` で代表 1 NH のみの temporary group を SAI に登録する。

1. RouteOrch はルート解決を継続できる（ECMP なしの単一 NH ルート）
2. ECMP 動作は一時的に失われる（トラフィックは 1 NH に集中）
3. リソース解放後の次 `doTask()` で temp NHG が完全 NHG に昇格

SRv6 NHG はこの暫定措置を持たないため、リソース枯渇時はルート解決そのものが保留される。

<!-- /failure -->
