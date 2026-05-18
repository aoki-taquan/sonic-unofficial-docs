# SYSLOG_CONFIG_FEATURE — Phase B 書込み順依存 調査メモ

調査日: 2026-05-18
調査者: Claude batch #6 (agent)

## 調査対象ソース

- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py` (ContainerConfigDaemon, SyslogHandler)
- `sonic-host-services/scripts/hostcfgd` (RSyslogCfg, subscribe 登録部 L2499-2503)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-syslog.yang` (leafref 制約)

## 検出された順序依存

### 1. FEATURE → SYSLOG_CONFIG_FEATURE (YANG leafref 制約)

`sonic-syslog.yang` の `SYSLOG_CONFIG_FEATURE_LIST` の `leaf service` は
`/feature:sonic-feature/feature:FEATURE/feature:FEATURE_LIST/feature:name` への leafref。
`FEATURE` テーブルに未登録の service 名を key とした書込みは YANG バリデーション違反で拒否される。

**強制先行**: `FEATURE|<service>` が CONFIG_DB に存在していなければ
`SYSLOG_CONFIG_FEATURE|<service>` は書き込めない。

### 2. containercfgd の init 時スナップショット読込

`ContainerConfigDaemon.run()` は `config_db.connect(wait_for_init=True)` → `config_db.listen(init_data_handler=...)` を呼ぶ。
`init_data_handler` 内で全ハンドラの `handle_init_data(init_data)` を一括実行し、
`SyslogHandler.handle_init_data` が `init_data[SYSLOG_CONFIG_FEATURE_TABLE][service_name]` を取り出して `update_syslog_config` を呼ぶ。

**含意**: containercfgd 起動時点で `SYSLOG_CONFIG_FEATURE|<service>` がまだ書かれていない場合、
初期スナップショットにエントリが存在せず init 処理はスキップされる。
その後 CLI 等で書込みが発生すると `handle_config` が非同期で呼ばれ、rsyslogd が再起動される。
つまり **containercfgd 起動より後に SYSLOG_CONFIG_FEATURE が書かれても問題なく反映される**。

### 3. key ≠ service_name の早期 return

`handle_config` は `if key != service_name: return` で他コンテナ向けエントリを無視する。
複数コンテナが同一 CONFIG_DB を購読しているが、各 containercfgd インスタンスは自分の service_name のエントリのみ処理する。
書込み順やバースト配信の順序は、各コンテナにとって独立であり、相互干渉なし。

### 4. SYSLOG_CONFIG (グローバル) との関係

- `hostcfgd` が `SYSLOG_CONFIG` を購読し、グローバル rsyslog 設定を `/etc/rsyslog.d/` に書き込む
- `containercfgd` 内 `SyslogHandler` が `SYSLOG_CONFIG_FEATURE` を購読し、コンテナ内 `/etc/rsyslog.conf` を書き込む
- 両テーブルは**独立した購読チェーン**で処理される。`SYSLOG_CONFIG` 変更が `SYSLOG_CONFIG_FEATURE` 処理を直接トリガしない
- ただし、per-feature エントリが**存在しない**場合のみ hostcfgd が生成したグローバル設定が有効（上位層でのフォールバック）

### 5. 削除順序

`SYSLOG_CONFIG_FEATURE|<service>` が DEL された場合:
- `handle_config` が `data={}` (空dict) で呼ばれる
- `new_interval = '0'`, `new_burst = '0'` となり rsyslogd が rate-limit 0 設定で再起動
- `FEATURE` エントリ削除より先に `SYSLOG_CONFIG_FEATURE` を削除することが推奨（逆順だと YANG leafref 状態は壊れないが CONFIG_DB 上に孤立エントリが残る）

## 結論

| # | 依存関係 | 方向 | 強度 |
|---|----------|------|------|
| 1 | `FEATURE|<service>` → `SYSLOG_CONFIG_FEATURE|<service>` | YANG leafref 強制先行 | 強（書込み拒否） |
| 2 | `SYSLOG_CONFIG_FEATURE|<service>` → containercfgd `init_data_handler` | 起動前存在推奨 | 弱（後書き可） |
| 3 | 各コンテナの containercfgd は独立 | 順序無関係 | N/A |
| 4 | `SYSLOG_CONFIG` と `SYSLOG_CONFIG_FEATURE` は独立チェーン | 直接依存なし | N/A |
| 5 | 削除時: `SYSLOG_CONFIG_FEATURE` → `FEATURE` | 推奨先行 | 弱（強制なし） |
