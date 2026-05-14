# switch-hash — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`SWITCH_HASH`

## 段階 1: Consumer 登録

- **orchagent / SwitchOrch** (`sonic-swss/orchagent/switchorch.cpp`): `SWITCH_HASH` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- SwitchOrch がハッシュフィールドリスト (`hash_field_list`) と ECMP/LAG ハッシュ設定を解析。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- SwitchOrch が `sai_switch_api->set_switch_attribute()` で `SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_ALGORITHM` / `SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_ALGORITHM` を設定。

## 段階 4: タイミング + 副作用

- 設定変更は即時有効。既存フローのハッシュ再計算によりトラフィック再分散が発生。
- 副作用: ハッシュフィールド変更でフローの ECMP メンバ割り当てが変わりパケット順序逆転が生じる可能性。
