# RADIUS — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (chore/q67-f-batch923)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `RADIUS\|<key>` で `key != 'global'` | `radius_global_update()` L528 | 内部状態更新なし・`modify_conf_file()` 呼び出しもスキップ (silent skip) | なし | `hostcfgd:527-533` |
| `statistics` に `is_true()` が失敗する値（`True/true/yes/1` 以外） | `is_true()` L156 | `False` 扱い・`syslog LOG_ERR` で "Failed to get bool value" 出力 | LOG_ERR | `hostcfgd:156-162, 531` |
| `src_intf` に対応する IP アドレスが解決できない | `modify_conf_file()` L697-700 | `syslog LOG_INFO` → `server['src_ip']` を削除して `pam_radius_auth.conf` 生成を継続 (`src_ip` 行省略) | LOG_INFO ("src_intf has no usable IP addr.") | `hostcfgd:695-700` |
| `src_intf` と `src_ip` が両方指定されている | `modify_conf_file()` L689-691 | `syslog LOG_INFO` → `src_intf` 優先で IP 解決・`src_ip` を無視して処理継続 | LOG_INFO ("src_intf found. Ignoring src_ip") | `hostcfgd:687-696` |
| Jinja2 テンプレート (`pam-auth-sonic.j2`) レンダリング中に例外発生 | `modify_conf_file()` L716-731 | 例外がそのまま伝播 (catch なし) → `modify_conf_file()` が中断・PAM 設定ファイル未更新 | スタックトレースが syslog へ (未捕捉) | `hostcfgd:716-731` |
| PAM 設定ファイル (`common-auth-sonic`) の `open()` / `os.rename()` が `OSError` | `modify_conf_file()` L728-731 | 例外伝播・ファイル未更新 (`.tmp` ファイルが残存する場合あり) | スタックトレースが syslog へ (未捕捉) | `hostcfgd:728-731` |
| NSS RADIUS 設定ファイル (`/etc/radius_nss.conf`) の `open()` が `OSError` | `modify_conf_file()` L822 | 例外伝播 (catch なし)・`radius_nss.conf` 未更新 | スタックトレースが syslog へ (未捕捉) | `hostcfgd:820-823` |
| `pam_radius_auth.conf` ディレクトリ配下のファイル書き込みに失敗 | `modify_conf_file()` L834-837 | 例外伝播 (catch なし)・per-server PAM conf 未更新 | スタックトレースが syslog へ (未捕捉) | `hostcfgd:826-837` |
| `aaastatsd` サービスの start/stop が `CalledProcessError` | `modify_conf_file()` L846-851 | `syslog LOG_ERR` のみ・処理継続 (NSLCD 設定へ進む) | LOG_ERR ("{cmd} - failed: return code - {}, output:...") | `hostcfgd:846-851` |
| `nas_ip` 未指定かつ `eth0` に IP がない (`get_interface_ip("eth0")` が空) | `modify_conf_file()` L672-674 | `nas_ip` キーが `radius_global` に追加されず・PAM 設定の `nas_ip` 行が省略される | なし (silent) | `hostcfgd:671-674` |
| `nas_id` 未指定かつ `get_hostname()` が空文字を返す | `modify_conf_file()` L675-678 | `nas_id` キーが `radius_global` に追加されず・PAM 設定の `nas_id` 行が省略される | なし (silent) | `hostcfgd:675-678` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `RADIUS\|global` の DEL (`data == {}`) | `radius_global_update()` L527-533 → `radius_server_update()` L536 | `self.radius_global` が空 dict `{}` にリセットされ `radius_global_default` のみが有効に。`modify_conf_file()` が呼ばれ PAM 設定がデフォルト状態に再生成される | なし | `hostcfgd:527-533` |
| `RADIUS_SERVER\|<addr>` の DEL で `data == {}` | `radius_server_update()` L536-538 | `self.radius_servers` から当該エントリを削除。`modify_conf_file()` が呼ばれ `pam_radius_auth.d/<addr>_*.conf` は残存するが NSS / PAM 設定からは除外される | なし | `hostcfgd:535-545` |

### 検出ロジック補足

- **key バリデーションは `if key == 'global'` のみ**: `radius_global_update()` はキーを `'global'` とのみ比較し、それ以外は関数本体をスキップする。ログ出力も例外送出もなく silent drop となる (evidence: `hostcfgd:527-528`)。
- **PAM 設定の atomic 書き込み**: `modify_conf_file()` は `.tmp` ファイルを経由して `os.rename()` で atomic に置換する。`os.rename()` が失敗した場合は `.tmp` ファイルが残存し PAM 設定は変化しない。
- **per-server conf ファイルの残留**: `RADIUS_SERVER` エントリが DEL されても `/etc/pam_radius_auth.d/<ip>_<port>.conf` は削除されない (`modify_conf_file()` は既存ファイルを上書きまたは新規作成するが古いファイルを消さない)。残留ファイルは `pam_radius` が直接参照しないため通常は無害だが、IP 再利用時に混乱する可能性がある。
- **`statistics` の self-heal**: `radius_global_update()` で `statistics` が不正値だった場合でも `modify_conf_file()` は呼び出されるため、PAM 設定は `statistics=False` として生成される。`aaastatsd` は stop されるだけで設定破損には至らない。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `radius_global_update()` 内 silent skip | 1 | `hostcfgd:527-528 (key != 'global')` |
| `LOG_ERR` (aaastatsd) | 1 | `hostcfgd:849-851` |
| `LOG_INFO` (src_intf 系) | 2 | `hostcfgd:690-691, 698-699` |
| 例外非捕捉 (PAM/NSS ファイル I/O) | 3 | `hostcfgd:728-731 (PAM), 822-823 (NSS), 834-837 (per-server)` |

<!-- /failure -->
