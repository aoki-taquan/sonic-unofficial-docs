# DEVICE_NEIGHBOR_METADATA フィールド値分析

## string フィールド

### `type` (string: LeafRouter/SpineRouter/ToRRouter 等)
- `LeafRouter` / `SpineRouter` / `ToRRouter` / `Server` 等 → BGP テンプレート生成（bgpcfgd）で role を参照し、eBGP セッション設定を分岐させることがある
- 任意の文字列 → YANG 上 string 型で制約なし。実装側がチェック

## union フィールド

### `lo_addr` / `lo_addr_v6` / `mgmt_addr` / `mgmt_addr_v6`
- ipv4/ipv6-prefix 形式 → prefix 長付き
- ipv4/ipv6-address 形式 → ホストアドレス
- いずれも YANG union 型。書式が正しければ両形式を受理

## cross-cutting
- 明示的な enum 制約なし（type は string、IP 系は union）
- DEVICE_NEIGHBOR の `name` フィールドと hostname を一致させることで、BGP neighbor 名解決と lldpmgrd の期待 neighbor チェックが機能する（YANG レベルの leafref はない）
