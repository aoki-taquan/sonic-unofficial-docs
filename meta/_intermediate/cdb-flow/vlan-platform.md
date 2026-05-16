# VLAN — Phase H プラットフォーム差分

対象ページ: `docs/reference/config-db/vlan.md`
ソース: `sonic-swss/cfgmgr/vlanmgr.cpp`, `sonic-swss/orchagent/portsorch.cpp`

---

## 1. VOQ chassis / DPU モード差 (gMySwitchType)

**ソース**: `sonic-swss/orchagent/portsorch.cpp:987-1066`

`PortsOrch` の初期化時に `gMySwitchType` を参照し、`"dpu"` の場合は以下をスキップする:

| 処理 | 通常モード | DPU モード (`gMySwitchType == "dpu"`) |
|------|-----------|--------------------------------------|
| SAI デフォルト 1Q Bridge OID 取得 (`SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID`) | 実行 | スキップ |
| SAI デフォルト VLAN OID 取得 (`SAI_SWITCH_ATTR_DEFAULT_VLAN_ID`) | 実行 | スキップ |
| `removeDefaultVlanMembers()` | 実行 | スキップ |
| `removeDefaultBridgePorts()` | 実行 | スキップ |
| FDB event notify 設定 (`SAI_SWITCH_ATTR_FDB_EVENT_NOTIFY`) | 実行 | スキップ |

DPU（SmartSwitch Data Processing Unit）モードでは SAI bridge/VLAN の初期化フローが別経路となり、orchagent は VLAN の SAI 作成を通常と同じ `create_vlan()` 呼び出しで行うが、デフォルト VLAN メンバの削除やブリッジポート清掃を行わない。DPU はホスト側 Linux bridge を通常通り作成する（vlanmgr.cpp 側は `gMySwitchType` を参照しない）。

**VOQ chassis** (`gMySwitchType == "voq"`) については `portsorch.cpp` に LAG/SystemPort 関連の分岐が存在するが、VLAN テーブル処理（`doVlanTask` / `addVlan` / `removeVlan`）に直接影響する分岐は存在しない。VLAN の SAI 作成フローは VOQ chassis でも標準と同一。

---

## 2. SmartSwitch DPU — `host_ifname` による SAI HOSTIF バインド

**ソース**: `sonic-swss/orchagent/portsorch.cpp:5774-5828`, `3802-3848`

通常の Linux bridge ではなく、APP_DB `VLAN_TABLE` の `host_ifname` フィールドが設定されている場合に `createVlanHostIntf()` が呼ばれ、SAI `create_hostif()` を使用して VLAN OID に `SAI_HOSTIF_TYPE_NETDEV` のホストインタフェースをバインドする。

```cpp
// portsorch.cpp:5820-5828
if (!hostif_name.empty())
{
    if (!createVlanHostIntf(vl, hostif_name))
    {
        // Error は print 済み、graceful failure
        it = consumer.m_toSync.erase(it);
        continue;
    }
}
```

- `host_ifname` は CONFIG_DB `VLAN` テーブルには定義されていない（YANG の外）。vlanmgrd がフィールドを受け取った場合は APP_DB に透過転送するだけ（vlanmgr.cpp:416-418, 434）。
- SmartSwitch NPU 側から DPU 向けに監視用ホスト IF を作成するユースケースで使用される。
- `removeVlan()` 実行時に `host_intf_id` が設定されていれば `removeVlanHostIntf()` が先に呼ばれる（portsorch.cpp:7457）。

---

## 3. カーネル Linux bridge vs SAI VLAN — 二重平面の非対称動作

**ソース**: `sonic-swss/cfgmgr/vlanmgr.cpp:76-116`, `portsorch.cpp:7392`

SONiC の VLAN 制御は 2 つの独立した平面で動作する:

| 平面 | コンポーネント | 実装 | タイミング |
|------|--------------|------|-----------|
| カーネル側 | vlanmgrd | `ip link add Bridge type bridge`<br>`bridge vlan add vid <N>` | CONFIG_DB 変更を直接受信 |
| ASIC/SAI 側 | orchagent (VlanOrch) | `sai_vlan_api->create_vlan(SAI_VLAN_ATTR_VLAN_ID)` | APP_DB 経由 |

両平面は並列に動作し、互いの完了を待たない。以下の非対称挙動が生じる:

- **DPU モード**: vlanmgrd は変わらずカーネル bridge を作成する（`gMySwitchType` 非参照）。ただし DPU の転送はカーネルブリッジを通過しないため、カーネル bridge は制御面・管理面専用となる。
- **SAI デフォルト属性依存**: `create_vlan()` は `SAI_VLAN_ATTR_VLAN_ID` のみ指定し flooding control 等は SAI ベンダーデフォルトに依存する（portsorch.cpp:7392）。VS (Virtual Switch) SAI と実 ASIC SAI でデフォルト挙動が異なる。
- **MTU の非対称**: vlanmgrd は `DEFAULT_MTU_STR=9100` を APP_DB に書き込むが、カーネル側の netdev MTU 設定は TODO 状態（vlanmgr.cpp:401-406）。ホスト側と SAI 側で MTU が不一致になり得る。
- **カーネル bridge 初期化の冪等性**: warm-restart 時 vlanmgrd は既存 bridge を検出してスキップするが、SAI VLAN は orchagent が warm-restart reconciliation で再確認する。カーネル bridge と SAI VLAN の状態が乖離した場合のリカバリは manual 操作が必要。

---

## 4. SAI VLAN Flood Control capability — `COMBINED` 非対応 ASIC

**ソース**: `sonic-swss/orchagent/portsorch.cpp:900-931, 7517-7524`

`orchagent` 起動時に `sai_query_attribute_enum_values_capability()` で UUC / BC の flood control タイプを問い合わせる。`SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED` をサポートしない ASIC では、VXLAN EVPN の flood group 設定がエラー終了する。VS SAI は `ALL` / `NONE` / `L2MC_GROUP` の 3 種のみを返し `COMBINED` を返さない。

---

## 5. `SAI_HOSTIF_VLAN_TAG` — ベンダー間の段階的サポート

**ソース**: `sonic-swss/orchagent/portsorch.cpp:3043-3045`

コードコメントに「`SAI_HOSTIF_VLAN_TAG_ORIGINAL` は全 ASIC ベンダーの libsai でサポートされる前」と明記。orchagent は VLAN メンバ追加時に `STRIP` / `KEEP` を条件で切り替えており、CPU ポートへのパケット受信時の VLAN タグ有無がベンダー実装で異なる可能性がある。
