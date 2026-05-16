# PREFIX_LIST フィールド デフォルト調査 (Phase A)

## 調査対象

`docs/reference/config-db/prefix-list.md` — `PREFIX_LIST` テーブル (BGP)

## ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-prefix-list.yang`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py`
- `sonic-buildimage/src/sonic-bgpcfgd/tests/test_prefix_list.py`

## フィールド別デフォルト

### `prefix_type` (key フィールド)

- YANG: デフォルト値なし (`type string`、key の一部)
- コード由来デフォルト: なし。key フィールドのため省略不可
- 有効値: `ANCHOR_PREFIX` / `SUPPRESS_PREFIX`（その他は `log_warn` + スキップ）

### `ip-prefix` (key フィールド)

- YANG: デフォルト値なし (`union(sonic-ip4-prefix | sonic-ip6-prefix)`、key の一部)
- コード由来デフォルト: なし。key フィールドのため省略不可
- `netaddr.IPNetwork()` でパース後 `.cidr` 形式に正規化される

### `family` (任意フィールド)

- YANG: `default` 文なし (`type stypes:ip-family`、列挙 `IPv4`/`IPv6`)
- コード由来デフォルト: **なし**
  - `managers_prefix_list.py` の `set_handler` は `data["ipv"]` を `get_ip_type()` で
    `ip-prefix` の netaddr バージョンから算出する（`prefix.version == 4` → `"ip"`、`== 6` → `"ipv6"`）
  - `family` フィールド自体は FRR テンプレート展開に使われず、`ipv` 変数で制御される
  - YANG `must` 制約: `family==IPv6` なら `ip-prefix` に `:` を含む、`IPv4` なら `.` を含む

## 結論

| フィールド | YANG default | コード由来デフォルト | 備考 |
|-----------|-------------|-------------------|------|
| `prefix_type` | なし (key) | なし | `ANCHOR_PREFIX`/`SUPPRESS_PREFIX` のみサポート |
| `ip-prefix` | なし (key) | なし | CIDR 正規化は PrefixListMgr が実施 |
| `family` | なし | なし | YANG must で ip-prefix と整合性チェック。FRR 展開は `ipv` 変数で制御 |

PREFIX_LIST テーブルはすべてのフィールドが key か YANG must 制約付きで、
コードが自動補完するデフォルト値は存在しない。
`family` は後方互換用であり、実際の IPv4/IPv6 判定は `get_ip_type()` が
`ip-prefix` の netaddr version から動的に行う。

## 証跡

- `managers_prefix_list.py` L112: `data["ipv"] = self.get_ip_type(prefix)`
- `managers_prefix_list.py` L138-143: `get_ip_type` — version 4 → `"ip"`, version 6 → `"ipv6"`
- `sonic-bgp-prefix-list.yang` L48-59: `family` leaf — `must` 制約のみ、`default` 文なし
