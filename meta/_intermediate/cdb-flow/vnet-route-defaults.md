# VNET_ROUTE / VNET_ROUTE_TUNNEL — Phase A: コード由来のデフォルト解析

生成日: 2026-05-14
対象ファイル: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vnet.yang`、`sonic-swss/orchagent/vnetorch.cpp`、`sonic-swss/orchagent/vnetorch.h`

---

## フィールドごとのデフォルト・挙動まとめ

### VNET_ROUTE テーブル

key 構造: `VNET_ROUTE|<vnet_name>|<prefix>`

orchagent ハンドラ: `VNetRouteOrch::handleRoutes()` (vnetorch.cpp:1811)

#### `nexthop`

- **YANG デフォルト**: なし。`mandatory true`（`stypes:ipv4-address-list`）。
- **コード由来デフォルト**: `handleRoutes()` で `IpAddresses ip_addresses;` として初期化（空リスト）。ただし YANG mandatory のため省略時は YANG バリデーションで reject。
- **結論**: 省略不可。

#### `ifname`

- **YANG デフォルト**: なし。`mandatory true`（string）。
- **コード由来デフォルト**: `handleRoutes()` で `string ifname = "";`（空文字列）として初期化。ただし YANG mandatory のため省略時は YANG バリデーションで reject。
- **結論**: 省略不可。

---

### VNET_ROUTE_TUNNEL テーブル

key 構造: `VNET_ROUTE_TUNNEL|<vnet_name>|<prefix>`

orchagent ハンドラ: `VNetRouteOrch::handleTunnel()` (vnetorch.cpp:3196~)

#### `endpoint`

- **YANG デフォルト**: なし。`mandatory true`（`stypes:ipv4-address-list`）。
- **コード由来デフォルト**: `handleTunnel()` 冒頭で `vector<IpAddress> ip_list;` として初期化（空リスト）。ただし YANG mandatory のため省略時は YANG バリデーションで reject。
- **結論**: 省略不可。

#### `mac_address`

- **YANG デフォルト**: なし（optional `stypes:mac-address-list`）。
- **コード由来デフォルト**: `vector<string> mac_list;`（空ベクタ）として初期化。省略時は空リスト。`if (!mac_list.empty() && mac_list[idx_ip] != "")` のガードにより、空の場合は `NextHopKey` に `MacAddress mac;`（ゼロ MAC `00:00:00:00:00:00`）が使われる（vnetorch.cpp:3372-3375）。
- **結論**: 省略時は各 endpoint に対してゼロ MAC `00:00:00:00:00:00` がコードデフォルト。

#### `vni`

- **YANG デフォルト**: なし（optional `stypes:vnid-list`）。
- **コード由来デフォルト**: `vector<string> vni_list;`（空ベクタ）として初期化。省略時は空リスト。`vni = 0` となる（vnetorch.cpp:3362-3370）。VNI 0 の場合、VXLAN orch の `createNextHopTunnel()` に `vni=0` を渡し、VNET 本体の VNI が encapsulation に使われる。
- **結論**: 省略時は `0`（VNET 本体の `vni` が encapsulation に利用される）。

#### `endpoint_monitor`

- **YANG デフォルト**: なし（YANG 定義外 — orchagent のみで扱う APPL_DB 拡張フィールド）。
- **コード由来デフォルト**: `vector<IpAddress> monitor_list;`（空ベクタ）として初期化。省略時は `monitors` マップが空になり、BFD/カスタムモニタリングは無効。
- **結論**: 省略時はモニタリングなし。

#### `profile`

- **YANG デフォルト**: なし（YANG 定義外）。
- **コード由来デフォルト**: `string profile = "";`（空文字列）として初期化。省略時は空文字列。`doRouteTask()` で `if (!profile.empty())` で profile 適用をスキップ。
- **結論**: 省略時はプロファイル未適用。

#### `monitoring`

- **YANG デフォルト**: なし（YANG 定義外）。
- **コード由来デフォルト**: `string monitoring;`（空文字列）として初期化。省略時は `""` で、モニタリング動作が無効（`if (monitoring == "" && ...)` の分岐で処理）。
- **結論**: 省略時はモニタリングなし（空文字列）。

#### `adv_prefix`

- **YANG デフォルト**: なし（YANG 定義外）。
- **コード由来デフォルト**: `has_adv_pfx = false` の場合、`adv_prefix = ip_pfx`（ルート prefix と同じ）として扱われる（vnetorch.cpp:3421-3423）。
- **結論**: 省略時は該当ルートの prefix が adv_prefix として使われる（自己宣言）。

#### `check_directly_connected`

- **YANG デフォルト**: なし（YANG 定義外）。
- **コード由来デフォルト**: `bool check_directly_connected = false;`（vnetorch.cpp:3213）。省略時は false。false の場合、endpoint が directly connected かどうかのチェックをスキップし、`nhg_primary = NextHopGroupKey("", true)` として全て overlay 扱いにする。
- **結論**: 省略時は `false`（直接接続チェックを行わない）。

#### `rx_monitor_timer`

- **YANG デフォルト**: なし（YANG 定義外）。
- **コード由来デフォルト**: `int32_t rx_monitor_timer = -1;`（vnetorch.cpp:3208）。省略時は `-1`。BFD セッション作成時に `if (rx_monitor_timer >= 0)` で `-1` の場合はスキップ — BFD デフォルト値が使われる。
- **結論**: 省略時は `-1`（BFD デフォルト rx_interval）。

#### `tx_monitor_timer`

- **YANG デフォルト**: なし（YANG 定義外）。
- **コード由来デフォルト**: `int32_t tx_monitor_timer = -1;`（vnetorch.cpp:3209）。省略時は `-1`。BFD セッション作成時に `if (tx_monitor_timer >= 0)` で `-1` の場合はスキップ — BFD デフォルト値が使われる。
- **結論**: 省略時は `-1`（BFD デフォルト tx_interval）。

#### `pinned_state`

- **YANG デフォルト**: なし（YANG 定義外）。
- **コード由来デフォルト**: `vector<string> pinned_state_list;`（空ベクタ）として初期化。省略時は空リスト → 各 monitor が `PINNED_STATE_NONE` として扱われる（vnetorch.cpp:3402-3404）。
- **結論**: 省略時は `PINNED_STATE_NONE`（pinned なし）。

#### `primary`

- **YANG デフォルト**: なし（YANG 定義外）。
- **コード由来デフォルト**: `vector<IpAddress> primary_list;`（空ベクタ）として初期化。省略時は `has_priority_ep = false`、通常の ECMP ネクストホップグループとして処理される。
- **結論**: 省略時は primary/backup 優先ルーティングなし。

#### `consistent_hashing_buckets`

- **YANG デフォルト**: なし（optional uint16）。
- **コード由来デフォルト**: YANG 定義には存在するが `vnet_route_description`（vnetorch.h:310-329）に登録なし。orchagent は `consistent_hashing_buckets` フィールドを一切読まない。
- **結論**: dead field（orchagent 未使用）。CONFIG_DB に保存されるのみ。

#### `metric`

- **YANG デフォルト**: なし（optional uint8）。
- **YANG コメント**: "This value does not affect route behavior."
- **コード由来デフォルト**: `vnet_route_description`（vnetorch.h:327）では `{ "metric", REQ_T_UINT }` として登録されているが、`handleTunnel()` 内に metric の読み取り・使用コードが存在しない（vnetorch.cpp:3196-3290）。フィールドは request_description に登録されているが使用されない。
- **結論**: 実質 dead field。経路選択に影響しない（YANG コメント通り）。

---

## `<!-- defaults -->` ブロック用テキスト案

```markdown
<!-- defaults -->
## コード由来の暗黙デフォルト

### VNET_ROUTE

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `nexthop` | なし (mandatory) | 省略不可 | sonic-vnet.yang |
| `ifname` | なし (mandatory) | 省略不可 | sonic-vnet.yang |

### VNET_ROUTE_TUNNEL

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `endpoint` | なし (mandatory) | 省略不可 | sonic-vnet.yang |
| `mac_address` | なし | `00:00:00:00:00:00`（ゼロ MAC）per endpoint | vnetorch.cpp:3372-3375 |
| `vni` | なし | `0` — VNET 本体の VNI で encapsulation | vnetorch.cpp:3362-3370 |
| `endpoint_monitor` | YANG 外 | 空リスト — モニタリングなし | vnetorch.cpp:3203,3230-3232 |
| `profile` | YANG 外 | `""` — プロファイル未適用 | vnetorch.cpp:3204,3234-3236 |
| `monitoring` | YANG 外 | `""` — モニタリング種別なし | vnetorch.cpp:3207,3242-3244 |
| `adv_prefix` | YANG 外 | ルート prefix と同一（自己宣言）| vnetorch.cpp:3421-3423 |
| `check_directly_connected` | YANG 外 | `false` — 直接接続チェックなし | vnetorch.cpp:3213 |
| `rx_monitor_timer` | YANG 外 | `-1` — BFD デフォルト rx_interval | vnetorch.cpp:3208,2078-2081 |
| `tx_monitor_timer` | YANG 外 | `-1` — BFD デフォルト tx_interval | vnetorch.cpp:3209,2084-2087 |
| `pinned_state` | YANG 外 | `PINNED_STATE_NONE` — pinned なし | vnetorch.cpp:3402-3404 |
| `primary` | YANG 外 | 空リスト — primary/backup なし（通常 ECMP）| vnetorch.cpp:3205,3311-3315 |
| `consistent_hashing_buckets` | なし | orchagent 未使用（dead field）| vnetorch.h:310-329 |
| `metric` | なし | 実質未使用（dead field）— 経路選択に影響しない | vnetorch.h:327, vnetorch.cpp:3196-3290 |

### 注記

- **`consistent_hashing_buckets` の dead field 性**: YANG に定義があるが `vnet_route_description` に登録なし。orchagent は完全に無視する。
- **`metric` の semi-dead field 性**: `vnet_route_description` には登録されているが `handleTunnel()` 内で値を読み出して使用するコードが存在しない。YANG コメント通り「経路動作に影響しない」。
- **`vni` = 0 の意味**: `createNextHopTunnel()` に `vni=0` を渡した場合、vxlanorch 側はベース VXLAN tunnel の VNI を使用する。
- **`rx_monitor_timer` / `tx_monitor_timer` = -1**: `createBfdSession()` 内で `if (rx_monitor_timer >= 0)` ガードがあり、-1 の場合は BFD セッション作成時に rx/tx_interval 属性を渡さない（BFD デフォルト値が適用される）。
<!-- /defaults -->
```
