# vlan-member — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`VLAN_MEMBER`

## 段階 1: Consumer 登録

- **orchagent / VlanOrch** (`sonic-swss/orchagent/vlanorch.cpp`): `VLAN_MEMBER` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- VlanOrch がポートの VLAN 帰属 (`tagging_mode`) を解析。APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- VlanOrch が `sai_vlan_api->create_vlan_member()` でポートを VLAN に追加。
- `tagging_mode=tagged`: `SAI_VLAN_TAGGING_MODE_TAGGED`、`untagged`: `SAI_VLAN_TAGGING_MODE_UNTAGGED`。

## 段階 4: タイミング + 副作用

- VLAN テーブルと PORT テーブルが両方処理済みであることが前提。
- 副作用: ポートを VLAN から削除すると、そのポートの MAC エントリが FDB から自動削除される。
