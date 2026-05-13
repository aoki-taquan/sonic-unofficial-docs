# DEFAULT_LOSSLESS_BUFFER_PARAMETER 値依存挙動分析

## enum フィールド
なし（`default_dynamic_th`: int8 範囲値, `over_subscribe_ratio`: uint16）

## 値依存挙動

### default_dynamic_th (範囲 -8..7)
- alpha 値 = 2^(dynamic_th)。値が大きいほど shared buffer をより多く使用可能。
  - `-3`: alpha = 1/8 (保守的、shared を制限)
  - `0`: alpha = 1 (バランス)
  - `3`: alpha = 8 (積極的、shared を多用)
- `buffermgrdyn` が dynamic lossless `BUFFER_PROFILE` を自動生成する際の既定 threshold として使用。
  明示的な `BUFFER_PROFILE.dynamic_th` 設定がある場合はそちらが優先。
- static-buffer モードでは完全に無視される。

### over_subscribe_ratio
- `0` または未設定: Shared Headroom Pool (SHP) を無効化。
- `> 0`: SHP を有効化。値は共有 headroom pool のオーバーサブスクライブ比。
  `buffermgrdyn` が `BUFFER_POOL.xoff` (SHP サイズ) を参照してプロファイルを生成。
  `BUFFER_POOL` 側の `xoff` が未設定の場合、動的計算が破綻する (buffermgrdyn.cpp:1998-2002)。

## ソース
- `sonic-swss/cfgmgr/buffermgrdyn.cpp:1998-2002`
- YANG: `sonic-default-lossless-buffer-parameter.yang`
