# vxlan-tunnel-map — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`VXLAN_TUNNEL_MAP`

## 段階 1: Consumer 登録

- **orchagent / VxlanOrch**: `VXLAN_TUNNEL_MAP` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- VxlanOrch が VNI ↔ VLAN マッピングを解析。APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- VxlanOrch が `sai_tunnel_api->create_tunnel_map_entry()` で VNI ↔ VLAN のマッピングエントリをハードウェアに設定。

## 段階 4: タイミング + 副作用

- VXLAN_TUNNEL と VLAN テーブルが処理済みであることが前提。
- 副作用: VNI マッピング削除時は対応する EVPN MAC/IP ルートも連動して削除。
