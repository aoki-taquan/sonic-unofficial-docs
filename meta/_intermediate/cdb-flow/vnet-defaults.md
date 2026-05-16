# VNET / VNET_ROUTE — Phase A: コード由来のデフォルト解析

生成日: 2026-05-14  
対象ファイル: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vnet.yang`、`sonic-swss/orchagent/vnetorch.cpp`、`sonic-swss/orchagent/vnetorch.h`、`sonic-swss-common/common/macaddress.cpp`

---

## フィールドごとのデフォルト・挙動まとめ

### VNET テーブル

#### `vxlan_tunnel`

- **YANG デフォルト**: なし。`mandatory true`。
- **コード由来デフォルト**: なし。省略時は YANG バリデーションで reject。
- **結論**: 省略不可。

#### `vni`

- **YANG デフォルト**: なし。`mandatory true`（`stypes:vnid_type`）。
- **コード由来デフォルト**: `vnetorch.cpp:442` で `uint32_t vni=0;` として初期化されるが、フィールドが省略されても `vni=0` のまま `VNetInfo` に渡る。YANG `mandatory true` がある場合は YANG バリデーションが先に reject する想定。orchagent は `vni=0` を受け付けるが VNI 0 は無効な VXLAN ヘッダとなり、VxlanTunnelMap の作成 (`createVxlanTunnelMap`) が失敗する可能性がある。
- **結論**: 省略不可（YANG mandatory）。VNI 0 はコード上初期値だが実質無効。

#### `peer_list`

- **YANG デフォルト**: なし（optional leaf, type string）。
- **コード由来デフォルト**: `vnetorch.cpp:440` で `set<string> peer_list = {};`（空セット）として初期化。フィールドが存在しない場合、空セットが `VNetInfo.peers` に渡る。
- **結論**: 省略時は空セット `{}` がコードレベルのデフォルト。peer なし動作。

#### `guid`

- **YANG デフォルト**: なし（optional leaf）。
- **コード由来デフォルト**: `vnetorch.h` の `vnet_request_description` に `guid` エントリが**存在しない**（`REQ_T_STRING` として登録されていない）。つまり orchagent は `guid` フィールドを一切読まない。
- **結論**: `guid` は orchagent にとって dead field。CONFIG_DB に保存されるのみ。

#### `scope`

- **YANG デフォルト**: なし（optional leaf、pattern `"default"` のみ）。
- **コード由来デフォルト**: `vnetorch.cpp:444` で `string scope;`（空文字列）として初期化。フィールドが省略された場合は空文字列のまま `VNetInfo.scope` に渡る。`getScope()` は空文字列を返す。`vnetorch.cpp:118` で `if (getScope() != "default")` の分岐が存在するが、空文字列は `"default"` でないため別経路に入る可能性がある。
- **結論**: 省略時は空文字列 `""` がコードデフォルト。YANG pattern `"default"` を通る場合は必ず `"default"` が設定されている。

#### `advertise_prefix`

- **YANG デフォルト**: なし（optional boolean）。
- **コード由来デフォルト**: `vnetorch.cpp:441` で `bool advertise_prefix = false;` として初期化。フィールドが存在しない場合は `false` のまま `VNetInfo.advertise_prefix` に渡る。
- **結論**: 省略時のコードデフォルトは `false`（prefix を BGP に広告しない）。

#### `overlay_dmac`

- **YANG デフォルト**: なし（optional `yang:mac-address`）。
- **コード由来デフォルト**: `vnetorch.cpp:445` で `swss::MacAddress overlay_dmac;` として初期化。`MacAddress()` デフォルトコンストラクタは `memset(m_mac, 0, ETHER_ADDR_LEN)` でゼロ MAC `00:00:00:00:00:00` を設定（`macaddress.cpp:10-13`）。
- **ゼロ MAC チェック**: `vnetorch.cpp:525` で `if (!!overlay_dmac && ...)` — `operator!()` がゼロ MAC を `true` に評価するため (`macaddress.h:46-50`)、`!!overlay_dmac` がゼロ MAC なら `false`。つまり省略時はアップデート経路に入らない。
- **結論**: 省略時は `00:00:00:00:00:00`（ゼロ MAC）がコードデフォルト。VNET ping 用の overlay dmac が未設定 → ping 機能は動作しない。

#### `src_mac`

- **YANG デフォルト**: なし（optional `yang:mac-address`）。
- **コード由来デフォルト**: フィールドが存在する場合のみ `SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS` として SAI に渡す（`vnetorch.cpp:449-454`）。省略時は `attrs` リストに追加されず、SAI の VRF 作成時に src_mac 属性が渡らない。SAI デフォルト（通常はスイッチ MAC）が使われる。
- **結論**: 省略時は SAI/プラットフォームデフォルト（スイッチ MAC）が適用される。

---

### VNET_ROUTE テーブル

#### `nexthop`

- **YANG デフォルト**: なし。`mandatory true`（`stypes:ipv4-address-list`）。
- **コード由来デフォルト**: なし。省略不可。

#### `ifname`

- **YANG デフォルト**: なし。`mandatory true`（string）。
- **コード由来デフォルト**: なし。省略不可。

---

### VNET_ROUTE_TUNNEL テーブル

#### `endpoint`

- **YANG デフォルト**: なし。`mandatory true`（`stypes:ipv4-address-list`）。
- **コード由来デフォルト**: なし。省略不可。

#### `mac_address`

- **YANG デフォルト**: なし（optional `stypes:mac-address-list`）。
- **コード由来デフォルト**: `vnetorch.cpp` の `handleTunnel()` で `vector<string> mac_list;`（空ベクタ）として初期化。省略時は空リスト。`mac_list` が空の場合、各 endpoint の `NextHopKey` に `MacAddress mac;`（ゼロ MAC）が使われる（`vnetorch.cpp:3362-3383`）。
- **結論**: 省略時は各 endpoint に対してゼロ MAC `00:00:00:00:00:00` がデフォルト。

#### `vni`（VNET_ROUTE_TUNNEL）

- **YANG デフォルト**: なし（optional `stypes:vnid-list`）。
- **コード由来デフォルト**: `vector<string> vni_list;`（空ベクタ）として初期化。省略時は空リスト。各 endpoint の `vni = 0` となる（`vnetorch.cpp:3362-3370`）。VNI 0 の場合、tunnel nexthop 作成時にベースの tunnel VNI が使われる（VXLAN orch 側の挙動）。
- **結論**: 省略時は `0`（VNET 本体の `vni` が encapsulation に使われる）。

#### `consistent_hashing_buckets`

- **YANG デフォルト**: なし（optional uint16）。
- **コード由来デフォルト**: `vnetorch.h:327` に `{ "metric", REQ_T_UINT }` のみ登録されており、`consistent_hashing_buckets` は `vnet_route_description` に**存在しない**。orchagent は `consistent_hashing_buckets` を一切読まない。
- **結論**: dead field（orchagent 未使用）。CONFIG_DB に保存されるのみ。

#### `metric`

- **YANG デフォルト**: なし（optional uint8）。
- **YANG コメント**: "This value does not affect route behavior."
- **コード由来デフォルト**: `vnetorch.h:327` で `{ "metric", REQ_T_UINT }` として登録されているが、`handleTunnel()` 内に `metric` の読み取り・使用コードが存在しない（`vnetorch.cpp:3196-3290`）。フィールドは parse されるが使用されない。
- **結論**: 省略時のデフォルトなし（未使用）。YANG コメント通り経路選択に影響しない dead field。

---

## `<!-- defaults -->` ブロック用テキスト案

```markdown
<!-- defaults -->
## コード由来の暗黙デフォルト

### VNET

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `vxlan_tunnel` | なし (mandatory) | 省略不可 | sonic-vnet.yang |
| `vni` | なし (mandatory) | 省略不可。orchagent 初期値は `0` だが実質無効 | vnetorch.cpp:442 |
| `peer_list` | なし | 空セット `{}` — peer なし動作 | vnetorch.cpp:440 |
| `guid` | なし | orchagent 未使用（dead field）| vnetorch.h |
| `scope` | なし | 空文字列 `""` — YANG を通れば常に `"default"` | vnetorch.cpp:444 |
| `advertise_prefix` | なし | `false` — prefix を BGP 広告しない | vnetorch.cpp:441 |
| `overlay_dmac` | なし | `00:00:00:00:00:00`（ゼロ MAC）— ping 機能無効 | macaddress.cpp:10-13, vnetorch.cpp:445 |
| `src_mac` | なし | SAI/プラットフォームデフォルト（スイッチ MAC）| vnetorch.cpp:449-454 |

### VNET_ROUTE

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `nexthop` | なし (mandatory) | 省略不可 | sonic-vnet.yang |
| `ifname` | なし (mandatory) | 省略不可 | sonic-vnet.yang |

### VNET_ROUTE_TUNNEL

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `endpoint` | なし (mandatory) | 省略不可 | sonic-vnet.yang |
| `mac_address` | なし | `00:00:00:00:00:00`（ゼロ MAC）per endpoint | vnetorch.cpp:3362-3383 |
| `vni` | なし | `0` — VNET 本体の VNI で encapsulation | vnetorch.cpp:3362-3370 |
| `consistent_hashing_buckets` | なし | orchagent 未使用（dead field）| vnetorch.h |
| `metric` | なし | orchagent 未使用（dead field）。経路選択に影響しない | vnetorch.cpp:3196-3290 |

### 注記

- **`guid`・`consistent_hashing_buckets`・`metric` の dead field 性**: これら 3 フィールドは orchagent が parse しない（`vnet_request_description` / `vnet_route_description` に登録なし、または登録はあるが `handleTunnel()` 内で使用されない）。CONFIG_DB に保存されるのみ。
- **`overlay_dmac` のゼロ MAC ガード**: orchagent は `!!overlay_dmac`（`operator bool`）でゼロ MAC を検出し、ゼロ MAC の場合は setOverlayDMac() を呼ばない（vnetorch.cpp:525）。
- **`src_mac` の SAI デフォルト委譲**: 省略時に SAI 属性を渡さないため、プラットフォームの SAI デフォルト（通常はスイッチシステム MAC）が VRF の src_mac として使われる。
- **`vni` (VNET_ROUTE_TUNNEL) = 0**: VNI リストが空または 0 の場合、vxlan orch 側でベース tunnel の VNI が encapsulation に使われる（VXLAN orch の createNextHopTunnel() に vni=0 を渡す）。
<!-- /defaults -->
```
