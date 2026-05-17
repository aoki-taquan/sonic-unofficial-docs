# DASH_VNET — Phase B 書込み順依存スキャンノート

対象テーブル: `DASH_VNET`
Consumer: `DashVnetOrch` (`sonic-swss/orchagent/dash/dashvnetorch.cpp`)
スキャン範囲: `doTaskVnetTable()` 全行、`addVnet()` L53-79、`addVnetPost()` L81-108、`removeVnet()` L110-130、`removeVnetPost()` L132-171、`doTaskVnetMapTable()` 全行、`addVnetMap()` L485-496、`addOutboundCaToPa()` L301-448
Evidence: sonic-swss `orchagent/dash/dashvnetorch.cpp` sha `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 検出した順序依存・タイミング依存

### 1. DASH_APPLIANCE が先行必須（addVnet の強制ガード）

- `addVnet()` L63-68: `DashOrch::hasApplianceEntry()` が `false` の場合、即 `return false` して
  消費キューに残す（リトライ待ちになる）。`SWSS_LOG_INFO("Retry as no appliance table entry found")` を記録。
- これは **ハードブロック**。`DASH_APPLIANCE` テーブルにエントリが存在しない限り、VNET エントリは
  SAI に一切反映されない。リトライ自体は次の orchagent イベントループで自動発生するため、後から
  `DASH_APPLIANCE` を追加すれば自動解消される。
- **順序依存**: `DASH_VNET` を書く前に必ず `DASH_APPLIANCE|<appliance_name>` を書くこと。
- evidence: `dashvnetorch.cpp:63-68`, `dashorch.cpp:97`

### 2. DASH_VNET が先行必須（VNET_MAPPING 書き込み前）

- `addVnetMap()` L489-494: `gVnetNameToId.find(ctxt.vnet_name) != gVnetNameToId.end()` が false の場合、
  `SWSS_LOG_INFO("Not creating VNET map for %s since VNET %s doesn't exist")` を記録して `return false`
  （リトライ待ち）。
- `gVnetNameToId` はグローバルマップで `addVnetPost()` L101 で `gVnetNameToId[vnet_name] = id` に追加される。
  つまり `DASH_VNET` エントリが SAI に正常作成されてから `DASH_VNET_MAPPING_TABLE` エントリが処理される。
- **順序依存**: `DASH_VNET_MAPPING_TABLE` (CA-to-PA マッピング) を書く前に対応する `DASH_VNET` が
  SAI に反映済みであること。起動時一括投入では `DASH_APPLIANCE → DASH_VNET → DASH_VNET_MAPPING_TABLE`
  の順を守ること。
- evidence: `dashvnetorch.cpp:489-494`, `dashvnetorch.cpp:101`

### 3. DASH_ROUTE_TYPE が先行必須（VNET_MAPPING の routing_type 解決）

- `addOutboundCaToPa()` L314-319: `dash_orch->getRouteTypeActions(ctxt.metadata.routing_type(), route_type_actions)`
  が `false` を返すと、`SWSS_LOG_INFO("Failed to get route type actions")` を記録して `return false`
  （リトライ待ち）。
- `getRouteTypeActions()` は `DashOrch` の内部 route_type テーブルを参照する。`DASH_ROUTE_TYPE` エントリが
  存在しない限りマッピング処理が進まない。
- **順序依存**: `DASH_VNET_MAPPING_TABLE` を書く前に、対応する `routing_type` の `DASH_ROUTE_TYPE` エントリを
  先に設定すること。
- evidence: `dashvnetorch.cpp:314-319`, `dashorch.cpp:82-96`

### 4. DashTunnelOrch / DashPortMapOrch の事前存在（PRIVATELINK ルーティング時）

- `addOutboundCaToPa()` L354-364: `ctxt.metadata.has_tunnel()` が true の場合、
  `DashTunnelOrch::getTunnelOid(ctxt.metadata.tunnel())` が `SAI_NULL_OBJECT_ID` を返すと `return false`
  （リトライ待ち）。対象トンネルが DASH_TUNNEL テーブルに先行登録されていない場合はブロックされる。
- L409-420: `ctxt.metadata.has_port_map()` が true かつ `DashPortMapOrch::getPortMapOid()` が
  `SAI_NULL_OBJECT_ID` を返すと `return false`。
- **順序依存**: `routing_type` が `PRIVATELINK` でトンネルやポートマップを使う場合は
  `DASH_TUNNEL` / `DASH_PORT_MAP` エントリを先に書くこと。
- evidence: `dashvnetorch.cpp:354-365`, `dashvnetorch.cpp:409-422`

### 5. DEL 順序 — VNET は VNET_MAPPING より後に削除すること

- `removePaValidation()` L598-617: VNET 削除時に `vnet_table_[ctxt.vnet_name].underlay_ips` を全走査して
  PA Validation エントリを一括削除する。VNET_MAPPING が残った状態で VNET を先に削除すると、
  `vnet_table_` からエントリが消え (`vnet_table_.erase(vnet_name)` L166)、
  VNET_MAPPING の DEL 処理時に `gVnetNameToId[ctxt.vnet_name]` が無効エントリを参照する危険がある。
- また `removeVnetPost()` L150-154: SAI が `SAI_STATUS_NOT_EXECUTED` を返した場合は `return false` で
  リトライ待ちとなる（参照カウントが残っている場合）。
- **推奨 DEL 順序**: `DASH_VNET_MAPPING_TABLE` のエントリを先に削除 → その後 `DASH_VNET` を削除。
- evidence: `dashvnetorch.cpp:166`, `dashvnetorch.cpp:598-617`, `dashvnetorch.cpp:150-154`

---

## SET 操作の推奨順序

```
# 1. DASH_APPLIANCE を先行設定（必須）
SET DASH_APPLIANCE|<appliance_name>  ...

# 2. DASH_ROUTE_TYPE を先行設定（VNET_MAPPING で使う routing_type ごとに）
SET DASH_ROUTE_TYPE|<type_name>  ...

# 3. DASH_TUNNEL / DASH_PORT_MAP（PRIVATELINK 使用時のみ）
SET DASH_TUNNEL|<tunnel_name>  ...

# 4. DASH_VNET を作成
SET DASH_VNET|<vnet_name>  vni=<vni>

# 5. DASH_VNET_MAPPING_TABLE（CA-to-PA マッピング）
SET DASH_VNET_MAPPING_TABLE|<vnet_name>:<ca_ip>  ...
```

---

## DEL 操作の安全順序

```
# 1. DASH_VNET_MAPPING_TABLE を先に削除
DEL DASH_VNET_MAPPING_TABLE|<vnet_name>:<ca_ip>

# 2. DASH_VNET を削除
DEL DASH_VNET|<vnet_name>

# 3. DASH_APPLIANCE はすべての VNET 削除後に削除可能
DEL DASH_APPLIANCE|<appliance_name>
```

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DASH_APPLIANCE` SET → `DASH_VNET` SET | **必須先行**（欠如時 addVnet がリトライ待ちで SAI 反映なし） | `DASH_APPLIANCE` 追加後の次イベントループで自動解消 |
| 2 | `DASH_VNET` SAI 反映完了 → `DASH_VNET_MAPPING_TABLE` SET | **必須先行**（`gVnetNameToId` に未登録の間は addVnetMap がリトライ待ち） | VNET 作成後の次イベントループで自動解消 |
| 3 | `DASH_ROUTE_TYPE` SET → `DASH_VNET_MAPPING_TABLE` SET | **必須先行**（routing_type 未解決の間は addOutboundCaToPa がリトライ待ち） | ROUTE_TYPE 追加後の次イベントループで自動解消 |
| 4 | `DASH_TUNNEL` / `DASH_PORT_MAP` SET → `DASH_VNET_MAPPING_TABLE` SET (PRIVATELINK) | **必須先行**（OID 未解決の間は addOutboundCaToPa がリトライ待ち） | 依存リソース追加後の次イベントループで自動解消 |
| 5 | `DASH_VNET_MAPPING_TABLE` DEL → `DASH_VNET` DEL | **推奨先行**（VNET 先行 DEL は underlay_ip 参照不整合のリスク） | 逆順でも SAI 側の参照カウントで部分的に保護される |
