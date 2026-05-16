# VXLAN_TUNNEL_MAP — Phase A: Implicit Defaults & Code-derived Behaviors

## フィールド一覧

| フィールド | YANG 型 | 必須 | YANG default |
|-----------|---------|------|-------------|
| `name` (key) | leafref `VXLAN_TUNNEL.name` | ✅ | なし |
| `mapname` (key) | string | ✅ | なし |
| `vlan` | string `Vlan<id>` パターン | ✅ | なし |
| `vni` | `vnid_type` (uint32 0..16777215) | ✅ | なし |

---

## コード由来の暗黙デフォルト / fallback

### 1. mapping type — 常に VNI_TO_VLAN_ID / VLAN_ID_TO_VNI の双方向ペアが生成

**根拠**: `vxlanorch.cpp:759-760`
```cpp
ids_.tunnel_decap_id[TUNNEL_MAP_T_VLAN] = create_tunnel_map(MAP_T::VNI_TO_VLAN_ID);
ids_.tunnel_encap_id[TUNNEL_MAP_T_VLAN] = create_tunnel_map(MAP_T::VLAN_ID_TO_VNI);
```

**根拠**: `vxlanorch.cpp:38-45` グローバルマップテーブル
```cpp
const map<MAP_T, uint32_t> vxlanTunnelMap = {
    { MAP_T::VNI_TO_VLAN_ID, SAI_TUNNEL_MAP_TYPE_VNI_TO_VLAN_ID },
    { MAP_T::VLAN_ID_TO_VNI, SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI },
    ...
};
```

**根拠**: `vxlanorch.cpp:102,112`
```cpp
// encap
case TUNNEL_MAP_T_VLAN : return MAP_T::VLAN_ID_TO_VNI;
// decap
case TUNNEL_MAP_T_VLAN : return MAP_T::VNI_TO_VLAN_ID;
```

**結論**: VXLAN_TUNNEL_MAP エントリが追加されると、親トンネルが inactive の場合 `createTunnelHw()` が呼ばれ、VLAN 用の decap (`VNI_TO_VLAN_ID`) と encap (`VLAN_ID_TO_VNI`) の SAI tunnel-map オブジェクトが **必ずペアで** 自動生成される。CONFIG_DB フィールドで mapping type を指定する手段はない — **暗黙固定デフォルト**。

---

### 2. addOperation の TUNNELMAP_SET_VLAN + TUNNELMAP_SET_VRF — 常に VLAN/VRF 両マッパーを作成

**根拠**: `vxlanorch.cpp:2065-2072` (`VxlanTunnelMapOrch::addOperation`)
```cpp
uint8_t mapper_list = 0;
TUNNELMAP_SET_VLAN(mapper_list);
TUNNELMAP_SET_VRF(mapper_list);
bool tunnel_created = tunnel_obj->createTunnelHw(mapper_list,
                                    TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP);
```

**結論**: トンネルが inactive 時に初回 MAP エントリを追加すると、VLAN マッパー加えて VRF マッパー (`SAI_TUNNEL_MAP_TYPE_VIRTUAL_ROUTER_ID_TO_VNI` / `_TO_VIRTUAL_ROUTER_ID`) も同時に初期化される。EVPN L3VNI の使用有無に関わらず SAI オブジェクトが先行して生成される — **先行プロビジョニング (over-provision) パターン**。

---

### 3. `vni_id` 上限チェック — 16777215 (0xFFFFFF) 以上は即時破棄

**根拠**: `vxlanorch.h:48`
```cpp
#define MAX_VNI_ID 16777215
```

**根拠**: `vxlanorch.cpp:2037-2040`
```cpp
if (vni_id >= MAX_VNI_ID)
{
    SWSS_LOG_ERROR("Vxlan tunnel map vni id is too big: %d", vni_id);
    return true;  // permanent discard (not retry)
}
```

**結論**: `vni` >= 16777215 は YANG バリデーション (`vnid_type` 型: 0..16777215) でも弾くはずだが、orchagent 側でも独立に上限チェックし永続破棄する。`return true` (not false) なのでリトライなしに消える — **permanent silent discard**。二重チェック経路が存在する。

---

### 4. isL3Vni == true の場合 — SAI tunnel-map entry を生成しない (SAI_NULL_OBJECT_ID)

**根拠**: `vxlanorch.cpp:2101-2113`
```cpp
if (isL3Vni == false)
{
    auto tunnel_map_entry_id = create_tunnel_map_entry(MAP_T::VNI_TO_VLAN_ID,
                                                       tunnel_map_id, vni_id, vlan_id);
    vxlan_tunnel_map_table_[...].map_entry_id = tunnel_map_entry_id;
}
else
{
    vxlan_tunnel_map_table_[...].map_entry_id = SAI_NULL_OBJECT_ID;
}
```

**結論**: EVPN L3VNI として登録済みの VNI に対して VXLAN_TUNNEL_MAP エントリを作成しても、SAI `create_tunnel_map_entry()` は呼ばれない。MAP エントリはテーブルに記録されるが SAI オブジェクトは `SAI_NULL_OBJECT_ID` のまま — **L3VNI の場合は暗黙 no-op**。CONFIG_DB にこの区別を制御するフィールドはなく、VRFOrch の内部状態 (`isL3VniVlan()`) で決まる。

---

### 5. VLAN 存在チェック — VLAN 未作成の場合リトライ (false 返却)

**根拠**: `vxlanorch.cpp:2031-2035`
```cpp
if (!gPortsOrch->getVlanByVlanId(vlan_id, tempPort))
{
    SWSS_LOG_WARN("Vxlan tunnel map vlan id doesn't exist: %d", vlan_id);
    return false;  // retry
}
```

**結論**: `vlan` フィールドが指す VLAN が PortsOrch のポートテーブルに存在しない場合、addOperation は `false` を返してリトライキューに戻る。VLAN が後から作成されると自動的に処理が再開される — **依存順序による自動リトライ**。

---

### 6. tunnel_name 存在チェック — トンネル未存在の場合リトライ (false 返却)

**根拠**: `vxlanorch.cpp:2047-2051`
```cpp
if (!tunnel_orch->isTunnelExists(tunnel_name))
{
    SWSS_LOG_WARN("Vxlan tunnel '%s' doesn't exist", tunnel_name.c_str());
    return false;
}
```

**結論**: key の `<tunnel_name>` が `VXLAN_TUNNEL` テーブルにまだ存在しない場合もリトライ。

---

### 7. del_tnl_hw_pending フラグ — 削除保留中はリトライ

**根拠**: `vxlanorch.cpp:2053-2058`
```cpp
if (tunnel_obj->del_tnl_hw_pending)
{
    SWSS_LOG_WARN("Tunnel Mapper deletion is pending");
    return false;
}
```

**結論**: 親トンネルの HW 削除処理が完了していない間は MAP エントリの追加もブロックされる。CONFIG_DB に制御フィールドなし — **内部状態依存の暗黙ブロック**。

---

## 要約テーブル

| 挙動 | 実装動作 | コードロケーション |
|------|---------|------------------|
| mapping type | 常に `VNI_TO_VLAN_ID` (decap) + `VLAN_ID_TO_VNI` (encap) のペアを自動生成 | `vxlanorch.cpp:759-760` |
| VRF マッパー初期化 | VLAN マッパー追加時に VRF マッパーも同時に自動生成 (over-provision) | `vxlanorch.cpp:2065-2072` |
| `vni` >= 16777215 | `return true` で永続破棄 (リトライなし) | `vxlanorch.cpp:2037-2040` |
| L3VNI の場合 | SAI entry 生成スキップ (`SAI_NULL_OBJECT_ID`) | `vxlanorch.cpp:2101-2113` |
| VLAN 未存在 | `return false` でリトライ待ち | `vxlanorch.cpp:2031-2035` |
| tunnel 未存在 | `return false` でリトライ待ち | `vxlanorch.cpp:2047-2051` |
| del_tnl_hw_pending | `return false` でリトライ待ち | `vxlanorch.cpp:2053-2058` |
