# ROUTE_MAP_SET — Phase G pubsub 調査証跡

## 調査日
2026-05-19

## 調査対象
- `sonic-net/sonic-buildimage`: `src/sonic-frr/patch/`、`sonic/frrcfgd/frrcfgd.py`
- `sonic-net/sonic-buildimage`: `src/sonic-bgpcfgd/bgpcfgd/`
- `sonic-net/sonic-swss`: `orchagent/` (全 grep)

## 結論
`ROUTE_MAP_SET` テーブルを購読するデーモンは **存在しない**。

## 証拠

### frrcfgd.py
`table_handler_list` (L2293-2338) を全文 grep した結果、`ROUTE_MAP_SET` の出現なし。
登録されているのは `ROUTE_MAP`（`bgp_table_handler_common`）のみ。

```python
# frrcfgd.py L2302 (ROUTE_MAP のみ登録)
('ROUTE_MAP', self.bgp_table_handler_common),
# 'ROUTE_MAP_SET' は table_handler_list に存在しない
```

`ExtConfigDBConnector.subscribe()` は `table_handler_list` に登録されたテーブルのみを Redis keyspace 通知で監視する。`ROUTE_MAP_SET` は登録されないため、通知は届かない。

### bgpcfgd
`bgpcfgd/` ディレクトリ全文 grep で `ROUTE_MAP_SET` 出現なし。`bgpcfgd` は `ROUTE_MAP` テーブルも直接購読せず、テンプレートエンジン経由で参照するが、`ROUTE_MAP_SET` については完全に無視。

### orchagent
`orchagent/` 全文 grep で `ROUTE_MAP_SET` 出現なし。ルーティングポリシーは FRR 側で処理され、SAI 経路では処理されない。

## 購読メカニズムの不在理由
`ROUTE_MAP_SET` は YANG leafref 整合性検証のための「名前レジストリ」として設計されており、FRR や SAI への直接的な設定投入は意図されていない。実際の route-map 設定は `ROUTE_MAP|<name>|<seq>` テーブルが担う。

## Redis Pub/Sub イベントの扱い
CONFIG_DB への `ROUTE_MAP_SET` SET/DEL 操作は Redis keyspace 通知 (`__keyspace@4__:ROUTE_MAP_SET|*`) を発行するが、購読者がいないためイベントは消費されない。
