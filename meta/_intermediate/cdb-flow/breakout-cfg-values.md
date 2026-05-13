# BREAKOUT_CFG 値依存挙動分析

## enum フィールド
- なし (brkout_mode は string、platform.json 依存)

## brkout_mode (string, platform.json 検証)
- 妥当値はプラットフォーム依存 (platform.json `breakout_modes`)
- 典型値: `1x100G[40G]`, `2x50G`, `4x25G`, `1x400G`, `2x200G`, `4x100G` 等
- DPB 処理がこの値に基づいて PORT テーブルの子ポートを生成/削除

## まとめ
- enum 値なし (platform.json で定義、ドキュメント内で列挙不能)
