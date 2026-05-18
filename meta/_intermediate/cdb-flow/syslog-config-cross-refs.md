# SYSLOG_CONFIG — Phase C 暗黙参照スキャンノート

対象テーブル: `SYSLOG_CONFIG`
Consumer: `hostcfgd` / `RSyslogCfg` (`sonic-host-services/scripts/hostcfgd`)
テンプレート: `sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2`
スキャン範囲: `RSyslogCfg.update_rsyslog_config()`, `rsyslog_handler()`, `rsyslog.conf.j2` 全行精読

---

## 検出した暗黙参照

### 1. SYSLOG_SERVER — 常にペアで読まれる

- `rsyslog_handler()` (hostcfgd:2410-2415) は `SYSLOG_CONFIG` と `SYSLOG_SERVER` を同時に `get_table()` で取得して `RSyslogCfg.update_rsyslog_config(rsyslog_config, rsyslog_servers)` へ渡す。
- `rsyslog.conf.j2` (L84-125) が `{% for server in SYSLOG_SERVER %}` でサーバエントリを展開する。
- **暗黙参照**: `SYSLOG_CONFIG|GLOBAL.format` フィールドが `welf` の場合、テンプレート内で `SYSLOG_SERVER` 側の出力テンプレートも `WelfRemoteFormat` に切り替わる (rsyslog.conf.j2:99-105)。`SYSLOG_CONFIG` の `format` 値が `SYSLOG_SERVER` の出力形式を間接的に制御する。
- **YANG leafref なし** (同一モジュール内の別コンテナ)。
- evidence: `hostcfgd:2410-2415`, `rsyslog.conf.j2:84-125`

### 2. DEVICE_METADATA — welf_firewall_name のフォールバック

- `rsyslog.conf.j2` L52: `{% set fw_name = gconf.get('welf_firewall_name', hostname) %}` — `welf_firewall_name` が未設定の場合、Jinja2 変数 `hostname` が fallback として使われる。
- `hostname` は `sonic-cfggen -d` が `DEVICE_METADATA|localhost.hostname` から取得してテンプレートに渡す。
- **暗黙参照**: `format = welf` かつ `welf_firewall_name` が未設定の場合、`DEVICE_METADATA|localhost.hostname` が WELF ログのファイアウォール名として使用される。
- **YANG leafref なし**（テンプレートの変数注入）。
- evidence: `rsyslog.conf.j2:52-53`, `sonic-cfggen` の `-d` オプション

### 3. SYSLOG_CONFIG_FEATURE — グローバル値をフォールバック提供

- `containercfgd` が `rsyslog-container.conf.j2` を展開する際、`SYSLOG_CONFIG_FEATURE[container].rate_limit_interval` が未設定の場合 `|default('300')` を使用する (rsyslog-container.conf.j2)。
- `SYSLOG_CONFIG|GLOBAL.rate_limit_interval` / `rate_limit_burst` は `containercfgd` が直接参照するのではなく、`hostcfgd` が `rsyslog.conf.j2` でホスト側 rsyslog の rate limit として反映する。
- **暗黙参照**: `SYSLOG_CONFIG|GLOBAL` の rate limit 設定はホスト rsyslog に、`SYSLOG_CONFIG_FEATURE` の per-feature 設定は各コンテナ rsyslog に別々に反映される。`SYSLOG_CONFIG_FEATURE` が未設定のコンテナはデフォルト値 (`interval=300`, `burst=20000`) にフォールバックし、`SYSLOG_CONFIG|GLOBAL` の値は継承**しない**（テンプレートのハードコードデフォルトが使われる）。
- **YANG leafref なし**（アーキテクチャ上の間接依存）。
- evidence: `rsyslog-container.conf.j2` `|default('300')` / `|default('20000')`, `hostcfgd:2410-2415`

---

## 暗黙参照サマリ

| 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `SYSLOG_SERVER` | CONFIG_DB | 読み取り (毎回ペア取得 + テンプレート展開) | なし | 任意 (0件でも動作) | `hostcfgd:2410-2415`, `rsyslog.conf.j2:84-125` |
| `DEVICE_METADATA\|localhost.hostname` | CONFIG_DB | 読み取り (welf_firewall_name フォールバック) | なし | 条件付き必須 (format=welf かつ welf_firewall_name 未設定時) | `rsyslog.conf.j2:52` |
| `SYSLOG_CONFIG_FEATURE` | CONFIG_DB | 参照元として rate-limit 提供 (ホスト側のみ) | なし | アーキテクチャ上の独立 | `rsyslog-container.conf.j2` defaults |
