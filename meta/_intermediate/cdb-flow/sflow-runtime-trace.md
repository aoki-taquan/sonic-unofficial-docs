# sflow — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`SFLOW / SFLOW_SESSION`

## 段階 1: Consumer 登録

- **sflowmgrd** (`sonic-swss/cfgmgr/sflowmgr.cpp`): `SFLOW` / `SFLOW_SESSION` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- sflowmgrd が `hsflowd` (sFlow エージェント) の設定ファイルを更新し再起動。
- ポート単位のサンプリングレート設定を APP_DB `SFLOW_SESSION_TABLE` に書き込み。

## 段階 3: APPL → SAI

- orchagent / SflowOrch が APP_DB `SFLOW_SESSION_TABLE` を購読し `sai_samplepacket_api` でハードウェアサンプリングを設定。

## 段階 4: タイミング + 副作用

- グローバル有効化 (`admin_state=up`) 後に各ポートのサンプリングが有効になる。
- 副作用: サンプリングレートを低くしすぎると CPU 負荷が増大。デフォルト 512 は一般的な設定。
