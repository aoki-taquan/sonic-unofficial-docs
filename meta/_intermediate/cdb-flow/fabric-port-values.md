# FABRIC_PORT フィールド値分析

## boolean フィールド

### `isolateStatus` (boolean_type: True/False, デフォルト False)
- `True` → fabricmgr が APPL_DB に isolateStatus=True を書き込み、syncd 経由で SAI がポートを fabric trunk から除外（fabricmgr.cpp:86-89）
- `False` (デフォルト) → 通常接続状態。FABRIC_MONITOR が自動制御する場合もここを True/False に変更する

## uint フィールド

### `forceUnisolateStatus` (uint32, デフォルト 0)
- 0 以外 → 強制的に unisolate する（FABRIC_MONITOR による自動 isolate を上書き）
- 0 (デフォルト) → 通常の FABRIC_MONITOR 制御に委ねる

## string フィールド

### `lanes` (string, mandatory)
- プラットフォーム固有のレーン番号文字列。SAI 側でポートを特定するのに使用
- 未設定（mandatory 違反）→ YANG validate で reject

### `alias`
- 任意のエイリアス名。APPL_DB に転写されて show コマンド等で表示

## cross-cutting
- `isolateStatus = True` のまま FABRIC_MONITOR を disable にすると、自動復帰がかからず手動で False に戻すまで isolate が継続
- forceUnisolateStatus は `isolateStatus = True` の状態を強制解除する緊急用途
