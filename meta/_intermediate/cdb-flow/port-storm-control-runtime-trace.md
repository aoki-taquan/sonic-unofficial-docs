# port-storm-control — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`PORT_STORM_CONTROL`

## 段階 1: Consumer 登録

- **orchagent / StormControlOrch**: `PORT_STORM_CONTROL` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- StormControlOrch がエントリを解析し、ストームコントロール種別 (`broadcast`, `unknown_unicast`, `unknown_multicast`) とレート (kbps/pps) を取得。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- orchagent が `sai_port_api->set_port_attribute()` でストームコントロール policer を適用。
- SAI 属性: `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` 等。

## 段階 4: タイミング + 副作用

- 設定は即時 SAI に反映。既存フラッディングトラフィックへの影響は ms 単位。
- 副作用: レートを低く設定しすぎると正常な broadcast (ARP 等) も制限される。
