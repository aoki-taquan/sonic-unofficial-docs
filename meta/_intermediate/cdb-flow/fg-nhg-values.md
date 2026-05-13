# FG_NHG 値依存挙動分析

## enum フィールド

### match_mode (fgnhgorch.cpp L1695-1705)
- `nexthop-based`: nexthop IP のみで FG 判定。FG_NHG_PREFIX 投入は no-op (NOTICE ログ)
- `route-based`: prefix + nexthop IP 両方で FG 判定（デフォルトフォールバック先）
- `prefix-based`: prefix のみ。FG_NHG_MEMBER 不要（dynamic NHG）。シングルバンク強制。max_next_hops 必須
- その他: SWSS_LOG_WARN → route-based にフォールバック

### bucket_size
- 0: SWSS_LOG_ERROR → return true（エントリ破棄）
- 正値: バケット数として使用。メンバ数の LCM を推奨

### max_next_hops
- 0 かつ prefix-based: SWSS_LOG_ERROR（処理継続、SAI 動作不定）
- 0 かつ他モード: 無視
- 超過した NH: SWSS_LOG_WARN → 超過分無視

## 結論
enum 有り: match_mode。bucket_size/max_next_hops は数値。
