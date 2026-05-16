# community-set Phase A — 暗黙デフォルト調査

調査日: 2026-05-14
対象: `COMMUNITY_SET` テーブル
主要ソース:
- `frrcfgd.py` L981-1007, L1569-1603, L2875-2893
- `bgpd.conf.db.comm_list.j2` L9-22
- `sonic-routing-policy-sets.yang` COMMUNITY_SET_LIST

## フィールド別 暗黙デフォルト・挙動

### `set_type`

| 検出種類 | 詳細 | evidence |
|---|---|---|
| YANG default なし | YANG に `default` 文なし。省略時は null → `is_std = None` | sonic-routing-policy-sets.yang L145-151 |
| 必須フィールド扱い（複合） | `is_configurable()` = `match_action is not None AND is_std is not None AND len(mbr_list) > 0`。省略時は `is_configurable() == False` → FRR コマンド生成スキップ（サイレント） | frrcfgd.py L1580-1582 |
| 大文字小文字非感知 → 小文字変換 | `set_type` の値は `args[1][0][0].lower()` で小文字化して FRR コマンドに埋め込む。DB 格納値は `STANDARD`/`EXPANDED` (大文字) だが FRR へは `standard`/`expanded` (小文字) として送出 | frrcfgd.py L985 |
| YANG 実装 discrepancy なし | YANG enum は `STANDARD`/`EXPANDED`、実装も同様に判定。一致 | — |

### `match_action`

| 検出種類 | 詳細 | evidence |
|---|---|---|
| YANG default なし | YANG に `default` 文なし。省略時は `match_action = None` | sonic-routing-policy-sets.yang L153-159 |
| 必須フィールド扱い（複合） | `is_configurable()` 条件に含まれる。省略時は FRR コマンド生成スキップ（サイレント） | frrcfgd.py L1580-1582 |
| 大文字小文字非感知 → 小文字変換 | `db_data_to_attr` 内で `.lower()` 比較。`hdl_com_set` 内でも `.lower()` 変換後に FRR コマン生成 | frrcfgd.py L1588, L992 |
| **silent fallback**: 'all' 以外は全て MATCH_ANY 扱い | `db_data_to_attr` の分岐: `val.lower() == 'all'` → MATCH_ALL、それ以外 → MATCH_ANY。YANG enum 外の値（例: `ANY` 以外の文字列）を書いても MATCH_ANY として処理される | frrcfgd.py L1588-1591 |
| Jinja2 側は大文字小文字感知 | `bgpd.conf.db.comm_list.j2` は `cm_val['match_action']|lower` でフィルタしているが、frrcfgd 経由では Jinja2 テンプレートは使用されない（vtysh コマンド直接生成）。Jinja2 は別コードパス（起動時 bgpd.conf 生成）で使用 | bgpd.conf.db.comm_list.j2 L10, L16 |
| Jinja2 コードパス: 'all'/'any' 以外 → サイレントスキップ | `bgpd.conf.db.comm_list.j2` は `|lower == 'all'` / `|lower == 'any'` の 2 択。どちらにも入らない値はコマンド非生成 | bgpd.conf.db.comm_list.j2 L10-20 |

### `community_member`

| 検出種類 | 詳細 | evidence |
|---|---|---|
| YANG default なし | leaf-list に `default` なし。省略時は `mbr_list = []` | sonic-routing-policy-sets.yang L167-172 |
| 必須フィールド扱い（複合） | `len(mbr_list) > 0` が `is_configurable()` 条件。空リスト時は FRR コマンド生成スキップ | frrcfgd.py L1581 |
| **fallback: string → comma-split** | DB から string 型で来た場合 (leaf-list が単一値で格納された場合など) に `val.split(',')` でリスト化。list 型なら直接利用 | frrcfgd.py L1600-1603 |
| ordered-by user 維持 | YANG `ordered-by user` 宣言に対応。frrcfgd は受け取った順序でそのまま FRR コマンドに並べる（`match_action==all` 時は空白結合、`any` 時は個別コマンド） | sonic-routing-policy-sets.yang L169; frrcfgd.py L998, L1001-1006 |

### `action`

| 検出種類 | 詳細 | evidence |
|---|---|---|
| **dead field (実装上は完全無視)** | YANG に `action` フィールド (`permit`/`deny`) が定義されているが、`community_set_key_map` は `('set_type', 'match_action', 'community_member')` の 3 フィールドのみを抽出。`action` は key_map に含まれず、frrcfgd も `db_data_to_attr` でも処理しない | frrcfgd.py L1974, L1583-1603 |
| **ハードコード固定値: permit** | frrcfgd `hdl_com_set` および Jinja2 テンプレートは常に `permit` を FRR コマンドに埋め込む。DB の `action: deny` を設定しても `bgp community-list ... permit ...` が生成される | frrcfgd.py L998, L1005; bgpd.conf.db.comm_list.j2 L15, L18 |
| YANG-実装 discrepancy | YANG は `permit`/`deny` を enum で定義するが、実装は `permit` 固定。`deny` は機能しない | sonic-routing-policy-sets.yang L160-165; frrcfgd.py L998 |

### `name` (key)

| 検出種類 | 詳細 | evidence |
|---|---|---|
| 大文字小文字感知 | key はそのまま FRR community-list 名として使用される。大文字/小文字は FRR 側で区別される | frrcfgd.py L984, L986 |
| 空文字チェックなし | YANG は `type string` のみで min-length 制約なし | sonic-routing-policy-sets.yang L141-143 |

## 複合必須制約

`set_type` + `match_action` + `community_member` の 3 フィールドがすべて存在する場合のみ FRR コマンドが生成される。いずれか 1 つでも欠如するとサイレントスキップ。エラーログは出力されない。

- `hdl_com_set` L982: `0 not in args[1] or 1 not in args[1] or 2 not in args[1]` → `return None`
- Jinja2 テンプレート L9: `'set_type' in cm_val and 'match_action' in cm_val and 'community_member' in cm_val`

## FRR コマンド生成の前提条件依存

既存の community-list の削除（`no bgp community-list`）は `is_configurable()` が `True` の場合のみ実行される。これは CommunityList オブジェクトが `comm_set_list` に登録済みであり、かつ 3 フィールドが揃っている場合に限られる。フィールドが欠如した状態で DEL イベントを受けた場合、FRR 側の古い設定が残留する可能性がある（partial failure）。

- frrcfgd.py L989: `com_set_list[com_name].is_configurable()` チェック

## Jinja2 vs frrcfgd コードパスの乖離

起動時の `bgpd.conf` 生成 (Jinja2) とランタイムの設定変更 (frrcfgd vtysh) は別コードパス。  
Jinja2 は `match_action` の大文字小文字を `|lower` フィルタで正規化するが、`action` フィールドをそもそも参照しない点は同様。  
Jinja2 コードパスでは `EXPANDED`/`STANDARD` の `set_type` を `|lower` で小文字化した値を FRR コマンドに使う点もランタイムと一致。
