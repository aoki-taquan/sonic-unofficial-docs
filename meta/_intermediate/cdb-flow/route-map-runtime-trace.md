# route-map — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`ROUTE_MAP`

## 段階 1: Consumer 登録

- **bgpcfgd**: `ROUTE_MAP` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- bgpcfgd が FRR の `route-map` を `vtysh` 経由で設定。PREFIX_LIST / PREFIX_SET を参照する場合は先に作成が必要。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- FRR がルートマップを BGP ポリシー (import/export filter, redistribution) として使用。SAI 経由なし。

## 段階 4: タイミング + 副作用

- route-map 変更は FRR に即時反映。BGP ピアへの影響は次の UPDATE/KEEPALIVE から。
- 副作用: `set local-preference` 変更等でルート選択が変わり、トラフィックパスが切り替わる可能性。
