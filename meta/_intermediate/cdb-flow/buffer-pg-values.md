# BUFFER_PG 値依存挙動分析

## enum フィールド
- なし (profile は leafref or NULL string)

## profile フィールド
- `NULL` 文字列: buffermgrd が PG を削除扱いにする
- leafref `BUFFER_PROFILE.name`: 対応 profile の xon/xoff/threshold で PG を設定

## pg_num (key, string pattern)
- `0`-`7` 単一値 または `0-3` 等の範囲表記を受け入れ
- buffermgrd が範囲をパースして各 PG に適用

## まとめ
- enum 値なし。profile=NULL が特殊な削除トリガー
