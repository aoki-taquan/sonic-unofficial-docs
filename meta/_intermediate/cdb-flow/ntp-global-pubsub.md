# NTP_GLOBAL — Phase G: 通信メカニズム (pubsub) スキャンノート

対象ページ: `docs/reference/config-db/ntp-global.md`
ソース参照: `meta/_intermediate/cdb-flow/ntp-pubsub.md`

---

## CONFIG_DB Subscribe 登録

| 購読テーブル | ハンドラ | 発行コマンド | evidence |
|------------|---------|------------|----------|
| `NTP` (`CFG_NTP_GLOBAL_TABLE_NAME`) | `ntp_global_handler` → `ntp_global_update()` | `systemctl restart chrony` | `hostcfgd:2511-2513` |
| `NTP_SERVER` | `ntp_srv_key_handler` → `ntp_srv_key_update()` | `systemctl restart chrony` | `hostcfgd:2514-2516` |
| `NTP_KEY` | `ntp_srv_key_handler` → `ntp_srv_key_update()` | `systemctl restart chrony` | `hostcfgd:2517` |
| `LOOPBACK_INTERFACE` | `lpbk_handler` → `handle_ntp_source_intf_chg()` | `systemctl restart chrony` (src_intf 一致時のみ) | `hostcfgd:2483` |

NTP_SERVER / NTP_KEY は共通ハンドラに集約。SIGHUP によるホットリロードは採用されない。

## 差分チェック

- `ntp_global_update`: `cache.get('global', {}) == data` の場合 no-op
- `ntp_srv_key_update`: servers/keys 双方一致なら no-op
- `handle_ntp_source_intf_chg`: 差分チェックなし

## 初期化パス

`config_db.listen(init_data_handler=self.load)` — ループ開始前に全スナップショットを一括取得 (`hostcfgd:2527-2528`)

## evidence

- `sonic-host-services/scripts/hostcfgd` L111-112,1280,1312-1329,1331-1406,2387-2391,2483,2511-2528
