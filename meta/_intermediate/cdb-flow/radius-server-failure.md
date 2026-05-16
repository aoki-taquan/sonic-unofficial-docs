# RADIUS_SERVER — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-radius-server)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-host-services/scripts/hostcfgd`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `priority` に YANG 範囲外の値 (0 または 65+) が直接 DB 書き込みされた場合 | `modify_conf_file()` L703 `int(t['priority'])` | `int()` 変換は成功するが YANG バリデーションをバイパス。priority=0 は降順ソートで最低優先度になる。priority が文字列でない場合は `ValueError` が伝播し `modify_conf_file()` が例外で中断する | なし (priority=0 は syslog なし) | `hostcfgd:703, 375` |
| `priority` フィールドが非数値文字列 (例: `"high"`) で DB に書き込まれた場合 | `modify_conf_file()` L703 `int(t['priority'])` | `ValueError` が発生しスタックトレースが syslog へ。`modify_conf_file()` が中断され PAM 設定ファイル未更新 | スタックトレーム (未捕捉) | `hostcfgd:703` |
| `auth_type` に `pap`/`chap`/`mschapv2` 以外の値が設定された場合 | `pam_radius_auth.conf.j2` テンプレートレンダリング時 | テンプレートが不正な `auth_type` をそのまま展開。PAM ライブラリが起動時に不正な設定を拒否し認証不能になる | なし (hostcfgd 側での検証なし) | `hostcfgd:L96 RADIUS_SERVER_AUTH_TYPE_DEFAULT` |
| `skip_msg_auth` に `'True'`/`'False'` 以外の文字列が設定された場合 | `radius_server_update()` L542 `is_true()` | `is_true()` が `False` 扱いし `syslog LOG_ERR` "Failed to get bool value" を出力。`skip_msg_auth=False` として動作継続 | LOG_ERR ("Failed to get bool value, instead val={}") | `hostcfgd:160-162, 541-542` |
| `pam_radius_auth.conf.j2` テンプレートレンダリング中に例外が発生した場合 | `modify_conf_file()` L832 `template.render(server=srv)` | 例外がそのまま伝播 (catch なし) → `modify_conf_file()` が中断され以降のサーバの設定ファイルが生成されない | スタックトレース (未捕捉) | `hostcfgd:829-837` |
| `/etc/pam_radius_auth.d/<ip>_<port>.conf` の `open()` / `os.chmod()` / ファイル書き込みが `OSError` の場合 | `modify_conf_file()` L834-837 | 例外が伝播し以降のサーバ設定ファイルが未生成のまま処理中断 | スタックトレース (未捕捉) | `hostcfgd:834-837` |
| `src_intf` に対応するインタフェースが CONFIG_DB に存在しない or IP アドレス未設定の場合 | `modify_conf_file()` L697-700 `get_interface_ip()` | `get_interface_ip()` が空文字列を返し `server['src_ip']` を削除。pam_radius_auth.conf に source_ip 行なしで生成。サーバ側 NAS-IP-Address チェックが厳格な場合は認証失敗する可能性あり | LOG_INFO ("RADIUS_SERVER|{}: src_intf has no usable IP addr.") | `hostcfgd:697-700` |
| `src_intf` と `src_ip` が同時に設定されている場合 | `modify_conf_file()` L689-691 | `src_intf` 優先。`src_ip` は無視され syslog INFO が出力される | LOG_INFO ("RADIUS_SERVER|{}: src_intf found. Ignoring src_ip") | `hostcfgd:689-691` |
| `aaastatsd` サービスの start/stop が `CalledProcessError` の場合 | `modify_conf_file()` L848-851 | `syslog LOG_ERR` のみ。処理継続 (NSLCD 設定へ進む)。統計収集が機能しないが認証は継続される | LOG_ERR ("{cmd} - failed: return code - {}, output:\n{}") | `hostcfgd:848-851` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `RADIUS_SERVER` エントリを DEL (`data == {}`) したが対象 key が `self.radius_servers` に存在しない場合 | `radius_server_update()` L537 `if key in self.radius_servers` | サイレントスキップ。`del` は実行されず `modify_conf_file()` が呼ばれる。結果として設定ファイルは変化しない | なし | `hostcfgd:536-545` |
| `auth_port` 変更後に旧ポートの pam_radius_auth.conf が残留する場合 | `modify_conf_file()` | 旧ファイル (`<ip>_<old_port>.conf`) は自動削除されない。pam_radius_auth モジュールが旧設定ファイルを参照し続ける可能性がある | なし | `hostcfgd:829` |

### PAM 認証失敗につながる特殊挙動

| 状態 | 経路 | 影響 | evidence |
|---|---|---|---|
| `passkey` 未設定 (`RADIUS_SERVER_PASSKEY_DEFAULT = ""`) | `radius_global_default` → pam_radius_auth.conf 生成 | 空の shared secret で PAM 設定が生成される。RADIUS サーバ側で空 passkey を拒否すると認証失敗。設定ファイル自体は生成される (silent drop なし) | `hostcfgd:93, 377` |
| `AAA.authentication.login` に `radius` が含まれない場合 | `modify_conf_file()` L722 | `common-auth-sonic.j2` の分岐で RADIUS PAM スタックが組まれない。pam_radius_auth.conf は存在しても認証に使用されない (silent) | `hostcfgd:722-723` |
| `radsrvs_conf` が空 (RADIUS_SERVER エントリなし) の場合 | `modify_conf_file()` L681-703 | pam_radius_auth.conf の生成をスキップ。PAM スタックには RADIUS が組まれているが接続先がないため認証失敗 | `hostcfgd:681` |

### 検出ロジック補足

- **`int(t['priority'])` の脆弱性**: `priority` が数値変換不可能な文字列の場合、`ValueError` が伝播しソート処理が中断する。ただし YANG と CLI の両方で `uint8 1..64` を強制するため、正規経路では発生しない。
- **`auth_type` の無検証パススルー**: hostcfgd は `auth_type` の値を検証せず pam_radius_auth.conf テンプレートに渡す。不正な値は PAM ライブラリがエラーを返すまで検出されない。
- **`modify_conf_file()` の例外伝播**: RADIUS_SERVER 処理部 (L825-837) に try/except がないため、途中のサーバでテンプレートレンダリングやファイル書き込みが失敗した場合、残りのサーバの設定ファイルが生成されない。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERR` (radius 関連) | 1 | `hostcfgd:848-851 (aaastatsd CalledProcessError)` |
| `LOG_INFO` (src_intf) | 2 | `hostcfgd:691, 699` |
| `LOG_INFO` (NAS IP change) | 1 | `hostcfgd:509` |
| `is_true()` による `LOG_ERR` (bool 変換失敗) | 1 | `hostcfgd:160-162 (skip_msg_auth 経由)` |
| 例外 catch なし (伝播) | 2 | `hostcfgd:703 (priority sort), 832-837 (pam conf 生成)` |

<!-- /failure -->
