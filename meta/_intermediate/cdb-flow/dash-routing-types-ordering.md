# DASH_ROUTING_TYPE — Phase B 書込み順依存スキャンノート

調査日: 2026-05-17
対象テーブル: APPL_DB `DASH_ROUTING_TYPE_TABLE` (YANG: CONFIG_DB `DASH_ROUTING_TYPE`)
Consumer: `DashOrch::doTaskRoutingTypeTable()` (`sonic-swss/orchagent/dash/dashorch.cpp`)
スキャン範囲: dashorch.cpp L82-94, L441-537, L1346; dashvnetorch.cpp L300-410, L771

---

## 検出した順序依存・タイミング依存

### 1. DASH_ROUTING_TYPE は外部テーブル依存なし（自己完結）

`addRoutingTypeEntry()` (`dashorch.cpp:441-455`) は外部 orchagent の状態を一切参照しない。
受信した protobuf を `routing_type_entries_` マップに格納するのみ。

- `parsePbMessage()` によるデシリアライズ失敗時のみエントリを erase してスキップ（再試行なし）
- 既存エントリへの上書きを WARN + `return true` でサイレントスキップ（再試行なし）
- `doTaskRoutingTypeTable()` は DASH_APPLIANCE / DASH_VNET 等の前後に関係なく処理できる

**順序依存**: DASH_ROUTING_TYPE_TABLE の SET 自体は前提テーブルなし。

---

### 2. DASH_VNET_MAPPING_TABLE は DASH_ROUTING_TYPE の先行設定を必須とする（逆依存）

`DashVnetOrch::addOutboundCaToPa()` (`dashvnetorch.cpp:313-317`):

```cpp
DashOrch* dash_orch = gDirectory.get<DashOrch*>();
dash::route_type::RouteType route_type_actions;
if (!dash_orch->getRouteTypeActions(ctxt.metadata.routing_type(), route_type_actions))
{
    SWSS_LOG_INFO("Failed to get route type actions for %s", key.c_str());
    return false;  // 呼び出し元が it++ で再試行
}
```

`getRouteTypeActions()` (`dashorch.cpp:82-94`) は `routing_type_entries_` に該当エントリが
存在しない場合 `SWSS_LOG_WARN` + `return false` を返す。
`addOutboundCaToPa()` が `false` を返すと上位の `doTask()` が `it++` で
エントリを保留し次の ConsumerBase 周回で自動再試行する（無限ポーリング）。

**順序依存**:
```
DASH_ROUTING_TYPE_TABLE|<routing_type>  SET 完了（routing_type_entries_ に格納済み）
  ↓
DASH_VNET_MAPPING_TABLE|<vnet>:<ip>  SET
```

**違反時**: `DASH_VNET_MAPPING_TABLE` の SET は保留され、`DASH_ROUTING_TYPE_TABLE` が
登録されると自動的に処理再開される（無限ポーリングで自動回復）。

---

### 3. DEL 時の逆順推奨（参照先を先に削除しない）

`removeRoutingTypeEntry()` (`dashorch.cpp:457-471`) は `routing_type_entries_` から即時削除する。
`DASH_VNET_MAPPING_TABLE` のエントリが残ったまま参照先の ROUTING_TYPE を削除すると、
当該 VNET Mapping の再 SET または orchagent 再起動時に `getRouteTypeActions()` が `false` を返し
VNET Mapping が反映されなくなる。

**推奨 DEL 順序**:
```
DASH_VNET_MAPPING_TABLE|<vnet>:<ip>  DEL  先行（推奨）
  ↓
DASH_ROUTING_TYPE_TABLE|<routing_type>  DEL
```

**違反時**: 機能的には ROUTING_TYPE のみの削除は SAI に即時影響しない（orchagent はメモリから除去するだけ）。
ただし VNET Mapping の再設定時に ROUTING_TYPE が存在しない状態になり Mapping が再試行待ちになる。

---

### 4. DASH_ROUTE_TABLE との依存関係（依存なし）

`dashrouteorch.cpp:43-46` で `routing_type` を SAI アクション (`SAI_OUTBOUND_ROUTING_ENTRY_ACTION_*`)
に変換するための静的 map が定義されているが、`getRouteTypeActions()` を呼ぶのではなく
enum 値を直接 map lookup するため、`routing_type_entries_` には依存しない。

**順序依存**: DASH_ROUTE_TABLE と DASH_ROUTING_TYPE_TABLE の間に先行依存関係はない。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 違反時挙動 |
|---|----------|------|-----------|
| 1 | DASH_ROUTING_TYPE_TABLE SET 自体に前提テーブルなし | — | — |
| 2 | DASH_ROUTING_TYPE_TABLE SET → DASH_VNET_MAPPING_TABLE SET | 強制先行（自動再試行で自動回復） | VNET Mapping が保留され自動回復 |
| 3 | DASH_VNET_MAPPING_TABLE DEL → DASH_ROUTING_TYPE_TABLE DEL | 推奨先行（違反しても即時影響なし） | VNET Mapping 再設定時に再試行待ち |
| 4 | DASH_ROUTE_TABLE との依存なし | — | — |

---

## evidence

- `dashorch.cpp:441-455` — `addRoutingTypeEntry()` 外部依存なし
- `dashorch.cpp:82-94` — `getRouteTypeActions()` miss 時 false
- `dashorch.cpp:473-537` — `doTaskRoutingTypeTable()` erase/skip パス
- `dashvnetorch.cpp:313-319` — `addOutboundCaToPa()` での getRouteTypeActions 呼び出し
- `dashrouteorch.cpp:43-46` — routing_type の静的 map (getRouteTypeActions 非依存)
