# prefix-list — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`PREFIX_LIST`

## 段階 1: Consumer 登録

- **bgpcfgd** (`sonic-utilities` bgpcfgd): `PREFIX_LIST` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- bgpcfgd が FRR の `vtysh` に `ip prefix-list` コマンドを送信してプレフィックスリストを設定。
- APP_DB への書き込みなし (FRR 直接設定)。

## 段階 3: APPL → SAI

- FRR がプレフィックスリストをルートフィルタとして使用。SAI 経由なし (コントロールプレーン処理)。

## 段階 4: タイミング + 副作用

- vtysh 設定は即時有効。BGP セッションへの影響は次の UPDATE メッセージから。
- 副作用: 既存 BGP ピアのルートフィルタ変更はソフトリセット (`clear bgp soft`) が必要な場合あり。
