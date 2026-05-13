# DEVICE_NEIGHBOR フィールド値分析

## string フィールド

### `type` (string: ToRRouter/LeafRouter 等)
- 任意の役割文字列 → YANG 上 string 型で制約なし。lldpmgrd や BGP テンプレが参照することがある

### `local_port` (leafref → PORT.name)
- 存在する PORT.name → lldpmgrd が期待 neighbor の照合に使用
- 存在しない PORT.name → YANG leafref 違反で reject

## cross-cutting
- 明示的な enum なし（string フィールドのみ）
- `name` が DEVICE_NEIGHBOR_METADATA に存在しない場合、BGP セッション確立に支障が出ることがあるが YANG レベルでは強制されない
- minigraph.xml 取り込み（sonic-cfggen）経由で自動生成されるのが一般的
