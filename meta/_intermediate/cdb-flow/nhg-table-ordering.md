# nhg-table ordering (Phase B) — 調査メモ

## 対象ファイル
- `docs/reference/config-db/nhg-table.md`

## 調査ソース
- `sonic-swss/orchagent/nhgorch.cpp`
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp`
- `sonic-swss/fpmsyncd/routesync.cpp`

## 検出した順序依存

1. **PortsOrch 初期化ガード**: `doTask()` 先頭で `allPortsReady()` をチェック。false なら即 return（nhgorch.cpp:41、cbfnhgorch.cpp:42）。
2. **fpmsyncd 書込み順**: `m_nexthop_groupTable.set()` → `m_routeTable->set()` の順（routesync.cpp:1882-1896）。
3. **再帰 NHG 子依存**: 子未存在は `non_existent_member=true` でキューに残す（nhgorch.cpp:130-134、298-305）。子が recursive/temporary は即破棄（nhgorch.cpp:143-156）。
4. **NHG 上限 → temporary NHG**: 上限到達時は 1NH の仮グループを作成してキューに残す（nhgorch.cpp:252-281）。SRv6 は temp 非対応（nhgorch.cpp:257-261）。CBF は success=false で保留（cbfnhgorch.cpp:100-104）。
5. **CBF selection_map 依存**: MAP 未存在で `return false` → 再試行（cbfnhgorch.cpp:321-324）。
6. **CBF hasTemps() 監視**: temp メンバーが残る間 success=false（cbfnhgorch.cpp:113-121）。
7. **DEL + pending SET**: `m_toSync.count(key) > 1` で DEL をスキップ（nhgorch.cpp:402-404）。
8. **ref_count による DEL ガード**: `ref_count > 0` の間は DEL 保留（nhgorch.cpp:414-416）。
