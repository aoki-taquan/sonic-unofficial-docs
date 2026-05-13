# BMP 値依存挙動分析

## enum フィールド
- なし (boolean のみ)

## boolean フィールド挙動 (bmpcfgd.py)
- 設定変更時: 常に stop_bmp() → reset_bmp_table() → start_bmp() の 3 ステップを実行
- `bgp_neighbor_table=true` → openbmpd が BGP_NEIGHBOR テーブルダンプを STATE_DB に書く
- `bgp_rib_in_table=true`   → Adj-RIB-In テーブルダンプ
- `bgp_rib_out_table=true`  → Adj-RIB-Out テーブルダンプ
- `false` にすると BMP_STATE_DB から対応エントリを全削除してから再起動

## 重要な副作用
- 任意の boolean 変更でも openbmpd が再起動する (全テーブル再構築)

## まとめ
- enum 値なし。boolean 変更時は常に openbmpd 再起動が発生
