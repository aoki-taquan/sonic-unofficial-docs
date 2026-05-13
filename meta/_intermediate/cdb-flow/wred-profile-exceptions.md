# WRED_PROFILE テーブル — 例外条件・特殊挙動

## スキーマ検証

- **名前パターン**: `pattern '[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})'`、長さ 1〜32 文字。違反は `"Invalid length for wred profile name."` エラー[^e2]。
- **max >= min 制約**: YANG `must` で各色の max threshold >= min threshold を強制。違反は `"Yellow/Green/Red max threshold must be greater than or equal to min threshold"` エラー[^e2]。
- **`ecn` のデフォルト**: YANG `default ecn_none`[^e2]。
- **`wred_*_enable` のデフォルト**: YANG `default false`[^e2]。
- **`*_drop_probability` のデフォルト**: YANG `default 100`（100%）[^e2]。

## ignore / skip

- **`convertBool` エラー**: `wred_green_enable` 等に `"true"` / `"false"` 以外の文字列を渡すと `SWSS_LOG_ERROR("Invalid input specified")` を記録して `false` を返す（エントリは破棄）[^e1]。

## 旧 schema / 特殊挙動

- **threshold 更新の 2 フェーズ適用**: orchagent の `WredMapHandler` は閾値変更時に min/max の順序違反を防ぐため、「現在値 > 新 max」または「現在値 < 新 min」となる属性を deferred リストに回し、残りを先に SAI に適用してから deferred を適用する。この動作により一部ベンダー SAI でのエラーを回避する[^e1]。

[^e1]: `sonic-swss/orchagent/qosorch.cpp` (WredMapHandler) <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/qosorch.cpp>
[^e2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-wred-profile.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-wred-profile.yang>
