# control-plane-acl — Phase E: コード定数カタログ

## 調査対象ファイル

| ファイル | SHA |
|---------|-----|
| `sonic-swss/orchagent/acltable.h` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `sonic-swss/orchagent/aclorch.h` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `sonic-swss/orchagent/aclorch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `sonic-host-services/scripts/caclmgrd` | c5bbbe8b07b96f078fa4b761316627404b01bd04 |

---

## 1. acltable.h: フィールド名マクロ

```c
// acltable.h:12-16
#define ACL_TABLE_DESCRIPTION  "POLICY_DESC"
#define ACL_TABLE_STAGE        "STAGE"
#define ACL_TABLE_TYPE         "TYPE"
#define ACL_TABLE_PORTS        "PORTS"
#define ACL_TABLE_SERVICES     "SERVICES"
```

CONFIG_DB の field 名と C++ マクロ名の対応。  
CTRLPLANE ACL に関係するのは TYPE/STAGE/SERVICES の 3 つ。

## 2. acltable.h: テーブル TYPE 値マクロ

```c
// acltable.h:26-42
#define TABLE_TYPE_L3                   "L3"
#define TABLE_TYPE_L3V6                 "L3V6"
#define TABLE_TYPE_L3V4V6               "L3V4V6"
#define TABLE_TYPE_MIRROR               "MIRROR"
#define TABLE_TYPE_MIRRORV6             "MIRRORV6"
#define TABLE_TYPE_MIRROR_DSCP          "MIRROR_DSCP"
#define TABLE_TYPE_PFCWD                "PFCWD"
#define TABLE_TYPE_CTRLPLANE            "CTRLPLANE"   // ← CTRLPLANE 専用
#define TABLE_TYPE_DTEL_FLOW_WATCHLIST  "DTEL_FLOW_WATCHLIST"
#define TABLE_TYPE_MCLAG                "MCLAG"
#define TABLE_TYPE_MUX                  "MUX"
#define TABLE_TYPE_DROP                 "DROP"
#define TABLE_TYPE_MARK_META            "MARK_META"
#define TABLE_TYPE_MARK_META_V6         "MARK_METAV6"
#define TABLE_TYPE_EGR_SET_DSCP         "EGR_SET_DSCP"
#define TABLE_TYPE_UNDERLAY_SET_DSCP    "UNDERLAY_SET_DSCP"
#define TABLE_TYPE_UNDERLAY_SET_DSCPV6  "UNDERLAY_SET_DSCPV6"
```

## 3. acltable.h: STAGE 値マクロと enum

```c
// acltable.h:22-24
#define STAGE_INGRESS      "INGRESS"
#define STAGE_EGRESS       "EGRESS"
#define STAGE_PRE_INGRESS  "PRE_INGRESS"

// acltable.h:44-50
typedef enum {
    ACL_STAGE_UNKNOWN,
    ACL_STAGE_INGRESS,
    ACL_STAGE_EGRESS,
    ACL_STAGE_PRE_INGRESS
} acl_stage_type_t;
```

CTRLPLANE テーブルでは `validate()` が stage チェックをスキップするため INGRESS/EGRESS はどちらも実質無効。

## 4. aclorch.h: PACKET_ACTION 値マクロ

```c
// aclorch.h:83-88
#define PACKET_ACTION_FORWARD      "FORWARD"
#define PACKET_ACTION_DROP         "DROP"
#define PACKET_ACTION_COPY         "COPY"
#define PACKET_ACTION_REDIRECT     "REDIRECT"
#define PACKET_ACTION_DO_NOT_NAT   "DO_NOT_NAT"
#define PACKET_ACTION_DISABLE_TRIM "DISABLE_TRIM"
```

caclmgrd は ACL_RULE.PACKET_ACTION を `iptables -j <値>` の jump target に直接渡す（`caclmgrd:873`）。
使用可能値は `ACCEPT` / `DROP` のみ（iptables 互換）。`FORWARD` / `COPY` / `REDIRECT` はカーネルが未認識で iptables コマンドが失敗する。

## 5. caclmgrd: モジュールレベル定数

```python
# caclmgrd:28-32
VERSION = "1.0"
SYSLOG_IDENTIFIER = "caclmgrd"
DEFAULT_NAMESPACE = ''
```

## 6. caclmgrd: クラス定数 (ControlPlaneAclManager)

```python
# caclmgrd:77-123
FEATURE_TABLE = "FEATURE"
ACL_TABLE = "ACL_TABLE"
ACL_RULE = "ACL_RULE"
DEVICE_METADATA_TABLE = "DEVICE_METADATA"
MUX_CABLE_TABLE = "MUX_CABLE_TABLE"
CONFIG_MUX_CABLE = "MUX_CABLE"
LOOPBACK_TABLE = "LOOPBACK_INTERFACE"
VLAN_INTF_TABLE = "VLAN_INTERFACE"

ACL_TABLE_TYPE_CTRLPLANE = "CTRLPLANE"   # type=CTRLPLANE の比較に使用

BFD_SESSION_TABLE = "BFD_SESSION_TABLE"
VXLAN_TUNNEL_TABLE = "VXLAN_TUNNEL"
DPU_TABLE = "DPU"
MID_PLANE_BRIDGE_TABLE = "MID_PLANE_BRIDGE"

smartswitch_midplane_bridge_ip = "169.254.200.254"   # SmartSwitch デフォルト Midplane IP

UPDATE_DELAY_SECS = 0.5   # ACL 更新デバウンス間隔 (秒)

DualToR = False
bfdAllowed = False
VxlanAllowed = False
VxlanSrcIP = ""
dashHaPortMap = {}   # dpu名→swbus_port マップ
```

## 7. caclmgrd: ACL_SERVICES 定数テーブル

```python
# caclmgrd:95-120
ACL_SERVICES = {
    "NTP": {
        "ip_protocols": ["udp"],
        "dst_ports": ["123"],
        "multi_asic_ns_to_host_fwd": False
    },
    "SNMP": {
        "ip_protocols": ["tcp", "udp"],
        "dst_ports": ["161"],
        "multi_asic_ns_to_host_fwd": True
    },
    "SSH": {
        "ip_protocols": ["tcp"],
        "dst_ports": ["22"],
        "multi_asic_ns_to_host_fwd": True
    },
    "EXTERNAL_CLIENT": {
        "ip_protocols": ["tcp"],
        # dst_ports なし → ACL_RULE の L4_DST_PORT / L4_DST_PORT_RANGE から取得
        "multi_asic_ns_to_host_fwd": False
    },
    "ANY": {
        "ip_protocols": ["any"],
        "dst_ports": ["0"],    # 0 = 全ポート (dst port フィルタ無効)
        "multi_asic_ns_to_host_fwd": False
    }
}
```

`services` フィールドに設定できる有効値はこの 5 種のみ。それ以外は `log_warning` + スキップ。  
`dst_ports: ["0"]` は caclmgrd 内部の「全ポート」フラグ: `if dst_port != "0": rule_cmd += ["--dport", ...]`

## 8. caclmgrd: ハードコードポート番号

| プロトコル | ポート番号 | 用途 | コード箇所 |
|---|---|---|---|
| UDP 123 | 123 | NTP | `ACL_SERVICES` |
| TCP/UDP 161 | 161 | SNMP | `ACL_SERVICES` |
| TCP 22 | 22 | SSH | `ACL_SERVICES` |
| UDP 67:68 | 67-68 | DHCP v4 | `caclmgrd:711` |
| UDP 546:547 | 546-547 | DHCP v6 | `caclmgrd:715` |
| TCP 179 | 179 | BGP | `caclmgrd:720-721` |
| UDP 3784, 4784 | 3784, 4784 | BFD | `get_bfd_iptable_commands()` |
| UDP 4789 | 4789 | VxLAN | `get_vxlan_port_iptable_commands()` |
| UDP/TCP 1025:65535 | 1025-65535 | traceroute TTL<2 | `caclmgrd:891-894` |

## 9. caclmgrd: TCP_PROTOCOL_NUM (aclorch.cpp)

```c
// aclorch.cpp:54
const int TCP_PROTOCOL_NUM = 6; // TCP protocol number
```

orchagent 内部の TCP プロトコル番号定数。CTRLPLANE ACL では SAI に送出されないため直接影響しない。

## 10. 定数利用フロー図

```
CONFIG_DB ACL_TABLE.type ──→ ACL_TABLE_TYPE_CTRLPLANE 比較 (caclmgrd:743, acltable.h:33)
                               └─ "CTRLPLANE" 一致 → ACL_SERVICES 参照
CONFIG_DB ACL_TABLE.services ──→ ACL_SERVICES dict キー照合
                                  ├─ "NTP" → ip_protocols=[udp], dst_ports=[123]
                                  ├─ "SNMP" → ip_protocols=[tcp,udp], dst_ports=[161]
                                  ├─ "SSH" → ip_protocols=[tcp], dst_ports=[22]
                                  ├─ "EXTERNAL_CLIENT" → dst_ports は ACL_RULE から取得
                                  └─ "ANY" → ip_protocols=[any], dst_ports=[0] (全ポート)
CONFIG_DB ACL_RULE.PACKET_ACTION ──→ iptables -j <VALUE> に直接渡す
                                       ├─ "ACCEPT" ✅
                                       └─ "DROP" ✅
                                       └─ その他 → iptables コマンド失敗
```
