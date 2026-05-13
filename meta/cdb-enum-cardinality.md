# CDB enum cardinality report

本ファイルは `meta/scripts/scan_cdb_enum_cardinality.py` の出力。
高カーディナリティ enum を持つ CDB ページは値別深掘りで dilution されるので、
値別解析バッチを以下のサイズに分けると過学習なく汎用に深さを揃えられる。

| tier | 閾値 | 推奨 batch サイズ |
|---|---|---|
| high | enum 値 ≥ 15 | 1 page / agent |
| mid | 6 ≤ values < 15 | 3 pages / agent |
| low | values < 6 | 12 pages / agent |

## high tier (0)


## mid tier (0)


## low tier (121)

low tier は通常の 12 ページ/agent で十分。詳細は JSON 参照。
