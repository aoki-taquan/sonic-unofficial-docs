# SYSLOG_CONFIG — Phase B 書込み順依存スキャンノート

対象テーブル: `SYSLOG_CONFIG`
Consumer: `hostcfgd` / `RSyslogCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: `RSyslogCfg.load()`, `RSyslogCfg.update_rsyslog_config()`, `rsyslog_handler()`, `rsyslog_config_handler()`, `rsyslog_server_handler()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. SYSLOG_CONFIG と SYSLOG_SERVER は常にペアで読まれる

- `rsyslog_handler()` (hostcfgd:2410) は `SYSLOG_CONFIG` と `SYSLOG_SERVER` の両テーブルを `get_table()` で一括取得し、`RSyslogCfg.update_rsyslog_config(rsyslog_config, rsyslog_servers)` へ渡す。
- `rsyslog_config_handler()` (hostcfgd:2421) も `rsyslog_server_handler()` (hostcfgd:2417) も、どちらが呼ばれても同じ `rsyslog_handler()` を経由する。
- **どちらのテーブルを変更しても rsyslog-config が再起動される**。
- **順序依存（推奨）**: `SYSLOG_SERVER` エントリを先に投入してから `SYSLOG_CONFIG|GLOBAL` を書き込む順序にすると、rsyslog-config の再起動は 1 回で済む。逆順だと `SYSLOG_CONFIG` 書き込み時に 1 回、`SYSLOG_SERVER` 書き込み時にもう 1 回、計 2 回の rsyslog-config 再起動が発生する。
- evidence: `hostcfgd:2410-2415`, `hostcfgd:2499-2503`

### 2. load() フェーズでの一括初期化

- `HostConfigDaemon.__init__()` (hostcfgd:2203) で `RSyslogCfg` を生成する。
- `load()` (hostcfgd:2269) は `syslog_cfg = init_data.get(CFG_SYSLOG_CONFIG_TABLE_NAME, {})` と `syslog_srv = init_data.get(CFG_SYSLOG_SERVER_TABLE_NAME, {})` を同時に取得して `rsyslogcfg.load()` を呼ぶ。
- `RSyslogCfg.load()` は rsyslog-config を再起動**しない**（キャッシュ初期化のみ）。
- **順序依存なし**（load フェーズはスナップショット取得であり、どちらが先でも同結果）。
- evidence: `hostcfgd:2250-2269`

### 3. 変更なしはノーオペレーション（キャッシュ比較）

- `update_rsyslog_config()` は `self.cache.get('config', {}) != rsyslog_config` または `self.cache.get('servers', {}) != rsyslog_servers` の場合のみ `systemctl restart rsyslog-config` を実行する (hostcfgd:1725-1726)。
- `SYSLOG_CONFIG|GLOBAL` の同一値を再度書き込んでも rsyslog-config 再起動は発生しない。
- evidence: `hostcfgd:1725-1726`

### 4. welf_firewall_name の YANG must 制約 — format 先行書き込みは不可

- YANG `sonic-syslog.yang` の `must "(../format != 'standard')"` 制約により、`welf_firewall_name` は `format = welf` の状態でなければ書き込めない。
- **順序依存**: `format = welf` と `welf_firewall_name` を別々に書く場合、`format` を先に `welf` に変更してから `welf_firewall_name` を書く必要がある。逆順（`format = standard` のまま `welf_firewall_name` を書く）は YANG バリデーションエラーになる。
- evidence: `sonic-syslog.yang:must "(../format != 'standard')"`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SYSLOG_SERVER → SYSLOG_CONFIG の順で投入 | 推奨（rsyslog 再起動 1 回化） | 逆順でも最終状態は同じ。再起動が 2 回になるだけ |
| 2 | load フェーズ順序依存なし | — | 両テーブルをスナップショット取得 |
| 3 | 同一値書き込みはノーオペレーション | — | キャッシュ比較で自動スキップ |
| 4 | format=welf → welf_firewall_name の順で書き込み | 必須（YANG 制約） | format 変更後に welf_firewall_name を書く |
