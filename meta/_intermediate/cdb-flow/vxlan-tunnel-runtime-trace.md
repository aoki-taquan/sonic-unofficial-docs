# vxlan-tunnel — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`VXLAN_TUNNEL`

## 段階 1: Consumer 登録

- **orchagent / VxlanOrch**: `VXLAN_TUNNEL` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- VxlanOrch が VTEP の src_ip / dst_ip を解析し SAI トンネルオブジェクト作成の準備をする。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- VxlanOrch が `sai_tunnel_api->create_tunnel()` で SAI_TUNNEL_TYPE_VXLAN トンネルを作成し OID を保持。

## 段階 4: タイミング + 副作用

- トンネル作成は orchagent 処理後数 ms 以内。アンダーレイルートがない場合はトンネルが inactive。
- 副作用: VXLAN_TUNNEL 削除時は TUNNEL_MAP / EVPN_NVO など依存オブジェクトを先に削除する必要あり。
