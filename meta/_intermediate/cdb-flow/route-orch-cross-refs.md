# FLOW_COUNTER_ROUTE_PATTERN — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/route-orch.md` Phase C 追加分。
ソース: `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp`（全 997 行精読）

YANG 定義なし（`FLOW_COUNTER_ROUTE_PATTERN` は YANG 未カバー）のため leafref は存在しない。
全依存が実装レベルの暗黙参照となる。

## ソースファイル

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` | FlowCounterRouteOrch 実装本体 |
| `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.h` | クラス定義・マクロ (`ROUTE_FLOW_COUNTER_FLEX_COUNTER_GROUP = "ROUTE_FLOW_COUNTER"`) |
| `sonic-swss-common/common/schema.h` | `COUNTERS_ROUTE_NAME_MAP`, `COUNTERS_ROUTE_TO_PATTERN_MAP`, `STATE_FLOW_COUNTER_CAPABILITY_TABLE_NAME` |

## YANG leafref

YANG 未定義テーブルのため leafref は存在しない。全参照が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. RouteOrch / APPL_DB ROUTE_TABLE — getSyncdRoutes() 経由

- **参照先**: `RouteOrch` が内部管理するシンク済みルートキャッシュ（APPL_DB `ROUTE_TABLE` 由来）
- **参照方向**: 読み取り（ルート一覧走査）
- **参照元**: `flowcounterrouteorch.cpp:634` `gRouteOrch->getSyncdRoutes()`
- **意味**: `createRouteFlowCounterByPattern()` 内でデフォルト VRF およびカスタム VRF のシンク済みルート全件を走査し、パターンに一致する経路へ flex counter をバインドする。`gRouteOrch` が null の場合は `doTask()` の先頭ガード（L58）で即時 return し、ROUTE_TABLE への依存は全てスキップされる。
- **ブロッキング依存**: `gRouteOrch` が初期化されるまで全 CONFIG_DB パターン処理が保留される（L57-60）。

### 2. VRFOrch / CONFIG_DB VRF テーブル — getVRFname() 経由

- **参照先**: `VRFOrch`（CONFIG_DB `VRF` テーブルの管理者）
- **参照方向**: OID → 名前変換（読み取り）
- **参照元**: `flowcounterrouteorch.cpp:410-411` `gDirectory.get<VRFOrch*>()->getVRFname(vrf_id)`
- **意味**: `onAddVR()` / `onRemoveVR()` で VRF OID に対応するパターン名を解決し、該当パターンに対してカウンターを生成・削除する。VRF 名が解決できない場合は WARN ログのみでパターン更新はスキップされる。

### 3. VNetOrch / VNET ルートキャッシュ

- **参照先**: `VNetOrch`（VNET オーバーレイルート管理）
- **参照方向**: 読み取り（VNET ルートマップ走査）
- **参照元**: `flowcounterrouteorch.cpp:696-743` `gDirectory.get<VNetOrch*>()->getTypePtr<VNetVrfObject>(vrf_name)->getRouteMap()`
- **意味**: `createRouteFlowCounterFromVnetRoutes()` 内で VNET 名にスコープされたルートを走査し、パターン一致経路へカウンターをバインドする。VNET が存在しない場合は早期 return（L699-701）。

### 4. FlexCounterOrch / CONFIG_DB FLEX_COUNTER_TABLE

- **参照先**: `FlexCounterOrch`（CONFIG_DB `FLEX_COUNTER_TABLE` の管理者）
- **参照方向**: 状態読み取り（カウンター有効化フラグ）
- **参照元**: `flowcounterrouteorch.cpp:947-948` `flexCounterOrch->getRouteFlowCountersState()`
- **意味**: `isRouteFlowCounterEnabled()` がこの状態を返す。`FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE` の `FLEX_COUNTER_STATUS = enable` でないと `createRouteFlowCounterByPattern()` / `handleRouteAdd()` / `handleRouteRemove()` がいずれも早期 return する。FlexCounterOrch が null（未初期化）でも `false` 扱いとなりカウンター操作はスキップされる。

### 5. ASIC_DB / VIDTORID テーブル

- **参照先**: `ASIC_DB:VIDTORID`
- **参照方向**: 読み取り（VID → RID 変換、存在確認）
- **参照元**: `flowcounterrouteorch.cpp:32, 116` `mVidToRidTable->hget("", id, value)`
- **意味**: `doTask(SelectableTimer&)` の FlexDB 更新タイマー内で、SAI object ID が ASIC_DB に実際に登録されているかを確認してから COUNTERS_DB への書き込みを行う。未登録（RID が存在しない）の場合は `mPendingAddToFlexCntr` にキューイングし続け、次タイマー周期で再試行する。

### 6. COUNTERS_DB / COUNTERS_ROUTE_NAME_MAP

- **参照先**: `COUNTERS_DB:COUNTERS_ROUTE_NAME_MAP`
- **参照方向**: 書き込み（prefix → counter OID マッピング登録）
- **参照元**: `flowcounterrouteorch.cpp:33, 126, 152` `mPrefixToCounterTable->set("", prefixToCounterMap)` / `hdel()`（L921）
- **意味**: バインド成功後に `<vrf>:<prefix>` → SAI counter OID のマップエントリを書き込む。`show flow_counters route` が参照する。カウンター削除時は `hdel()` で除去する。

### 7. COUNTERS_DB / COUNTERS_ROUTE_TO_PATTERN_MAP

- **参照先**: `COUNTERS_DB:COUNTERS_ROUTE_TO_PATTERN_MAP`
- **参照方向**: 書き込み（prefix → パターン逆引きマップ登録）
- **参照元**: `flowcounterrouteorch.cpp:34, 129, 155` `mPrefixToPatternTable->set("", prefixToPatternMap)` / `hdel()`（L920）
- **意味**: どのパターン設定により当該経路がカウンター対象になっているかを COUNTERS_DB に記録する。`show flow_counters route` の `Pattern` 列表示に使用される。

### 8. STATE_DB / FLOW_COUNTER_CAPABILITY_TABLE

- **参照先**: `STATE_DB:FLOW_COUNTER_CAPABILITY_TABLE|route`（フィールド: `support`）
- **参照方向**: 書き込み（プラットフォームサポート状態の公開）
- **参照元**: `flowcounterrouteorch.cpp:174-178` `capability_table.set(FLOW_COUNTER_ROUTE_KEY, fvs)`
- **意味**: `initRouteFlowCounterCapability()` 内でプラットフォームの SAI route flow counter サポート可否を `"true"` / `"false"` として書き込む。このエントリを確認することで、ユーザー / 管理ツールが当該プラットフォームでの機能利用可否を判断できる。書き込みは orchagent 起動時の一度だけ。

## 排他関係 / semantics

- `gRouteOrch` が null → CONFIG_DB パターン処理全体が保留（L57-60）。
- `mRouteFlowCounterSupported = false`（プラットフォーム非対応）→ CONFIG_DB パターン処理全体が保留（L57-60）。
- `isRouteFlowCounterEnabled() = false`（FLEX_COUNTER_TABLE で無効）→ `createRouteFlowCounterByPattern()` / `handleRouteAdd()` / `handleRouteRemove()` が早期 return。ただし `addRoutePattern()` 自体はパターンセットに追加する（有効化後に `generateRouteFlowStats()` で一括適用される想定）。
- ASIC_DB に VID が存在しない段階でのバインド → `mPendingAddToFlexCntr` にキューイング。`FLEX_COUNTER_UPD_TIMER`（1秒周期）で再試行。

## 範囲外

- `ROUTE_TABLE (STATE_DB)` — デフォルトルート到達性の side-effect 書き込み先であり、FlowCounterRouteOrch は参照しない。
- `STATIC_ROUTE (CONFIG_DB)` — `staticrouteorch` 経由で APPL_DB `ROUTE_TABLE` に書かれた後、`RouteOrch` が普通のルートとして扱うため、FlowCounterRouteOrch から見れば透過的。
- `NEIGH_TABLE` / `INTF_TABLE` — RouteOrch が参照するが FlowCounterRouteOrch は直接参照しない。
