# BGP_PEER_RANGE — ハードコード定数スキャン (Phase E)

調査日: 2026-05-16
対象ソース:
- `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/policies.conf.j2`
- `dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/peer-group.conf.j2`
- `dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/instance.conf.j2`
- `dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/update.conf.j2`

---

## 1. FRR コマンド literal（bgp listen range / limit / peer-group）

### `bgp listen range <prefix> peer-group <name>`

- **ソース**: `dynamic/instance.conf.j2` L13-14（`{% for ip_range in bgp_session['ip_range'].split(',') %}`）
- **説明**: `ip_range` の各 CIDR プレフィックスに対して展開。`<name>` は `bgp_session['name']` に対応し、CONFIG_DB の `peer_range_name` と同一。
- **可変部分**: `<prefix>` と `<name>` のみ。コマンド構造自体はハードコード。

### `no bgp listen range <prefix> peer-group <name>`

- **ソース**: `managers_bgp.py:109`（テンプレート文字列 `'no bgp listen range {{ ip_range }} peer-group {{peer_group}}'`）
- **使用箇所**: `del_handler()` (L467) および `change_ip_range()` の削除処理
- **FRR 10.1+ 制約**: peer-group 削除前に必ずこのコマンドを先行して発行する必要がある（L456-472 コメント）

### `bgp listen limit <N>`

- **ソース**: `frrcfgd.py:1802`
  ```python
  ('max_dynamic_neighbors', '{no:no-prefix}bgp listen limit {}')
  ```
- **CONFIG_DB フィールド対応**: `BGP_GLOBALS_LISTEN_PREFIX` ではなく `BGP_GLOBALS` テーブルの `max_dynamic_neighbors` フィールド経由（frrcfgd パス）。bgpcfgd パスでは直接制御しない。
- **デフォルト値**: FRR デフォルト 100（FRR ソース由来、sonic-buildimage では明示なし）

### `neighbor <name> peer-group`（peer-group 宣言）

- **ソース**: `dynamic/instance.conf.j2` L5
  ```
  neighbor {{ bgp_session['name'] }} peer-group
  ```
- **説明**: `bgp listen range` を設定する前に peer-group 宣言が必要。`BGPPeerGroupMgr.update_pg()` 経由で事前送信される。

---

## 2. 固定 route-map 名（FROM_BGP_SPEAKER / TO_BGP_SPEAKER）

### `FROM_BGP_SPEAKER`

- **ソース**: `dynamic/policies.conf.j2` L4
  ```
  route-map FROM_BGP_SPEAKER permit 10
  ```
  および `dynamic/instance.conf.j2` L9
  ```
  neighbor {{ bgp_session['name'] }} route-map FROM_BGP_SPEAKER in
  ```
- **意味**: inbound route-map。dynamic peer-group に対して無条件 permit（シーケンス 10）。
- **変更可否**: 不可。route-map 名は Jinja2 テンプレートにリテラル文字列としてハードコード。

### `TO_BGP_SPEAKER`

- **ソース**: `dynamic/policies.conf.j2` L6
  ```
  route-map TO_BGP_SPEAKER deny 1
  ```
  および `dynamic/instance.conf.j2` L10
  ```
  neighbor {{ bgp_session['name'] }} route-map TO_BGP_SPEAKER out
  ```
- **意味**: outbound route-map。dynamic peer-group へのルート広告を全拒否（deny、シーケンス 1）。
- **変更可否**: 不可。route-map 名はハードコード。

---

## 3. デフォルト peer-group 名・固定 neighbor 属性

### 固定 neighbor 属性一覧（dynamic/instance.conf.j2）

| FRR コマンド | 固定値 | ソース行 |
|-------------|--------|---------|
| `neighbor <name> passive` | 常時有効 | L6 |
| `neighbor <name> ebgp-multihop 255` | TTL 255 固定 | L7 |
| `neighbor <name> soft-reconfiguration inbound` | 常時有効 | L8 |
| `neighbor <name> route-map FROM_BGP_SPEAKER in` | route-map 名固定 | L9 |
| `neighbor <name> route-map TO_BGP_SPEAKER out` | route-map 名固定 | L10 |
| `address-family ipv4` + `neighbor <name> activate` | IPv4 AF 常時有効化 | L26-28 |
| `address-family ipv6` + `neighbor <name> activate` | IPv6 AF 常時有効化 | L29-31 |

### `bgp suppress-fib-pending`

- **ソース**: `managers_bgp.py:502`
  ```python
  enable_bgp_suppress_fib_pending_cmd = 'bgp suppress-fib-pending'
  ```
- **説明**: `apply_op()` メソッドで全 VRF の BGP ルーター設定ブロックに無条件付与。BGP_PEER_RANGE の SET/DEL 操作すべてに適用される。変数名は `enable_bgp_suppress_fib_pending_cmd` だが enable/disable の切替手段はない。

---

## 4. Loopback1 ハードコード参照

- **ソース**: `dynamic/instance.conf.j2` L21
  ```
  neighbor {{ bgp_session['name'] }} update-source {{ get_ipv4_loopback_address(CONFIG_DB__LOOPBACK_INTERFACE, "Loopback1") | ip }}
  ```
- **説明**: `src_address` フィールド未設定時の fallback。`"Loopback1"` という名前がリテラルにハードコード（`"Loopback0"` や別名への変更不可）。

---

## 5. peer-group.conf.j2 (dynamic) の内容

`dynamic/peer-group.conf.j2` は実質的に空（コメントのみ）。peer-group 属性のカスタマイズ用途だが、dynamic タイプではすべてが `instance.conf.j2` で設定済みのため空になっている。

---

## まとめ

| カテゴリ | 定数 / リテラル | 変更可否 |
|---------|---------------|---------|
| FRR コマンド | `bgp listen range <prefix> peer-group <name>` | 構造固定 |
| FRR コマンド | `no bgp listen range <prefix> peer-group <name>` | 構造固定 |
| FRR コマンド | `bgp listen limit <N>` (frrcfgd 経由) | N は max_dynamic_neighbors で制御可 |
| FRR コマンド | `bgp suppress-fib-pending` | 常時固定（無効化手段なし） |
| route-map 名 | `FROM_BGP_SPEAKER` (inbound permit 10) | 固定 |
| route-map 名 | `TO_BGP_SPEAKER` (outbound deny 1) | 固定 |
| neighbor 属性 | `passive` | 固定 |
| neighbor 属性 | `ebgp-multihop 255` | 255 固定 |
| neighbor 属性 | `soft-reconfiguration inbound` | 固定 |
| neighbor 属性 | `address-family ipv4/ipv6 activate` | 常時有効 |
| interface 名 | `Loopback1` (src_address fallback) | ハードコード |
