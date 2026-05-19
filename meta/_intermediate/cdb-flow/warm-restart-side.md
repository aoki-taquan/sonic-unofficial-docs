# warm-restart — Phase F side-effects スキャンノート

## 調査対象

- CONFIG_DB テーブル: `WARM_RESTART`
- 主要ソース:
  - `sonic-swss-common/common/warm_restart.cpp`
  - `sonic-swss/orchagent/orchdaemon.cpp`
  - `sonic-swss/cfgmgr/vlanmgr.cpp`, `intfmgr.cpp`, `vrfmgrdyn.cpp`, `tunnelmgr.cpp`, `buffermgrdyn.cpp`
  - `sonic-swss/fpmsyncd/bgp_eoiu_marker.py`
  - `sonic-buildimage/files/image_config/warmboot-finalizer/finalize-warmboot.sh`

## STATE_DB 書き込み

### `WARM_RESTART_TABLE` (STATE_DB)

`WarmStart::checkWarmStart()` (warm_restart.cpp:86-147):
- cold start 判定時: `hset(app_name, "restore_count", "0")` — L113
- restore_count 未存在 + warm start: フォールバック `hset(app_name, "restore_count", "0")` — L125
- warm start 確認済み: `restore_count++` → `hset(app_name, "restore_count", to_string(restore_count))` — L133

`WarmStart::setWarmStartState()` (warm_restart.cpp:227):
- `hset(app_name, "state", <state_str>)` で状態遷移を記録
- state 文字列マッピング (warm_restart.cpp:11-14):
  - `INITIALIZED` → `"initialized"`
  - `REPLAYED` → `"replayed"`
  - `RECONCILED` → `"reconciled"`
  - `WSDISABLED` → `"wsdisabled"`

`WarmStart::setDataCheckState()` (warm_restart.cpp:237-249):
- `hset(app_name, <field>, <state>)` で data check 結果を記録

### `BGP_STATE_TABLE` (STATE_DB)

`bgp_eoiu_marker.py` (sonic-swss/fpmsyncd/bgp_eoiu_marker.py):
- BGP EOR (End-of-Route) 収集後に `STATE_DB:BGP_STATE_TABLE|<AF>|eoiu` に `state` / `timestamp` を SET (L85-87)
- cleanup 時に IPv4/IPv6 eoiu キーを DEL (L94-95)
- このプロセスは supervisord.conf.j2:239 で `bgp_eoiu=true` の場合のみ登録される

## プロセス別 STATE_DB 書き込みタイミング

| プロセス | setWarmStartState 呼び出し | ファイル | 行 |
|---|---|---|---|
| orchagent | INITIALIZED | orchdaemon.cpp | 1099 |
| orchagent | RECONCILED | orchdaemon.cpp | 1170 |
| orchagent | RESTORED | orchdaemon.cpp | 1204 |
| intfmgrd | REPLAYED, RECONCILED | intfmgr.cpp | 289, 292 |
| vlanmgrd | REPLAYED, RECONCILED | vlanmgr.cpp | 59, 61 |
| vrfmgrd | REPLAYED, RECONCILED | vrfmgrdyn.cpp | 74, 77 |
| tunnelmgrd | REPLAYED, RECONCILED | tunnelmgr.cpp | 423, 425 |
| buffermgrd | INITIALIZED, WSDISABLED | buffermgrdyn.cpp | 165, 170 |

## CONFIG_DB 書き戻し

`finalize-warmboot.sh:175`:
```bash
sonic-db-cli -n "$NETNS" CONFIG_DB DEL "WARM_RESTART|teamd"
```
fast-reboot 完了時のみ実行。teamsyncd_timer エントリを削除する副作用。

## APPL_DB / ERROR_TABLE

- APPL_DB: 書き込みなし（CONFIG_DB → 各プロセス直接読み取り経路）
- ERROR_TABLE: 書き込みなし
- ASIC_DB: syncd_apply_view() 経由で間接更新のみ（WARM_RESTART テーブル直接起因ではない）
