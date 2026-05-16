# ROUTE_MAP ハードコード定数分析 (Phase E)

生成日: 2026-05-16
対象ページ: `docs/reference/config-db/route-map.md`

## 分析ソース

| ファイル | パス |
|---------|------|
| managers_rm.py | `src/sonic-bgpcfgd/bgpcfgd/managers_rm.py` |

SHA: `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

## 検出定数一覧

### 1. 許可キー定数 (`ROUTE_MAPS` リスト)

`RouteMapMgr` が処理するキーは `managers_rm.py:5` の定数リストに固定列挙されている。これ以外のキーは `log_err` で拒否される。

| 定数名 | 値 | evidence |
|--------|-----|---------|
| `ROUTE_MAPS[0]` | `"FROM_SDN_SLB_ROUTES"` | `managers_rm.py:5` |
| `ROUTE_MAPS[1]` | `"FROM_SDN_APPLIANCE_ROUTES"` | `managers_rm.py:5` |

### 2. `FROM_SDN_SLB_DEPLOYMENT_ID` 定数

`__read_asn()` で参照される deployment ID。`constants["deployment_id_asn_map"]` から ASN を引く際のキーとして使用する。

| 定数名 | 値 | 型 | evidence |
|--------|-----|-----|---------|
| `FROM_SDN_SLB_DEPLOYMENT_ID` | `'2'` | str | `managers_rm.py:6` |

### 3. action enum (permit/deny)

`RouteMapMgr` が生成する FRR コマンドの action 値。`__update_rm()` / `__remove_rm()` でハードコードされる。

| FRR コマンド | action 値 | シーケンス番号 | evidence |
|-------------|----------|-------------|---------|
| `route-map <name>_RM permit 100` | `permit` | `100` | `managers_rm.py:87` |
| `no route-map <name>_RM permit 100` | `permit` | `100` | `managers_rm.py:41` |

> `deny` action は `RouteMapMgr` では一切生成されない。汎用 route-map（frr-mgmt-framework 経路）は YANG モデル `sonic-route-map.yang` の `route_operation` フィールド（`PERMIT` / `DENY`）を直接使用するが、`bgpcfgd` の `RouteMapMgr` は SDN ユースケース専用 2 キーのみを `permit 100` 固定で処理する。

### 4. シーケンス番号定数

| 値 | 用途 | evidence |
|----|------|---------|
| `100` | SDN route-map statement の固定シーケンス番号 | `managers_rm.py:41,87` |

### 5. FRR コマンド構成テンプレート (set 句)

`__update_rm()` が生成する FRR コマンド列（ハードコード部分）:

| FRR コマンド | ハードコード値 | 動的値 | evidence |
|------------|-------------|--------|---------|
| `route-map <rm_name> permit 100` | `permit 100` | `<rm_name>` = `<key>_RM` | `managers_rm.py:87` |
| ` set as-path prepend <asn> <asn>` | コマンド形式 | `<asn>` = constants から取得 | `managers_rm.py:92` |
| ` set community <community_id>` | コマンド形式 | `<community_id>` = data フィールド値 | `managers_rm.py:93` |
| ` set origin incomplete` | `incomplete` 固定 | — | `managers_rm.py:94` |

### 6. community_id バリデーション範囲

`__set_handler_validate()` で検証される community ID の値域:

| 検証対象 | 許容範囲 | evidence |
|---------|---------|---------|
| community_id 形式 | `<A>:<B>` (コロン区切り 2 要素) | `managers_rm.py:56-57` |
| `<A>` (左辺) | `0` 〜 `65535` | `managers_rm.py:58` |
| `<B>` (右辺) | `0` 〜 `65535` | `managers_rm.py:59` |

### 7. 名前生成テンプレート

`RouteMapMgr` が参照する route-map 名のサフィックスルール:

| テンプレート | 生成例 | evidence |
|-----------|--------|---------|
| `<key>_RM` | `FROM_SDN_SLB_ROUTES_RM`, `FROM_SDN_APPLIANCE_ROUTES_RM` | `managers_rm.py:41,87,92,95` |

### 8. constants 依存キー

`__read_asn()` が参照する `self.constants` のキー:

| 定数キー | 型 | 必須 | evidence |
|---------|-----|------|---------|
| `deployment_id_asn_map` | dict | yes | `managers_rm.py:76` |
| `deployment_id_asn_map["2"]` | str / int | yes (for SDN SLB) | `managers_rm.py:79` |

## 非検出事項

- `managers_rm.py` は `BGPAllowListMgr` とは別実装であり、`ROUTE_MAP_ENTRY_WITH_COMMUNITY_START/END` 等の allow-list 用シーケンス番号定数は利用しない。
- `match_*` / `set_*` フィールド群（YANG モデル経由の汎用 route-map）の処理は `frr-mgmt-framework` / `frrcfgd` が担い、`bgpcfgd` の `RouteMapMgr` は関与しない。
- `priority range` (1〜65535) は YANG モデル `sonic-route-map.yang` の `<stmt_name>` (uint16) として定義されるが、`managers_rm.py` は stmt_name を参照せずシーケンス番号 `100` を固定使用する。
