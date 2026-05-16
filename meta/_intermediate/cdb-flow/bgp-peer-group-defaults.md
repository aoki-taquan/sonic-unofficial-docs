# BGP_PEER_GROUP — Phase A: コード由来の暗黙デフォルト

調査日: 2026-05-14  
ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`, `templates/bgpd/bgpd.conf.db.nbr_or_peer.j2`, `yang-models/sonic-bgp-common.yang`

---

## 1. YANG デフォルト一覧

`sonic-bgp-common.yang` の `sonic-bgp-cmn` grouping に **`default` 文は一切存在しない**。すべての leaf は省略可能 (mandatory なし)。YANG レベルでは全フィールドがオプション扱いであり、デフォルト値は YANG 外 (FRR / frrcfgd) で決まる。

---

## 2. 実装レベルの暗黙デフォルト・fallback

### 2.1 `asn` + `peer_type` — remote-as の決定ロジック

**ソース**: `bgpd.conf.db.nbr_or_peer.j2` L14-23, `frrcfgd.py` cmn_key_map L1866

```jinja2
{% set remote_as = '' %}
{% if 'asn' in nbr_or_peer %}
{% set remote_as = nbr_or_peer['asn'] %}
{% endif %}
{% if 'peer_type' in nbr_or_peer %}
{% set remote_as = nbr_or_peer['peer_type'] %}
{% endif %}
```

- `peer_type` が存在すれば `asn` を上書き (後優先)。
- 両方未設定なら `remote-as` コマンド自体が生成されない → FRR ピアグループは `remote-as` なしで作成される (有効なピアを受け入れない state)。
- frrcfgd cmn_key_map では `asn&peer_type` を複合キーとして扱う: **どちらか一方でも存在すれば FRR コマンドを生成**する。

### 2.2 `keepalive` / `holdtime` — comb_attr_list 制約

**ソース**: `frrcfgd.py` L3942-3943

```python
def bgp_neighbor_handler(self, table, key, data):
    self.bgp_table_handler_common(table, key, data, [{'keepalive', 'holdtime'}])
```

`comb_attr_list = [{'keepalive', 'holdtime'}]` による制約:
- `keepalive` と `holdtime` の **両方が揃わない場合、FRR タイマーコマンド (`neighbor <pg> timers {} {}`) は生成されない**。
- 片方だけ書いても無視される。
- FRR のデフォルトタイマーが引き継がれる: keepalive=60s, holdtime=180s (FRR bgpd 組み込み値)。
- Jinja2 テンプレートでも同様: `{% if 'keepalive' in nbr_or_peer and 'holdtime' in nbr_or_peer %}` (L83-84) で両方必須。

### 2.3 `local_asn` 未設定 VRF でのスキップ

**ソース**: `frrcfgd.py` L2658-2662

```python
local_asn = self.__get_vrf_asn(vrf)
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured')
    continue
```

- VRF の `local_asn` (BGP_GLOBALS) が未設定なら `BGP_PEER_GROUP` の更新全体が **silently drop**される。
- エラーではなく LOG_DEBUG のみ → オペレータが気づかない可能性あり。

### 2.4 `admin_status` — 省略時の FRR 挙動

**ソース**: `frrcfgd.py` cmn_key_map L1869, `bgpd.conf.db.nbr_or_peer.j2` L33-38

```jinja2
{% if 'admin_status' in nbr_or_peer and nbr_or_peer['admin_status'] in ['false', 'down'] %}
 neighbor {{name_or_ip}} shutdown
{% endif %}
```

- `admin_status` 未設定時: `shutdown` コマンドは生成されない → FRR デフォルトは **no shutdown (up)**。
- `admin_status = 'up'` と明示しても `shutdown` コマンドは生成されない (同じ結果)。
- `admin_status = 'down'` または `'false'` のみ shutdown コマンドが出る。
- frrcfgd での `hdl_admin_status_shutdown_msg` も同様: `status == 'false'` 時のみ shutdown。

### 2.5 `ebgp_multihop` / `ebgp_multihop_ttl` — オプション組み合わせ

**ソース**: `bgpd.conf.db.nbr_or_peer.j2` L58-67

```jinja2
{% set mhop = '' %}
{% if 'ebgp_multihop' in nbr_or_peer and nbr_or_peer['ebgp_multihop'] == 'true' %}
{% set mhop = 255 %}     {# ← 暗黙デフォルト TTL = 255 #}
{% endif %}
{% if 'ebgp_multihop_ttl' in nbr_or_peer %}
{% set mhop = nbr_or_peer['ebgp_multihop_ttl'] %}   {# TTL 明示値で上書き #}
{% endif %}
```

- `ebgp_multihop = 'true'` かつ `ebgp_multihop_ttl` 未設定 → TTL **255** (最大ホップ) が暗黙使用される。
- `ebgp_multihop_ttl` のみ設定して `ebgp_multihop` を省略しても TTL は適用される (j2 側)。
- frrcfgd cmn_key_map では `['ebgp_multihop', '+ebgp_multihop_ttl']` (+は任意) のため frrcfgd 経由でも同様の組み合わせが可能。

### 2.6 `bfd` / `bfd_check_ctrl_plane_failure` — 自動昇格

**ソース**: `frrcfgd.py` L2812-2817

```python
bfd_val = data.get('bfd', None)
if (bfd_val is not None and bfd_val.data == 'true'):
    cp_chk_val = data.get('bfd_check_ctrl_plane_failure', None)
    if cp_chk_val is not None and cp_chk_val.op == CachedDataWithOp.OP_NONE and cp_chk_val.data == 'true':
        cp_chk_val.op = CachedDataWithOp.OP_ADD
```

- `bfd = 'true'` に変更した際に `bfd_check_ctrl_plane_failure` が **OP_NONE (変更なし) かつ既存キャッシュが 'true'** の場合、frrcfgd が自動的に OP_ADD に昇格させて FRR に再送する。
- これは `bfd_check_ctrl_plane_failure` の CONFIG_DB 書き込みなしに FRR へ反映される暗黙動作。

### 2.7 `local_asn` (peer-group 側) — `local_as_no_prepend` / `local_as_replace_as` 連動

**ソース**: `frrcfgd.py` cmn_key_map L1867-1868

```python
(['local_asn', '+local_as_no_prepend', '+local_as_replace_as'],
 '{no:no-prefix}neighbor {} local-as {} {:no-prepend} {:replace-as}'),
```

- `local_asn` が必須キー。`+` 付きの 2 つはオプション。
- `local_asn` のみで `local_as_no_prepend` / `local_as_replace_as` が未設定の場合、FRR コマンドは `neighbor <pg> local-as <asn>` のみ (オプションフラグなし)。
- Jinja2 側 (L27-28): `{% if 'local_asn' in nbr_or_peer %}` — `local_as_no_prepend`/`replace_as` の条件チェックなし。J2 とfrrcfgdで挙動差あり (J2 はオプションフラグを出力しない)。

### 2.8 peer-group 未作成時の自動作成

**ソース**: `frrcfgd.py` L2793-2802

```python
if key not in self.bgp_peer_group.setdefault(vrf, {}):
    command = [..., 'neighbor {} peer-group'.format(key)]
    if not self.__run_command(table, command):
        syslog.syslog(syslog.LOG_ERR, 'failed to create peer-group %s for VRF %s' % (key, vrf))
        continue
    self.bgp_peer_group[vrf][key] = BGPPeerGroup(vrf)
```

- SET が来た時点で FRR に peer-group がなければ `neighbor <pg_name> peer-group` を自動発行。
- フィールド値より先にこの "存在確保" コマンドが走る。

### 2.9 `asn` による "apply" / "delete" の自動トリガー

**ソース**: `frrcfgd.py` L2548-2563 (`__nbr_impl_action`)

```python
if is_pg:
    chk_attrs = ['asn']
```

- peer-group では `asn` フィールドの OP が `OP_ADD` → `'apply'` (依存テーブル全体再適用)。
- `asn` の OP が `OP_DELETE` → `'delete'` (peer-group に紐づく全ネイバーを削除シーケンス)。
- `asn` 未変更 (OP_NONE) なら apply/delete どちらも起きない。

---

## 3. YANG vs 実装の discrepancy

| フィールド | YANG | 実装 | 差異 |
|-----------|------|------|------|
| `ebgp_multihop_ttl` | range 1..255, optional | `ebgp_multihop=true` かつ未設定で TTL=255 を暗黙使用 | YANG に default 文なし。実装が 255 を補完 |
| `keepalive` / `holdtime` | 各々 uint16, optional | 両方揃わないと FRR タイマーコマンド未生成 | YANG は独立 leaf だが実装は comb_attr_list で連動 |
| `local_asn` (peer-group フィールド) | optional | J2 テンプレートでは `local_as_no_prepend`/`replace_as` を無視、frrcfgd では付与 | 書き込み経路 (初期設定 vs 動的変更) で差異 |
| `admin_status` | optional, enum up/down | 省略時は FRR デフォルトの no shutdown (up) | YANG default 文なし、FRR 側デフォルト依存 |
| `bfd_check_ctrl_plane_failure` | optional | `bfd` が true に変更されキャッシュに true があれば自動再送 | CONFIG_DB 未変更のまま FRR に影響 |

---

## 4. 書き込み経路依存の乖離

| 経路 | 動作 |
|------|------|
| frrcfgd (動的 SET) | `bgp_neighbor_handler` → `bgp_table_handler_common` → comb_attr_list 検証 → キューイング → FRR vtysh |
| Jinja2 テンプレート (起動時 FRR 設定生成) | `bgpd.conf.db.j2` → `bgpd.conf.db.nbr_or_peer.j2`。`local_as_no_prepend`/`replace_as` はテンプレートに反映されない (L27-28)。`strict_capability_match` は `== true` (bool) 比較で常に false の可能性 (Redis 値は文字列) |
| REST/gNMI (sonic-mgmt-common) | OpenConfig BGP peer-group 経由で CONFIG_DB に書き込み → frrcfgd が購読して同経路 |
| minigraph / sonic-cfggen | BGP_PEER_GROUP を直接生成しない |

---

## 5. 複合必須制約まとめ

| 制約 | フィールド群 | 動作 |
|------|------------|------|
| comb_attr_list | `keepalive` + `holdtime` | 両方揃わないと FRR タイマー未設定 (FRR デフォルト 60/180s) |
| j2 template | `keepalive` + `holdtime` | 同上 (L83-84) |
| j2 template | `ebgp_multihop=true` + `ebgp_multihop_ttl` 省略 | TTL=255 で multihop 有効化 |
| frrcfgd implicit | `asn` OP_ADD | peer-group 紐付きネイバー全体を再適用 |
