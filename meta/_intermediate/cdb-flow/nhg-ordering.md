# NEXTHOP_GROUP_TABLE (APPL_DB) — Phase B 書込み順依存スキャンノート

対象ページ: `docs/reference/config-db/nhg.md`
対象テーブル: `APPL_DB`
  - `NEXTHOP_GROUP_TABLE`
Producer: `fpmsyncd` (`routesync.cpp`), Consumer/Orch: `NhgOrch` (`sonic-swss/orchagent/nhgorch.cpp`)
スキャン範囲: `NhgOrch::doTask()` / `NextHopGroup::sync()` / `NextHopGroup::update()` / `NextHopGroup::syncMembers()` / `NextHopGroup::remove()` / `NhgOrch::validateNextHop()` / `NhgOrch::invalidateNextHop()` / `createTempNhg()` の全行精読

---

## 検出した順序依存・タイミング依存

### 1. 再帰 NHG — メンバー NHG の先行登録が必須

- 再帰 NHG (`nexthop_group` フィールドあり) を処理する際、`doTask()` は各メンバー NHG が `m_syncdNextHopGroups` に登録済みかを確認する (`nhgorch.cpp:L130`)。
- 未登録メンバーが存在する場合、**全メンバー未登録** → `++it` で silent retry。**一部未登録** → 存在するメンバーのみで partial NHG を即時作成し `m_syncdNextHopGroups` に登録する (`nhgorch.cpp:L160-164`, `L296-302`)。
- **順序依存（強制）**: メンバー NHG エントリが `NEXTHOP_GROUP_TABLE` に先行して書き込まれていなければ、親 NHG は解決されないか部分解決状態になる。`fpmsyncd` が再帰 NHG を書き込む前にメンバー NHG を書き込む保証がなければ、consumer (`RouteOrch`) から見てルートの nexthop group が暫定的に縮退した状態で観測される。
- evidence: `nhgorch.cpp:L118-164`

### 2. ROUTE_TABLE → NEXTHOP_GROUP_TABLE の依存逆転

- `ROUTE_TABLE`（APPL_DB）の `nexthop_group` フィールドは `NEXTHOP_GROUP_TABLE` のキーを参照する。`RouteOrch` がルートを処理する際、NHG が未解決の場合は `m_toSync` に残留して待機する。
- **順序依存（逆転リスク）**: `fpmsyncd` が NHG エントリを書き込む前に `ROUTE_TABLE` の `nexthop_group` 参照が先に届くと、`RouteOrch` はルートを一時的に解決不能として処理を延期する。NHG エントリ到着後に自動解消されるが、起動シーケンス中や FRR 再接続直後に生じやすい。
- evidence: `nhgorch.cpp:L14` (`extern RouteOrch *gRouteOrch`), `routeorch.cpp` NHG 参照解決ロジック

### 3. DEL 前に ROUTE_TABLE からの参照解除が必要

- NHG の DEL_COMMAND は `nhg_it->second.ref_count > 0` の間は `success = false` でブロックされる (`nhgorch.cpp:L413-417`)。
- **順序依存（強制）**: NHG を削除するには、先に NHG を参照しているすべてのルート（`ROUTE_TABLE`）が削除または他の NHG に切り替わって参照カウントが 0 になる必要がある。`fpmsyncd` が ROUTE_TABLE DEL → NHG DEL の順で書かなければ NHG は削除されずに残留する。
- evidence: `nhgorch.cpp:L392-430`

### 4. DEL と後続 SET が競合する場合 — DEL をスキップ

- 同一キーに対して DEL の後に SET が `m_toSync` にキューされている場合（`consumer.m_toSync.count(it->first) > 1`）、DEL 処理をスキップして SET を適用する (`nhgorch.cpp:L401-405`)。
- **順序依存（自動調停）**: `fpmsyncd` が短い間隔で DEL → SET を送信した場合、`m_toSync` 内のキュー状態次第で DEL がスキップされ最終状態（SET 後の値）に収束する。consumer から見ると DEL が「透過」したように見える。
- evidence: `nhgorch.cpp:L401-405`

### 5. NeighOrch → NhgOrch の ARP/NDP 解決イベント

- `NhgOrch::validateNextHop(nh_key)` は `NeighOrch` が ARP/NDP 解決を通知した際に呼ばれ、そのネクストホップを含むすべての NHG を走査して `syncMembers()` を実行し SAI メンバーを追加する (`nhgorch.cpp:L466-487`)。
- `NhgOrch::invalidateNextHop(nh_key)` はインタフェース DOWN 等でネクストホップが失効した際に呼ばれ、関連メンバーを SAI から削除する (`nhgorch.cpp:L502-525`)。
- **順序依存**: NHG 自体が `NEXTHOP_GROUP_TABLE` に書き込まれていても、`NeighOrch` がネクストホップの ARP/NDP を解決するまで SAI メンバーは追加されない。したがって「NHG エントリの書込み」と「NHG が ASIC で有効化される」の間にはネイバー解決の待機時間が介在する。
- evidence: `nhgorch.cpp:L466-525`

### 6. NHG 数上限到達時の temporary NHG — 完全 ECMP 適用前に単一 NH で暫定適用

- `gRouteOrch->getNhgCount() + NextHopGroup::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` が真のとき、非 SRv6 NHG は `createTempNhg()` で代表 1 NH のみの temporary group として SAI に登録され `m_syncdNextHopGroups` に格納される (`nhgorch.cpp:L246-270`)。
- **順序依存**: リソースが解放されて次の `doTask()` イテレーションで上限を下回ると、temporary NHG を完全な ECMP NHG に昇格させる処理が走る (`nhgorch.cpp:L314-391`)。consumer から見ると「同じ NHG キーが temporary（1 NH）→ full ECMP」に非同期で切り替わる。昇格中の短い窓でトラフィックが縮退する可能性がある。
- evidence: `nhgorch.cpp:L246-391`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | メンバー NHG 登録 → 親（再帰）NHG の完全解決 | **強制先行** | 部分解決で即時適用（partial NHG）、残りはメンバー登録後に自動昇格 |
| 2 | NEXTHOP_GROUP_TABLE 書込み → ROUTE_TABLE nexthop_group 参照 | 推奨先行 | 逆転時は RouteOrch が NHG 解決まで待機して自動解消 |
| 3 | ROUTE_TABLE 参照クリア → NEXTHOP_GROUP_TABLE DEL | **強制先行** | ref_count > 0 の間 DEL はブロック・自動 retry |
| 4 | DEL と後続 SET が競合 → DEL をスキップ | 自動調停 | `m_toSync` キューで DEL を skip して最終 SET を適用 |
| 5 | NeighOrch ARP/NDP 解決 → NhgOrch SAI メンバー追加 | 非同期（イベント駆動） | invalidateNextHop / validateNextHop で自動的に同期 |
| 6 | NHG 数上限 → temporary NHG → full ECMP 昇格 | 非同期（リソース依存） | リソース解放後の次 doTask() 呼び出し時に自動昇格 |

---

## ページ反映方針

- `<!-- ordering -->` ブロックを `<!-- defaults -->` ブロックの直前（`## 引用元` セクションの直後、`<!-- defaults -->` の直前）に挿入する。
- サマリ表 + 主要制約の散文（依存 #1 / #3 / #5 を主軸）を含める。
- 既存の `<!-- defaults -->` / `<!-- pubsub -->` / `<!-- failure -->` / `<!-- constants -->` ブロックは触らない。
