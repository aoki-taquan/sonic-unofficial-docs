# NVGRE_TUNNEL / NVGRE_TUNNEL_MAP — Phase C 暗黙参照調査

## 調査対象ファイル

- `sonic-swss/orchagent/nvgreorch.cpp` (全行精読)
- `sonic-swss/orchagent/nvgreorch.h` (全行精読)
- `sonic-swss/orchagent/orchdaemon.cpp:361-364,598-599`
- `sonic-swss/orchagent/main.cpp:48-49,902-974`

## 検出した暗黙参照

### 1. `VLAN` テーブル (CONFIG_DB) — via PortsOrch

`NvgreTunnelMapOrch::addOperation()` L489:
```cpp
if (!gPortsOrch->getVlanByVlanId(vlan_id, port))
{
    SWSS_LOG_WARN("VLAN ID doesn't exist: %d", vlan_id);
    return true;  // エントリを破棄
}
```

`gPortsOrch` は起動時グローバル。`getVlanByVlanId()` は PortsOrch が CONFIG_DB `VLAN` テーブルから構築した内部マップを参照する。
`VLAN` エントリが登録されていない場合、MAP エントリは **silent drop** される（retry なし）。

### 2. `gVirtualRouterId` — SAI スイッチ属性から取得

`main.cpp:902`:
```cpp
gVirtualRouterId = attr.value.oid;
```
`SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID` をスイッチ初期化時 (orchagent main) に取得。
`NvgreTunnel::NvgreTunnel()` L313 で `sai_create_tunnel_termination()` の引数として使用。
orch 起動前に orchagent main が設定済み。

### 3. `gUnderlayIfId` — SAI ルーターインターフェース (グローバルループバック RIF)

`main.cpp:967`:
```cpp
status = sai_router_intfs_api->create_router_interface(&gUnderlayIfId, ...);
```
orchagent 起動時に SAI でアンダーレイ RIF を作成してグローバル変数に格納。
`NvgreTunnel::NvgreTunnel()` L312 で `sai_create_tunnel()` の引数として使用。

### 4. `NvgreTunnelOrch` (内部) — NVGRE_TUNNEL テーブル

`NvgreTunnelMapOrch::addOperation()` L469-471:
```cpp
NvgreTunnelOrch* tunnel_orch = gDirectory.get<NvgreTunnelOrch*>();
if (!tunnel_orch->isTunnelExists(tunnel_name))
{
    SWSS_LOG_WARN("NVGRE tunnel '%s' doesn't exist", tunnel_name.c_str());
    return true;  // エントリを破棄
}
```
`gDirectory` 経由で `NvgreTunnelOrch` を取得し、内部マップ `m_nvgreTunnels` に存在確認。
`NVGRE_TUNNEL` エントリが未登録の場合は MAP エントリが **silent drop** される（retry なし）。

### 5. YANG leafref — `NVGRE_TUNNEL_MAP.tunnel_name`

`sonic-nvgre-tunnel.yang`:
```
leaf tunnel_name {
    type leafref {
        path "/stun:sonic-nvgre-tunnel/stun:NVGRE_TUNNEL/stun:NVGRE_TUNNEL_LIST/stun:tunnel_name";
    }
}
```
YANG スキーマレベルでも `NVGRE_TUNNEL_MAP` は `NVGRE_TUNNEL` を参照する leafref が定義されている。

## 結論

| 参照先 | 参照フィールド/変数 | 未解決時の挙動 | 証跡 |
|--------|----------------|--------------|------|
| `CONFIG_DB VLAN` テーブル | `vlan_id` → PortsOrch 内部マップ | MAP エントリ silent drop (return true) | `nvgreorch.cpp:489` |
| `NvgreTunnelOrch` 内部 (NVGRE_TUNNEL) | `tunnel_name` → `m_nvgreTunnels` | MAP エントリ silent drop (return true) | `nvgreorch.cpp:471` |
| `gVirtualRouterId` (SAI スイッチ属性) | デフォルト VRF OID | orchagent 起動時に設定済み (依存なし) | `main.cpp:902`, `nvgreorch.cpp:313` |
| `gUnderlayIfId` (SAI RIF) | アンダーレイ RIF OID | orchagent 起動時に設定済み (依存なし) | `main.cpp:967`, `nvgreorch.cpp:312` |
