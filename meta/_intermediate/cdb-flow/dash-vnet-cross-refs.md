# DASH_VNET — Phase C 暗黙参照 (cross-table refs) 調査メモ

対象テーブル: `DASH_VNET`
Consumer: `DashVnetOrch` (`sonic-swss/orchagent/dash/dashvnetorch.cpp`)
スキャン範囲: sonic-dash.yang 全体、dashvnetorch.cpp 全行、dashvnetorch.h 全行
Evidence: sonic-buildimage sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`, sonic-swss sha `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## YANG leafref 定義（DASH_VNET を参照する側）

`DASH_VNET` 自体は他テーブルへの leafref を持たない（参照元ではなく参照先）。
以下は `DASH_VNET|<name>` を leafref で指す他テーブルの一覧:

| 参照元テーブル | leafref フィールド | 条件 | YANG evidence |
|--------------|-------------------|------|----------------|
| `DASH_ENI` | `vnet` | 常時（ENI が所属する VNET） | `sonic-dash.yang:153-155` |
| `DASH_VNET_MAPPING_TABLE` | `vnet` (key) | 常時（マッピング先 VNET） | `sonic-dash.yang:482-484` |
| `DASH_ROUTE_TABLE` | `vnet` | `action_type = 'vnet'` or `'vnet_direct'` のとき | `sonic-dash.yang:428-430` |

これらの leafref により、YANG バリデーション層では `DASH_VNET` エントリが存在しない状態での
`DASH_ENI` / `DASH_VNET_MAPPING_TABLE` / `DASH_ROUTE_TABLE` への書き込みは CLI 経由では reject される。

---

## 実装レベルの暗黙参照（DASH_VNET が参照する側）

### 1. DASH_APPLIANCE（addVnet の依存）

- **参照先**: `DashOrch` 内部の appliance エントリ（`DASH_APPLIANCE` テーブルが背後）
- **参照方向**: 存在確認（ハードブロック）
- **条件**: `DASH_VNET` SET 操作時に常に確認
- **参照元**: `dashvnetorch.cpp:63-68` — `DashOrch::hasApplianceEntry()` が `false` なら `return false`（リトライ待ち）
- **意味**: `DASH_APPLIANCE` テーブルにエントリが 1 件も存在しない間は、`DASH_VNET` エントリが SAI に一切反映されない

### 2. gVnetNameToId グローバルマップ（VNET_MAPPING の依存先として機能）

- **参照先**: `gVnetNameToId` — `addVnetPost()` (dashvnetorch.cpp:101) で VNET SAI 作成成功時に追記
- **参照方向**: 書き込み（VNET 登録） / 消去（VNET 削除時）
- **条件**: `addVnetPost()` 成功時に登録、`removeVnetPost()` 成功時に消去
- **参照元**: `dashvnetorch.cpp:101` (`gVnetNameToId[vnet_name] = id`), `dashvnetorch.cpp:167` (`gVnetNameToId.erase(vnet_name)`)
- **意味**: このマップが `DASH_VNET_MAPPING_TABLE` の `addVnetMap()` (L489-494) でも参照される。VNET 削除後にマッピング処理が走るとマップが空の状態で `outbound_ca_to_pa_entry.dst_vnet_id` に無効値が入る危険がある

### 3. CRM カウンタ（CrmOrch）

- **参照先**: `CrmOrch` の `CRM_DASH_VNET` リソースカウンタ
- **参照方向**: 読み書き（参照カウント管理）
- **条件**: VNET 作成成功時に `incCrmResUsedCounter(CRM_DASH_VNET)` (L103)、削除成功時に `decCrmResUsedCounter(CRM_DASH_VNET)` (L164)
- **参照元**: `dashvnetorch.cpp:103`, `dashvnetorch.cpp:164`
- **意味**: CRM リソース枯渇時に SAI が VNET 作成を拒否する可能性がある（SAI 実装依存）。CRM は外部からは直接見えないが、`show system-resources` でカウンタを確認可能

---

## DASH_VNET_MAPPING_TABLE の参照構造（付記）

`DASH_VNET_MAPPING_TABLE` のオーケストレーション (`doTaskVnetMapTable()`) 内での追加参照:

| 参照先 | 参照元 | 条件 |
|--------|--------|------|
| `DASH_ROUTE_TYPE` (routing_type アクション解決) | `dashvnetorch.cpp:314-319` `DashOrch::getRouteTypeActions()` | 常時（routing_type 未解決はリトライ待ち） |
| `DASH_TUNNEL` (tunnel OID 解決) | `dashvnetorch.cpp:354-365` `DashTunnelOrch::getTunnelOid()` | `metadata.has_tunnel()` が true のとき |
| `DASH_PORT_MAP` (port_map OID 解決) | `dashvnetorch.cpp:409-422` `DashPortMapOrch::getPortMapOid()` | `PRIVATELINK` かつ `metadata.has_port_map()` が true のとき |
| `PA Validation` (underlay_ip refcount) | `dashvnetorch.cpp:450-483` `addPaValidation()` | VnetMap 追加時に自動的に PA validation エントリも作成 |

---

## 参照関係サマリ

```
DASH_VNET
  ├─ [実装依存・ハードブロック]  DASH_APPLIANCE       (addVnet: hasApplianceEntry() ガード)
  ├─ [CRM]                      CrmOrch              (VNET 作成/削除時のリソースカウンタ更新)
  └─ [被参照・YANG leafref]      ←── DASH_ENI.vnet
                                 ←── DASH_VNET_MAPPING_TABLE.vnet (key)
                                 ←── DASH_ROUTE_TABLE.vnet (action_type=vnet/vnet_direct 時)
```

## evidence

- `sonic-dash.yang:153-155` (DASH_ENI.vnet leafref)
- `sonic-dash.yang:428-430` (DASH_ROUTE_TABLE.vnet leafref)
- `sonic-dash.yang:482-484` (DASH_VNET_MAPPING_TABLE.vnet leafref)
- `dashvnetorch.cpp:63-68` (addVnet DASH_APPLIANCE ガード)
- `dashvnetorch.cpp:101, 167` (gVnetNameToId 追記/消去)
- `dashvnetorch.cpp:103, 164` (CRM incCrmResUsedCounter/decCrmResUsedCounter)
- `dashvnetorch.cpp:314-319` (getRouteTypeActions)
- `dashvnetorch.cpp:354-365` (getTunnelOid)
- `dashvnetorch.cpp:409-422` (getPortMapOid)
- `dashvnetorch.cpp:450-483` (addPaValidation)
