# DPU orchagent (DpuOrchDaemon) 暗黙参照調査メモ (Phase C)

調査日: 2026-05-19
対象: `DpuOrchDaemon` および配下 DASH Orch 群が暗黙的に参照する DB / テーブル

## 調査対象ファイル

- `sonic-swss/orchagent/orchdaemon.cpp` (DpuOrchDaemon::init)
- `sonic-swss/orchagent/orchdaemon.h` (DpuOrchDaemon クラス)
- `sonic-swss/orchagent/main.cpp` (switch_type 判定・DPU_APPL_DB 接続)
- `sonic-swss/orchagent/dash/dashorch.cpp`
- `sonic-swss/orchagent/dash/dashhaorch.cpp`
- `sonic-swss/orchagent/dash/dashvnetorch.cpp`
- `sonic-swss/orchagent/dash/dashaclorch.cpp`

---

## grep エントリポイント

```bash
# DPU_APPL_DB / DPU_APPL_STATE_DB 接続箇所
grep -n "DPU_APPL\|dpu_app" sonic-swss/orchagent/main.cpp sonic-swss/orchagent/orchdaemon.cpp

# DASH テーブル名定数一覧
grep -n "APP_DASH_" sonic-swss/orchagent/orchdaemon.cpp

# DASH Orch が CONFIG_DB を読むか確認
grep -rn "CFG_\|CONFIG_DB\|configDb\|hget\|hgetall" sonic-swss/orchagent/dash/*.cpp | grep -v "//.*CFG"
```

---

## DPU_APPL_DB テーブル参照一覧

DpuOrchDaemon::init() が配下 DASH Orch に渡すテーブル (orchdaemon.cpp:1336-1406):

| DASH Orch | 購読テーブル (DPU_APPL_DB) |
|-----------|--------------------------|
| DashVnetOrch | APP_DASH_VNET_TABLE, APP_DASH_VNET_MAPPING_TABLE |
| DashOrch | APP_DASH_APPLIANCE_TABLE, APP_DASH_ROUTING_TYPE_TABLE, APP_DASH_ENI_TABLE, APP_DASH_ENI_ROUTE_TABLE, APP_DASH_QOS_TABLE |
| DashHaOrch | APP_DASH_HA_SET_TABLE, APP_DASH_HA_SCOPE_TABLE, APP_BFD_SESSION_TABLE |
| DashRouteOrch | APP_DASH_ROUTE_TABLE, APP_DASH_ROUTE_RULE_TABLE, APP_DASH_ROUTE_GROUP_TABLE |
| DashAclOrch | APP_DASH_PREFIX_TAG_TABLE, APP_DASH_ACL_IN_TABLE, APP_DASH_ACL_OUT_TABLE, APP_DASH_ACL_GROUP_TABLE, APP_DASH_ACL_RULE_TABLE |
| DashTunnelOrch | APP_DASH_TUNNEL_TABLE |
| DashMeterOrch | APP_DASH_METER_POLICY_TABLE, APP_DASH_METER_RULE_TABLE |
| DashPortMapOrch | APP_DASH_OUTBOUND_PORT_MAP_TABLE, APP_DASH_OUTBOUND_PORT_MAP_RANGE_TABLE |
| DashHaFlowOrch | APP_DASH_FLOW_SYNC_SESSION_TABLE, APP_DASH_FLOW_DUMP_FILTER_TABLE |

## DPU_APPL_STATE_DB 参照

全 DASH Orch コンストラクタに `m_dpu_appstateDb` が渡される (orchdaemon.cpp:1339,1350,1359,1368,1378,1384,1392,1399,1406)。
各 DASH Orch は処理完了後に DPU_APPL_STATE_DB へ結果を書き込む。

## APPL_DB|BFD_SESSION 参照 (DashHaOrch)

DashHaOrch は `APP_BFD_SESSION_TABLE_NAME` を `dash_ha_tables` に含めるとともに、
`gBfdOrch` ポインタを受け取る (orchdaemon.cpp:1359)。
`gBfdOrch` は `OrchDaemon::init()` (基底クラス) 内の `BfdOrch` インスタンス (orchdaemon.cpp:243-244)。
DashHaOrch は BFD セッションへの参照を通じて HA スコープの BFD 状態を追跡する。

## CONFIG_DB 参照状況

DASH Orch 群 (dashorch.cpp / dashhaorch.cpp / dashvnetorch.cpp 等) は CONFIG_DB を直接読み出さない。
CONFIG_DB 参照はすべて orchdaemon.cpp 上位層 (main.cpp + DpuOrchDaemon::init) で完結する:
- `DEVICE_METADATA|localhost.switch_type` → main.cpp getCfgSwitchType()
- `DEVICE_METADATA|localhost.orch_northbond_dash_zmq_enabled` → orchdaemon.cpp get_feature_status()

## 結論

DpuOrchDaemon の暗黙参照は以下の 3 層に分類できる:

1. **CONFIG_DB 参照層** (起動時 1 回): `DEVICE_METADATA|localhost` の 2 フィールド (Phase A/B で記述済み)
2. **DPU_APPL_DB 購読層** (実行時): 9 DASH Orch が購読する 18 テーブル
3. **DPU_APPL_STATE_DB 書込み層** (実行時): 全 DASH Orch の処理結果出力先
4. **APPL_DB 横断参照** (DashHaOrch): `BFD_SESSION` テーブルを gBfdOrch 経由で間接参照
