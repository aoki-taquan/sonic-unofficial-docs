# PORTCHANNEL_INTERFACE — Phase A コード由来暗黙デフォルト調査

生成日: 2026-05-15

## 調査ソース

- `sonic-swss/cfgmgr/intfmgr.cpp` (PORTCHANNEL_INTERFACE / INTERFACE / LOOPBACK 共通の `doIntfGeneralTask()` を精読)
- `sonic-swss/cfgmgr/intfmgr.h`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang`

> 補足: `PORTCHANNEL_INTERFACE` は `IntfMgr::doIntfGeneralTask()` で `INTERFACE` / `LOOPBACK_INTERFACE` / `VLAN_INTERFACE` と共通処理される。よって intfmgr.cpp に出現するハードコード定数は PortChannel L3 IF にも適用される。

---

## ハードコード定数 (intfmgr.cpp 冒頭)

| マクロ | 値 | 用途 |
|---|---|---|
| `DEFAULT_MTU_STR` | `9100` | サブインタフェースの parent MTU が未取得時のフォールバック (intfmgr.cpp:29, 402, 420) |
| `MTU_INHERITANCE` | `"0"` | サブインタフェース `mtu=0` の特殊値 (親 IF の MTU を継承) |
| `LOOPBACK_DEFAULT_MTU_STR` | `65536` | Loopback IF 専用 MTU (PortChannel IF には適用されない) |

---

## フィールド別デフォルト・暗黙挙動 (PORTCHANNEL_INTERFACE)

### `admin_status`

- **YANG**: `PORTCHANNEL_INTERFACE` の属性ロウに `admin_status` leaf は**定義なし**。属性ロウは `vrf_name` / `loopback_action` / `nat_zone` / `mpls` / `ipv6_use_link_local_only` / `mac_addr` のみ。
- **intfmgr.cpp:776,797-800**: `string adminStatus = "";` で初期化。`admin_status` フィールドが存在しても、**PORTCHANNEL IF (非 loopback) の場合 `adminStatus` 変数を読み取らない**。
  - intfmgr.cpp:852-883 の `is_lo` ブランチ (loopback IF) でのみ `adminStatus` が処理され、空なら `"up"` フォールバック (L861-864) → `setIntfAdminStatus()` 呼び出し。
  - PORTCHANNEL IF (非 loopback) は L884-... の `else` 節で `nat_zone` / `loopback_action` / `mpls` / `ipv6_link_local_mode` を APP_DB に転送するが、`adminStatus` は無視される。
- **silent dead field**: `PORTCHANNEL_INTERFACE` に `admin_status` を書いても intfmgrd は反応しない (admin up/down は `PORTCHANNEL` テーブル側の `admin_status` で決まり、teammgrd が制御)。
- **discrepancy**: YANG schema では PORTCHANNEL_INTERFACE 属性ロウに admin_status は存在しないので合致。ただし誤って書き込んでも警告なしで silently 無視される点に注意。

### `mtu`

- **YANG**: `PORTCHANNEL_INTERFACE` 属性ロウに `mtu` leaf **定義なし**。MTU は `PORTCHANNEL` テーブル側で管理。
- **intfmgr.cpp:775**: `string mtu = "";` で初期化。`PORTCHANNEL_INTERFACE` の processing 経路では `mtu` フィールドを読み取らない (read ループに `mtu` 分岐なし)。
- **サブインタフェース経路**: `PortChannel0001.10` 形式 (VLAN sub-interface) の場合のみ `getIntfMtu()` (intfmgr.cpp:376-405) が呼ばれ、親 PortChannel から `mtu` を取得。取得失敗時は `DEFAULT_MTU_STR` (= `"9100"`) フォールバック (L400-402)。
- **silent dead field**: `PORTCHANNEL_INTERFACE` 直書きの `mtu` は無視される。MTU 変更は `PORTCHANNEL` テーブルで行う必要あり。

### `loopback_action`

- **YANG**: optional leaf `loopback_action` (type: `loopback_action`, values: `drop` / `forward`)。**default 文なし**。
- **intfmgr.cpp:782,825-828,893-898**: 空なら APP_DB に何も push しない (silent skip)。値が設定されていれば `FieldValueTuple("loopback_action", value)` を APP_INTF_TABLE に転送。
- **ハードコード default なし**: コード経路にフォールバック値の注入がなく、未設定時の SAI 側挙動 (=デフォルトの forward に近い動作) はベンダー SAI 実装依存。
- **適用範囲制約**: intfmgr.cpp:893 の `else` 節 (非 loopback IF) 内で処理されるため、`LOOPBACK_INTERFACE` には適用されない。PORTCHANNEL_INTERFACE / INTERFACE / VLAN_INTERFACE のみが対象。
- **silent skip**: フィールドなし → APP_DB に push されず、orchagent は前回値 (またはデフォルト) を保持。

### `nat_zone`

- **YANG**: optional uint8、range `0..3`、default 値なし。description には "Default zone is 0" と記述あり。
- **intfmgr.cpp:777,813-816,886-891**: 空なら APP_DB に push しない (silent skip)。値があれば push。
- **ドキュメント側 default `0` と コード side**: APP_INTF_TABLE で `nat_zone` フィールドなし → natmgrd は zone 0 として扱う (natmgr.cpp 側のデフォルト)。intfmgr.cpp 自体は 0 を補填しない。

### `mpls`

- **YANG**: optional enum `enable` / `disable`、default 文なし。
- **intfmgr.cpp:780,809-812**: 値があれば `mpls_action` として処理 (L900-953 付近で `setIntfMpls()`)。空なら何もしない (silent skip)。
- **ハードコード default なし**: 未設定時はカーネル netdev の MPLS 設定を変更しない。Linux 側のシステムデフォルト (通常 disable) に委ねる。

### `ipv6_use_link_local_only`

- **YANG**: optional `mode-status`、default `disable`。
- **intfmgr.cpp:781,817-820**: 値があれば `setIntfIpv6LinkLocalMode()` を呼び出す。空なら処理しない (silent skip)。
- **コード side default 補填なし**: 未設定時はカーネルの IPv6 デフォルト動作 (グローバルアドレスあり)。

### `vrf_name`

- **YANG**: optional leafref `VRF.name`、default 文なし。
- **intfmgr.cpp:774,789-792,839-843**: 値があれば VRF 状態 (`isIntfStateOk(vrf_name)`) を待ち、`isIntfChangeVrf()` で VRF 変更を検出して reject (L846-850)。空なら default VRF (Linux global namespace) に置く。
- **silent default**: 未設定時は default VRF (`Vrfdefault` 相当) — ユーザーには不可視。

### `mac_addr`

- **YANG**: optional mac-address、default 文なし。
- **intfmgr.cpp:773,793-796**: 値があれば `setIntfMac()` で netdev MAC 変更。空ならカーネル側のシステム MAC (`DEVICE_METADATA.localhost.mac` 由来) を使用 — intfmgr.cpp 自身は補填しない。

---

## サマリー表 (PORTCHANNEL_INTERFACE 固有)

| フィールド | YANG default | intfmgr.cpp fallback | 経路 | 備考 |
|---|---|---|---|---|
| `admin_status` | leaf 定義なし | N/A (非 loopback ブランチで参照されない) | intfmgr.cpp:797,884- | 書いても silent drop (loopback IF のみ "up" fallback) |
| `mtu` | leaf 定義なし | N/A (read ループに `mtu` 分岐なし) | — | PORTCHANNEL_INTERFACE 直書きの `mtu` は dead field |
| `loopback_action` | なし | silent skip (空なら push しない) | intfmgr.cpp:825-828,893-898 | SAI 側デフォルト (実装依存、概ね forward) に委ねる |
| `nat_zone` | なし (説明上 "0") | silent skip (空なら push しない) | intfmgr.cpp:813-816,886-891 | natmgrd 側で zone 0 扱い |
| `mpls` | なし | silent skip | intfmgr.cpp:809-812 | Linux netdev MPLS 設定を変更しない |
| `ipv6_use_link_local_only` | `disable` | silent skip | intfmgr.cpp:817-820 | YANG default `disable` と一致 (実装は補填せず Linux デフォルト) |
| `vrf_name` | なし | silent default (`Vrfdefault`) | intfmgr.cpp:789-792 | 未設定 = default VRF |
| `mac_addr` | なし | silent skip (システム MAC 使用) | intfmgr.cpp:793-796 | `DEVICE_METADATA.localhost.mac` 継承 |

### ハードコード定数 (intfmgr.cpp 全体で参照されるが PORTCHANNEL_INTERFACE 経路では未使用)

| 定数 | 値 | PORTCHANNEL_INTERFACE 適用? |
|---|---|---|
| `DEFAULT_MTU_STR` | `9100` | × (サブインタフェース fallback のみ) |
| `LOOPBACK_DEFAULT_MTU_STR` | `65536` | × (Loopback IF 専用) |
| `MTU_INHERITANCE` | `"0"` | × (sub-interface 専用) |

---

## 主要 discrepancy / silent 罠

1. **`admin_status` silent drop**: `PORTCHANNEL_INTERFACE` 属性ロウに `admin_status` を書いても intfmgrd は読まない。LAG の admin up/down は `PORTCHANNEL` テーブル側で管理する必要があり、混同するとユーザーは「admin_status を書いたのに反映されない」と感じる。
2. **`mtu` silent drop**: 同様に `PORTCHANNEL_INTERFACE` 直書きの `mtu` は intfmgrd の読み取り対象外。MTU 変更は `PORTCHANNEL` テーブルで行う。
3. **`loopback_action` 未設定時のデフォルト不明**: intfmgr.cpp はフィールドなし時に APP_DB に push しないため、SAI 実装側の初期値が表に出る。ベンダー SAI 実装依存で `drop` か `forward` か明文化されない。
4. **`ipv6_use_link_local_only` の YANG default vs 実装**: YANG default は `disable` だが intfmgr.cpp はフィールドなし時に何もしない。Linux netdev のシステムデフォルトと整合するため実害なし。
5. **Loopback ブランチとの共通コード混入**: `is_lo` 判定で分岐するが、変数 (`adminStatus` 等) は両ブランチで共通宣言されるため、PORTCHANNEL_INTERFACE 経路でも未使用変数が初期化される。コードリーディング時の誤読源。
