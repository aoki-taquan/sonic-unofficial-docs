# VLAN_MEMBER テーブル — プラットフォーム差 (Phase H)

調査日: 2026-05-16
調査対象:
- sonic-swss/cfgmgr/vlanmgr.cpp
- sonic-swss/orchagent/portsorch.cpp
- sonic-sairedis/vslib/SwitchStateBase.cpp (参照: vlan-platform.md)
- sonic-buildimage/src/sonic-config-engine/minigraph.py

---

## 検出したプラットフォーム差

### 1. EVPN `end_point_ip` — `SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED` 非対応 ASIC でメンバ追加失敗

**検出箇所**: `portsorch.cpp:7511-7529`

```cpp
bool PortsOrch::addVlanMember(Port &vlan, Port &port, string &tagging_mode, string end_point_ip)
{
    if (!end_point_ip.empty())
    {
        if ((uuc_sup_flood_control_type.find(SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED)
             == uuc_sup_flood_control_type.end()) ||
            (bc_sup_flood_control_type.find(SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED)
             == bc_sup_flood_control_type.end()))
        {
            SWSS_LOG_ERROR("Flood group with end point ip is not supported");
            return false;
        }
        return addVlanFloodGroups(vlan, port, end_point_ip);
    }
    // ...
}
```

- APP_DB の `VLAN_MEMBER_TABLE` エントリに `end_point_ip` が付与された場合（EVPN VXLAN BUM flooding 用）、`addVlanMember()` は flood control capability チェックを行う
- 起動時に `sai_query_attribute_enum_values_capability()` で照会した結果に `COMBINED` が含まれない ASIC ではエラーで即時 return false
- VS SAI は `ALL`, `NONE`, `L2MC_GROUP` のみ返すため **VS 環境では `end_point_ip` を持つ VLAN_MEMBER は常に失敗する**
- CONFIG_DB の `VLAN_MEMBER` テーブル自体は `end_point_ip` フィールドを持たない（YANG 定義外）。APP_DB 経由で VxlanOrch が動的に注入する経路のみ

**影響**: EVPN BUM flooding 設定が ASIC/VS 依存。Broadcom TD3/TH 系は `COMBINED` をサポートするケースが多いが、Mellanox / VS / 一部ホワイトボックス ASIC では不可

---

### 2. TUNNEL ポートへの PVID 設定スキップ

**検出箇所**: `portsorch.cpp:7568-7575`, `portsorch.cpp:7905-7912`

```cpp
/* Use untagged VLAN as pvid of the member port */
if (sai_tagging_mode == SAI_VLAN_TAGGING_MODE_UNTAGGED &&
    port.m_type != Port::TUNNEL)
{
    if(!setPortPvid(port, vlan.m_vlan_info.vlan_id))
        return false;
}
```

- `tagging_mode=untagged` 時、通常の物理ポート / LAG は `setPortPvid()` でポートの PVID を VLAN ID に設定する
- `Port::TUNNEL` 型（VXLAN トンネルポート）はこのステップを **スキップ**する
- TUNNEL ポートは PVID の概念が適用されないためで、VS 環境や EVPN 構成で出現する
- 同様の `removeVlanMember()` 側でも `Port::TUNNEL` チェックあり (`portsorch.cpp:7905-7912`)

**影響**: VXLAN EVPN 構成（TUNNEL ポートが VLAN_MEMBER として存在する環境）では `tagging_mode=untagged` を設定しても SAI 側で PVID は変更されない

---

### 3. Storage Backend T0 — minigraph 経由で全メンバを強制 `tagged`

**検出箇所**: `minigraph.py:2559-2594`

```python
# storage backend T0 have all vlan members tagged
for vlan in vlan_members:
    vlan_members[vlan]["tagging_mode"] = "tagged"
```

- `BackEndToRRouter` / `BackEndLeafRouter` デバイスタイプ（Storage Backend T0）では、minigraph.py が VLAN_MEMBER の `tagging_mode` をすべて `"tagged"` に **上書き**する
- `vlan_sub_intfs`（VLAN_SUB_INTERFACE）を持つ backend T0 でも同様
- これは minigraph での設定生成段階の処理であり、CONFIG_DB に書き込まれる時点ですでに `tagged` が入る
- 通常の T0 / T1 / T2 ではこの強制上書きは発生しない

**影響**: Storage Backend デバイスでは `sonic-cfggen` / `minigraph.py` で生成した config を使う限り、VLAN_MEMBER の `tagging_mode` を `untagged` にできない（設定しても上書きされる）

---

### 4. VOQ chassis — VLAN_MEMBER への直接影響なし（Inband Vlan は Interface 経路）

**検出箇所**: `minigraph.py:895-910`

```python
if ipintf_name in ["v6VoqInband", "VoqInband"]:
    if intfalias.startswith("Ethernet"):
        voq_intf_type = "Port"
    # Vlan interface is not used, adding to be future proof
    elif intfalias.startswith("Vlan"):
        voq_intf_type = "Vlan"
    if intfalias not in voq_inband_intfs:
        voq_inband_intfs[intfalias] = {'inband_type': voq_intf_type}
```

- VOQ Chassis の Inband インタフェースに `Vlan` タイプが定義されているが、コメントに "not used, adding to be future proof" とある通り現時点では使用されない
- VOQ Chassis の `VLAN_MEMBER` テーブルへの固有分岐は vlanmgr.cpp / portsorch.cpp のいずれにも存在しない
- `gMySwitchType == "voq"` はポートトリム・SystemPort 系の分岐に影響するが `addVlanMember()` / `removeVlanMember()` のコードパスは通常と同一

**影響**: VOQ Chassis で VLAN_MEMBER を使う場合、通常の物理 T0 と同一の処理経路。Inband Vlan パターンは将来予約のみ

---

### 5. SmartSwitch DPU — vlanmgrd は通常通り動作するが orchagent は SAI 1Q bridge 初期化をスキップ

**検出箇所**: `portsorch.cpp:987-1066` (参照: vlan-platform.md §6)、`vlanmgr.cpp:71-116`

- `gMySwitchType == "dpu"` 時、orchagent は SAI デフォルト 1Q Bridge/VLAN の取得・デフォルトメンバ削除・FDB event notify 設定をスキップする
- 一方 vlanmgrd は `gMySwitchType` を参照せず、DPU 上でも Linux kernel bridge を通常通り作成する
- つまり DPU では「kernel bridge は存在するが SAI VLAN は初期状態が通常と異なる」という二重平面の非対称状態になる
- `VLAN_MEMBER` テーブル自体の YANG 定義・フィールドに DPU 固有制約はない

**影響**: DPU 上では VLAN_MEMBER を CONFIG_DB に書いても SAI 側の VLAN member が正しく作られない可能性がある（SAI 1Q bridge 初期化が省略されているため）。SmartSwitch NPU 側の VLAN_MEMBER 操作は通常通り動作する

---

### 6. Multi-ASIC — CLI で `--namespace` 必須

**検出箇所**: `config/vlan.py:23`, `multi_asic_vlan_test.py:84-92`

```python
@multi_asic_util.multi_asic_click_option_namespace(required=True)
def vlan(ctx, namespace):
    if namespace is None:
        namespace = multi_asic.DEFAULT_NAMESPACE
```

- Multi-ASIC 環境（マルチ ASIC T0 など）では `config vlan member add/del` に `--namespace` が必須
- 指定なしの場合はエラー終了する
- Single ASIC 環境では `DEFAULT_NAMESPACE` が自動設定されるため不要
- CONFIG_DB 書き込み先が ASIC ごとに分離されており、`VLAN_MEMBER` は特定 ASIC の namespace DB に書かれる

**影響**: Multi-ASIC 環境では CLI で namespace を指定しないと VLAN_MEMBER の設定ができない。REST / gNMI 経由では影響なし（API レイヤで吸収）

---

## 結論

| 差の性質 | 対象プラットフォーム | 影響フィールド |
|---------|---------|------|
| `end_point_ip` EVPN flood group 非対応 | VS SAI / `COMBINED` 非対応 ASIC | APP_DB 経由注入フィールド `end_point_ip` |
| TUNNEL ポートへの PVID 設定スキップ | VXLAN / EVPN 構成 | `tagging_mode=untagged` の PVID 設定 |
| Storage Backend T0 全メンバ `tagged` 強制 | `BackEndToRRouter` / `BackEndLeafRouter` | `tagging_mode` (minigraph 生成時に上書き) |
| VOQ Chassis Inband Vlan — 未使用 | VOQ Chassis | 影響なし（将来予約のみ） |
| DPU SAI 1Q Bridge 初期化省略 | SmartSwitch DPU | VLAN_MEMBER の SAI 反映が不完全になる可能性 |
| Multi-ASIC CLI namespace 必須 | Multi-ASIC T0 など | `config vlan member` CLI 操作 |
