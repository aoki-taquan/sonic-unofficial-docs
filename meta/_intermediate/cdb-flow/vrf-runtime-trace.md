# vrf — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`VRF`

## 段階 1: Consumer 登録

- **orchagent / VrfOrch** (`sonic-swss/orchagent/vrforch.cpp`): `VRF` テーブルを `SubscriberStateTable` で購読。
- **vrfmgrd** (`sonic-swss/cfgmgr/vrfmgr.cpp`): `VRF` テーブルを購読して Linux VRF デバイスを管理。

## 段階 2: CFG → APPL 翻訳

- vrfmgrd が `ip vrf add <name>` でカーネル VRF デバイスを作成し APP_DB `VRF_TABLE` に書き込む。

## 段階 3: APPL → SAI

- VrfOrch が APP_DB を読み `sai_virtual_router_api->create_virtual_router()` でハードウェア VRF を作成。
- VRF OID は後続の INTERFACE / ROUTE テーブル処理で使用される。

## 段階 4: タイミング + 副作用

- カーネル VRF 作成 (vrfmgrd) と SAI VRF 作成 (VrfOrch) はほぼ同時。
- 副作用: VRF 削除時は所属インタフェース・ルートを先に削除しないと `VRF is in use` エラー。
