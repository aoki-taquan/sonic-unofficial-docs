# prefix-set — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`PREFIX_SET`

## 段階 1: Consumer 登録

- **bgpcfgd** または **sonic-cfggen**: `PREFIX_SET` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- bgpcfgd が FRR の prefix-list 設定を生成して vtysh 経由で反映。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- FRR がプレフィックスセットをポリシーマッチ条件として使用。SAI 経由なし。

## 段階 4: タイミング + 副作用

- FRR 設定反映は即時。ルーティングポリシーへの影響はピアの next UPDATE から。
