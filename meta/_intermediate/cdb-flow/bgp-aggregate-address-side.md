# BGP_AGGREGATE_ADDRESS — 副次 DB 書込スキャン (Task F Phase F)

> 対象ページ: `docs/reference/config-db/bgp-aggregate-address.md`
> 対象ソース: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py`,
> `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
> 調査日: 2026-05-16

## 結論サマリ

`BGP_AGGREGATE_ADDRESS` テーブルの set/del を契機に bgpcfgd
(`AggregateAddressMgr`) が行う副次 DB 書込は **STATE_DB
`BGP_AGGREGATE_ADDRESS|<prefix>` の `state` フィールドのみ**。
COUNTERS_DB / APPL_STATE_DB / ASIC_DB への副次書込は無く、それ以外の経路
反映は FRR vtysh push (BGP RIB → APPL_DB `ROUTE_TABLE` 経由) に閉じる。

## 副次 DB 走査結果

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| STATE_DB | あり | `AggregateAddressMgr.__init__` で `state_db_connector` から `BGP_AGGREGATE_ADDRESS` テーブルをオープン (`managers_aggregate_address.py:42-44`)。`set_address_state()` (L209-216) が `state=active|inactive` を書込み。`set_handler` / `del_handler` / `on_bbr_change` / `address_set_handler` の各成功・失敗パスから呼ばれる |
| COUNTERS_DB | なし | `managers_aggregate_address.py` / `frrcfgd.py` どちらにも `COUNTERS_DB` / `FlexCounter` 参照なし。BGP 集約はカウンタ統合対象外 |
| APPL_STATE_DB | なし | 両ファイルに `APPL_STATE_DB` / `APP_STATE_DB` 参照なし。FRR が APPL_DB `ROUTE_TABLE` に集約ルートを注入する経路は `RouteOrch` 配下で扱われ、`BGP_AGGREGATE_ADDRESS` の handler からは独立 |
| ASIC_DB | なし (間接のみ) | bgpcfgd は SAI を直接触らない。FRR `bgpd` → APPL_DB `ROUTE_TABLE` → `RouteOrch` → `sairedis` 経路で ASIC_DB に達するが、これは `ROUTE_TABLE` の副作用であり `BGP_AGGREGATE_ADDRESS` の handler 由来ではない |
| ERROR_TABLE | なし | `failure.md` 既調査どおり ERROR_TABLE 書込は実装されていない |

## STATE_DB 書込の発火点

| 発火点 | 書込値 | コード根拠 |
|---|---|---|
| `AggregateAddressMgr.__init__` 末尾 (起動時) | 全 `BGP_AGGREGATE_ADDRESS|*` を delete (`remove_all_state_of_address`) | `managers_aggregate_address.py:42-44, 203-207` |
| `set_handler` 内 prefix 不正 | `state=inactive` | L65-72 |
| `set_handler` 内 `bbr-required=true` かつ BBR `disabled` / 不明 | `state=inactive` | L78-83 |
| `address_set_handler` 成功時 (FRR push の結果未検証) | `state=active` | L85 |
| `del_handler` 内 `state=inactive` の場合 | テーブル row 削除のみ (FRR no コマンドはスキップ) | L138-146 |
| `on_bbr_change` (`enabled`→`disabled`) | 走査対象を `state=inactive` に再設定 | L57-61 |

## frrcfgd 経路 (BGP_GLOBALS_AF_AGGREGATE_ADDR)

`frr-mgmt-framework` (`frrcfgd.py`) が処理する代替テーブル
`BGP_GLOBALS_AF_AGGREGATE_ADDR` も同様に副次 DB 書込を持たない。

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| STATE_DB | なし | `frrcfgd.py` の aggregate-address 経路 (L1982-1983, L2658-2676) は vtysh push のみ。STATE_DB connector への書込呼び出しなし |
| COUNTERS_DB | なし | カウンタ統合なし |
| APPL_STATE_DB | なし | 該当参照なし |

bgpcfgd 経路と frrcfgd 経路で STATE_DB ミラーの有無が**非対称**である
点に注意 (本ページ対象は bgpcfgd 経路)。

## 検証手段

```bash
# STATE_DB 反映確認
sonic-db-cli STATE_DB keys 'BGP_AGGREGATE_ADDRESS|*'
sonic-db-cli STATE_DB hgetall 'BGP_AGGREGATE_ADDRESS|10.0.0.0/24'

# COUNTERS_DB に該当キーが無いこと
sonic-db-cli COUNTERS_DB keys '*AGGREGATE*'
```
