# ERSPAN Platform Investigation (Phase H)

## 調査対象
- `sonic-swss/orchagent/mirrororch.cpp`
- `sonic-swss/orchagent/switchorch.cpp`
- `sonic-swss/orchagent/orch.h`

## 主要発見事項

### 1. Mellanox gre_type 分岐 (mirrororch.cpp:57-71)

`MirrorEntry::MirrorEntry(const string& platform)` がコンストラクタ引数で platform 文字列を受け取り、
`MLNX_PLATFORM_SUBSTRING = "mellanox"` に一致する場合 `greType = 0x8949`、それ以外は `0x88be`。

呼び出し元: `createEntry()` (mirrororch.cpp:395) で `getenv("platform")` を platform として渡す。

YANG では `0x88be` のみがデフォルトとして定義されており、Mellanox では YANG 定義と実装が乖離。

### 2. SAI_MIRROR_SESSION_ATTR_TC 非対応プラットフォーム (mirrororch.cpp:931-936)

`queue != 0` のときのみ `SAI_MIRROR_SESSION_ATTR_TC` を attrs に push する。
コメント: "Some platforms don't support SAI_MIRROR_SESSION_ATTR_TC and only support global mirror session traffic class."

デフォルト `queue = 0` にすることで、未対応 ASIC への誤送出を回避している設計。

### 3. ポートミラー Capability クエリ (switchorch.cpp:1903-1952)

`querySwitchPortMirrorCapability()` が起動時に:
- `SAI_PORT_ATTR_INGRESS_MIRROR_SESSION` → `m_portIngressMirrorSupported`
- `SAI_PORT_ATTR_EGRESS_MIRROR_SESSION` → `m_portEgressMirrorSupported`

クエリ失敗時は `true` フォールバック（MirrorOrch がエラーを後続で受け取る設計）。

`mirrororch.cpp:817-824` で `isPortIngressMirrorSupported()` / `isPortEgressMirrorSupported()` を参照。

### 4. VoQ DST_MAC 分岐 (mirrororch.cpp:1037-1044)

```cpp
if ((gMySwitchType == "voq") && (session.type == MIRROR_SESSION_ERSPAN))
    memcpy(attr.value.mac, gMacAddress.getMac(), sizeof(sai_mac_t));
else
    memcpy(attr.value.mac, session.neighborInfo.mac.getMac(), sizeof(sai_mac_t));
```

VoQ シャーシでは router MAC を ERSPAN の dst MAC に使う。

### 5. VLAN 経由ネクストホップ (mirrororch.cpp:980-1003)

`session.neighborInfo.port.m_type == Port::VLAN` のときのみ:
- VLAN_HEADER_VALID / VLAN_TPID / VLAN_ID / VLAN_PRI / VLAN_CFI を attrs に追加。
非 VLAN ではこれらの属性は送られない。

### 6. ERSPAN_ENCAPSULATION_TYPE は全環境共通

常に `SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL` (mirrororch.cpp:1005-1006)。
