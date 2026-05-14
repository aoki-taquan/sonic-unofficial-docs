# ROUTE_MAP — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`bgpcfgd` の `RouteMapMgr` が `ROUTE_MAP` テーブルを読み、FRR の `route-map` 設定コマンドを生成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| FRR `route-map permit/deny` | `route_map_entry.action` | `permit` または `deny` | `managers_route_map.py` |
| FRR `match` 句 | `MATCH_PREFIX_LIST` / `MATCH_AS_PATH` 等のフィールド | 対応する FRR `match` コマンド | `managers_route_map.py` |
| FRR `set` 句 | `SET_COMMUNITY` / `SET_LOCAL_PREF` 等のフィールド | 対応する FRR `set` コマンド | `managers_route_map.py` |

**CONFIG_DB 内フィールド間の自動付与なし**: すべてのフィールドは FRR テキストコマンドへの変換のみ。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `bgpcfgd` は常時起動 | `RouteMapMgr` は無条件登録 | `bgpcfgd/main.py` |
| 参照する `PREFIX_LIST` / `AS_PATH_SET` / `COMMUNITY_SET` が未設定 | FRR コマンドは発行されるが、FRR 側で未解決参照エラー | FRR vtysh |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `RouteMapMgr` | `action==permit` | `route-map <name> permit <seq>` | `managers_route_map.py` |
| `RouteMapMgr` | `action==deny` | `route-map <name> deny <seq>` | `managers_route_map.py` |
| `RouteMapMgr` | `MATCH_PREFIX_LIST` フィールドあり | `match ip address prefix-list <list>` 追加 | `managers_route_map.py` |
| `RouteMapMgr` | `MATCH_AS_PATH` フィールドあり | `match as-path <list>` 追加 | `managers_route_map.py` |
| `RouteMapMgr` | `SET_COMMUNITY` フィールドあり | `set community <value>` 追加 | `managers_route_map.py` |
| `RouteMapMgr` | del_handler | FRR に `no route-map <name>` 発行 | `managers_route_map.py` |

> **スキャン証跡**: `ROUTE_MAP` は BGP ルーティングポリシーの中核。bgpcfgd が FRR vtysh に変換。CONFIG_DB 内フィールド間の自動派生なし。
