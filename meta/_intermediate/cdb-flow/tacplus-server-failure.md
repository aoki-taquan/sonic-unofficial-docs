# TACPLUS_SERVER — Phase D 失敗挙動 証跡

## 対象ファイル

- `sonic-host-services/scripts/hostcfgd` (ref: c5bbbe8b07b96f078fa4b761316627404b01bd04)

## 抽出した失敗挙動

### 1. 不正 priority による ValueError

`modify_conf_file()` L665:
```python
servers_conf = sorted(servers_conf, key=lambda t: int(t['priority']), reverse=True)
```
`priority` フィールドが整数として解釈できない文字列の場合、`int()` が `ValueError` を送出し、`sorted()` の時点で例外が伝播する。`modify_conf_file()` 全体が中断し PAM / NSS 設定ファイルは更新されない。ただし例外はキャッチされず、呼び出し元の `tacacs_server_update()` / `tacacs_global_update()` にそのまま伝播する（unhandled exception）。

証跡: `hostcfgd L665`、`hostcfgd L473-481`

### 2. PAM 設定生成失敗 (generate_file_from_template / open + rename)

`modify_conf_file()` L728-731:
```python
with open(PAM_AUTH_CONF + ".tmp", 'w') as f:
    f.write(pam_conf)
os.chmod(PAM_AUTH_CONF + ".tmp", 0o644)
os.rename(PAM_AUTH_CONF + ".tmp", PAM_AUTH_CONF)
```
Jinja2 テンプレートレンダリングや `.tmp` ファイルへの書き込みが失敗した場合、例外は `modify_conf_file()` 内でキャッチされず上位に伝播する。`generate_file_from_template()` 関数 (L200-216) は独自の try/except を持ち `LOG_ERR: 'Failed generate_file_from_template error={e}'` を出力するが、`modify_conf_file()` の直接 `open/write/rename` パスでは同様のキャッチがない。

証跡: `hostcfgd L200-216`、`hostcfgd L728-731`

### 3. 不正 auth_type による pam_tacplus 認証失敗

`auth_type` は YANG で `enum pap/chap/mschap/login` と定義されるが、hostcfgd は `auth_type` の値を直接 Jinja2 テンプレートに渡す（L725: `template.render(..., servers=servers_conf)`）。テンプレート `common-auth-sonic.j2` L18:
```jinja
pam_tacplus.so server={{ server.ip }}:{{ server.tcp_port }} secret={{ server.passkey }} login={{ server.auth_type }} ...
```
YANG 列挙外の文字列（例: `"ascii"`, `"invalid"`）が設定されると、hostcfgd は拒否せずそのまま `login=invalid` を PAM 行に書き込む。pam_tacplus モジュールが認識しない `login=` 値を受け取った場合、サーバーへの接続は行われるが認証プロトコルのネゴシエーションに失敗し、認証拒否 (`auth_err`) となる。エラーログは出力されない（silent failure）。

証跡: `hostcfgd L725`、`sonic-host-services/data/templates/common-auth-sonic.j2 L18,22,27`

### 4. audisp-tacplus SIGHUP 失敗

`notify_audisp_tacplus_reload_config()` L483-493:
```python
try:
    os.kill(int(pid), signal.SIGHUP)
except Exception as ex:
    syslog.syslog(syslog.LOG_WARNING, "Send SIGHUP to audisp-tacplus failed with exception: {}".format(ex))
```
audisp-tacplus プロセスが存在しない、または PID ファイルが不正の場合に `LOG_WARNING` を出力して継続する。PAM 設定自体の更新は完了しているため、認証には影響しない。ただし TACACS+ accounting の設定再読み込みが失敗するため、accounting ログが古い設定で動作し続ける。

証跡: `hostcfgd L483-493`, `hostcfgd L816`
