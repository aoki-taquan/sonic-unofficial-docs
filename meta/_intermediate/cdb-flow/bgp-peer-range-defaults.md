# BGP_PEER_RANGE — Phase A: フィールド暗黙デフォルト調査

対象ファイル:
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/instance.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/update.conf.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-peerrange.yang`
- `sonic-buildimage/files/image_config/constants/constants.yml`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-gnmi/pkg/bypass/bypass.go`

---

## フィールド列挙（YANG 由来）

| フィールド | YANG default 定義 | 備考 |
|-----------|-------------------|------|
| `name` | なし（must 制約のみ） | `peer_range_name` と一致必須 |
| `src_address` | なし | optional |
| `peer_asn` | なし | optional (uint32 1..4294967295) |
| `ip_range` | なし | leaf-list、optional |

YANG 側に `default` 文は一切存在しない。

---

## フィールド別 fallback 詳細

### `peer_asn` — 最重要 fallback

**YANG default**: なし

**実行時 fallback** (`instance.conf.j2` L13-17):

```jinja2
{% if bgp_session['peer_asn'] is defined %}
  neighbor {{ bgp_session['name'] }} remote-as {{ bgp_session['peer_asn'] }}
{% else %}
  neighbor {{ bgp_session['name'] }} remote-as {{ constants.deployment_id_asn_map[CONFIG_DB__DEVICE_METADATA['localhost']['deployment_id']] }}
{% endif %}
```

- `peer_asn` 未設定の場合、`constants.yml` の `deployment_id_asn_map` を参照
- `deployment_id` → ASN マッピング (constants.yml):
  - `"1"` → `65432`
  - `"2"` → `65433`
- このフォールバックが動くのは `constants.bgp.use_deployment_id: false`（デフォルト）の場合でも動作する
  （template 側は `use_deployment_id` フラグに依存せず、`peer_asn` の有無だけで分岐）
- DEVICE_METADATA に `deployment_id` が未設定の場合 → Jinja2 `KeyError` → `log_err` + `return True`（drop）

**YANG vs 実装 discrepancy**: YANG は `peer_asn` を optional としているが、未設定時に `deployment_id_asn_map` fallback が自動発動する。この fallback の存在は YANG コメントに記載なし。

---

### `src_address` — Loopback1 fallback

**YANG default**: なし

**実行時 fallback** (`instance.conf.j2` L24-28):

```jinja2
{% if bgp_session['src_address'] is defined %}
  neighbor {{ bgp_session['name'] }} update-source {{ bgp_session['src_address'] | ip }}
{% else %}
  neighbor {{ bgp_session['name'] }} update-source {{ get_ipv4_loopback_address(CONFIG_DB__LOOPBACK_INTERFACE, "Loopback1") | ip }}
{% endif %}
```

- 未設定時は **Loopback1 の IPv4 アドレス**で自動補完
- Loopback1 が存在しない / IPv4 アドレス未設定の場合 → `get_ipv4_loopback_address` が `None` を返す → Jinja2 `| ip` フィルタが `None` に適用されエラー → `log_err` + drop

**ハードコード固定値**: `"Loopback1"` という文字列は templates 内にリテラルでハードコード。CONFIG_DB 経由で変更不可。

---

### `ip_range` — 空送信 or split(",") 処理

**YANG default**: なし（leaf-list）

**書き込み経路依存の乖離**:
- minigraph 経由: `ip_range` は Python list として渡される（`minigraph.py` L1403）
- CONFIG_DB 経由 (SET): bgpcfgd は `data["ip_range"].split(",")` でカンマ区切り文字列として処理
  (`managers_bgp.py` L368)
- **YANG は leaf-list だが、bgpcfgd 内部ではカンマ結合文字列として扱う**（Jinja2 も `.split(',')` で展開）

**空値の挙動**:
- `ip_range` が空文字または未設定の場合、`change_ip_range()` の `if data['ip_range']:` チェック（L366）がスキップ
- `instance.conf.j2` では `{% for ip_range in bgp_session['ip_range'].split(',') %}` が空リストを展開 → FRR に `bgp listen range` コマンドが送られない（range なし状態）

**update 時の挙動** (`update.conf.j2`):
- `delete_ranges` を先に削除し、`add_ranges` を追加するデルタ方式
- `get_existing_ip_ranges()` が vtysh JSON 取得失敗時は空リスト返却 → 全 range を新規追加として処理（冪等性破壊の可能性）

---

### `name` — dead field 候補

**YANG default**: なし、must: `peer_range_name` と一致必須

**実装側挙動**:
- `instance.conf.j2` では `bgp_session['name']` をそのまま peer-group 名に使用
- minigraph 経由では `name` フィールドを明示的に設定 (`minigraph.py` L1401)
- YANG `must` 制約により `peer_range_name` と同一値が強制される
- **実質的に冗長フィールド**（key の `peer_range_name` と同一値しか入らない）だが FRR コマンド生成に使われるため dead field ではない

---

### ハードコード固定値（CONFIG_DB 非依存）

`instance.conf.j2` で以下が**全 dynamic peer に無条件適用**:

| FRR コマンド | ハードコード値 | 変更手段 |
|------------|--------------|---------|
| `neighbor <name> passive` | 常時 passive | 設定不可 |
| `neighbor <name> ebgp-multihop 255` | 最大 255 hop | 設定不可 |
| `neighbor <name> soft-reconfiguration inbound` | 常時有効 | 設定不可 |
| `neighbor <name> route-map FROM_BGP_SPEAKER in` | route-map 名固定 | 設定不可 |
| `neighbor <name> route-map TO_BGP_SPEAKER out` | route-map 名固定 | 設定不可 |
| `address-family ipv4 activate` | 常時有効 | 設定不可 |
| `address-family ipv6 activate` | 常時有効 | 設定不可 |
| Loopback1 fallback (`src_address` 未設定時) | `"Loopback1"` | 設定不可 |

これらは BGP_PEER_RANGE の任意フィールドでは制御できない。YANG にも定義なし。

---

## 書き込み経路依存の乖離

### CLI vs minigraph

| 項目 | CLI (`config bgp`) | minigraph (`sonic-cfggen`) |
|------|--------------------|-----------------------------|
| `ip_range` の型 | カンマ区切り文字列 (CONFIG_DB Hash) | Python list → Redis Hash では同じカンマ区切りに変換される |
| `peer_asn` の設定 | 任意 | `<PeerAsn>` 要素があれば設定、なければ未設定 |
| `src_address` | 任意 | `<Address>` 要素があれば設定 |
| VRF 付与 | key に `<vrf>|<name>` | `bgp_peers_with_range` に直接格納（VRF は key 構造） |

### gNMI (sonic-gnmi bypass)

`sonic-gnmi/pkg/bypass/bypass.go` L29 で `BGP_PEER_RANGE` は `AllowedTables` に列挙されており、gNMI Set 操作時に DBUS/GCU 検証をバイパスして CONFIG_DB 直接書き込みが可能。ただし対象 HwSku は `Cisco-8102/8101/8223` のみ。

---

## 複合必須制約 (comb_attr_list)

YANG には `comb_attr_list` に相当する制約はなし。`must` 制約は `name == peer_range_name` のみ。

実装上の事実上の必須フィールド:
- `name`: `instance.conf.j2` で `bgp_session['name']` を参照するため未設定時 Jinja2 `UndefinedError` → drop
- `ip_range`: 未設定の場合 `split(',')` 参照で `AttributeError` → drop（空文字許容だが `bgp listen range` が発行されない）

---

## 検出サマリ

| 種類 | フィールド / 対象 | 詳細 |
|------|-----------------|------|
| YANG外 fallback（実行時） | `peer_asn` | `deployment_id_asn_map` (constants.yml) 参照 |
| YANG外 fallback（実行時） | `src_address` | Loopback1 IPv4 ハードコード参照 |
| ハードコード固定値 | passive, ebgp-multihop 255, soft-reconfig, route-map名, AF activate | `instance.conf.j2` 全 dynamic peer に無条件適用 |
| YANG vs 実装 discrepancy | `peer_asn` optional だが fallback あり | YANG コメントに fallback 記載なし |
| 書き込み経路依存乖離 | gNMI bypass | Cisco-8102/8101/8223 のみ DBUS バイパス可能 |
| dead field 候補 | `name` | peer_range_name と同一値強制だが FRR コマンドに使用 (not dead) |
| 空値危険 | `ip_range` 空文字 | FRR range コマンド未発行 (silent no-op) |
| 空値危険 | Loopback1 未設定時の `src_address` fallback | Jinja2 エラー → drop |
