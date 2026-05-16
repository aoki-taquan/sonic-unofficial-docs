# BGP_GLOBALS — Phase H プラットフォーム差 (intermediate)

## スコープ

- 対象テーブル: `BGP_GLOBALS` (および参考: `BGP_GLOBALS_AF`, `BGP_GLOBALS_AF_NETWORK`,
  `BGP_GLOBALS_AF_AGGREGATE_ADDR`, `BGP_GLOBALS_LISTEN_PREFIX`)。
- 一次経路: CONFIG_DB → `frr-mgmt-framework` (`frrcfgd.py`) → vtysh → FRR `bgpd`。
- 補助経路: `bgpcfgd` (`managers_bgp.py` / `managers_device_global.py`) は
  BGP_GLOBALS 自体は購読しない。`BGP_DEVICE_GLOBAL` 経由で TSA / IDF /
  W-ECMP の挙動を変更し、結果として `router bgp <asn>` ブロック配下の
  neighbor / route-map に影響する。

## 結論サマリ

| 観点 | 結果 |
|------|------|
| BGP_GLOBALS フィールド本体の値マッピング (router_id / local_asn / keepalive / holdtime / max_med 等) | プラットフォーム差なし。`frrcfgd.py` / `bgpd.conf.db.j2` の全文 grep で `platform` / `asic_type` / `switch_type` / `chassis` / `multi_npu` / `namespace` / `sub_role` の参照 0 ヒット。 |
| `local_asn` / `router_id` 等の FRR コマンド生成 | ベンダー / HwSku / multi-asic を問わず同一文字列を `vtysh` に push。 |
| `chassis_tsa` 影響 | **間接**: `BGP_GLOBALS` のフィールド自体は変えない。`BGP_DEVICE_GLOBAL.tsa_enabled` と `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL\|STATE.tsa_enabled` の OR が真のとき、`BGPPeerGroupMgr.update_pg()` が `router bgp <local_asn>` ブロックに TSA 用 route-map を追記する (`managers_bgp.py:69-71`, `managers_device_global.py:171-181, 238-251`)。これは `BGP_GLOBALS` の YANG / CONFIG_DB スキーマ上のフィールドではなく、同一 `router bgp` コンテキスト下に並ぶ neighbor の `route-map ... out` 差し替えに過ぎない。 |
| `switch_role` (`DEVICE_METADATA.localhost.type`) 影響 | **間接**: `SpineRouter` / `LowerSpineRouter` / `UpperSpineRouter` のみ IDF isolation の route-map push が走る (`managers_device_global.py:260-262`)。`UpstreamLC` または `UpperSpineRouter` で `AsPathMgr` が追加起動 (`main.py:122-129`)。いずれも BGP_GLOBALS フィールド値の書き換えではない。 |
| `switch_type == 'chassis-packet'` 影響 | **間接**: TSA route-map 整形時に `_INTERNAL_` / `VOQ_` を含む name を `internal_route_map=1` で render し chassis 内 iBGP を保持 (`managers_device_global.py:213-225`)。BGP_GLOBALS のフィールド変換には不介入。 |
| `device_info.is_chassis()` 影響 | bgpcfgd 起動時に `ChassisAppDbMgr` を追加 (`main.py:112-113`)。これは `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL` を購読して `chassis_tsa` を取得するためで、`BGP_GLOBALS` 本体は触れない。 |
| multi-asic (`is_multi_npu()` / `asicN` namespace) | `frrcfgd` / `bgpd.conf.db.j2` に namespace / multi-asic 専用分岐は無い。各 namespace の CONFIG_DB を独立した `frrcfgd` プロセスが処理する設計のため、ASIC ごとに `router bgp <asn>` が個別生成されるが、テーブル受理ロジックは全 namespace で同一。 |
| HwSku / ASIC ベンダー (broadcom / mellanox / marvell / cisco-8000 / barefoot / nephos / centec / vs) | grep 0 ヒット。BGP_GLOBALS は SAI 経路を持たないため ASIC 種別非依存。 |

## 一次証跡 (grep)

### `frrcfgd.py` (3985 行)

```
$ grep -cE 'platform|chassis|asic_type|switch_type|multi_npu|namespace|sub_role|TSA' \
    src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py
0
```

`BGP_GLOBALS` のフィールド処理を担う `global_key_map` (L1784-1821)、
`bgp_global_handler()` (L3918-3937)、`__update_bgp()` (L2685-2727) を含む
全行に platform / chassis / asic 系の分岐記述は無い。`vrf == 'default'`
か否かの分岐のみが構文上の場合分けである。

### `bgpd.conf.db.j2` (204 行)

```
$ grep -cE 'platform|chassis|asic_type|switch_type' \
    src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.j2
0
```

`BGP_GLOBALS` 反映テンプレートは vrf / フィールド有無のみで分岐する。

### `bgpcfgd/managers_bgp.py` (597 行)

```
$ grep -cE 'BGP_GLOBALS|chassis_tsa|switch_type|sub_role' \
    src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py
0    # BGP_GLOBALS 文字列の直接購読なし
```

`BGPPeerMgrBase` は `BGP_NEIGHBOR` / `BGP_INTERNAL_NEIGHBOR` /
`BGP_MONITORS` / `BGP_PEER_RANGE` / `BGP_VOQ_CHASSIS_NEIGHBOR` /
`BGP_SENTINELS` を購読するが、`BGP_GLOBALS` は購読しない。
`router bgp <asn>` を発行するのは neighbor 反映時の peer-group 構築
(`managers_bgp.py:69-71`) であり、`BGP_GLOBALS.local_asn` の値は
`DEVICE_METADATA.bgp_asn` または NEIGHBOR_META から取得する別経路を
通る。

### `bgpcfgd/managers_device_global.py`

`chassis_tsa` / `switch_role` / `switch_type` を持つが、いずれも
`BGP_DEVICE_GLOBAL` テーブル経由で **route-map** と **frr 設定 push** に
反映するもので、`BGP_GLOBALS` フィールドの値変換には介入しない。

| 関数 | 行 | 役割 | BGP_GLOBALS への作用 |
|------|----|------|----------------------|
| `get_chassis_tsa_status()` | 238-251 | `device_info.is_chassis()` 真なら `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL\|STATE.tsa_enabled` を取得 | なし (戻り値は `check_state_and_get_tsa_routemaps()` 経由で neighbor route-map に伝播) |
| `check_state_and_get_tsa_routemaps()` | 170-181 | tsa_status または chassis_tsa が `true` のとき TSA route-map 文字列を返す | なし (peer-group push 時に `router bgp <asn>` ブロック末尾に追記、`BGP_GLOBALS` フィールドは変更しない) |
| `downstream_isolate_unisolate()` | 257-... | `switch_role` が SpineRouter / LowerSpineRouter / UpperSpineRouter のときのみ IDF route-map を push | なし |
| `__generate_routemaps_from_template()` | 213-225 | `_INTERNAL_` / `VOQ_` を含む route-map 名を chassis-packet 用に internal フラグ `1` で render | なし |

### `bgpcfgd/main.py`

| 行 | 条件 | manager | BGP_GLOBALS への作用 |
|----|------|---------|----------------------|
| 112-113 | `device_info.is_chassis()` | `ChassisAppDbMgr` を追加 | なし (CHASSIS_APP_DB の `BGP_DEVICE_GLOBAL` を Directory にミラーするのみ) |
| 122-129 | `type == 'SpineRouter' and subtype == 'UpstreamLC'` または `type == 'UpperSpineRouter'` | `AsPathMgr` を追加 | なし (`DEVICE_METADATA` を購読し as-path access-list を FRR に push) |

## 観点別判定

### ASIC ベンダー / HwSku

直接分岐なし。BGP_GLOBALS は SAI を駆動しないため ASIC ベンダー固有の
capability 問合せ・属性 ID 切替・mandatory フィールド差はそもそも
発生しない。FRR vtysh への push は文字列のみで完結する。

### multi-asic (`is_multi_npu`)

`frrcfgd` は単一プロセスとして起動するが、namespace ごとに CONFIG_DB
が独立しているため、各 namespace で個別の `frrcfgd` が同一コードで
動作する。テーブル受理ロジックに `namespace` の参照は無い。
`BGP_GLOBALS|<vrf>` の key 空間は namespace ごとに独立する。

### VOQ / packet-based chassis

`BGP_GLOBALS` 自体には差なし。間接影響:

- 起動時 `ChassisAppDbMgr` 追加で `chassis_tsa` を取得可能化。
- `chassis_tsa=='true'` のとき `router bgp <asn>` ブロック配下の
  neighbor `route-map ... out` を TSA 用に差し替え。`BGP_GLOBALS` の
  `local_asn` / `router_id` / `keepalive` 等は変更されない。
- `switch_type='chassis-packet'` のときシャーシ内 iBGP セッション
  (route-map 名に `_INTERNAL_` / `VOQ_` を含む) を `internal_route_map=1`
  で扱い、TSA 適用時にも shut down しないよう render する。

### switch_role

`SpineRouter` / `LowerSpineRouter` / `UpperSpineRouter` のとき IDF
isolation route-map が push される。`UpstreamLC` / `UpperSpineRouter`
で `AsPathMgr` が追加起動する。`BGP_GLOBALS` のフィールド本体は
いずれの role でも同一に処理される。

### vrf == default vs 非 default

唯一の構文上の分岐: `frrcfgd.py:2162-2166, 2442-2447` で `default` VRF
のみ `DEVICE_METADATA.bgp_asn` を `local_asn` の代替 source として
受け入れる。これはプラットフォーム差ではなく VRF scope 差。

## 結論

**BGP_GLOBALS テーブルの値変換・FRR コマンド生成自体にはプラットフォーム
差・ASIC 差・HwSku 差・multi-asic 差は無い** (grep evidence 上記)。
`chassis_tsa` / `switch_role` / `switch_type` / `device_info.is_chassis()`
は `BGP_DEVICE_GLOBAL` 経路で **同一 `router bgp <asn>` ブロック配下の
neighbor route-map と IDF state push** に影響するが、`BGP_GLOBALS` の
フィールド値そのものを書き換えない。詳細な分岐挙動は
`docs/reference/config-db/bgp-device-global.md` の Phase H ブロック
および `meta/_intermediate/cdb-flow/bgp-device-global-platform.md` を
参照。

## 参照

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
  (全 3985 行 grep)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.j2`
  (全 204 行 grep)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:69-71, 504-506`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py:12-251`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:112-129`
