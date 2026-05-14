# voq-inband-interface — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`VOQ_INBAND_INTERFACE`

## 段階 1: Consumer 登録

- **orchagent / VoqOrch** (`sonic-swss/orchagent/voqorch.cpp`): `VOQ_INBAND_INTERFACE` テーブルを購読 (VOQ chassis 環境専用)。

## 段階 2: CFG → APPL 翻訳

- VoqOrch が inband インタフェース (asic-asic 通信用) を APP_DB `INTF_TABLE` に書き込む。

## 段階 3: APPL → SAI

- IntfsOrch が SAI で inband ポートの RIF を作成し、VOQ 配送に使用するルートを設定。

## 段階 4: タイミング + 副作用

- VOQ chassis 環境でのみ有効。non-VOQ 環境では orchagent が処理をスキップ。
