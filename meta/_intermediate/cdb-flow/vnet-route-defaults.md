# VNET_ROUTE / VNET_ROUTE_TUNNEL — Phase A: コード由来のデフォルト解析

生成日: 2026-05-15
対象ファイル:
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vnet.yang` (9ea932ec)
- `sonic-swss/orchagent/vnetorch.cpp` (43055961)
- `sonic-swss/orchagent/vnetorch.h` (43055961)
- `sonic-swss-common/common/schema.h` (158de8d3)

---

## 調査の前提

CONFIG_DB の `VNET_ROUTE` / `VNET_ROUTE_TUNNEL` テーブルは `VNetCfgRouteOrch`
(`vnetorch.cpp:3577`) が購読する。このクラスは fields を一切解釈せず、
`CFG_VNET_RT_TABLE_NAME` / `CFG_VNET_RT_TUNNEL_TABLE_NAME` のメッセージを
そのまま APPL_DB の `VNET_ROUTE_TABLE` / `VNET_ROUTE_TUNNEL_TABLE` に passthrough する
（`doVnetRouteTask` / `doVnetTunnelRouteTask`、vnetorch.cpp:3613-3661）。

実際のフィールド解釈・デフォルト適用は APPL_DB を消費する `VNetRouteOrch` の
`handleRoutes()` / `handleTunnel()` が担う。
フィールド定義の正規ソースは YANG (`sonic-vnet.yang`) であり、YANG に無いフィールドは
CONFIG_DB には存在しない（APPL_DB 拡張フィールドは別途）。

---

## VNET_ROUTE テーブル

key 形式: `VNET_ROUTE|<vnet_name>|<prefix>`

### `nexthop`

- **YANG 型**: `stypes:ipv4-address-list` — `mandatory true`
- **YANG デフォルト**: なし（必須フィールド）
- **コード由来デフォルト**: なし。省略不可。
- **`handleRoutes()` (vnetorch.cpp:1815-1827)**: `IpAddresses ip_addresses;` で空初期化されるが、
  YANG mandatory があるため実際に空のまま処理されることはない。
- **結論**: 省略不可。

### `ifname`

- **YANG 型**: `string` — `mandatory true`
- **YANG デフォルト**: なし（必須フィールド）
- **コード由来デフォルト**: `string ifname = "";`（vnetorch.cpp:1816）。
  フィールドが省略された場合は空文字列のまま `nextHop.ifname` に渡る。
  YANG mandatory があるため実際に省略されることはないが、
  コード上の初期値は `""` （空文字列 = インタフェース未指定）。
- **結論**: 省略不可（YANG mandatory）。コード初期値 `""` だが実質無効。

---

## VNET_ROUTE_TUNNEL テーブル

key 形式: `VNET_ROUTE_TUNNEL|<vnet_name>|<prefix>`

`handleTunnel()` が処理するフィールド（vnetorch.cpp:3195-3272）。

### `endpoint`

- **YANG 型**: `stypes:ipv4-address-list` — `mandatory true`
- **YANG デフォルト**: なし（必須フィールド）
- **コード由来デフォルト**: なし。省略不可。
- **コード**: `vector<IpAddress> ip_list;`（空ベクタで初期化）。mandatory なので空で到達しない。
- **結論**: 省略不可。

### `mac_address`

- **YANG 型**: `stypes:mac-address-list` — optional
- **YANG デフォルト**: なし
- **コード由来デフォルト**:
  - `vector<string> mac_list;`（空ベクタ）で初期化（vnetorch.cpp:3200）。
  - 省略時: `mac_list` が空 → ループ内 `mac_list[idx_ip]` に到達しない →
    各 endpoint の `MacAddress mac;` はデフォルトコンストラクタ（ゼロ MAC）のまま。
  - ゼロ MAC `00:00:00:00:00:00` が `NextHopKey` の `mac_address` に設定される
    （vnetorch.cpp:3361-3375）。
- **結論**: 省略時は各 endpoint に `00:00:00:00:00:00`（ゼロ MAC）が適用される。
  VXLAN encapsulation の inner dst-mac がゼロのまま送出される。

### `vni`

- **YANG 型**: `stypes:vnid-list` — optional
- **YANG デフォルト**: なし
- **コード由来デフォルト**:
  - `vector<string> vni_list;`（空ベクタ）で初期化（vnetorch.cpp:3201）。
  - 省略時: `vni_list` が空 → 各 endpoint の `uint32_t vni = 0` のまま（vnetorch.cpp:3362）。
  - `vni=0` で `vrf_obj->getTunnelNextHop(nexthop)` → `VxlanTunnelOrch::createNextHopTunnel()` に
    `vni=0` が渡る → VXLAN orch はベース tunnel の VNI を使う。
- **結論**: 省略時は `0`（VNET 本体の VNI で encapsulation）。

### `consistent_hashing_buckets`

- **YANG 型**: `uint16` — optional
- **YANG デフォルト**: なし
- **コード由来デフォルト**:
  - `vnetorch.h` の `vnet_route_description` を確認すると `consistent_hashing_buckets` が
    登録されていない（dead field）。
  - `handleTunnel()` 内（vnetorch.cpp:3214-3272）に対応する `else if` ブランチなし。
    フィールドが存在しても `SWSS_LOG_INFO("Unknown attribute: %s")` で無視される。
- **結論**: orchagent が全く読まない dead field。CONFIG_DB に保存されるのみ。

### `metric`

- **YANG 型**: `uint8` — optional
- **YANG コメント**: "This value does not affect route behavior."
- **YANG デフォルト**: なし
- **コード由来デフォルト**:
  - `vnetorch.h:327` に `{ "metric", REQ_T_UINT }` が登録されているため parse は試みる。
  - しかし `handleTunnel()` のフィールド処理ループ（vnetorch.cpp:3214-3272）に
    `metric` の読み取り・使用コードが**存在しない**。
  - parse されても変数に格納されず、処理に使われない。
- **結論**: 省略時デフォルトなし（未使用）。YANG コメント通り経路選択に影響しない dead field。

---

## 初期値サマリ表

### VNET_ROUTE

| フィールド | YANG default | コード初期値 / デフォルト | 出典 |
|-----------|-------------|--------------------------|------|
| `nexthop` | なし (mandatory) | 省略不可 | sonic-vnet.yang:133 |
| `ifname` | なし (mandatory) | 省略不可。コード初期値 `""` | vnetorch.cpp:1816 |

### VNET_ROUTE_TUNNEL

| フィールド | YANG default | コード初期値 / デフォルト | 出典 |
|-----------|-------------|--------------------------|------|
| `endpoint` | なし (mandatory) | 省略不可 | sonic-vnet.yang:169 |
| `mac_address` | なし | `00:00:00:00:00:00`（ゼロ MAC）per endpoint | vnetorch.cpp:3200, 3361-3375 |
| `vni` | なし | `0` — VNET 本体 VNI で encapsulation | vnetorch.cpp:3201, 3362 |
| `consistent_hashing_buckets` | なし | orchagent 未使用（dead field） | vnetorch.h (登録なし) |
| `metric` | なし | orchagent 未使用（dead field） | vnetorch.cpp:3214-3272 |

---

## 注記

### passthrough アーキテクチャの含意

CONFIG_DB のフィールドは YANG でのみ検証される。`VNetCfgRouteOrch` は fields の
バリデーションを行わず全フィールドを APPL_DB に転送するため、YANG に定義されていない
フィールドを CONFIG_DB に書いても APPL_DB に転送されてしまう（YANG バリデーションが
有効な環境では事前に reject される）。

### `vni=0` の転送挙動

`NextHopKey` に `vni=0` が設定された場合、`vnetorch.cpp` の
`VNetVrfObject::getTunnelNextHop()` → `VxlanTunnelOrch::createNextHopTunnel()` に
`vni=0` が渡る。VXLAN orch はこれをベース tunnel の VNI として解釈する
（VNI 0 のトンネル lookup は tunnel 自体の VNI にフォールバックする）。

### `mac_address` = ゼロ MAC の転送挙動

ゼロ MAC が `NextHopKey.mac_address` に設定されると、SAI 側の VXLAN
encapsulation で inner dst-mac として `00:00:00:00:00:00` が使われる。
適切な MAC が不要な場合（remote VTEP が MAC 学習する構成など）は問題ないが、
明示的な MAC が必要な構成では `mac_address` を指定すること。
