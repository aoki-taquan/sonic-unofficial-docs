# COMMUNITY_SET 値依存挙動分析

## enum フィールド
1. `set_type`: `STANDARD` / `EXPANDED`
2. `match_action`: `ANY` / `ALL`
3. `action`: `permit` / `deny`

## 値依存挙動

### set_type
- `STANDARD`: FRR の `bgp community-list standard <name> permit <value>` に展開される。
  数値 community (`AS:value` 形式) および well-known community に対して完全一致でマッチ。
- `EXPANDED`: FRR の `bgp community-list expanded` に展開される。
  正規表現マッチが可能。`.*:100` のようなパターンが使える。

### match_action
- `ANY`: いずれか一つの `community_member` に一致するルートを対象とする（OR 条件）。
- `ALL`: すべての `community_member` を同時に持つルートのみを対象とする（AND 条件）。

### community_member の順序 (ordered-by user)
- `frr-mgmt-framework` が FRR へ展開するとき、ユーザ指定順でリストが生成される。
  FRR の community-list は EXPANDED の場合、正規表現を順番に評価するため順序が意味を持つ場合がある。

## ソース
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py:373-374`
- YANG: `sonic-routing-policy-sets.yang`
