# BGP_AGGREGATE_ADDRESS — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/bgp-aggregate-address.md` Phase C 追加分。
`BGP_AGGREGATE_ADDRESS` の YANG (`sonic-bgp-aggregate-address.yang`) には leafref が宣言されていないため、外部テーブルへの参照はすべて bgpcfgd / frr-mgmt-framework 実装上の暗黙参照となる。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py` | `AggregateAddressMgr` — `BGP_AGGREGATE_ADDRESS` 購読、`DEVICE_METADATA.localhost/bgp_asn` 依存、`BGP_BBR` 連動 |
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | 別経路 `BGP_GLOBALS_AF_AGGREGATE_ADDR` (VRF/AF 分離) を扱うハンドラ。`aggr-policy` 経由で `ROUTE_MAP` 参照 |

## YANG leafref

`sonic-bgp-aggregate-address.yang` には leafref 宣言なし。`aggregate-address-prefix-list` / `contributing-address-prefix-list` は `string` 型で `PREFIX_SET` への形式的な参照宣言はない (実装側で FRR `prefix-list` に直接マッピング)。

## 暗黙参照 (実装レベル)

### 1. DEVICE_METADATA.localhost.bgp_asn (必須)

- **参照先テーブル**: `DEVICE_METADATA|localhost` の `bgp_asn` フィールド
- **参照方向**: 読み取り（コンストラクタで `subscribe` + ハンドラ内で `directory.get_slot`）
- **条件**: 常時 (set/del いずれの handler でも先頭で参照)
- **参照元**: `managers_aggregate_address.py` L36 (`subscribe` 宣言), L93 (`address_set_handler`), L149 (`address_del_handler`)
- **意味**: FRR `router bgp <asn>` コマンドの asn を `DEVICE_METADATA.localhost.bgp_asn` から取得。未設定なら `KeyError` が上位伝播し全 `BGP_AGGREGATE_ADDRESS` エントリの処理が失敗する (起動順制約)。
- **ブロッキング依存**: `Manager.__init__` の `subscribe` リストにより、`DEVICE_METADATA` 受信前は `BGP_AGGREGATE_ADDRESS` の `set_handler` がコールされない。

### 2. BGP_BBR.bbr_status (条件付き)

- **参照先テーブル**: `BGP_BBR` (`BGP_BBR_TABLE_NAME` / `BGP_BBR_STATUS_KEY`)
- **参照方向**: 購読 (`directory.subscribe`) + 都度参照 (`directory.get`)
- **条件**: `bbr-required=true` のエントリのみ実害あり。false なら値に関わらず通常処理。
- **参照元**: `managers_aggregate_address.py` L41 (`subscribe` + `on_bbr_change`), L73-83 (`set_handler` 内 BBR 状態分岐)
- **意味**:
  - `BGP_BBR` が存在しない → `bbr_status = ""` → `bbr-required=true` なら `ADDRESS_INACTIVE_STATE` へ落とす。
  - `BGP_BBR.status = disabled` かつ `bbr-required=true` → INACTIVE。
  - BBR が enabled→disabled に変化 → STATE_DB から `bbr-required=true` の全アドレスを取得し FRR から削除 + STATE_DB を inactive 更新 (`on_bbr_change` L57-61)。
  - BBR が disabled→enabled に変化 → 同集合を FRR に再投入 (`on_bbr_change` L49-56)。
- **注意**: `bbr-required` フィールド自体は YANG にも宣言されており、`BGP_BBR` の存在/状態と組み合わせて挙動が決まる。

### 3. BGP_GLOBALS / BGP_GLOBALS_AF (frr-mgmt-framework 経路のみ)

- **参照先テーブル**: `BGP_GLOBALS` (VRF と `local_asn`)、`BGP_GLOBALS_AF` (address-family コンテキスト)
- **参照方向**: コマンド組立て時の前提条件 (`cmd_prefix` 生成)
- **条件**: `frrcfgd` 経路 (`BGP_GLOBALS_AF_AGGREGATE_ADDR` テーブル) のみ。`bgpcfgd` 経路 (`BGP_AGGREGATE_ADDRESS` テーブル) は VRF を取らず default VRF 固定。
- **参照元**: `frrcfgd.py` L3161-3163, L3179-3181 (`'router bgp {} vrf {}'.format(local_asn, vrf)` / `'address-family {} {}'.format(af, ip_type)`)
- **意味**: frrcfgd は `BGP_GLOBALS` から `local_asn` を、`BGP_GLOBALS_AF` から AF コンテキストを取り、これを `cmd_prefix` として aggregate-address コマンドの前に投入する。`BGP_GLOBALS` 未投入時は VRF/asn が解決できず投入失敗。
- **注意**: 本ページの主対象である `bgpcfgd` 経路 (`BGP_AGGREGATE_ADDRESS`) では `BGP_GLOBALS` を**直接購読しない** (`DEVICE_METADATA` のみ)。`BGP_GLOBALS` への暗黙依存は frrcfgd 経路 (`BGP_GLOBALS_AF_AGGREGATE_ADDR`) で発生する。

### 4. ROUTE_MAP (frr-mgmt-framework 経路のみ)

- **参照先テーブル**: `ROUTE_MAP` (FRR route-map 名)
- **参照方向**: 値参照 (`aggr-policy` フォーマッタ経由)
- **条件**: `BGP_GLOBALS_AF_AGGREGATE_ADDR` の `policy` フィールドが非空のとき
- **参照元**: `frrcfgd.py` L1982-1983 (`af_aggregate_key_map` の `'+policy'` + `{5:aggr-policy}`), L928-930 (`aggr-policy` フォーマッタ: `'route-map %s' % self.to_str()`)
- **意味**: `policy` フィールド値がそのまま FRR `route-map <name>` の名前として `aggregate-address ... route-map <name>` に展開される。指定された route-map が FRR に未投入だと FRR 側で no-op。`ROUTE_MAP` テーブル (CONFIG_DB) → frr-mgmt-framework → FRR route-map の同期は別経路。
- **注意**: 本ページのスコープ (`BGP_AGGREGATE_ADDRESS`) には `policy` フィールドが**存在しない**。`bgpcfgd` 経路では `aggregate-address-prefix-list` / `contributing-address-prefix-list` が代替手段として使われ、これらは `ROUTE_MAP` ではなく FRR `prefix-list` を生成する (`generate_prefix_list_commands` L255-264)。

### 5. FRR prefix-list (aggregate-address-prefix-list / contributing-address-prefix-list)

- **参照先**: FRR `ip prefix-list <name>` (CONFIG_DB の `PREFIX_SET` テーブルとは別の名前空間)
- **参照方向**: 書き込み (FRR config 直接生成)
- **条件**: 各フィールドが非空のとき
- **参照元**: `managers_aggregate_address.py` L114-122 (`AGGREGATE_ADDRESS_PREFIX_LIST_KEY`), L124-132 (`CONTRIBUTING_ADDRESS_PREFIX_LIST_KEY`), L255-264 (`generate_prefix_list_commands`)
- **意味**: 指定された prefix-list 名で FRR に `ip prefix-list <name> permit <prefix>` (contributing 側は `le 32` / `le 128` 付与) を投入する。`PREFIX_SET` テーブル (CONFIG_DB) との連携はコード上は確認できず、bgpcfgd 自身が FRR prefix-list を生成・管理する。
- **注意**: CONFIG_DB `PREFIX_SET` テーブルへの参照ではない (related の表記との整合に注意)。frontmatter の `PREFIX_SET` リンクは「BGP 周辺の関連テーブル」の意味合いに留まる。

## 参照関係サマリ

```
BGP_AGGREGATE_ADDRESS  (bgpcfgd 経路)
  ├─ [暗黙・必須] DEVICE_METADATA|localhost.bgp_asn  (FRR router bgp <asn>)
  ├─ [暗黙・条件付き] BGP_BBR.bbr_status              (bbr-required=true のみ)
  └─ [出力] FRR ip prefix-list <name>                (aggregate/contributing prefix-list フィールド)

BGP_GLOBALS_AF_AGGREGATE_ADDR  (frrcfgd 経路 — 別テーブル、参考)
  ├─ [暗黙・必須] BGP_GLOBALS.local_asn / vrf       (cmd_prefix)
  ├─ [暗黙・必須] BGP_GLOBALS_AF                    (address-family コンテキスト)
  └─ [暗黙・条件付き] ROUTE_MAP                      (policy フィールド非空時)
```

## evidence

- `managers_aggregate_address.py`: L7 (`managers_bbr` import), L36 (`DEVICE_METADATA` subscribe), L41 (`BGP_BBR` subscribe), L46-63 (`on_bbr_change`), L73-83 (BBR 連動分岐), L93 (`bgp_asn` 取得), L114-132 (prefix-list フィールド処理), L255-264 (`generate_prefix_list_commands`)
- `frrcfgd.py`: L98 (`BGP_GLOBALS_AF_AGGREGATE_ADDR` daemon mapping), L928-930 (`aggr-policy` フォーマッタ), L1313-1328 (`hdl_af_aggregate`), L1982-1983 (`af_aggregate_key_map`), L3169-3196 (`BGP_GLOBALS_AF_AGGREGATE_ADDR` 処理ブロック)
