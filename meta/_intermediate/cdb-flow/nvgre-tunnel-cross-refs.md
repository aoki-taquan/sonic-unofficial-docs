# NVGRE_TUNNEL / NVGRE_TUNNEL_MAP — Phase C cross-refs 調査ノート

## 調査対象

- `sonic-swss/orchagent/nvgreorch.cpp`
- `sonic-swss/orchagent/nvgreorch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 調査結果

### 1. NVGRE_TUNNEL_MAP → NVGRE_TUNNEL 参照 (orchagent 内部 map)

`NvgreTunnelMapOrch::addOperation()` (L464-508) は冒頭で以下を実行する:

```cpp
// nvgreorch.cpp:464-472
auto tunnel_orch = gDirectory.get<NvgreTunnelOrch*>();
if (!tunnel_orch->isTunnelExists(tunnel_name))
{
    SWSS_LOG_WARN("NVGRE tunnel '%s' doesn't exist", tunnel_name.c_str());
    return true;  // エントリを破棄（retry キューへ戻さない）
}
```

`isTunnelExists()` は orchagent 内部の `tunnel_table_` map を参照する (CONFIG_DB への再 hget は行わない)。

### 2. VLAN 参照 (gPortsOrch)

```cpp
// nvgreorch.cpp:489-492
if (!gPortsOrch->getVlanByVlanId(vlan_id, port))
{
    SWSS_LOG_WARN("VLAN ID doesn't exist: %d", vlan_id);
    return true;  // エントリ破棄
}
```

`getVlanByVlanId()` は PortsOrch の内部 VLAN テーブル (CONFIG_DB `VLAN` テーブルから同期) を参照する。VLAN が PortsOrch に登録されていない場合、MAP エントリは永続的に消失する。

### 3. gUnderlayIfId (グローバル SAI オブジェクト)

```cpp
// nvgreorch.cpp:12
extern sai_object_id_t  gUnderlayIfId;
// nvgreorch.cpp:312
tunnel_ids_.tunnel_id = sai_create_tunnel(tunnel_ids_, ip_addr, gUnderlayIfId);
```

`gUnderlayIfId` は orchagent 起動時に `main.cpp` が SAI を初期化する際に設定するグローバル変数。
アンダーレイインターフェースの Router Interface (RIF) OID。CONFIG_DB への依存ではなく orchagent 内部。

### 4. gVirtualRouterId (グローバル SAI オブジェクト)

```cpp
// nvgreorch.cpp:13
extern sai_object_id_t  gVirtualRouterId;
// nvgreorch.cpp:313
tunnel_ids_.tunnel_term_id = sai_create_tunnel_termination(tunnel_ids_.tunnel_id, ip_addr, gVirtualRouterId);
```

`gVirtualRouterId` はデフォルト VRF の SAI Virtual Router OID。orchagent 起動時に初期化。

## 結論

YANG leafref 以外の暗黙参照は以下の 4 つ:
1. `NVGRE_TUNNEL` (orchagent 内部 map) — MAP 登録前にトンネルが処理完了必須
2. `VLAN` (gPortsOrch 経由) — MAP 登録前に VLAN が PortsOrch に登録必須
3. `gUnderlayIfId` — orchagent 起動時 SAI 初期化済みのため実用上の前提条件にならない
4. `gVirtualRouterId` — 同上
