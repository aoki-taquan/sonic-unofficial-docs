# PREFIX_LIST — Phase E ハードコード定数スキャン中間ファイル

生成日: 2026-05-16 (chore/q67-f-phaseE-prefix-list)
ソース: sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py

<!-- constants -->
## Phase E: ハードコード定数スキャン結果

### スキャン対象

- `managers_prefix_list.py` — `PREFIX_TYPE_CONFIG` 辞書 + `PrefixListMgr` クラス全体
- `tests/test_prefix_list.py` — constants override テストから実際の使われ方を確認

### PREFIX_TYPE_CONFIG 辞書 (L6-26)

```python
PREFIX_TYPE_CONFIG = {
    "ANCHOR_PREFIX": {
        "add_template": "bgpd/radian/add_radian",
        "del_template": "bgpd/radian/del_radian",
        "allowed_devices": [
            ("SpineRouter", "UpstreamLC"),
            ("UpperSpineRouter", None),
        ],
        "prefix_list_name": lambda ipv: "ANCHOR_CONTRIBUTING_ROUTES",
        "log_label": "Anchor prefix",
        "log_label_target": "radian",
    },
    "SUPPRESS_PREFIX": {
        "add_template": "bgpd/suppress_prefix/add_suppress_prefix",
        "del_template": "bgpd/suppress_prefix/del_suppress_prefix",
        "allowed_devices": None,
        "prefix_list_name": lambda ipv: "SUPPRESS_IPV4_PREFIX" if ipv == "ip" else "SUPPRESS_IPV6_PREFIX",
        "log_label": "Suppress prefix",
        "log_label_target": "suppress_prefix",
    },
}
```

### 定数一覧

| 種別 | 定数名/キー | 値 | 行番号 |
|------|-----------|-----|--------|
| prefix_type キー | `ANCHOR_PREFIX` | ハードコード文字列 | L6 |
| prefix_type キー | `SUPPRESS_PREFIX` | ハードコード文字列 | L11 |
| FRR テンプレート | `add_template` (ANCHOR) | `"bgpd/radian/add_radian"` | L7 |
| FRR テンプレート | `del_template` (ANCHOR) | `"bgpd/radian/del_radian"` | L8 |
| FRR テンプレート | `add_template` (SUPPRESS) | `"bgpd/suppress_prefix/add_suppress_prefix"` | L19 |
| FRR テンプレート | `del_template` (SUPPRESS) | `"bgpd/suppress_prefix/del_suppress_prefix"` | L20 |
| prefix list 名 (ANCHOR IPv4/IPv6) | `prefix_list_name` lambda | `"ANCHOR_CONTRIBUTING_ROUTES"` | L14 |
| prefix list 名 (SUPPRESS IPv4) | `prefix_list_name` lambda | `"SUPPRESS_IPV4_PREFIX"` | L22 |
| prefix list 名 (SUPPRESS IPv6) | `prefix_list_name` lambda | `"SUPPRESS_IPV6_PREFIX"` | L22 |
| 許可デバイス (ANCHOR)[0] | `allowed_devices` | `("SpineRouter", "UpstreamLC")` | L12 |
| 許可デバイス (ANCHOR)[1] | `allowed_devices` | `("UpperSpineRouter", None)` | L13 |
| 許可デバイス (SUPPRESS) | `allowed_devices` | `None` (全許可) | L21 |
| IP 判定文字列 (v4) | `get_ip_type()` 戻り値 | `"ip"` | L140 |
| IP 判定文字列 (v6) | `get_ip_type()` 戻り値 | `"ipv6"` | L142 |
| log_label (ANCHOR) | `log_label` | `"Anchor prefix"` | L15 |
| log_label (SUPPRESS) | `log_label` | `"Suppress prefix"` | L23 |
| log_label_target (ANCHOR) | `log_label_target` | `"radian"` | L16 |
| log_label_target (SUPPRESS) | `log_label_target` | `"suppress_prefix"` | L24 |

### constants オーバーライドキー (L89-91)

```python
pl_overrides = self.constants.get("bgp", {}).get("prefix_list", {}).get(prefix_type, {})
name_key = "ipv4_name" if data["ipv"] == "ip" else "ipv6_name"
data["prefix_list_name"] = pl_overrides.get(name_key, type_cfg["prefix_list_name"](data["ipv"]))
```

- `bgp.prefix_list.<type>.ipv4_name` → SUPPRESS_PREFIX/ANCHOR_PREFIX の IPv4 list 名上書き
- `bgp.prefix_list.<type>.ipv6_name` → IPv6 list 名上書き

テスト `test_suppress_prefix_constants_override` で確認済み (test_prefix_list.py L135-142)。

### action / family / seq / prefixlen について

この `PREFIX_LIST` テーブルは bgpcfgd の簡易テーブル実装であり:
- `action` (permit/deny) フィールドは CONFIG_DB には存在しない。FRR テンプレートが暗黙的に `permit` のみ生成する
- `seq` (シーケンス番号) は CONFIG_DB フィールドに存在せず、FRR テンプレート側でインクリメントされる
- `ge`/`le` (prefix length range) はこのテーブルには存在しない（`PREFIX_SET` 系テーブルで対応）
- `family` フィールドは YANG の `must` 制約用で、実際の IP バージョン判定は `netaddr.IPNetwork.version` から行う

<!-- /constants -->
