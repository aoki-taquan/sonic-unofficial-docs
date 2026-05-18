# ROUTE_MAP_SET — Phase E ハードコード定数スキャンノート

## 調査対象

`docs/reference/config-db/route-map-set.md`

## 参照ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang` L125-134
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` 全文
- `sonic-buildimage/src/sonic-utilities/scripts/db_migrator.py`

## 調査結果

ROUTE_MAP_SET テーブルは frrcfgd・bgpcfgd・orchagent のいずれも購読しない。
実装コードがこのテーブルを処理しないため、ランタイムでのハードコード定数は存在しない。

### YANG 定義上の制約（定数相当）

| 制約 | 値 / 内容 | ソース |
|------|----------|--------|
| `name` 型 | `string`（長さ制約なし、YANG デフォルト） | `sonic-route-map.yang:129` |
| フィールド数 | key (`name`) のみ。データフィールドなし | `sonic-route-map.yang:126-133` |

### frrcfgd / db_migrator 参照なし

- `frrcfgd.py` 全文を grep した結果、`ROUTE_MAP_SET` の文字列は出現しない（`table_handler_list` L2293-2338、`tbl_to_key_map` L2106-2134 いずれにも含まれない）。
- `db_migrator.py` にも `ROUTE_MAP_SET` の参照なし。
- `sonic-db-cli` / `config load` 経由の書き込みのみ。YANG 文字列型以外のランタイム制限なし。

## サマリ

ROUTE_MAP_SET はデータフィールドを持たない名前レジストリであり、
実装コードによるハードコード定数は存在しない。
YANG レベルの唯一の制約は `name` が `string` 型であること（長さ制限なし）。
