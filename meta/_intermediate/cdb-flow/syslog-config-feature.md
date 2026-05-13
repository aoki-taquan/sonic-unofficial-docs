# SYSLOG_CONFIG_FEATURE 例外条件調査メモ

ソース: `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

## 抽出した例外条件

1. **キー不一致時はスキップ** — `handle_config()` は `key != service_name` の場合に早期 return する。
   docker 内の `ContainerConfigDaemon` は自 container の service_name に一致するエントリのみ処理し、他 container 向けのエントリは無視する。

2. **設定エラーの catch** — `update_syslog_config()` を try/except で囲み、
   例外発生時は `"Failed to config syslog for container {} with data {} - {}"` を LOG_ERROR してスキップ。
   rsyslogd の再起動コマンド失敗も同じパスで吸収される。

3. **変更なしはノーオペレーション** — `new_interval == self.current_interval and new_burst == self.current_burst` の場合、
   `"Syslog rate limit configuration does not change, ignore it"` を LOG_NOTICE してスキップ。
   不要な rsyslogd 再起動を防ぐキャッシュ機構。

4. **テンプレート生成失敗** — `sonic-cfggen` の実行に失敗すると `run_command()` が例外を送出し、
   上位の try/except で catch されてログ出力のみで続行する。
