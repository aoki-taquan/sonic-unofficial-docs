# policer — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`POLICER`

## 段階 1: Consumer 登録

- **orchagent / PolicerOrch** (`sonic-swss/orchagent/policerorch.cpp`): `POLICER` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- PolicerOrch がエントリを解析し SAI policer オブジェクトを作成。他の orch (MirrorOrch, AclOrch) から leafref 参照される。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- PolicerOrch が `sai_policer_api->create_policer()` を呼び出して SAI POLICER を作成。
- `meter_type`, `mode`, `cir`, `cbs`, `pir`, `pbs`, `action` を SAI 属性にマッピング。

## 段階 4: タイミング + 副作用

- POLICER オブジェクト作成後、MIRROR_SESSION や ACL から参照されることで有効化。
- 副作用: policer 削除時に MirrorOrch/AclOrch が参照している場合、削除は失敗 (`policer is still referenced`)。
