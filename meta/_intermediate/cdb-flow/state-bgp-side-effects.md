# state-bgp Phase F 調査メモ — 副次 DB 書込

## 調査対象

`STATE_DB BGP_STATE_TABLE` / `STATE_DB BGP_PEER_CONFIGURED_TABLE` / `BMP_STATE_DB BGP_NEIGHBOR_TABLE` / `BMP_STATE_DB BGP_RIB_IN_TABLE` / `BMP_STATE_DB BGP_RIB_OUT_TABLE`

## BGP_STATE_TABLE の副次効果

### fpmsyncd の EOIU ポーリングと RIB reconciliation

- `fpmsyncd.cpp` L54–70: `eoiuFlagsSet()` が `BGP_STATE_TABLE|IPv4|eoiu` と `IPv6|eoiu` を `hget` でポーリング
- L219–239: 両方が `"reached"` になると `DEFAULT_EOIU_HOLD_INTERVAL`（3 秒）の hold timer を開始
- L201–218: hold timer 満了 or warm_restart タイマー（120 秒）満了で `WarmStartHelper::runRestoration()` を呼び出し → APPL_DB `ROUTE_TABLE` の reconciliation
- routesync.cpp L162: `m_warmStartHelper(pipeline, m_routeTable.get(), APP_ROUTE_TABLE_NAME, "bgp", "bgp")` — ルートテーブルを reconciliation 対象として登録

### APPL_DB ROUTE_TABLE への経路再投入

- fpmsyncd.cpp L320: reconciliation 完了後 (`isReconciled()` = true) に通常のルート受信処理が再開
- routesync.cpp L1433: `/* Write route to ROUTE_TABLE */` — FRR からの経路を APPL_DB ROUTE_TABLE へ書き込む
- routesync.cpp L156–158: ROUTE_TABLE と LABEL_ROUTE_TABLE が対象

## BGP_PEER_CONFIGURED_TABLE の副次効果

- managers_bgp.py の `update_state_db()` L277–297: STATE_DB への書込みのみ、APPL_DB / ASIC_DB への書込みなし
- `apply_op()` L494–508 は FRR vtysh へのコマンドキューへの追加のみ
- sonic-utilities/config/main.py L1613: `delete_all_by_pattern` による全削除は State_DB 限定

## BMP テーブルの副次効果

- bmpcfgd.py L64–65: `delete_all_by_pattern(BMP_STATE_DB, 'BGP_RIB_IN_TABLE*')` 等 — BMP_STATE_DB 内部のみ
- openbmpd は BMP_STATE_DB にのみ書き込む（APPL_DB / COUNTERS_DB / FLEX_COUNTER_DB への書込みなし）

## 結論

| テーブル | 副次 DB 書込 | 詳細 |
|---------|------------|------|
| BGP_STATE_TABLE | APPL_DB / ROUTE_TABLE (間接) | `"reached"` → fpmsyncd reconciliation → ROUTE_TABLE 再投入 |
| BGP_PEER_CONFIGURED_TABLE | なし | STATE_DB 書込みのみ、他 DB 非経由 |
| BGP_NEIGHBOR_TABLE | なし | 読み取り専用（show bmp コマンド） |
| BGP_RIB_IN_TABLE | なし | 読み取り専用 |
| BGP_RIB_OUT_TABLE | なし | 読み取り専用 |
