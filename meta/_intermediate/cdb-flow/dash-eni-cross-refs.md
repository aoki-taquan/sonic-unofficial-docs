# DASH_ENI_TABLE — Phase C 暗黙参照 (cross-table refs) 調査メモ

生成日: 2026-05-17
対象ページ: `docs/reference/config-db/dash-eni.md`

## 訪問ファイル・関数一覧

| ファイル | 関数/セクション | 目的 |
|---------|---------------|------|
| `sonic-swss/orchagent/dash/dashorch.cpp` | `addEniObject()` L566-768 | ENI 作成時の外部テーブル参照 (VNET/Appliance/Meter) |
| `sonic-swss/orchagent/dash/dashorch.cpp` | `setEniRoute()` L1183-1230 | ENI_ROUTE 設定時の ENI/RouteGroup 参照 |
| `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` | `bind()` L421-510 | ACL bind 時に ENI の eni_id を参照 |
| `sonic-swss/orchagent/dash/dashrouteorch.cpp` | `taskAddLocalVnetMapping()` L425-440 | Inbound routing 設定時に ENI の eni_id を参照 |
| `sonic-swss/orchagent/dash/dashhaorch.cpp` | `doTask()` L651-663 | HA 設定時に ENI エントリを参照 |

## YANG leafref

`DASH_ENI_TABLE` は YANG 未定義テーブルのため leafref は存在しない。以下はすべて実装レベルの暗黙参照。

## DASH_ENI_TABLE が参照するテーブル（参照元として）

### 1. DASH_VNET_TABLE（vnet フィールド）

- **参照先テーブル**: `DASH_VNET_TABLE`
- **参照方向**: 存在確認 + OID 解決（読み取り）
- **条件**: `vnet` フィールドに VNET 名が指定されたとき（必須フィールド）
- **参照元**: `dashorch.cpp` L570–576 (`gVnetNameToId.find(vnet)`), L614 (`gVnetNameToId[entry.metadata.vnet()]`)
- **意味**: `DashVnetOrch` が管理する `gVnetNameToId` マップから VNET SAI OID を解決し、`SAI_ENI_ATTR_VNET_ID` に設定。VNET が未登録の場合は `addEniObject()` が `false` を返してリトライキューに戻す。
- **ブロッキング依存**: DASH_VNET_TABLE の先行登録が必須。

### 2. DASH_APPLIANCE_TABLE（Appliance エントリ参照）

- **参照先テーブル**: `DASH_APPLIANCE_TABLE`
- **参照方向**: 存在確認 + 値読み取り（`vm_vni`）
- **条件**: 常時（全 ENI 作成で参照）
- **参照元**: `dashorch.cpp` L578–582 (`appliance_entries_.empty()`), L651–653 (`appliance_entries_.begin()->second.metadata.vm_vni()`)
- **意味**: `appliance_entries_` が空の場合は即座にリトライ。存在する場合は最初のエントリの `vm_vni()` を取得して `SAI_ENI_ATTR_VM_VNI` に設定。
- **ブロッキング依存**: DASH_APPLIANCE_TABLE の先行登録が必須。

### 3. DASH_METER_POLICY_TABLE（v4/v6 meter_policy フィールド）

- **参照先テーブル**: `DASH_METER_POLICY_TABLE`（`DashMeterOrch` 管理）
- **参照方向**: OID 解決（読み取り）
- **条件**: `v4_meter_policy_id` / `v6_meter_policy_id` が指定されたとき（任意フィールド）
- **参照元**: `dashorch.cpp` L584–607 (`getMeterPolicyOid()` が SAI_NULL_OBJECT_ID → リトライ), L670–677 (OID を `SAI_ENI_ATTR_V4_METER_POLICY_ID` / `SAI_ENI_ATTR_V6_METER_POLICY_ID` に設定)
- **意味**: `DashMeterOrch::getMeterPolicyOid()` で OID を取得。未登録なら `addEniObject()` が `false` を返してリトライ。
- **ブロッキング依存**: メータポリシー使用時は DASH_METER_POLICY_TABLE の先行登録が必須。

### 4. DASH_QOS_TABLE（qos フィールド）

- **参照先テーブル**: `DASH_QOS_TABLE`
- **参照方向**: 存在確認 + 値読み取り（`bw` / `cps` / `flows`）
- **条件**: `qos` フィールドが指定されたとき（任意フィールド）
- **参照元**: `dashorch.cpp` L617–631 (`qos_entries_.find()`, has_qos フラグ)
- **意味**: `qos_entries_` に QoS エントリが存在する場合のみ `SAI_ENI_ATTR_PPS` / `SAI_ENI_ATTR_CPS` / `SAI_ENI_ATTR_FLOWS` を SAI 属性リストに追加。**QoS エントリが未登録でもリトライせず**、QoS 属性なしで ENI を作成する（非ブロッキング参照）。
- **ブロッキング依存**: なし（QoS 未設定の ENI が作成される）。

## DASH_ENI_TABLE が参照される側（参照先として）

### 5. DASH_ENI_ROUTE_TABLE（ENI route binding）

- **参照先テーブル**: `DASH_ENI_TABLE`（ENI OID 取得元）
- **参照方向**: `DashRouteOrch` が `getEni()` で ENI エントリを参照
- **参照元**: `dashorch.cpp` L1186 (`eni_entries_.find(eni) == end()` → リトライ), `dashrouteorch.cpp` L425 (`dash_orch_->getEni(ctxt.eni)` → nullptr チェック)
- **意味**: `DASH_ENI_ROUTE_TABLE` の処理は対応 ENI が `eni_entries_` に登録済みである必要がある。ENI 未登録の場合は `setEniRoute()` が `false` を返してリトライ。

### 6. DASH_ACL_IN_TABLE / DASH_ACL_OUT_TABLE（ACL binding）

- **参照先テーブル**: `DASH_ENI_TABLE`（ENI OID 取得元）
- **参照方向**: `DashAclGroupMgr` が `DashOrch::getEni()` で ENI エントリを参照
- **参照元**: `dashaclgroupmgr.cpp` L457 (`m_dash_orch->getEni(eni_id)` — bind で eni_id 取得), L506 (`m_dash_orch->getEni(eni_id)` — unbind で eni_id 取得)
- **意味**: ACL グループを ENI にバインドする際に ENI の `eni_id` (SAI OID) が必要。ENI が未登録なら nullptr → バインド失敗。

### 7. DASH_HA_SET_TABLE / DASH_HA_SCOPE_TABLE（HA 設定）

- **参照先テーブル**: `DASH_ENI_TABLE`（ENI エントリ参照）
- **参照方向**: `DashHaOrch` が `DashOrch::getEni()` / `getEniTable()` で参照
- **参照元**: `dashhaorch.cpp` L651 (`m_dash_orch->getEni(key)`), L662 (`m_dash_orch->getEniTable()`)
- **意味**: HA 設定処理で ENI エントリの存在確認と全 ENI テーブルのイテレーションを行う。ENI が先行して登録されている必要がある。

## 参照関係サマリ

```
DASH_ENI_TABLE
  ├─ [参照する] DASH_VNET_TABLE.name         (vnet フィールド — SAI VNET OID 解決、必須・ブロッキング)
  ├─ [参照する] DASH_APPLIANCE_TABLE          (vm_vni 読み取り — 全ENI作成で必須・ブロッキング)
  ├─ [参照する] DASH_METER_POLICY_TABLE.id    (v4/v6_meter_policy_id — OID 解決、ブロッキング)
  ├─ [参照する] DASH_QOS_TABLE.name           (qos フィールド — PPS/CPS/FLOWS 読み取り、非ブロッキング)
  ├─ [参照される] DASH_ENI_ROUTE_TABLE        (ENI OID を参照; ENI 未存在 → リトライ)
  ├─ [参照される] DASH_ACL_IN/OUT_TABLE       (ACL bind 時に ENI OID を参照)
  └─ [参照される] DASH_HA_SET/SCOPE_TABLE     (HA 設定で ENI エントリを参照)
```

## evidence

- `dashorch.cpp`: L570–576 (VNET 参照), L578–582 (Appliance 参照), L584–607 (Meter 参照), L617–631 (QoS 参照), L614 (VNET OID 設定), L651–653 (vm_vni 設定), L1186 (ENI 未存在 → リトライ)
- `dashaclgroupmgr.cpp`: L457, L506 (ENI OID 取得)
- `dashrouteorch.cpp`: L425, L439, L521 (ENI OID 取得)
- `dashhaorch.cpp`: L651, L662 (ENI エントリ参照)
