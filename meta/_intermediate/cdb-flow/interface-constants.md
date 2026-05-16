# INTERFACE — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-net/sonic-swss/cfgmgr/intfmgr.cpp` (MTU デフォルト、ループバック MTU、MTU 継承マーカー、Consumer 優先度、prefix 長閾値、VoQ IPv6 metric)
- `sonic-net/sonic-swss/orchagent/intfsorch.cpp` (Orch 優先度、タイマー周期)
- `sonic-net/sonic-swss/orchagent/intfsorch.h` (RIF フレックスカウンター定数)
- `sonic-net/sonic-swss/lib/subintf.cpp` (インタフェース名長上限)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-interface.yang` (nat_zone range/default)

---

## 1. MTU 関連定数 (intfmgr.cpp L24-29)

| 定数 / マクロ名 | 値 | 定義ファイル | 意味・影響 |
|-----------------|-----|--------------|-----------|
| `DEFAULT_MTU_STR` | `9100` | `intfmgr.cpp:29` | 物理 Ethernet ポートの **デフォルト MTU** (bytes)。PORT テーブルに `mtu` フィールドがない場合にフォールバックされる |
| `LOOPBACK_DEFAULT_MTU_STR` | `"65536"` | `intfmgr.cpp:28` | `ip link add <alias> mtu 65536 type dummy` でループバック作成時に固定使用。物理ポートへは適用されない |
| `MTU_INHERITANCE` | `"0"` | `intfmgr.cpp:24` | サブインタフェースが親ポートの MTU を継承することを示す内部マーカー。APP_DB に `mtu=0` として書き込まれる |

> **`DEFAULT_MTU_STR 9100` の出処**: SONiC の歴史的デフォルト値。Ethernet フレームの Jumbo Frame 標準 (9000 bytes payload + 100 bytes overhead) に由来するとされるが、公式 HLD には明記なし。

---

## 2. インタフェース名前接頭辞 / VRF 識別 (intfmgr.cpp L19-26)

| 定数 / マクロ名 | 値 | 定義ファイル | 意味・影響 |
|-----------------|-----|--------------|-----------|
| `LOOPBACK_PREFIX` | `"Loopback"` | `intfmgr.cpp:22` | ループバックインタフェース判定の文字列プレフィクス |
| `VRF_PREFIX` | `"Vrf"` | `intfmgr.cpp:25` | VRF インタフェース判定の文字列プレフィクス。`alias.compare(0, strlen(VRF_PREFIX), VRF_PREFIX)` で比較 |
| `VRF_MGMT` | `"mgmt"` | `intfmgr.cpp:26` | mgmt VRF の識別名。`intfsorch.cpp:47` では `MGMT_VRF "mgmt"` として再定義 |

---

## 3. SAI Router Interface 属性 (intfsorch.cpp)

| 属性 ID | 操作 | 定義 / 使用箇所 | 意味 |
|---------|------|----------------|------|
| `SAI_ROUTER_INTERFACE_ATTR_MTU` | SET | `intfsorch.cpp:226` | RIF の MTU を SAI に設定。`port.m_mtu` の値を渡す |
| `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` | SET/CREATE | `intfsorch.cpp:252` | RIF の送信元 MAC。`port.m_mac` または `gMacAddress` (グローバル) をフォールバック |
| `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` | SET | `intfsorch.cpp:285` | NAT ゾーン ID (0..3)。デフォルト `0` は SAI 初期化時 (`port.m_nat_zone_id = 0`) で設定 |
| `SAI_ROUTER_INTERFACE_ATTR_ADMIN_V4_STATE` | SET | `intfsorch.cpp:312` | IPv4 admin state (enable/disable) |
| `SAI_ROUTER_INTERFACE_ATTR_ADMIN_V6_STATE` | SET | `intfsorch.cpp:326` | IPv6 admin state (enable/disable) |
| `SAI_ROUTER_INTERFACE_ATTR_ADMIN_MPLS_STATE` | SET | `intfsorch.cpp:201` | MPLS admin state |
| `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` | SET/CREATE | `intfsorch.cpp:441,1192` | ループバックパケット処置 (drop/forward/trap 等) |

---

## 4. フレックスカウンター / タイマー定数 (intfsorch.h, intfsorch.cpp)

| 定数 / マクロ名 | 値 | 定義ファイル | 意味・影響 |
|-----------------|-----|--------------|-----------|
| `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"RIF_STAT_COUNTER"` | `intfsorch.h:19` | RIF 統計カウンターグループ名 (FLEX_COUNTER_DB のキー) |
| `RIF_RATE_COUNTER_FLEX_COUNTER_GROUP` | `"RIF_RATE_COUNTER"` | `intfsorch.h:20` | RIF レートカウンターグループ名 |
| `RIF_FLEX_STAT_COUNTER_POLL_MSECS` | `"1000"` ms | `intfsorch.h:21` | RIF 統計フレックスカウンターのポーリング間隔。1 秒周期で SAI から in/out パケット・オクテット・エラーを収集 |
| `UPDATE_MAPS_SEC` | `1` 秒 | `intfsorch.cpp:45` | `m_updateMapsTimer` 周期。RIF 名 → カウンタ ID マップを COUNTERS_DB に更新する間隔 |
| `intfsorch_pri` | `35` | `intfsorch.cpp:43` | `IntfsOrch` の Orch 優先度。数値が小さいほど優先度高 |

---

## 5. Consumer キュー優先度 (intfmgr.cpp)

| 定数 | 値 | 定義ファイル | 意味・影響 |
|------|----|--------------|-----------|
| STATE_PORT Consumer 優先度 | `100` | `intfmgr.cpp:46` | `SubscriberStateTable` の pri 引数。STATE_PORT_TABLE 変化通知のキュー優先度 |
| STATE_LAG Consumer 優先度 | `200` | `intfmgr.cpp:51` | STATE_LAG_TABLE 変化通知のキュー優先度 |
| `DEFAULT_POP_BATCH_SIZE` | `128` | `sonic-swss-common` `table.h:164` | Consumer キューの 1 回あたりデフォルトポップ数 |

---

## 6. IP アドレス付与閾値 (intfmgr.cpp)

| 条件 | 値 | 定義ファイル | 意味・影響 |
|------|----|--------------|-----------|
| IPv4 broadcast 付与閾値 | プレフィクス長 `< 31` | `intfmgr.cpp:89` | `/31` 以上 (`/31`, `/32`) では broadcast オプションなしで `ip address add` を実行 |
| IPv6 broadcast 付与閾値 | プレフィクス長 `< 127` | `intfmgr.cpp:108` | `/127` 以上 (`/127`, `/128`) では broadcast オプションなしで `ip -6 address add` を実行 |
| VoQ IPv6 metric | `256` | `intfmgr.cpp:105` | `switch_type=voq` のときのみ IPv6 アドレス追加に `metric 256` を付与。通常構成では metric 指定なし (kernel default) |

---

## 7. IPv6 link-local 除外フィルタ (intfmgr.cpp L252-255)

`intfmgr.cpp` の IP アドレス数カウント処理では `grep -v 'inet6 fe80:'` を使用して link-local アドレス (`fe80::/10`) を明示的に除外する。これにより「ユーザ設定 IP アドレス数が 0 か否か」の判定が正確に行われる。

---

## 8. サブインタフェース名長上限 (subintf.cpp)

| 条件 | 値 | 定義ファイル | 意味・影響 |
|------|----|--------------|-----------|
| サブインタフェース名上限 | `< IFNAMSIZ` (16) → **15 文字以下** | `subintf.cpp:65` | `alias.length() >= IFNAMSIZ` を満たすとサブインタフェース無効判定。Linux カーネルの `IFNAMSIZ=16` に由来 |

---

## 9. YANG 制約 (sonic-interface.yang)

| フィールド | 制約 | 定義ファイル | 意味 |
|-----------|------|--------------|------|
| `nat_zone` | `range "0..3"` (uint8) | `sonic-interface.yang:79` | 4 ゾーンのみ許容。YANG バリデーションと SAI 初期化 (`port.m_nat_zone_id = 0`) の両方でデフォルト `0` を保持 |

> **nat_zone の二重定義**: `nat_zone` デフォルト `0` は YANG `default "0"` と SAI 初期化 (`port.m_nat_zone_id = 0`, `intfsorch.cpp:1361`) の両方に現れる。どちらか片方の変更では不整合が生じる。

---

## 特記事項

1. **`DEFAULT_MTU_STR 9100`**: 物理 Ethernet ポートのデフォルト。`LOOPBACK_DEFAULT_MTU_STR 65536` はループバック (`type dummy`) 専用で、両者は別々に管理される。
2. **MTU 継承 (`MTU_INHERITANCE="0"`)**: サブインタフェースが `mtu=0` を持つ場合、親ポートの MTU を実行時に取得して適用する。APP_DB に `mtu=0` が書き込まれた時点では実 MTU は未確定。
3. **SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS**: ポートに `mac_addr` が設定されていない場合は `gMacAddress` (グローバル変数、`DEVICE_METADATA|localhost.mac` から初期化) を使用。
4. **IPv6 link-local (`fe80::`)**: `ipv6_use_link_local_only` フィールドで enable/disable 制御。disable 時は `APP_NEIGH_TABLE` から link-local ネイバーエントリを削除する副作用がある。
5. **VoQ IPv6 metric 256**: `switch_type=voq` 専用。非 VoQ 環境では Linux カーネルのデフォルト metric が使われる (通常 0 または 1024)。

---

## 出典

- `sonic-net/sonic-swss/cfgmgr/intfmgr.cpp` L19-29, L46-51, L89, L105, L108, L201, L227, L252-255, L677-678, L696, L913-926
- `sonic-net/sonic-swss/orchagent/intfsorch.cpp` L43-47, L201, L226-234, L252, L285, L312, L326, L441, L1148-1193, L1272-1273, L1361
- `sonic-net/sonic-swss/orchagent/intfsorch.h` L19-21
- `sonic-net/sonic-swss/lib/subintf.cpp` L65
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-interface.yang` L79
