# STATE_DB BGP 関連テーブル 副次 DB 書込スキャン (Phase F)

`docs/reference/config-db/state-bgp.md` の Phase F (副次 DB 書込) ブロック裏付け資料。

対象テーブル: `BGP_STATE_TABLE` / `BGP_PEER_CONFIGURED_TABLE` (STATE_DB), `BGP_NEIGHBOR_TABLE` / `BGP_RIB_IN_TABLE` / `BGP_RIB_OUT_TABLE` (BMP_STATE_DB)

## スキャン手順

```bash
# fpmsyncd が BGP_STATE_TABLE を読んだあとに APPL_DB 等へ何を書くか確認
grep -n "onWarmStartEnd\|reconcile\|ROUTE_TABLE\|APPL_STATE" \
    .cache/sonic-sources/sonic-swss/fpmsyncd/routesync.cpp

# bgpcfgd が BGP_PEER_CONFIGURED_TABLE を書いた後の副次操作
grep -n "STATE_DB\|APPL_DB\|COUNTERS\|notify" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py

# bmpcfgd が BMP_STATE_DB をリセットする際の副次書込
grep -n "delete_all\|set\|COUNTERS\|STATE_DB\|APPL_DB" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py

# config bgp コマンドで BGP_PEER_CONFIGURED_TABLE を全削除するコード
grep -n "BGP_PEER_CONFIGURED_TABLE" \
    .cache/sonic-sources/sonic-utilities/config/main.py
```

## 検出された副次書込

### 1. BGP_STATE_TABLE EOIU 到達 → APPL_DB ROUTE_TABLE (reconciliation)

`fpmsyncd` が `BGP_STATE_TABLE|{IPv4,IPv6}|eoiu` の `state=reached` を確認し EOIU hold timer 終了後、または warm-restart タイマー終了後に `RouteSync::onWarmStartEnd()` を呼ぶ。この中で `m_warmStartHelper.reconcile()` が実行され、待機中の BGP ルートが `APPL_DB ROUTE_TABLE` / `APP_LABEL_ROUTE_TABLE` へ書き込まれる。

| トリガ | 操作 | 対象 DB / テーブル | evidence |
|--------|------|------------------|---------|
| `BGP_STATE_TABLE\|IPv4\|eoiu` / `\|IPv6\|eoiu` の state が `"reached"` かつ EOIU hold timer 満了 | `m_warmStartHelper.reconcile()` → APPL_DB への ProducerStateTable SET | `APPL_DB ROUTE_TABLE` / `APP_LABEL_ROUTE_TABLE` | `fpmsyncd/fpmsyncd.cpp` L201, L212; `routesync.cpp` L3298-3312 |
| Warm restart タイマー (`DEFAULT_ROUTING_RESTART_INTERVAL=120s`) 先行満了時 | 上記と同 path | 同上 | `fpmsyncd.cpp` L196-213 |

`BGP_STATE_TABLE` 自体は読み取られるだけで他の DB への直接的な副次書込はない。副次書込はすべて warm-restart reconciliation の結果として `APPL_DB` に対して発生する。

### 2. BGP_PEER_CONFIGURED_TABLE — 副次書込なし

`bgpcfgd` の `update_state_db()` は `BGP_PEER_CONFIGURED_TABLE` への SET / DEL のみ行い、他 DB への書込は発生しない。

| DB | 副次書込 | 根拠 |
|----|---------|------|
| `APPL_DB` | なし | `managers_bgp.py:271-295` に APPL_DB 操作なし |
| `COUNTERS_DB` | なし | managers_bgp.py 全体に `COUNTERS` 参照なし |
| `ASIC_DB` | なし | bgpcfgd は ASIC_DB を直接操作しない |

`config bgp remove neighbor <peer>` 実行時に sonic-utilities が `delete_all_by_pattern(STATE_DB, "BGP_PEER_CONFIGURED_TABLE|*")` を呼ぶが (config/main.py:1613)、これは BGP_PEER_CONFIGURED_TABLE 内のクリアであり他 DB への副次書込ではない。

### 3. BMP_STATE_DB テーブル (BGP_NEIGHBOR_TABLE / BGP_RIB_IN_TABLE / BGP_RIB_OUT_TABLE) — 副次書込なし

BMP_STATE_DB テーブル自体への書込は `openbmpd` (FRR bgpd の BMP ソケット経由) が直接行う。これらのテーブルが他の DB へ副次書込をトリガーする経路はなく、BMP_STATE_DB テーブルは**完全に読み取り専用の観測データ**として機能する。

`bmpcfgd` の `reset_bmp_table()` は CONFIG_DB `BMP` テーブル変更時に `BMP_STATE_DB` の全テーブルを `delete_all_by_pattern` でクリアするが (bmpcfgd.py:61-65)、他 DB への書込は発生しない。

## まとめ — Phase F 記載対象

| カテゴリ | 副次書込先 | 条件 |
|---------|-----------|------|
| BGP_STATE_TABLE → APPL_DB | `ROUTE_TABLE` / `APP_LABEL_ROUTE_TABLE` | Warm Restart 時のみ。EOIU 到達 or タイマー満了で reconciliation トリガー |
| BGP_PEER_CONFIGURED_TABLE | なし | 副次書込なし |
| BMP_STATE_DB テーブル | なし | 副次書込なし。観測専用テーブル |
