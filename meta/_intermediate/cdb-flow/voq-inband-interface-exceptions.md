# VOQ_INBAND_INTERFACE テーブル — 例外条件・特殊挙動

## スキーマ検証

- **名前パターン**: YANG `pattern "Ethernet-IB[0-9]+"` — パターン違反は YANG バリデーションで reject[^e1]。
- **`inband_type` パターン**: `pattern "port|Port"` のみ許可[^e1]。
- **IP プレフィクス参照**: `VOQ_INBAND_INTERFACE_IPPREFIX_LIST` の `name` は `VOQ_INBAND_INTERFACE_LIST/name` への leafref — 対応エントリが存在しない場合は YANG の leafref 検証で reject[^e1]。

## デフォルト補完

- `inband_type` 省略時: YANG `default "port"` が補完される[^e1]。

## エラー時動作

- VOQ インバンドインタフェース向けの mgrd は `intfmgr` が兼務する。親インタフェースが STATE_DB に未登録の場合は通常の `VLAN_INTERFACE` と同様にリトライ待ちとなる[^e2]。

[^e1]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-voq-inband-interface.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-voq-inband-interface.yang>
[^e2]: `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
