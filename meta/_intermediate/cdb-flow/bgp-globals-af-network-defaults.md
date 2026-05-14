# BGP_GLOBALS_AF_NETWORK — Phase A: コード由来の暗黙デフォルト調査

## 対象フィールド

`BGP_GLOBALS_AF_NETWORK_LIST` (sonic-bgp-global.yang) のフィールド:

| フィールド | 種別 | YANG default 宣言 |
|---|---|---|
| `vrf_name` | key (leafref) | なし |
| `afi_safi` | key (string) | なし |
| `ip_prefix` | key (inet:ip-prefix) | なし |
| `policy` | leafref → ROUTE_MAP_SET.name | **なし** |
| `backdoor` | boolean | **なし** |

## YANG デフォルト

- `policy`: YANG default 宣言なし。省略時は空扱い。
- `backdoor`: YANG default 宣言なし。省略時は空扱い。
- キーフィールド (`vrf_name`, `afi_safi`, `ip_prefix`) はリストキーのため default 不可。

## コード由来の実行時フォールバック

### ソース: frrcfgd.py

#### key_map 定義 (L1985)

```python
af_network_key_map = [
    (['ip_prefix', '++policy', '+backdoor'],
     '{no:no-prefix}network {2} {3:network-policy} {4:network-backdoor}')
]
```

- `ip_prefix`: required (キーから合成、必ず存在)
- `++policy`: `opt_idx_list` に入る (`++` プレフィックス) → 欠如時は空文字列 `''` を用いて継続
- `+backdoor`: optional (`+` プレフィックス) だが `opt_idx_list` には入らない → 欠如時は `get_cmd_data` のループが break して後続フィールドも空文字列でパディングされる

#### フォーマッタ挙動 (L922-924, L811-826)

`network-policy` フォーマッタ:
```python
elif format == 'network-policy':
    if len(self.value) > 0:
        self.value = 'route-map %s' % self.to_str()
```
→ `policy` 欠如 or 空 → 何も出力されない (空文字列のまま)

`network-backdoor` フォーマッタ (bool_format テーブル):
```python
'network-backdoor': 'backdoor',
```
→ `backdoor == 'true'` → `'backdoor'` キーワードを出力
→ `backdoor == 'false'` → `''` (空文字列、FRR コマンドに追記なし)
→ `backdoor` 欠如 → `+backdoor` が absent → `get_cmd_data` break パス → 空文字列パディング → FRR コマンド末尾に何も追記されない

#### 生成される FRR コマンド例

| policy | backdoor | 生成コマンド |
|---|---|---|
| 未設定 | 未設定 | `network 10.1.0.0/16  ` (末尾スペースのみ、実質 `network 10.1.0.0/16`) |
| `MY_RM` | 未設定 | `network 10.1.0.0/16 route-map MY_RM ` |
| 未設定 | `true` | `network 10.1.0.0/16  backdoor` |
| `MY_RM` | `true` | `network 10.1.0.0/16 route-map MY_RM backdoor` |
| 未設定 | `false` | `network 10.1.0.0/16  ` |
| `MY_RM` | `false` | `network 10.1.0.0/16 route-map MY_RM ` |

注: Jinja2 テンプレート (`bgpd.conf.db.addr_family.j2`) も同様のロジックだが、
`backdoor` の順序が policy より **先** になる (`backdoor ` を先に追加してから `route-map` を連結)
→ テンプレート生成順: `network <prefix> [backdoor ][route-map <name>]`
→ frrcfgd 生成順: `network <prefix> [route-map <name>] [backdoor]`

**discrepancy 検出**: Jinja2 テンプレートと frrcfgd では `backdoor` と `route-map` の順序が逆。
FRR bgpd は `network <prefix> backdoor route-map <name>` も `network <prefix> route-map <name> backdoor` も受け付けるため実害は出ないが、YANG/HLD との整合性の観点で注記価値あり。

### ソース: bgpd.conf.db.addr_family.j2 (L35-45)

```jinja2
{% set af_nw_ns = namespace(nw_end = '') %}
{% if 'backdoor' in af_nw_val and af_nw_val['backdoor'] == 'true' %}
{% set af_nw_ns.nw_end = 'backdoor ' %}
{% endif %}
{% if 'policy' in af_nw_val %}
{% set af_nw_ns.nw_end = af_nw_ns.nw_end + 'route-map ' + af_nw_val['policy'] %}
{% endif %}
  network {{af_nw_key[2]}} {{af_nw_ns.nw_end}}
```

- `backdoor` 欠如 or `false`: `nw_end` への追記なし
- `policy` 欠如: `nw_end` への追記なし
- 両方欠如: `network <prefix> ` (末尾スペース)

### ソース: sonic-bgp-global.yang

- `backdoor` に `ext:custom-validation ValidateAfisafiForBackdoor;` がコメントアウトされている
  → `backdoor` は `ipv4_unicast` にのみ有効という検証が**無効化されている**
  → 現状コードでは `ipv6_unicast` や `l2vpn_evpn` でも `backdoor` を設定可能 (FRR 側で拒否される場合あり)

## YANG と実装の discrepancy

| 項目 | YANG 定義 | 実装挙動 |
|---|---|---|
| `backdoor` の afi 制約 | `ValidateAfisafiForBackdoor` が定義されるがコメントアウト | 検証なし、YANG は事実上制約なし |
| `backdoor` + `policy` 順序 | 未定義 | frrcfgd: `route-map` → `backdoor` 順; j2 テンプレート: `backdoor` → `route-map` 順 |
| `policy` デフォルト | なし | 欠如時は空文字列フォールバック、FRR コマンドに `route-map` なし |
| `backdoor` デフォルト | なし | 欠如時は `false` 相当 (FRR コマンドに `backdoor` キーワードなし) |

## 書き込み時 vs 実行時乖離

- **書き込み時**: CONFIG_DB に `{policy: "", backdoor: "false"}` と明示的に書いても、空 `policy` は `route-map` を生成しない (フォーマッタが `len(self.value) > 0` チェック)
- **実行時**: `network_import_check=true` (FRR デフォルト、BGP_GLOBALS にも default 宣言なし) の場合、CONFIG_DB 書き込み成功でも RIB にプレフィックスが存在しなければ FRR は BGP UPDATE に注入しない

## 結論

- `policy`: 暗黙デフォルト = 省略 (route-map なし)。YANG default なし、コードフォールバックは空文字列。
- `backdoor`: 暗黙デフォルト = `false` 相当 (backdoor キーワードなし)。YANG default なし、コードフォールバックは空文字列。
- 主要 discrepancy: j2 テンプレートと frrcfgd の `backdoor`/`route-map` 出力順が逆。
- `ValidateAfisafiForBackdoor` カスタムバリデーション無効化により afi 検証が欠落。

## evidence

- `frrcfgd.py:1985` — af_network_key_map 定義
- `frrcfgd.py:811-826` — bool_format/network-backdoor フォーマッタ
- `frrcfgd.py:922-924` — network-policy フォーマッタ
- `frrcfgd.py:3169-3186` — BGP_GLOBALS_AF_NETWORK ハンドラ分岐
- `bgpd.conf.db.addr_family.j2:35-45` — Jinja2 テンプレート
- `sonic-bgp-global.yang:509-543` — YANG 定義 (BGP_GLOBALS_AF_NETWORK_LIST)
