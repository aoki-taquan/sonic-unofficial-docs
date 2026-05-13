# RADIUS 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-host-services/scripts/hostcfgd`

## 抽出した例外条件

1. **radius_global_update は key='global' のみ処理**: それ以外の key は無視（サイレントスキップ）。
   - 証拠: `def radius_global_update(self, key, data, modify_conf=True): if key == 'global':` (l.527)

2. **radius_server_update でデータ空の場合は削除**: `data == {}` の時は `radius_servers` から当該サーバエントリを削除してから設定ファイルを再生成する。
   - 証拠: `if data == {}: if key in self.radius_servers: del self.radius_servers[key]` (l.535)

3. **src_intf 変更時の再設定**: グローバル `src_intf` や per-server `src_intf` が参照するインタフェースの IP が変わると `handle_radius_source_intf_ip_chg` が再度 `modify_conf_file()` を呼び出す。インタフェースが存在しない場合は設定ファイル生成時にテンプレートの `src_intf` 部分が空になり、pam_radius_auth.conf の `src_ip` 行が省略される。

4. **modify_conf_file の失敗は syslog のみ**: テンプレート展開やサービス SIGHUP 送信に失敗しても例外はキャッチされ `LOG_ERR` / `LOG_WARNING` に記録されるだけで radius_servers / radius_global は更新済みのままとなる（設定ファイルとのずれが生じる）。
   - 証拠: `run_cmd` / `run_cmd_pipe` の例外ハンドラ (l.123-151)

5. **statistics フィールドのブール変換**: `statistics` の値は `is_true()` で変換される。`True/true/yes/1` 以外はすべて False 扱い。
