# BGP_NEIGHBOR_AF — Phase A: コード由来の暗黙デフォルト調査

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/bgp-neighbor-af.md`  
エントリポイント grep: `grep -rln "BGP_NEIGHBOR_AF" .cache/sonic-sources/`

## ソースファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | frrcfgd メインロジック |
| `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.nbr_af.j2` | bgpcfgd テンプレートパス (Jinja2) |
| `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.addr_family.j2` | AF ブロック包含 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-neighbor.yang` | YANG スキーマ |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-common.yang` | grouping sonic-bgp-cmn-af |

## YANG 定義 — 全フィールドと型

YANG `grouping sonic-bgp-cmn-af` (L337-534) に **YANG `default` 節は一切なし**。全フィールドが optional leaf で、DB に値がなければフィールド自体が存在しない。

| フィールド | 型 | YANG default |
|-----------|-----|--------------|
| `afi_safi` | string (key) | なし |
| `admin_status` | stypes:admin_status | なし |
| `send_default_route` | boolean | なし |
| `default_rmap` | leafref (ROUTE_MAP) | なし |
| `max_prefix_limit` | uint32 | なし |
| `max_prefix_warning_only` | boolean | なし |
| `max_prefix_warning_threshold` | uint8 1..100 | なし |
| `max_prefix_restart_interval` | uint16 1..65535 | なし |
| `route_map_in` | leaf-list leafref, max-elements 1 | なし |
| `route_map_out` | leaf-list leafref, max-elements 1 | なし |
| `soft_reconfiguration_in` | boolean | なし |
| `unsuppress_map_name` | leafref | なし |
| `rrclient` | boolean | なし |
| `weight` | uint16 0..65535 | なし |
| `as_override` | boolean | なし |
| `send_community` | bgp_community_type | なし |
| `tx_add_paths` | bgp_tx_add_paths_type | なし |
| `unchanged_as_path` | boolean | なし |
| `unchanged_med` | boolean | なし |
| `unchanged_nexthop` | boolean | なし |
| `filter_list_in` | leafref | なし |
| `filter_list_out` | leafref | なし |
| `nhself` | boolean | なし |
| `nexthop_self_force` | boolean | なし |
| `prefix_list_in` | leafref | なし |
| `prefix_list_out` | leafref | なし |
| `remove_private_as_enabled` | boolean | なし |
| `replace_private_as` | boolean | なし |
| `remove_private_as_all` | boolean | なし |
| `allow_as_in` | boolean | なし |
| `allow_as_count` | uint8 | なし |
| `allow_as_origin` | boolean | なし |
| `cap_orf` | sonic_bgp_orf | なし |
| `route_server_client` | boolean | なし |

## コード調査結果

### 1. frrcfgd.py: `nbr_af_key_map` (L1895-1925)

`BGP_NEIGHBOR_AF` は `nbr_af_key_map` を経由して処理される（`tbl_to_key_map` L2111）。
プレフィックス記法の意味:
- 先頭なし = mandatory: DB にフィールドがなければコマンド自体スキップ
- `+` = optional: なくてもコマンドは発行するが、その位置は空文字になる
- `++` = optional かつ「変更なし」でも許容

#### `allow_as_in` + `allow_as_count` / `allow_as_origin`

```
(['allow_as_in', '+allow_as_count&allow_as_origin'], ...)
```

- `allow_as_in` が mandatory (boolean true/false で activate/deactivate)
- `allow_as_count` または `allow_as_origin` は optional (+)
- **実行時 fallback**: `allow_as_in=true` かつ `allow_as_count` も `allow_as_origin` も未設定 → FRR へ `neighbor X allowas-in`（カウント指定なし）。FRR 側デフォルトは 3 回。

同じロジックを Jinja2 テンプレートが確認 (L85-93 of nbr_af.j2):
```
{% if 'allow_as_in' in n_af_val and n_af_val['allow_as_in'] == 'true' %}
  {% if 'allow_as_origin' in n_af_val and n_af_val['allow_as_origin'] == 'true' %}
    neighbor X allowas-in origin
  {% elif 'allow_as_count' in n_af_val %}
    neighbor X allowas-in {{n_af_val['allow_as_count']}}
  {% else %}
    neighbor X allowas-in   ← カウント省略
  {% endif %}
{% endif %}
```

**discrepancy**: `allow_as_count` の YANG 型は `uint8` で default なし。カウント省略時 FRR は 3 をデフォルトとして使用するが、DB 上には値が存在しない。

#### `admin_status` — activate / deactivate

```python
('admin_status|ipv4', '{no:no-prefix}neighbor {} activate', hdl_admin_status),
('admin_status|ipv6', '{no:no-prefix}neighbor {} activate', hdl_admin_status),
('admin_status|l2vpn', '{no:no-prefix}neighbor {} activate', hdl_admin_status),
```

`hdl_admin_status` (L1456): `up` → `true` に正規化、`down` → `false`。DB になければコマンド不発行（YANG default なし）。
FRR 側では `ipv4_unicast` のみデフォルト activate（`no bgp default ipv4-unicast` を BGP_GLOBALS 設定時に実行 L2700）。

**書き込み時の注意**: `BGP_GLOBALS` に `local_asn` が書き込まれるとき、`no bgp default ipv4-unicast` が発行される。つまり:
- `ipv4_unicast` の BGP_NEIGHBOR_AF レコードがなくても、FRR 上では ipv4-unicast が **非** activate に変更される。
- BGP_NEIGHBOR_AF に `admin_status=up` を明示しないと、ipv4-unicast ネイバーは activate されない。

#### `send_community` — none の特殊処理

`hdl_send_com` (L945-956):
1. まず `no neighbor X send-community all` を発行（全クリア）
2. `send_community != 'none'` の場合のみ値を追加

**runtime fallback**: `send_community` が DB にない場合はコマンド不発行。FRR デフォルトは `no send-community`（送信なし）。
**書き込み時 vs 実行時の乖離**: `'none'` を書いても `'未設定'` でも FRR 上の効果は同じだが、DB 上は異なる状態。

Jinja2 パス (L35-49): send_community が DB にあれば `no neighbor X send-community ...` 系コマンドを発行するが、`none` の場合は `no neighbor X send-community all` だけ発行してそれ以上追加しない。frrcfgd と一致。

#### `send_default_route` + `default_rmap`

```python
(['send_default_route', '+default_rmap'], '{no:no-prefix}neighbor {} default-originate {:default-rmap}', ...)
('default_rmap', '{no:no-prefix}neighbor {} default-originate route-map {}'),
```

- `send_default_route` が mandatory。`true` でコマンド発行
- `default_rmap` は optional (+)。`send_default_route=true` かつ `default_rmap` 未設定 → `neighbor X default-originate`（route-map なし）
- `default_rmap` が独立エントリとしても別途発行される（L1900）

Jinja2 でも同様: `send_default_route=true` かつ `default_rmap` なし → `default-originate` のみ (L54-60)

**fallback確認済み**: `default_rmap` 欠如は許容設計。

#### `max_prefix_limit` 依存フィールド群

```python
(['max_prefix_limit', '++max_prefix_warning_threshold', '+max_prefix_restart_interval&max_prefix_warning_only'],
 '{no:no-prefix}neighbor {} maximum-prefix {} {} {:restart}')
```

- `max_prefix_limit` が mandatory (先頭なし)。**欠如するとコマンド全体スキップ**
- `max_prefix_warning_threshold` は `++`（optional、変更なしでも可）
- `max_prefix_restart_interval` または `max_prefix_warning_only` は `+`（optional）

**複合必須制約**: `max_prefix_warning_threshold` / `max_prefix_restart_interval` / `max_prefix_warning_only` のいずれかだけを書いても、`max_prefix_limit` がなければ FRR コマンドは発行されない。

Jinja2 でも同様 (L68-79): `max_prefix_limit` の有無でブロック全体を guard。

#### `nhself` + `nexthop_self_force` の依存

Jinja2 (L18-24):
```
{% if 'nhself' in n_af_val and n_af_val['nhself'] == 'true' %}
  {% if 'nexthop_self_force' in n_af_val and n_af_val['nexthop_self_force'] == 'true' %}
    neighbor X next-hop-self force
  {% else %}
    neighbor X next-hop-self
  {% endif %}
{% endif %}
```

`nhself=true` が前提。`nexthop_self_force=true` は `nhself=true` なしでは発行されない（Jinja2 パス）。
frrcfgd パスでは両者が独立エントリなので `nexthop_self_force` だけ書いても発行される。**CLI 経路と frrcfgd 経路で挙動が異なる潜在的 discrepancy**。

#### `remove_private_as_enabled` 複合条件

frrcfgd `hdl_rm_priv_as` (L958-970):
1. まず 4 パターン全 `no` コマンドで既存設定をフルクリア
2. `OP_DELETE` 以外の場合のみ新規コマンドを追加

Jinja2 (L25-34):
- `remove_private_as_enabled=true` が前提
- `remove_private_as_all` / `replace_private_as` は optional modifier

**fallback**: `remove_private_as_enabled=false` または未設定 → コマンド不発行 (Jinja2)。frrcfgd は DELETE 操作で全クリアする。

#### `unchanged_as_path` / `unchanged_med` / `unchanged_nexthop`

```python
(['++unchanged_as_path', '++unchanged_med', '++unchanged_nexthop'],
 '{no:no-prefix}neighbor {} attribute-unchanged {:uchg-as-path} {:uchg-med} {:uchg-nh}', hdl_attr_unchanged)
```

全て `++`（全 optional）。`hdl_attr_unchanged` (L1342): まず `no` コマンドで全クリア、次に値を設定。
3 フィールドのうち 1 つだけ変更しても `no attribute-unchanged` が先行発行される。

#### `cap_orf` — 削除時の全クリア

`hdl_capa_orf_pfxlist` (L972-979):
1. まず `no neighbor X capability orf prefix-list both` でクリア
2. DELETE 以外: 値を追加

**fallback**: `cap_orf` 未設定 → コマンド不発行。

#### `weight` — FRR デフォルト

`weight` 未設定 → コマンド不発行。FRR デフォルトは 0（weight なし）。
`weight=0` を明示書き込みした場合と未設定は FRR 上同じ挙動だが、DB では区別される。

#### `tx_add_paths` — Jinja2 と frrcfgd の差異

frrcfgd (L1911): `'{no:no-prefix}neighbor {} {:tx-add-paths}'`
Jinja2 (L11-16): `tx_all_paths` / `tx_best_path_per_as` の 2 値のみ対応。

Jinja2 には `add_path_tx_all` / `add_path_tx_bestpath` という**別フィールド名**への処理も含む (L95-100):
```
{% if 'add_path_tx_all' in n_af_val and n_af_val['add_path_tx_all'] == 'true' %}
  neighbor {{nbr_name}} addpath-tx-all-paths
```
これは YANG 定義に存在しない旧来フィールド。**テンプレートパスにのみ残る dead code の可能性**。

## 書き込み経路別デフォルト比較

| フィールド | frrcfgd (REST/gNMI/CLI) | bgpcfgd テンプレート (Jinja2) |
|-----------|------------------------|------------------------------|
| `admin_status` | 欠如→コマンド不発行。ipv4_unicast は BGP_GLOBALS の `no bgp default ipv4-unicast` により非 activate | 欠如→ブロックスキップ |
| `send_community` | 欠如→不発行 (FRR: 送信なし) | 欠如→不発行 |
| `allow_as_count` | `allow_as_in=true` + 欠如 → `allowas-in` (FRR が 3 を適用) | 同上 |
| `max_prefix_*` | `max_prefix_limit` 欠如→全スキップ | 同上 |
| `nexthop_self_force` | 単独で発行可能 | `nhself=true` が必要 |
| `add_path_tx_all` / `add_path_tx_bestpath` | YANG 非定義フィールド→無視 | Jinja2 に処理あり (旧来フィールド) |
| `send_default_route=false` | `no neighbor X default-originate` | ブロックスキップ (不発行) |

## 発見した discrepancy / 暗黙デフォルト

| 番号 | フィールド | 種類 | 内容 |
|------|-----------|------|------|
| D1 | `allow_as_count` | 実行時 fallback | 未設定時 FRR が 3 を適用するが DB 上は値なし |
| D2 | `admin_status` (ipv4_unicast) | 書き込み経路依存の乖離 | frrcfgd が BGP_GLOBALS 書き込み時に `no bgp default ipv4-unicast` を発行するため、ipv4_unicast の BGP_NEIGHBOR_AF を書かないと ipv4 経路交換が開始しない |
| D3 | `nexthop_self_force` | 書き込み経路依存の乖離 | frrcfgd パスは `nhself` なしで単独発行可能だが、Jinja2 パスは `nhself=true` が必要 |
| D4 | `send_community='none'` vs 未設定 | 書き込み時 default vs runtime fallback | DB 上の状態は異なるが FRR 上の効果は同じ（送信なし）|
| D5 | `add_path_tx_all` / `add_path_tx_bestpath` | YANG vs 実装 discrepancy | YANG 未定義フィールドが Jinja2 テンプレートに残存 |
| D6 | `weight=0` vs 未設定 | 書き込み時 default vs runtime fallback | FRR 上同じ (weight なし) だが DB 状態は異なる |
