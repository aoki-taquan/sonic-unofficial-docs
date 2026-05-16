# STATIC_ROUTE — Phase A: コード由来の暗黙デフォルト調査

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`
- `sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/main.py`
- `sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/vars.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/static_rt_timer.py`
- `sonic-utilities/config/main.py` (config route add/del)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-static-route.yang`

---

## 1. フィールドごとのコード由来デフォルト

### `nexthop`

- **YANG**: `default` なし（任意フィールド）
- **実装**: `set_handler` で `data.get('nexthop')` が存在しない場合、`nh_list = None`
- `IpNextHopSet.__init__` は `ip_list=None` をそのまま許容（empty set で返る）
- `IpNextHop.__init__` では `dst_ip is None` or `dst_ip == ''` の場合は `zero_ip(af_id)` = `'0.0.0.0'`(IPv4) / `'::'`(IPv6) を内部で使用
- **暗黙デフォルト**: フィールド不在→ nexthop なし扱い。`0.0.0.0` は interface route の規約であり DB に書かれる値ではなく FRR コマンド生成時のプレースホルダー
- **CLI**: `config route add` では nexthop なしの場合 `route['nexthop'] = ''`（空文字列）を書く

### `ifname`

- **YANG**: `default` なし（任意フィールド）
- **実装**: `data.get('ifname')` 不在 → `intf_list = None` → `IpNextHop.interface = ''`
- **CLI**: `config route add` では `route['ifname'] = ''` を書く（空文字列）
- **暗黙デフォルト**: 空文字列。コマンド生成時 `__format__` で空なら出力なし

### `advertise`

- **YANG**: `default "false"`（明示 YANG デフォルト）
- **実装 (`set_handler` L46)**:
  ```python
  route_tag = self.ROUTE_ADVERTISE_DISABLE_TAG if 'advertise' in data and data['advertise'] == "false" \
              else self.ROUTE_ADVERTISE_ENABLE_TAG
  ```
  **YANG-実装乖離**: フィールドが DB に存在しない場合（`'advertise' not in data`）は `else` 分岐に入り `ROUTE_ADVERTISE_ENABLE_TAG = '1'`（広告有効）が使われる。YANG デフォルト `"false"` と逆の挙動。
- **暗黙デフォルト**: フィールド不在 → BGP 広告有効（YANG と逆）

### `bfd`

- **YANG template list**: `default "false"`（明示）
- **YANG VRF-aware list**: `default` なし（フィールド自体が存在しない）
- **実装 (`set_handler` L45)**:
  ```python
  bfd_enable = arg_list(data['bfd']) if 'bfd' in data else None
  ```
  `bfd_enable = None` → `if bfd_enable and ...` が False → BFD 無効として処理
- **staticroutebfd (`static_route_set_handler` L388)**:
  ```python
  bfd_field = arg_list(data['bfd']) if 'bfd' in data else ["false"]
  ```
  フィールド不在 → `["false"]` のリストをデフォルトとして使用（こちらは正しい）
- **暗黙デフォルト**: bgpcfgd では None（BFD 無効）、staticroutebfd では `["false"]`。一貫してBFD無効

### `distance`

- **YANG**: VRF-aware list で `default "0"`（明示）、template list には distance フィールドなし
- **実装 (`IpNextHop.__init__` L265)**:
  ```python
  self.distance = 0 if dist is None else int(dist)
  ```
  `dist_list = None` の場合 `IpNextHop.distance = 0`
- **`__format__` (L303)**:
  ```python
  if not (self.distance is None or self.distance == 0):
      ret_val += ' %d' % self.distance
  ```
  `distance == 0` の場合は FRR コマンドに distance を含めない → FRR の static デフォルト AD=1 が適用される
- **暗黙デフォルト**: `0` → FRR コマンドに distance 出力なし → FRR デフォルト AD=1 が使用される
- **ドキュメントの記載との整合**: 既存ドキュメント「`distance: 0` → FRR デフォルト distance (1) を使用する」は正しい

### `nexthop-vrf`

- **YANG**: `default` なし（任意フィールド）、パターンは空文字列も許容
- **実装 (`set_handler` L44)**:
  ```python
  nh_vrf_list = arg_list(data['nexthop-vrf']) if 'nexthop-vrf' in data else None
  ```
- **`IpNextHop.__init__` (L269)**:
  ```python
  self.nh_vrf = '' if vrf is None else vrf
  ```
- **staticroutebfd (`static_route_set_handler` L413-421)**:
  ```python
  if nh_vrf_list is None and nh_list is not None:
      nh_vrf_list = [vrf] * len(nh_list)  # 現在の route key の vrf で補完
  elif nh_vrf_list is not None:
      for index in range(len(nh_vrf_list)):
          if len(nh_vrf_list[index]) == 0:
              nh_vrf_list[index] = vrf  # 空要素も key の vrf で補完
  ```
- **暗黙デフォルト**: フィールド不在 → bgpcfgd では nexthop-vrf なし（ローカル VRF 内）、staticroutebfd では key の VRF 名で自動補完

### `blackhole`

- **YANG**: VRF-aware list で `default "false"`（明示）
- **実装 (`set_handler` L40)**:
  ```python
  bkh_list = arg_list(data['blackhole']) if 'blackhole' in data else None
  ```
- **`IpNextHop.__init__` (L264)**:
  ```python
  self.blackhole = 'false' if blackhole is None or blackhole == '' else blackhole
  ```
  フィールド不在 → `blackhole = 'false'`（通常経路）
- **staticroutebfd (`static_route_set_handler` L426-428)**:
  ```python
  if bkh_list is not None and 'true' in bkh_list:
      log_info("Blackholing static route encountered, skipping it")
      return True  # staticroutebfd は blackhole route を完全にスキップ
  ```
  **Dead consumer**: `staticroutebfd` は `blackhole=true` の経路を処理せずスキップする。BFD と blackhole の組み合わせは未対応。
- **CLI**: `config route add` では `route['blackhole'] = 'false'` を明示的に書く（interface が `null` の場合 `'true'`）
- **暗黙デフォルト**: フィールド不在 → `'false'`（通常経路）

---

## 2. ハードコード値

| 定数名 | 値 | 定義場所 | 意味 |
|--------|-----|---------|------|
| `ROUTE_ADVERTISE_ENABLE_TAG` | `'1'` | `managers_static_rt.py` L32 | BGP 広告有効タグ |
| `ROUTE_ADVERTISE_DISABLE_TAG` | `'2'` | `managers_static_rt.py` L33 | BGP 広告無効タグ |
| `BFD_DEFAULT_CFG["multihop"]` | `"false"` | `staticroutebfd/main.py` L101 | BFD マルチホップ無効 |
| `BFD_DEFAULT_CFG["rx_interval"]` | `"50"` | `staticroutebfd/main.py` L101 | BFD rx interval 50ms |
| `BFD_DEFAULT_CFG["tx_interval"]` | `"50"` | `staticroutebfd/main.py` L101 | BFD tx interval 50ms |
| `bfd_multihop` | `"false"` | `staticroutebfd/vars.py` L2 | モジュールレベル変数 |
| `bfd_rx_interval` | `"50"` | `staticroutebfd/vars.py` L3 | |
| `bfd_tx_interval` | `"50"` | `staticroutebfd/vars.py` L4 | |
| `bfd_multiplier` | `"3"` | `staticroutebfd/vars.py` L5 | BFD 検出乗数 |
| `StaticRouteTimer.DEFAULT_TIMER` | `180` | `static_rt_timer.py` L13 | 静的経路有効期限 180秒 |
| `StaticRouteTimer.DEFAULT_SLEEP` | `60` | `static_rt_timer.py` L14 | タイマーポーリング間隔 |
| `StaticRouteTimer.MAX_TIMER` | `172800` | `static_rt_timer.py` L16 | 最大有効期限 2日 |
| `StaticRouteBfd.SELECT_TIMEOUT` | `1000` | `staticroutebfd/main.py` L100 | select タイムアウト 1秒 |
| route-map 名 | `'STATIC_ROUTE_FILTER'` | `managers_static_rt.py` L224 | ハードコードされた route-map 名 |
| route-map permit番号 | `10` | `managers_static_rt.py` L224 | `route-map STATIC_ROUTE_FILTER permit 10` |

---

## 3. YANG-実装 discrepancy（乖離）

### D-1: `advertise` フィールド不在時の挙動反転

- **YANG デフォルト**: `"false"` → BGP 広告無効
- **実装**: フィールド不在 (`'advertise' not in data`) → `ROUTE_ADVERTISE_ENABLE_TAG = '1'` → BGP 広告**有効**
- コード `managers_static_rt.py` L46:
  ```python
  route_tag = self.ROUTE_ADVERTISE_DISABLE_TAG if 'advertise' in data and data['advertise'] == "false" \
              else self.ROUTE_ADVERTISE_ENABLE_TAG
  ```
  フィールド存在かつ `"false"` の場合のみ無効タグを使う。不在の場合は有効タグ。
- **影響**: CLI の `config route add` は `advertise` を書かない（フィールド不在）ため、CLI 経由で追加した静的経路は常に BGP 広告有効として扱われる可能性がある。

### D-2: template list に `distance` フィールドなし

- **YANG STATIC_ROUTE_TEMPLATE_LIST**: `distance` leaf が定義されていない
- **YANG STATIC_ROUTE_LIST**: `distance` leaf あり、`default "0"`
- 実装は両形式を同一コードで処理するが、template 形式の key では `distance` が来ないことが前提

### D-3: `bfd` の YANG デフォルトと実装の非対称

- **YANG STATIC_ROUTE_TEMPLATE_LIST**: `bfd` に `default "false"`
- **YANG STATIC_ROUTE_LIST**: `bfd` leaf なし（定義なし）
- VRF-aware 形式 (`STATIC_ROUTE|<vrf>|<prefix>`) は YANG 上 BFD フィールドを持たないが、実装は両形式で BFD を処理する

---

## 4. Silent drop / 書込み順依存 / 経路依存乖離

### Silent drop: `IpNextHopSet` サイズ不一致

- `managers_static_rt.py` L316-321: nexthop / ifname / distance / nexthop-vrf の各リストのサイズが揃っていない場合、`log_err` を出力して `ValueError` を raise する
- `set_handler` の `except Exception` で捕捉 → `log_crit` → `return False` でスキップ（経路未設定）

### Silent drop: `IpNextHop` でゼロ IP + interface なし

- `IpNextHop.__init__` L273-275:
  ```python
  if self.blackhole != 'true' and self.is_zero_ip() and not self.is_portchannel() and len(self.interface.strip()) == 0:
      log_err('Mandatory attribute not found for nexthop')
      raise ValueError
  ```
  blackhole でなく、IP が 0.0.0.0 で、PortChannel でなく、interface も空の場合は ValueError。`IpNextHopSet` は `ValueError` を個々の nexthop に対して continue で無視する (L328)。

### 書込み順依存: BGP ASN 未設定時の redistribution 保留

- `set_handler` L66-70: 最初の静的経路設定時に `bgp_asn` が DEVICE_METADATA にない場合 `vrf_pending_redistribution.add(vrf)` に保留
- `on_bgp_asn_change` でコールバックされたときに再適用

### 経路依存乖離: BFD ↔ StaticRouteMgr の二重処理防止

- `set_handler` L49-55: `bfd=true` の場合は bgpcfgd の StaticRouteMgr は処理をスキップし `return True`
- staticroutebfd が APPL_DB 書き込みを担う

### Dead consumer: staticroutebfd の blackhole スキップ

- `static_route_set_handler` L426-428: `blackhole=true` の経路は `staticroutebfd` が完全スキップする
- BFD+blackhole の組み合わせは動作しない（blackhole 経路は BFD 監視対象外）

---

## 5. プラットフォーム依存

- `bfd_multihop`, `bfd_rx_interval`, `bfd_tx_interval`, `bfd_multiplier` は `vars.py` でハードコードされているが、`all([...])` チェックにより外部から override 可能な構造になっている (staticroutebfd/main.py L230-234, L487-491)
- BFD セッション作成は INTERFACE/PORTCHANNEL_INTERFACE テーブルからの IP アドレス取得に依存。インターフェース IP が取れない場合は `LOCAL_BFD_PENDING_TABLE` に pending として保留
- PortChannel を nexthop IP として指定する特殊ケース対応: `IpNextHop.is_portchannel()` が `ip.startswith('PortChannel')` を判定

---

## 6. 静的経路タイマー (static_rt_timer.py) の暗黙挙動

- APPL_DB の `STATIC_ROUTE:*` エントリに `expiry` フィールドが `"false"` のものは削除しない
- `expiry` が `"false"` 以外 (または不在) のエントリは `refresh` フィールドが `"true"` かどうかで生存判定
- `refresh` が `"true"` → `"false"` に更新して次サイクルへ
- `refresh` が `"true"` でない → DELETE（有効期限切れとして削除）
- デフォルト有効期限 180秒（`DEFAULT_TIMER`）。APPL_DB の `STATIC_ROUTE_EXPIRY_TIME` で上書き可能

---

## まとめ: defaults ブロックに追記すべき主要知見

1. `advertise` 不在 → 実装上は BGP 広告有効（YANG デフォルト `"false"` と逆）
2. `distance == 0` → FRR コマンドに distance なし → FRR デフォルト AD=1
3. `blackhole` 不在 → `'false'`（通常経路）
4. `bfd` 不在 → BFD 無効
5. `nexthop-vrf` 不在 → staticroutebfd では route key の VRF 名で自動補完
6. `ifname/nexthop` 不在 → 空文字列（FRR コマンドに出力なし）
7. BFD セッションデフォルト: multihop=false, rx/tx_interval=50ms, multiplier=3
8. route-map 名 `STATIC_ROUTE_FILTER` permit 10 はハードコード
9. staticroutebfd は `blackhole=true` 経路をスキップ（dead consumer パス）
10. `advertise` YANG-実装乖離は CLI 経由の経路追加に影響する可能性あり
