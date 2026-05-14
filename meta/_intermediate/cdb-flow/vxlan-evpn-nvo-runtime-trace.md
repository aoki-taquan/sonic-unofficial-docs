# vxlan-evpn-nvo — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`VXLAN_EVPN_NVO`

## 段階 1: Consumer 登録

- **orchagent / VxlanOrch** (`sonic-swss/orchagent/vxlanorch.cpp`): `VXLAN_EVPN_NVO` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- VxlanOrch が EVPN NVO 設定 (source vtep 名) を解析し FRR 経由で EVPN ルートを受信する準備をする。
- APP_DB への書き込みなし (orchagent → SAI 直接)。

## 段階 3: APPL → SAI

- VxlanOrch が SAI トンネルオブジェクト (VXLAN_TUNNEL 参照) に EVPN を関連付け、`sai_tunnel_api` で VTEP を設定。

## 段階 4: タイミング + 副作用

- VXLAN_TUNNEL テーブルが先に処理されている必要あり。BGP EVPN ルート受信後に MAC/IP ルートが SAI に展開される。
- 副作用: EVPN NVO 削除時は全 VNI・MAC エントリが一斉削除されトラフィックが断。
