# TACPLUS_SERVER 例外条件調査メモ

ソース: `sonic-host-services/scripts/hostcfgd` (SHA: c5bbbe8b07b96f078fa4b761316627404b01bd04)

## 抽出した例外条件

1. **エントリが空 dict のとき削除処理** — `tacacs_server_update()` は `data == {}` のとき
   既存エントリを `del self.tacplus_servers[key]` で削除する。DEL コマンドが来ると内部辞書からも除去され
   次の `modify_conf_file()` でテンプレートに反映される。

2. **priority ソートによる優先度制御** — 複数サーバーがある場合、`priority` フィールドで降順ソートされて
   設定ファイルに書き出される。`priority` が文字列 → int 変換に失敗すると `ValueError` が発生し
   設定ファイル生成が中断する（`run_cmd` 等の外側の try/except では捕捉されず hostcfgd がクラッシュする可能性）。

3. **`src_ip` なしでも動作** — `tacplus_global` に `src_ip` がない場合は `src_ip = None` として
   テンプレートに渡される。テンプレートで `None` チェックして送信元 IP 設定を省略する。

4. **audisp-tacplus SIGHUP 失敗** — accounting 連携の `notify_audisp_tacplus_reload_config()` で
   PID が見つからない場合や `os.kill()` が失敗した場合、`LOG_WARNING` を出力して処理を続行する
   (audisp-tacplus が動いていなくても認証設定は更新される)。

5. **テンプレート生成失敗** — Jinja2 テンプレート展開や設定ファイル書き込みに失敗すると、
   `generate_file_from_template()` 内で `"Failed generate_file_from_template error={e}"` を LOG_ERR する。
