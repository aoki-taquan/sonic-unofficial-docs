# PASSW_HARDENING — Phase H プラットフォーム差調査

調査対象: `sonic-host-services/scripts/hostcfgd`

## スキャン結果

`hostcfgd` 全体で `getenv("platform")`、`gMySwitchType`、`switch_type`、`mellanox`、`multi_asic`、`chassis` 等のプラットフォーム条件分岐を検索した結果、`PasswHardening` クラスおよびその呼び出しチェーン内に**プラットフォーム依存コードは存在しない**。

## 根拠

- `PasswHardening.__init__()`: `hostcfgd:874-878` — プラットフォーム参照なし
- `PasswHardening.load()`: `hostcfgd:881-885` — プラットフォーム参照なし
- `passw_policies_update()`: `hostcfgd:887-912` — `key == 'POLICIES'` のみで判定
- `set_passw_hardening_policies()`: `hostcfgd:912-958` — PAM テンプレートと `/etc/login.defs` の書き換えのみ
- `modify_passw_conf_file()`: `hostcfgd:1038-1043` — Jinja2 展開のみ
- `HostConfigDaemon.load()`: `hostcfgd:2232-2280` — `PASSW_HARDENING` 取り込みにプラットフォーム条件なし
- `register_callbacks()`: `hostcfgd:2456-2489` — `subscribe('PASSW_HARDENING', ...)` 登録にプラットフォーム条件なし

## 結論

`PASSW_HARDENING` の処理は Linux PAM および `/etc/login.defs` ファイル操作のみであり、
ASIC 種別・switch_type・multi-asic 構成・chassis 構成に一切依存しない。
全プラットフォームで同一挙動となる。
