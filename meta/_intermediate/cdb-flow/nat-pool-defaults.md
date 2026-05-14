# nat-pool-defaults — Phase A 調査メモ

対象ページ: `docs/reference/config-db/nat.md`  
対象テーブル: `NAT_POOL`、`NAT_BINDINGS`（関連）  
調査日: 2026-05-14

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-nat.yang`
- `sonic-swss/cfgmgr/natmgr.cpp`（`doNatPoolTask` L6482–6866、`doNatBindingTask` L6868–7100）
- `sonic-utilities/config/nat.py`（`add_pool` L673–772）

## 検出された implicit defaults / 特殊挙動

### NAT_POOL.nat_ip

- YANG: `mandatory true`、デフォルト値なし
- natmgr: `ipFound == false` → `SWSS_LOG_ERROR("Invalid nat_ip values, skipping %s") + erase`（L6539–6544）
- **silent drop**: `nat_ip` がフィールドごと欠落した場合にエントリが消費されるだけで再試行されない

### NAT_POOL.nat_port（省略時）

- YANG: optional、デフォルト値なし（`default` 節なし）
- CLI (`config nat add pool`): `global_port_range is None` → `"NULL"` を書き込む（`nat.py:721`）
- natmgr: `nat_port == "" or nat_port == "NULL"` → `m_natPoolInfo[key].port_range = EMPTY_STRING`（L6806–6813）
- iptables ルール生成時に `port_range.empty()` → port 制限なし（full-cone MASQUERADE）
- **経路依存乖離**: CLI 経由は `"NULL"` が DB に入るが natmgr は `""` と等価に扱う。直接 redis-cli で `nat_port` フィールドを書かなければ `portFound=false` となり同様に EMPTY_STRING 扱い

### NAT_POOL.nat_port — 単一ポート

- YANG pattern: `start-end` 形式のみ許可（例: `100-200`）
- natmgr: `nat_port_range.size() == 1` → `portValue_low` のみチェック（L6730–6748）
- 単一ポート（例: `100`）は YANG は拒否しないが natmgr は low のみ検証して受理する（実質 single-port pool）

### NAT_POOL.nat_ip — 単一 IP

- 単一 IP 指定時: natmgr が `ipv4_addr_high = ntohl(ipv4_addr_low)` と設定（L6652–6653）
- 実質 1-address pool として処理される

### NAT_POOL.nat_ip — 禁止アドレス（silent drop）

- Zero (0.0.0.0)、Broadcast、Loopback (127.x.x.x)、Multicast (224.x.x.x)、Reserved → `SWSS_LOG_ERROR + erase`（L6608–6661）
- YANG はこれらを `ip-address-range` typedef で拒否しない（バリデーションは natmgr のみ）

### NAT_POOL.nat_ip — 逆順範囲（low >= high）

- `ipv4_addr_low >= ipv4_addr_high` → `SWSS_LOG_ERROR + erase`（L6635–6640）
- YANG は範囲順序を検証しない（natmgr のみ検証）

### NAT_POOL — IP が STATIC_NAT エントリと重複

- pool の IP アドレスが既存 STATIC_NAT の global_ip と重複 → `SWSS_LOG_ERROR("Pool Ip address is overlaps with static NAT entry, skipping %s") + erase`（L6771–6776）
- YANG には重複チェックなし

### NAT_POOL — key サイズ ≠ 1

- `keys.size() != POOL_TABLE_KEY_SIZE (=1)` → `SWSS_LOG_ERROR + erase`（L6504–6509）
- YANG key は `name` の1フィールドのみ

### NAT_POOL — 既知フィールド以外のフィールド

- `nat_ip` / `nat_port` 以外のフィールドが存在 → `nonValueFound = true` → `SWSS_LOG_ERROR("Invalid value, skipping %s") + erase`（L6554–6560）

### NAT_BINDINGS.nat_type — YANG vs 実装 discrepancy

- YANG: `nat-type` enum は `snat` / `dnat` 両方定義、`default snat`
- natmgr `doNatBindingTask` L6985–6990: `nat_type != SNAT_NAT_TYPE ("snat")` → `SWSS_LOG_ERROR("Invalid nat_type %s, skipping %s") + erase`
- **YANG-実装 discrepancy**: YANG は `dnat` を許可するが natmgr は Dynamic NAT binding に対して `dnat` を完全拒否
- `nat_type` フィールドが欠落（省略）: `natTypeFound=false` → `m_natBindingInfo[key].nat_type = SNAT_NAT_TYPE`（L7056–7058）
- つまり省略も `"snat"` 指定も同じ挙動

### NAT_BINDINGS.twice_nat_id — NULL / 欠落

- `twice_nat_id == "NULL"` → `twiceNatFound = false; twice_nat_id = EMPTY_STRING`（L6993–6996）
- フィールド欠落 → `twice_nat_id = EMPTY_STRING`（L6880初期化）
- どちらも twice-NAT 無効として `m_natBindingInfo[key].twice_nat_id = EMPTY_STRING`

### NAT_BINDINGS.pool_interface / acl_interface — 内部初期値

- natmgr がキャッシュに追加する際: `m_natBindingInfo[key].pool_interface = NONE_STRING ("None")`（L7052）
- `m_natBindingInfo[key].acl_interface = NONE_STRING`（L7053）
- これらは CONFIG_DB フィールドではなく natmgr 内部キャッシュ構造体のみの値

### NAT_POOL.nat_port — L4 ポート範囲制限

- `portValue_low < L4_PORT_MIN (1)` または `portValue_low > L4_PORT_MAX (65535)` → drop（L6694–6699、L6743–6748）
- YANG pattern では 0–65535 が許容される文字列だが、natmgr は 1 以上を要求（port 0 は silent drop）

## 要約テーブル

| フィールド / 条件 | 検出種別 | 挙動 | ソース |
|---|---|---|---|
| `nat_ip` 欠落 | dead field 的 silent drop | ERROR + erase | `natmgr.cpp:6539` |
| `nat_port` 欠落 / `"NULL"` | 暗黙デフォルト | `EMPTY_STRING`（port 制限なし） | `natmgr.cpp:6812` / `nat.py:721` |
| `nat_port` 単一ポート | 経路依存乖離 | low のみ検証し受理 | `natmgr.cpp:6730` |
| `nat_ip` 単一 IP | ハードコード | low==high の 1-address pool | `natmgr.cpp:6652` |
| `nat_ip` 禁止アドレス | silent drop | ERROR + erase | `natmgr.cpp:6608` |
| `nat_ip` low >= high | silent drop | ERROR + erase | `natmgr.cpp:6635` |
| `nat_ip` が STATIC_NAT と重複 | silent drop | ERROR + erase | `natmgr.cpp:6771` |
| 不明フィールド存在 | silent drop | ERROR + erase | `natmgr.cpp:6557` |
| `NAT_BINDINGS.nat_type = "dnat"` | YANG-実装 discrepancy | natmgr が拒否 | `natmgr.cpp:6986` |
| `NAT_BINDINGS.nat_type` 欠落 | 暗黙デフォルト | `"snat"` にフォールバック | `natmgr.cpp:7056` |
| `NAT_BINDINGS.twice_nat_id` 欠落 / `"NULL"` | 暗黙デフォルト | EMPTY_STRING（twice-NAT 無効） | `natmgr.cpp:6993` |
| `nat_port` で port 0 指定 | silent drop | ERROR + erase | `natmgr.cpp:6694` |
