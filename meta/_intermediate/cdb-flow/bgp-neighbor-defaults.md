# BGP_NEIGHBOR — Phase A: コード由来の暗黙デフォルト調査

作成: 2026-05-14  
対象: `docs/reference/config-db/bgp-neighbor.md`

---

## 1. フィールド列挙 (YANG より)

sonic-bgp-cmn grouping (BGP_NEIGHBOR_LIST 用):
- `local_asn`, `name`, `asn`, `peer_type`, `ebgp_multihop`, `ebgp_multihop_ttl`, `auth_password`
- `keepalive`, `holdtime`, `conn_retry`, `min_adv_interval`, `local_addr`
- `passive_mode`, `capability_ext_nexthop`, `disable_ebgp_connected_route_check`
- `enforce_first_as`, `solo_peer`, `ttl_security_hops`, `bfd`, `bfd_check_ctrl_plane_failure`
- `capability_dynamic`, `dont_negotiate_capability`, `enforce_multihop`, `override_capability`
- `peer_port`, `shutdown_message`, `strict_capability_match`
- `admin_status`, `local_as_no_prepend`, `local_as_replace_as`

sonic-bgp-cmn-neigh grouping (BGP_NEIGHBOR_TEMPLATE_LIST 用):
- `asn`, `holdtime`, `keepalive`, `local_addr`, `name`, `nhopself`, `rrclient`, `admin_status`

BGP_NEIGHBOR_LIST 追加:
- `peer_group_name` (BGP_PEER_GROUP への leafref)

**注意**: YANG には `default` 文が一切ない。全フィールドが optional leaf。

---

## 2. grep entry point

`grep -rln "BGP_NEIGHBOR" .cache/sonic-sources/` 実行済み。  
主要コンシューマ:
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/*/instance.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/*/peer-group.conf.j2`

---

## 3. フィールドごとのコード由来デフォルト

### keepalive / holdtime

**YANG default**: なし (optional)

**minigraph 経路** (`minigraph.py:1313-1320`):
- `<HoldTime>` 要素なし → `holdtime = 180`
- `<KeepAliveTime>` 要素なし → `keepalive = 60`
- CONFIG_DB に明示値として書き込まれる

**bgpcfgd テンプレート** (`general/instance.conf.j2:7-10`):
```
{% if (bgp_session['keepalive'] is defined and bgp_session['keepalive'] | int != 60)
   or (bgp_session['holdtime'] is defined  and bgp_session['holdtime']  | int != 180) %}
  neighbor X timers {{ keepalive | default("60") }} {{ holdtime | default("180") }}
{% endif %}
```
→ `keepalive=60, holdtime=180` のとき `timers` コマンドは **発行しない** (FRR デフォルトに委ねる)。
→ 未設定時のフォールバック: `default("60")` / `default("180")`

**internal テンプレート** (`internal/instance.conf.j2:6`):
```
neighbor X timers 3 10
```
→ `peer_type=internal` では CONFIG_DB 値を **完全に無視** して keepalive=3, holdtime=10 を強制。

**voq_chassis テンプレート** (`voq_chassis/instance.conf.j2:13`):
```
neighbor X timers 2 7
```
→ `peer_type=voq_chassis` では keepalive=2, holdtime=7 を強制 (CONFIG_DB 値無視)。

**frrcfgd 経路** (`frrcfgd.py:1874`):
```python
(['keepalive', 'holdtime'], '{no:no-prefix}neighbor {} timers {} {}'),
```
→ CONFIG_DB 値をそのまま FRR に送る。未設定時は FRR デフォルト (keepalive=60, holdtime=180)。

**書き込み経路による乖離**:
| 経路 | keepalive | holdtime |
|------|-----------|----------|
| minigraph | 60 (フォールバック値を明示書き込み) | 180 |
| CLI/REST/gNMI | YANG validation 経由の指定値のみ | 同左 |
| bgpcfgd `general` | 60/180 (FRR デフォルト委任) | 180 |
| bgpcfgd `internal` | **3** (テンプレートハードコード) | **10** |
| bgpcfgd `voq_chassis` | **2** (テンプレートハードコード) | **7** |

### admin_status

**YANG default**: なし

**minigraph 経路** (`minigraph.py:1344-1368`):
- internal/VoQ chassis ピア → `admin_status = 'up'` を強制書き込み
- external (general) ピア → `admin_status = None` → フィールドを書き込まない
- `enable_internal_bgp_session()` (L1888-1901): VoQ chassis 構成で `admin_status='up'` に強制上書き

**bgpcfgd テンプレート** (`general/instance.conf.j2:13`):
```
{% if 'admin_status' in bgp_session and bgp_session['admin_status'] == 'down'
   or 'admin_status' not in bgp_session
      and 'default_bgp_status' in CONFIG_DB__DEVICE_METADATA['localhost']
      and CONFIG_DB__DEVICE_METADATA['localhost']['default_bgp_status'] == 'down' %}
  neighbor X shutdown
{% endif %}
```
→ `admin_status` フィールドが **存在しない** 場合: `DEVICE_METADATA.localhost.default_bgp_status` が `'down'` なら shutdown 発行。
→ `default_bgp_status` も未設定なら shutdown しない = ピアはアップ状態。

**実行時デフォルト**: `admin_status` フィールドなし + `default_bgp_status` なし → **ピアは up 扱い** (shutdown コマンド未発行)。

### local_addr

**YANG default**: なし

**minigraph 経路** (`minigraph.py:1361, 1372`):
- 常に `end_peer` / `start_peer` の IP を `local_addr` として書き込む

**bgpcfgd `add_peer()`** (`managers_bgp.py:194-202`):
```python
if "local_addr" not in data:
    log_warn("Peer %s. Missing attribute 'local_addr'" % nbr)
else:
    data["local_addr"] = str(netaddr.IPNetwork(str(data["local_addr"])).ip)
    interface = self.get_local_interface(data["local_addr"])
    if not interface:
        return False  # 対応インタフェース未設定なら追加待機
```
→ `local_addr` 未設定: warn ログのみ、peer 追加は続行 (update-source コマンド未発行 → FRR は自動選択)。
→ `local_addr` 設定済みでインタフェース未設定: `return False` でリトライ待ち。

**frrcfgd 経路** (`frrcfgd.py:1870`):
```python
('local_addr', '{no:no-prefix}neighbor {} update-source {}'),
```
→ フィールドがあれば `update-source` を発行。なければ何もしない。

### name (description)

**YANG default**: なし

**bgpcfgd テンプレート**: `general/instance.conf.j2:5` で `neighbor X description {{ bgp_session['name'] }}` を発行。
→ `name` フィールドがない場合: Jinja2 で `UndefinedError` → `log_err` してテンプレートレンダリング失敗 = peer 追加されない。
→ `check_neig_meta=True` 時は `data['name']` が DEVICE_NEIGHBOR_METADATA に存在しないと `return False`。

**minigraph 経路**: 必ず `name` (ルータ名) を書き込む。

**暗黙制約**: `general/internal/voq_chassis` テンプレートでは `name` は **必須** 扱い (YANG では optional だが実装上 required)。

### rrclient / nhopself

**YANG default**: なし (bgp-cmn-neigh では `uint8 {range "0..1"}`)

**minigraph 経路**: `rrclient = 1 if RRClient element else 0`、`nhopself = 1 if NextHopSelf element else 0` として **常に書き込む**。

**テンプレート** (`general/instance.conf.j2:27-33`):
```
{% if 'rrclient' in bgp_session and bgp_session['rrclient'] | int != 0 %}
  neighbor X route-reflector-client
{% endif %}
{% if 'nhopself' in bgp_session and bgp_session['nhopself'] | int != 0 %}
  neighbor X next-hop-self
{% endif %}
```
→ フィールド未設定またはゼロ → コマンド未発行。実質デフォルト 0。

### timers connect (conn_retry)

**YANG default**: なし (`range "1..65535"`)

**テンプレートハードコード**:
- `general/instance.conf.j2:11`: `neighbor X timers connect 10` (CONFIG_DB 値を **無視** してハードコード)
- `internal/instance.conf.j2:7`: `neighbor X timers connect 10` (同)
- `voq_chassis/instance.conf.j2`: `neighbor X timers connect 10` (同)

→ `conn_retry` フィールドは bgpcfgd パスでは **完全に無視される**。10秒ハードコード。
→ frrcfgd パスでは `frrcfgd.py:1875` で `conn_retry` を送出する (`neighbor X timers connect Y`)。

**書き込み経路による乖離**: bgpcfgd 経路では `conn_retry` 設定値が無効 (常に10秒)。frrcfgd 経路でのみ有効。

### peer_type (bgp_peer_type)

**YANG default**: なし (enum `internal`/`external`)

**bgpcfgd でのルーティング**: `constants.yml` の `peers.<type>.db_table` で各 peer_type が **別テーブル** にマップ:
- `general` → `BGP_NEIGHBOR` テーブル
- `internal` → `BGP_INTERNAL_NEIGHBOR` テーブル
- `voq_chassis` → `BGP_VOQ_CHASSIS_NEIGHBOR` テーブル

→ `BGP_NEIGHBOR` テーブルは `general` (external) ピア専用。`peer_type=internal` エントリは `BGP_INTERNAL_NEIGHBOR` に書くべきであり、`BGP_NEIGHBOR` の `peer_type` フィールドは bgpcfgd パスでは **参照されない**。

→ frrcfgd パスでは `BGP_NEIGHBOR` に `peer_type` を書くことで `external`/`internal` を区別する (`frrcfgd.py:1869` 周辺の nbr_key_map)。

**書き込み経路による乖離**: bgpcfgd 経路では `peer_type` フィールドは機能しない (テーブル名で決定)。frrcfgd 経路でのみ有効。

### ebgp_multihop / ebgp_multihop_ttl

**YANG default**: なし

**dynamic テンプレート** (`dynamic/instance.conf.j2:8`):
```
neighbor X ebgp-multihop 255
```
→ `BGP_PEER_RANGE` (dynamic peer) では `ebgp_multihop_ttl=255` がハードコード。CONFIG_DB 値は無視。

**general/internal テンプレート**: 明示的な ebgp-multihop コマンド未発行 → フィールド設定がなければ FRR デフォルト (disabled)。

### send_community (peer-group 設定)

**YANG default**: なし

**internal peer-group テンプレート** (`internal/peer-group.conf.j2:18, 31`):
```
neighbor INTERNAL_PEER_V4 send-community
neighbor INTERNAL_PEER_V6 send-community
```
→ `internal` ピアでは `send-community` が **自動付与** (standard)。general ピアでは未設定。

### soft-reconfiguration inbound (peer-group 設定)

**YANG default**: なし

**peer-group テンプレート**:
- `general/peer-group.conf.j2:14,29`: `PEER_V4/V6 soft-reconfiguration inbound` (常に付与)
- `internal/peer-group.conf.j2:14,27`: `INTERNAL_PEER_V4/V6 soft-reconfiguration inbound` (常に付与)

→ bgpcfgd 経路では全 peer でデフォルト有効。

### allowas-in (peer-group 設定)

**YANG default**: なし

**general peer-group** (`general/peer-group.conf.j2:7-13`):
```
{% if type == 'ToRRouter' %}
  allowas-in 1
{% elif type == 'LeafRouter' and BBR enabled %}
  allowas-in 1
{% endif %}
```
→ `ToRRouter` または `LeafRouter` (BBR enabled) では `allowas-in 1` が自動付与。他では未設定。

**internal peer-group** (`internal/peer-group.conf.j2:15, 29`): `allowas-in 1` 常時付与。

### next-hop-self force (instance 設定)

**internal テンプレート** (`internal/instance.conf.j2:13-15`):
```
{% if sub_role == 'BackEnd' or switch_type == 'chassis-packet' %}
  neighbor X next-hop-self force
{% endif %}
```
→ `sub_role=BackEnd` または `switch_type=chassis-packet` のとき自動付与。

### update-source (chassis-packet)

**internal peer-group テンプレート** (`internal/peer-group.conf.j2:6-9`):
```
{% if switch_type == 'chassis-packet' %}
  neighbor INTERNAL_PEER_V4 update-source Loopback4096
  neighbor INTERNAL_PEER_V4 ttl-security hops 1
{% endif %}
```
→ `switch_type=chassis-packet` では `Loopback4096` を update-source として **自動設定**。`ttl-security hops 1` も自動。

### bgp suppress-fib-pending (apply_op)

`managers_bgp.py:502-506` の `apply_op()` で **全 VRF** に対して:
```python
cmd = ('router bgp %s\n %s\n' % (bgp_asn, 'bgp suppress-fib-pending')) + cmd + "\nexit"
```
→ ネイバー追加・更新のたびに `bgp suppress-fib-pending` が BGP インスタンス設定として注入される。フィールドには現れない暗黙の副作用。

### no bgp default ipv4-unicast (frrcfgd)

`frrcfgd.py:2700`:
```python
command = ['vtysh', ..., 'no bgp default ipv4-unicast']
```
→ frrcfgd 経路では BGP_GLOBALS.local_asn 設定時に `no bgp default ipv4-unicast` を発行。
→ `BGP_NEIGHBOR_AF` の `admin_status` (ipv4/ipv6/l2vpn) が `activate` の有無を制御。

---

## 4. 書き込み経路依存の乖離サマリ

| フィールド | bgpcfgd (minigraph/CLI) | frrcfgd (REST/gNMI) |
|-----------|------------------------|---------------------|
| `keepalive` | general:60, internal:**3**, voq:**2** (テンプレートで強制) | CONFIG_DB 値をそのまま FRR へ |
| `holdtime` | general:180, internal:**10**, voq:**7** (テンプレートで強制) | CONFIG_DB 値をそのまま FRR へ |
| `conn_retry` | **常に10秒ハードコード** (フィールド無視) | CONFIG_DB 値を `timers connect` で送出 |
| `peer_type` | テーブル名で決定、フィールド無視 | フィールド値を使用 |
| `admin_status` | `default_bgp_status` メタデータで補完 | フィールド値を直接使用 |
| `ebgp_multihop_ttl` | dynamic: **255ハードコード** | CONFIG_DB 値を使用 |
| `send_community` | internal: ペアグループで自動付与 | フィールド `send_community` で制御 |

---

## 5. YANG と実装の discrepancy

1. **`peer_type` enum**: YANG は `internal`/`external` の2値。bgpcfgd は `general`, `internal`, `dynamic`, `voq_chassis`, `monitors`, `sentinels` の6分類をテーブル名で区別 → YANG と実装が乖離。
2. **`conn_retry` の bgpcfgd 無視**: YANG で `range "1..65535"` として定義するが bgpcfgd テンプレートが常に `timers connect 10` をハードコードするため CONFIG_DB 値が反映されない。
3. **`name` の実質必須化**: YANG では optional leaf だが bgpcfgd テンプレートで無条件参照されるため、設定なしではテンプレートレンダリング失敗 → ピア追加不可。
4. **`keepalive`/`holdtime` の internal/voq_chassis 強制上書き**: YANG には range 制約なし、bgpcfgd テンプレートが CONFIG_DB 値を完全に無視してハードコード値を使用。
