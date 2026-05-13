# ACL_RULE enum 値別深掘り grep 証跡 (v2)

生成日: 2026-05-13
対象ファイル: sonic-swss/orchagent/aclorch.h, aclorch.cpp, acltable.h
          sonic-swss-common/common/converter.h
          sonic-mgmt-common/models/yang/sonic/sonic-acl.yang

---

## フィールド: PACKET_ACTION (3 値)

### FORWARD
- grep hit: `aclorch.h:83` `#define PACKET_ACTION_FORWARD "FORWARD"`
- grep hit: `aclorch.cpp:145` `{ PACKET_ACTION_FORWARD, SAI_PACKET_ACTION_FORWARD }`
- SAI マッピング: `SAI_PACKET_ACTION_FORWARD`
- 挙動: パケットを通過させる

### DROP
- grep hit: `aclorch.h:84` `#define PACKET_ACTION_DROP "DROP"`
- grep hit: `aclorch.cpp:146` `{ PACKET_ACTION_DROP, SAI_PACKET_ACTION_DROP }`
- SAI マッピング: `SAI_PACKET_ACTION_DROP`
- 挙動: パケットをドロップ

### REDIRECT
- grep hit: `aclorch.h:86` `#define PACKET_ACTION_REDIRECT "REDIRECT"`
- grep hit: `aclorch.cpp:2013` backward compatibility として ACTION_PACKET_ACTION フィールドで `REDIRECT:` プレフィックス解析
- 挙動: `REDIRECT:<target>` 形式で指定、`getRedirectObjectId()` で解決。コロンなし or ターゲットなしは `return false` → rule INACTIVE
- 注: YANG では FORWARD/DROP/REDIRECT の 3 値のみ (sonic-acl.yang:114-116)

### 複合条件
- `PACKET_ACTION=REDIRECT` は `ACTION_REDIRECT_ACTION` フィールドとの混在も可能 (別フィールド経由)
- `aclPacketActionLookup` に存在しない値は backward compat REDIRECT チェック → それも失敗で `return false`

---

## フィールド: IP_TYPE (7 値)

### ANY
- grep hit: `aclorch.cpp:503` `{ IP_TYPE_ANY, SAI_ACL_IP_TYPE_ANY }`
- grep hit: `aclorch.h:100` `#define IP_TYPE_ANY "ANY"`
- SAI: `SAI_ACL_IP_TYPE_ANY` — IP/非IP 問わず全パケット

### IP
- grep hit: `aclorch.cpp:504` `{ IP_TYPE_IP, SAI_ACL_IP_TYPE_IP }`
- grep hit: `aclorch.h:99` `#define IP_TYPE_IP "IP"`
- SAI: `SAI_ACL_IP_TYPE_IP` — IPv4/IPv6 どちらかのパケット

### IPV4 (YANG: `IPV4`, aclorch: 実装上は IPV4ANY と同義)
- grep hit: YANG sonic-acl.yang:125 `enum IPV4`
- aclorch.h には `IP_TYPE_IPv4ANY "IPV4ANY"` はあるが `IPV4` は別途。YANG のみで定義

### IPV4ANY
- grep hit: `aclorch.cpp:506` `{ IP_TYPE_IPv4ANY, SAI_ACL_IP_TYPE_IPV4ANY }`
- grep hit: `aclorch.h:101` `#define IP_TYPE_IPv4ANY "IPV4ANY"`
- SAI: `SAI_ACL_IP_TYPE_IPV4ANY` — IPv4 パケット

### NON_IPV4
- grep hit: `aclorch.cpp:507` `{ IP_TYPE_NON_IPv4, SAI_ACL_IP_TYPE_NON_IPV4 }`
- grep hit: `aclorch.h:102` `#define IP_TYPE_NON_IPv4 "NON_IPV4"`
- SAI: `SAI_ACL_IP_TYPE_NON_IPV4` — 非 IPv4 パケット

### IPV6ANY
- grep hit: `aclorch.cpp:508` `{ IP_TYPE_IPv6ANY, SAI_ACL_IP_TYPE_IPV6ANY }`
- grep hit: `aclorch.h:103` `#define IP_TYPE_IPv6ANY "IPV6ANY"`
- SAI: `SAI_ACL_IP_TYPE_IPV6ANY` — IPv6 パケット

### NON_IPV6
- grep hit: `aclorch.cpp:509` `{ IP_TYPE_NON_IPv6, SAI_ACL_IP_TYPE_NON_IPV6 }`
- grep hit: `aclorch.h:104` `#define IP_TYPE_NON_IPv6 "NON_IPV6"`
- SAI: `SAI_ACL_IP_TYPE_NON_IPV6` — 非 IPv6 パケット

### 追加値 (aclorch 実装にあるが YANG 未定義)
- `ARP` → `SAI_ACL_IP_TYPE_ARP` (`aclorch.cpp:510`)
- `ARP_REQUEST` → `SAI_ACL_IP_TYPE_ARP_REQUEST` (`aclorch.cpp:511`)
- `ARP_REPLY` → `SAI_ACL_IP_TYPE_ARP_REPLY` (`aclorch.cpp:512`)

### YANG との cross-check
YANG (sonic-acl.yang:122-130) では `ANY/IP/IPV4/IPV4ANY/NON_IPV4/IPV6ANY/NON_IPV6` の 7 値。
aclorch は `ARP/ARP_REQUEST/ARP_REPLY` も追加で受理するが YANG バリデーション経路では通過しない。

### 複合条件
- `IP_TYPE=IPV4ANY` + `SRC_IPV6` 同一ルール → `bAllAttributesOk=false` → rule INACTIVE (aclorch.cpp:5636-5658)
- YANG `choice ip_src_dst` で `IP_TYPE` が IPv4 系の場合 SRC_IP/DST_IP のみ許可、IPv6 系の場合 SRC_IPV6/DST_IPV6 のみ許可 (sonic-acl.yang:150-168)

---

## フィールド: ETHER_TYPE (7 値)

YANG pattern: `(0x88CC)|(0x8100)|(0x8915)|(0x0806)|(0x0800)|(0x86DD)|(0x8847)` — 正規表現の交替、実際の格納値はこれらの文字列そのもの。

aclorch 解析: `to_uint<uint16_t>(attr_value)` (`aclorch.cpp:1066`)。
`__to_uint64` は `stoul(str, &idx, 0)` (base=0) で 0x プレフィックス自動判定 (`converter.h:18`)。

### 0x88CC
- grep hit: YANG sonic-acl.yang:142 (pattern)
- プロトコル: LLDP (Link Layer Discovery Protocol)

### 0x8100
- grep hit: YANG sonic-acl.yang:142 (pattern)
- プロトコル: IEEE 802.1Q VLAN タグ

### 0x8915
- grep hit: YANG sonic-acl.yang:142 (pattern)
- プロトコル: RoCE (RDMA over Converged Ethernet)

### 0x0806
- grep hit: YANG sonic-acl.yang:142 (pattern)
- プロトコル: ARP

### 0x0800
- grep hit: YANG sonic-acl.yang:142 (pattern)
- プロトコル: IPv4

### 0x86DD
- grep hit: YANG sonic-acl.yang:142 (pattern)
- プロトコル: IPv6

### 0x8847
- grep hit: YANG sonic-acl.yang:142 (pattern)
- プロトコル: MPLS ユニキャスト

### 注記
- aclorch 自体はこの 7 値以外の任意 uint16 も受理 (YANG バリデーション外)
- マスク: `0xFFFF` (完全一致) で SAI に投入 (`aclorch.cpp:1067`)

---

## フィールド: stage (2 値) — ACL_RULE の stage は ACL_TABLE から継承

ACL_RULE 自体に `stage` フィールドはないが、所属 ACL_TABLE の stage により動作が変わる。

### INGRESS
- grep hit: `aclorch.cpp:166` `{STAGE_INGRESS, ACL_STAGE_INGRESS}`
- grep hit: `aclorch.cpp:173` ACL_STAGE_INGRESS, `SAI_ACL_ACTION_TYPE_MIRROR_INGRESS`
- 挙動: MIRROR_INGRESS_ACTION が有効。ingress ポートでルール評価

### EGRESS
- grep hit: `aclorch.cpp:167` `{STAGE_EGRESS, ACL_STAGE_EGRESS}`
- grep hit: `aclorch.cpp:185` ACL_STAGE_EGRESS
- 挙動: MIRROR_EGRESS_ACTION のみ有効。egress ポートでルール評価

---

## フィールド: type (4 値) — ACL_TABLE の type フィールド (ACL_RULE に影響)

ACL_RULE は所属テーブルの `type` によって使用可能な match/action が制限される。

### MIRROR
- grep hit: `acltable.h:29` `#define TABLE_TYPE_MIRROR "MIRROR"`
- grep hit: `aclorch.cpp:260` MIRROR table definition with `SAI_ACL_ACTION_TYPE_MIRROR_INGRESS`
- grep hit: `aclorch.cpp:3502` `{ TABLE_TYPE_MIRROR, true }` mirror capability
- 挙動: MIRROR セッションへの転送専用。capability 確認なしでは reject

### MIRRORV6
- grep hit: `acltable.h:30` `#define TABLE_TYPE_MIRRORV6 "MIRRORV6"`
- grep hit: `aclorch.cpp:279` MIRRORV6 definition
- grep hit: `aclorch.cpp:3503` `{ TABLE_TYPE_MIRRORV6, true }`, `aclorch.cpp:3511` `{ TABLE_TYPE_MIRRORV6, false }` (capability が ASIC 依存)
- 挙動: IPv6 ミラー専用。`m_isCombinedMirrorV6Table` が true の場合は MIRROR テーブルと統合

### L3
- grep hit: `acltable.h:26` `#define TABLE_TYPE_L3 "L3"`
- grep hit: `aclorch.cpp:200` TABLE_TYPE_L3 definition, `aclorch.cpp:454` ingress stage match fields
- 挙動: 通常の IPv4 L3 ACL。MIRROR_INGRESS_ACTION 有効

### L3V6
- grep hit: `acltable.h:27` `#define TABLE_TYPE_L3V6 "L3V6"`
- grep hit: `aclorch.cpp:220` TABLE_TYPE_L3V6 definition, `aclorch.cpp:471` match fields
- grep hit: `aclorch.cpp:1231` IP_PROTOCOL on L3V6 tables deprecation warning
- 挙動: IPv6 L3 ACL。IP_PROTOCOL 使用は非推奨 (将来削除予定)、NEXT_HEADER を使う

---

## 値別 grep カバレッジサマリ

| フィールド | 値 | hit数 | 主要証跡 |
|---|---|---|---|
| PACKET_ACTION | FORWARD | 2 | aclorch.h:83, cpp:145 |
| PACKET_ACTION | DROP | 2 | aclorch.h:84, cpp:146 |
| PACKET_ACTION | REDIRECT | 2 | aclorch.h:86, cpp:2013 |
| IP_TYPE | ANY | 2 | aclorch.h:100, cpp:503 |
| IP_TYPE | IP | 2 | aclorch.h:99, cpp:504 |
| IP_TYPE | IPV4 | 1 | yang:125 (YANG のみ) |
| IP_TYPE | IPV4ANY | 2 | aclorch.h:101, cpp:506 |
| IP_TYPE | NON_IPV4 | 2 | aclorch.h:102, cpp:507 |
| IP_TYPE | IPV6ANY | 2 | aclorch.h:103, cpp:508 |
| IP_TYPE | NON_IPV6 | 2 | aclorch.h:104, cpp:509 |
| ETHER_TYPE | 0x88CC | 1 | yang:142 (LLDP) |
| ETHER_TYPE | 0x8100 | 1 | yang:142 (VLAN) |
| ETHER_TYPE | 0x8915 | 1 | yang:142 (RoCE) |
| ETHER_TYPE | 0x0806 | 1 | yang:142 (ARP) |
| ETHER_TYPE | 0x0800 | 1 | yang:142 (IPv4) |
| ETHER_TYPE | 0x86DD | 1 | yang:142 (IPv6) |
| ETHER_TYPE | 0x8847 | 1 | yang:142 (MPLS) |
| stage | INGRESS | 3 | cpp:166,173,265 |
| stage | EGRESS | 2 | cpp:167,185 |
| type | MIRROR | 4 | acltable.h:29, cpp:260,3502,3511 |
| type | MIRRORV6 | 4 | acltable.h:30, cpp:279,3503,3511 |
| type | L3 | 2 | acltable.h:26, cpp:200 |
| type | L3V6 | 3 | acltable.h:27, cpp:220,1231 |

## 複合条件発見数: 5

1. `IP_TYPE=IPV4ANY` + `SRC_IPV6` 混在 → rule INACTIVE (`aclorch.cpp:5636-5658`)
2. YANG `choice ip_src_dst` で IP_TYPE に応じて SRC_IP/SRC_IPV6 を制約 (`sonic-acl.yang:150-168`)
3. `MIRROR`/`MIRRORV6` type は ASIC capability 確認が必須 (`aclorch.cpp:3502-3541`)
4. `PACKET_ACTION=REDIRECT` の backward compat パス (`aclorch.cpp:2013`) — コロン/ターゲット不在で reject
5. stage=INGRESS vs EGRESS で MIRROR action の種類が変わる (`aclorch.cpp:263-291`)
