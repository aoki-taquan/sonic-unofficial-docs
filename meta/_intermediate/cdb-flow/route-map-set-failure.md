# route-map-set failure behavior — Phase D スキャン証跡

調査日: 2026-05-18
調査者: Claude (batch467)

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang` (L125-134, L269-273)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (全文 grep)
- `sonic-bgpcfgd/bgpcfgd/managers_static_rt.py` (全文 grep)

## 結論

ROUTE_MAP_SET テーブルには **購読デーモンが存在しない**。frrcfgd・bgpcfgd・orchagent のいずれも
ROUTE_MAP_SET を `table_handler_list` や `subscribe` に含まない。

このため「デーモンが書き込みを処理してエラーを返す」という形の失敗パスは存在しない。

## 失敗パターン

### 1. YANG 検証失敗（gNMI / NETCONF 経由）

sonic-yang-models の YANG モデル上、`ROUTE_MAP.call_route_map` は
`ROUTE_MAP_SET.name` への leafref である (`sonic-route-map.yang:271`)。

gNMI / NETCONF などの YANG 検証が有効なパスでは以下が失敗する:

| 操作 | 条件 | 失敗理由 |
|------|------|---------|
| ROUTE_MAP SET で `call_route_map` を指定 | 対応する ROUTE_MAP_SET エントリが未存在 | leafref 整合性違反 |
| ROUTE_MAP_SET エントリの DEL | ROUTE_MAP.call_route_map から参照中 | leafref 参照先削除による整合性違反 |
| ROUTE_MAP_SET エントリ作成 | key `name` が length 0 または制約違反 | YANG type validation 失敗 |

YANG の `ROUTE_MAP_SET_LIST` には `must`/`error-message` 句は存在しないため、
追加の制約違反メッセージはない (`sonic-route-map.yang:125-134`)。

### 2. sonic-db-cli 直接書き込み（YANG 検証バイパス）

`sonic-db-cli CONFIG_DB hset "ROUTE_MAP_SET|<name>" ...` では
YANG 検証は完全にバイパスされる。書き込みは常に成功し、
Redis に格納される。購読デーモンがないため副作用もない。

### 3. 存在しない ROUTE_MAP_SET を参照する ROUTE_MAP の FRR 反映

frrcfgd は ROUTE_MAP_SET エントリの存在を実行時にチェックしない。
`call_route_map` フィールドの値（name 文字列）をそのまま FRR vtysh の
`call <name>` コマンドに渡す (`frrcfgd.py:1942` 付近)。
FRR 側で対応する route-map が存在しない場合は FRR が `% Unknown command` 等で拒否するが、
frrcfgd はその結果を `LOG_ERR` で記録して `continue` する。

### 4. ステータス書き戻しなし

ROUTE_MAP_SET への SET/DEL 操作の成否は CONFIG_DB に書き戻されない。
YANG 検証エラーは gNMI/NETCONF のレスポンスで返されるのみ。

## grep 証拠

```
grep -n "ROUTE_MAP_SET" frrcfgd.py  → 0 ヒット
grep -n "ROUTE_MAP_SET" managers_static_rt.py → 0 ヒット
grep -n "must\|error-message" sonic-route-map.yang → ROUTE_MAP_SET ブロックに 0 ヒット
```
