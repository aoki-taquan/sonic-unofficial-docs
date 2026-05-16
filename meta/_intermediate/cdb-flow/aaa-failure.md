# AAA — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-aaa)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `key` が `authentication`/`authorization`/`accounting` 以外 | `aaa_update()` L419 | 内部状態更新なし・`modify_conf_file()` 呼び出しは実施 (設定ファイル変化なし) | なし | `hostcfgd:419-431` |
| `failthrough` に `'True'`/`'true'` 以外の文字列 (`'yes'`/`'1'` 等) | `is_true()` L156 | `False` 扱い・`syslog LOG_ERR` で "Failed to get bool value" 出力 | LOG_ERR | `hostcfgd:160-162` |
| `authentication.login` に `ldap` を含むが `bind_dn`/`bind_password`/`base_dn` のいずれかが空 | `is_ldap_config_complete()` L437 | `handle_nslcd_service(False)` → nslcd を stop & mask (LDAP 認証不能) | LOG_DEBUG ("nslcd: deactivating") | `hostcfgd:437-442, 246-251` |
| `authentication.login` に `ldap` を含むが `LDAP_SERVER` エントリなし | `is_ldap_config_complete()` L442 | `self.ldap_servers` が空 → `False` → nslcd を stop & mask | LOG_DEBUG | `hostcfgd:442` |
| PAM テンプレート (`common-auth-sonic.j2`) レンダリング中に `jinja2.TemplateError` など例外発生 | `modify_conf_file()` L716-731 | 例外がそのまま伝播 (catch なし) → `aaa_update()` が例外で中断 | スタックトレースが syslog へ (未捕捉) | `hostcfgd:716-731` |
| PAM 設定ファイル書き込み時 `open()` / `os.rename()` が `OSError` | `modify_conf_file()` L728-731 | 例外伝播・PAM ファイル未更新 (`.tmp` が残る場合あり) | スタックトレースが syslog へ (未捕捉) | `hostcfgd:728-731` |
| `aaastatsd` サービスの start/stop が `CalledProcessError` | `modify_conf_file()` L846-851 | `syslog LOG_ERR` のみ・処理継続 (NSLCD 設定へ進む) | LOG_ERR ("{cmd} - failed: return code...") | `hostcfgd:846-851` |
| NSLCD 設定ファイル生成 (`generate_file_from_template`) で例外 | `generate_file_from_template()` L214 | `syslog LOG_ERR` のみ・nslcd.conf 未更新 | LOG_ERR ("Failed generate_file_from_template error=...") | `hostcfgd:214-216` |
| LDAP conf ディレクトリ (`os.makedirs`) 作成失敗 | `modify_conf_file()` L860-862 | `syslog LOG_ERR` のみ・処理継続 (LDAP_CONF 生成試行は続く) | LOG_ERR ("Error occurred when using cmd makedirs...") | `hostcfgd:860-862` |
| `audisp-tacplus` への SIGHUP 送信失敗 (`os.kill` 例外) | `notify_audisp_tacplus_reload_config()` L490-493 | `syslog LOG_WARNING` のみ・処理継続 | LOG_WARNING | `hostcfgd:490-493` |
| `/etc/pam.d/sshd` や `/etc/pam.d/login` の `modify_single_file()` 中にファイル欠如 | `check_file_not_empty()` L619-620 | `syslog LOG_ERR` のみ・修正未適用 (sed 出力は空) | LOG_ERR ("file size check failed: {} is missing") | `hostcfgd:619-621` |
| nsswitch.conf (`NSS_CONF`) が存在しない | `modify_conf_file()` L755-783 | `os.path.isfile()` が False → sed 変更をスキップ (silent skip) | なし | `hostcfgd:756, 763-783` |
| `RADIUS_SERVER.src_intf` に対応する IP アドレスが解決できない場合 | `modify_conf_file()` L697-700 | `syslog LOG_INFO` → `server['src_ip']` を削除して RADIUS 設定を継続 | LOG_INFO ("src_intf has no usable IP addr.") | `hostcfgd:697-700` |
| `RADIUS_SERVER.src_intf` が存在するが `src_ip` も同時に設定されている場合 | `modify_conf_file()` L689-691 | `syslog LOG_INFO` → `src_intf` 優先・`src_ip` は無視して処理継続 | LOG_INFO ("src_intf found. Ignoring src_ip") | `hostcfgd:689-691` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `AAA` エントリの DEL (`data == {}`) | `aaa_update()` dispatch | key に対応する `self.authentication` / `self.authorization` / `self.accounting` は空の dict `{}` でなく default dict で初期化されているため、DEL 後は default に回帰 | なし | `hostcfgd:357-366, 641-648` |

### db_migrator における失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| migration 時 `TACPLUS|global.passkey` が空または未設定 | `migrate_aaa()` L869 | `AAA|authorization` エントリを**削除**。passkey 後追い設定後も自動復元されない | `db_migrator.py:869-900` |
| `AAA|authentication` が migration 元に存在しない | `migrate_aaa()` L869 | `None` を set → CONFIG_DB に `None` が書き込まれる可能性 (silent) | `db_migrator.py:875-877` |

### 検出ロジック補足

- **PAM 設定の atomic 書き込み**: `modify_conf_file()` は `.tmp` ファイルを経由して `os.rename()` で atomic に置換する。`os.rename()` が失敗した場合は `.tmp` ファイルが残存し PAM 設定は変化しない。
- **`is_ldap_config_complete()` の判定順序**: `ldap_global == {}` → `bind_dn` → `base_dn` → `bind_password` → `'ldap' in authentication.login` → `ldap_servers` の順で and チェーン。最初の falsy 値で短絡 → nslcd stop/mask。
- **`trace` フィールドの無効化**: `aaa_update()` に `trace` の更新ブロックがないため、CONFIG_DB の `trace=True` は `self.trace` (常に `False`) に反映されない。PAM テンプレートに `trace=False` が渡り、RADIUS `trace` オプションは機能しない (実装上のバグ)。
- **nslcd の自動復旧契機**: LDAP 設定が不完全で nslcd が mask された後、`ldap_global_update()` または `ldap_server_update()` が呼ばれると `handle_nslcd_service(is_ldap_config_complete())` が再評価され、完全になった時点で unmask & start される (`hostcfgd:547-564`)。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERR` (aaa 関連) | 5 | `hostcfgd:620, 625, 849, 862; generate_file_from_template:216` |
| `LOG_WARNING` | 1 | `hostcfgd:493` |
| `LOG_INFO` (src_intf) | 2 | `hostcfgd:691, 699` |
| `handle_nslcd_service(False)` | 2 | `hostcfgd:435 (aaa_update), 553 (ldap_global_update)` |
| `CalledProcessError` catch | 1 | `hostcfgd:848-851` |
| `generate_file_from_template` Exception catch | 1 | `hostcfgd:214-216` |
| `os.rename` (atomic PAM 書き込み) | 1 | `hostcfgd:731` |

<!-- /failure -->
