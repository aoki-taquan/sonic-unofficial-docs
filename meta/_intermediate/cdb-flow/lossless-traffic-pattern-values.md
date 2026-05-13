# LOSSLESS_TRAFFIC_PATTERN 値依存挙動分析

## 数値フィールド

### mtu (uint16 1..9216)
- `1500`: 標準イーサネット MTU
- `9216`: ジャンボフレーム対応
- 未設定: buffermgrdyn がデフォルト mtu 値を使用（"if mtu isn't configured, take the default value"）
- 実 MTU と乖離: headroom が過小（パケットロス）または過大（バッファ浪費）。バリデーションなし

### small_packet_percentage (uint8 0..100)
- `50`: 経験的な標準値
- `100`: 小パケット比率最大（ヘッドルーム増加）
- `0`: 小パケットなし（ヘッドルーム最小）
- 0〜100 範囲外: コード上バリデーションなし → headroom 計算式が異常値を返す可能性

## DB migration 初期値 (db_migrator.py L414)
- AZURE エントリ自動挿入時: mtu=1024, small_packet_percentage=100
- Mellanox 向け初期値（他プラットフォームには不適切な場合あり）

## 結論
enum なし。数値フィールドのみ。dynamic buffer モード以外では参照されない点が重要な条件。
