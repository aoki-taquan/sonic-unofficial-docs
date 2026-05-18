# community-list (SNMP_COMMUNITY) — Phase D 失敗挙動スキャンノート

ソース:
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-buildimage/dockers/docker-snmp/docker-snmp-init.sh`

## 抽出した失敗ケース

### 1. snmp.yml 不在 → sys.exit(1)、テーブル注入なし

- 場所: `snmp_yml_to_configdb.py L25-27`
- `/etc/sonic/snmp.yml` が存在しない場合、スクリプトは `logger.log_info` してから `sys.exit(1)` で終了
- `SNMP_COMMUNITY` への書き込みは一切行われない
- テーブルが空のまま snmpd が起動すると全 SNMPv1/v2c アクセスが拒否される

### 2. snmp.yml の snmp_location 未定義 → sys.exit(1)

- 場所: `snmp_yml_to_configdb.py L51-56`
- `snmp_location` キーが snmp.yml に存在しない場合、`logger.log_info` してから `sys.exit(1)` で終了
- この時点で community の書き込みは既に完了している（ループは L32-49）が、スクリプト全体が異常終了扱いとなる
- 監視スクリプト / supervisord がこの exit code を見て再試行するかはプラットフォーム依存

### 3. TYPE 小文字での書き込み → コミュニティ行不生成（サイレント）

- 場所: `snmpd.conf.j2 L50, L59`
- テンプレートは `SNMP_COMMUNITY[community]['TYPE'] == 'RO'` と大文字で比較する
- `sonic-db-cli` 等で `TYPE: ro`（小文字）を書き込んだ場合、どちらの条件にも一致しない
- `snmpd.conf` への community 行生成がスキップされる。エラーログ・例外なし
- snmpd は当該 community を認識しないが起動自体は成功する

### 4. TYPE フィールド欠如 → KeyError / サイレントスキップ

- 場所: `snmpd.conf.j2 L50, L59`
- `SNMP_COMMUNITY[community]['TYPE']` にキーが存在しない場合、Jinja2 の dict アクセスで `KeyError` が発生し、テンプレートレンダリングが途中で失敗する可能性がある
- ただし sonic-cfggen / jinja2 の実装では `Undefined` オブジェクトとして扱われ、比較が `False` を返す動作も観察されている（サイレントスキップ）
- いずれの場合も当該エントリは snmpd.conf に出力されず、エラーログは出力されない

### 5. ConfigDB 接続失敗 → 例外で即終了

- 場所: `snmp_yml_to_configdb.py L10` (`ConfigDBConnector().connect()`)
- Redis 未起動・ソケット不在の場合は `swsscommon.swsscommon.ConfigDBConnector` のコンストラクタまたは `connect()` が例外で失敗する
- スクリプト全体が uncaught exception で終了、テーブル注入なし

### 6. CLI (config snmp community add) の YANG バリデーション失敗 → 書き込まれない

- 場所: sonic-utilities `config/main.py` (YANG validation コード)
- community 名が YANG 制約（長さ 4〜32 文字、禁止文字）に違反する場合、`set_entry` 前にバリデーションが失敗してエラーメッセージが出力される
- DB への書き込みは発生しない

### 7. snmpd 設定反映の非即時性

- `SNMP_COMMUNITY` への SET / DEL は snmpd プロセスにリアルタイム通知されない
- `docker-snmp` コンテナ再起動または `systemctl restart snmp.service` まで反映されない
- CLI (`config snmp community add`) は自動的に `systemctl restart snmp.service` を発行するが（`config/main.py:4395-4401`）、direct DB 書き込みでは手動再起動が必要

## 中間ファイルの位置

詳細ブロックは `docs/reference/config-db/community-list.md` の `<!-- failure -->` / `<!-- /failure -->` を参照。
