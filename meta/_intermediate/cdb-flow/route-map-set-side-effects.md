# ROUTE_MAP_SET — Phase F 副次 DB 書込スキャン

## 調査概要

- **対象テーブル**: `ROUTE_MAP_SET`
- **フェーズ**: F (side-effects)
- **調査日**: 2026-05-19
- **ソース**: `sonic-net/sonic-buildimage` ref `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

## frrcfgd 購読確認

`frrcfgd.py` の `table_handler_list` および `tbl_to_key_map` を全行 grep した結果、
`ROUTE_MAP_SET` の出現は 0 件であった。

したがって frrcfgd が `ROUTE_MAP_SET` エントリを処理して何らかの DB 書込を副次的に行うことは
構造的に不可能である。

## bgpcfgd 購読確認

`bgpcfgd` ソース（`src/sonic-bgpcfgd/`）を `ROUTE_MAP_SET` で grep した結果、出現 0 件。
bgpcfgd は ROUTE_MAP_SET を購読しない。

## orchagent 購読確認

`orchagent` ソース（`src/sonic-swss/orchagent/`）を `ROUTE_MAP_SET` で grep した結果、出現 0 件。
ACL / routing orch は ROUTE_MAP_SET テーブルを一切処理しない。

## 副次 DB 書込マトリクス

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | frrcfgd / bgpcfgd が ROUTE_MAP_SET を購読しないため、AppDB への転送は発生しない |
| STATE_DB | なし | ROUTE_MAP_SET の処理コードが存在せず、STATE_DB への status 書戻しも存在しない |
| COUNTERS_DB | なし | routing エントリのためのカウンタテーブルは存在しない |
| ASIC_DB | なし | SAI 経路を経由しない（orchagent が購読しないため） |
| FLEX_COUNTER_DB | なし | カウンタ設定対象外 |
| LOGLEVEL_DB | なし | ROUTE_MAP_SET 処理コードが存在しないため |

## gNMI / NETCONF パス

gNMI / NETCONF 経由で YANG 検証が有効な場合、leafref 整合性エラーは
gNMI レスポンス（`google.rpc.Status`）として返されるが、
これは DB 書込ではなく RPC 応答レベルの副作用である。
CONFIG_DB / 他 DB への書込は発生しない。

## 結論

`ROUTE_MAP_SET` テーブルへの SET / DEL に伴う**副次 DB 書込は存在しない**。
副作用は YANG leafref 整合性検証（gNMI / NETCONF パスのみ）の
RPC レスポンスへの影響に限定される。
