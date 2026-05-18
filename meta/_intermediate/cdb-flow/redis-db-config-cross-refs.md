# redis-db-config 暗黙参照リソース調査メモ (Phase C)

調査日: 2026-05-18
対象: `database_config.json` / Redis DB インスタンス・データベース設定

## 調査対象ファイル

- `sonic-swss-common/common/dbconnector.cpp` — `initialize()`, `initializeGlobalConfig()`, `getDbInfo()` 等
- `sonic-buildimage/dockers/docker-database/docker-database-init.sh` — 起動時ファイル生成ロジック
- `sonic-buildimage/dockers/docker-database/database_global.json.j2` — グローバル設定テンプレート

---

## 暗黙参照リソース一覧

`database_config.json` は CONFIG_DB テーブルではなくインフラ層ファイルであり、
他 CONFIG_DB テーブルへの leafref は存在しない。
ただし `docker-database-init.sh` の起動ロジックおよび `SonicDBConfig` の初期化 API は
以下のファイル・設定を暗黙的に参照する。

---

### 1. `/etc/sonic/database_config.json` (オーバーライドファイル)

- **参照タイミング**: `docker-database-init.sh` 起動時 (L55-56)
- **依存内容**: このファイルが存在する場合、テンプレートレンダリングをスキップしてそのまま
  `/var/run/redis/sonic-db/database_config.json` にコピーする。
  存在しない場合のみ `database_config.json.j2` / `multi_database_config.json.j2` でレンダリング
- **evidence**: `docker-database-init.sh:55-61`

---

### 2. `/etc/sonic/enable_multidb` (マルチ DB フラグファイル)

- **参照タイミング**: `docker-database-init.sh` 起動時 (L58)
- **依存内容**: このファイルが存在すると `multi_database_config.json.j2` を使用し、
  存在しないと `database_config.json.j2` を使用する。
  マルチ DB 構成 (複数 ASIC / SmartSwitch) を有効化するスイッチ
- **evidence**: `docker-database-init.sh:58-61`

---

### 3. `/usr/share/sonic/platform/chassisdb.conf` (プラットフォーム chassis DB 設定)

- **参照タイミング**: `docker-database-init.sh` 起動時 (L77-78)
- **依存内容**: このファイルが存在する場合 `source` で読み込み、`start_chassis_db`、
  `chassis_db_address`、`chassis_db_port` 変数を取得する。
  `start_chassis_db=1` の場合のみ `CHASSIS_APP_DB` エントリを最終設定ファイルに含める
- **evidence**: `docker-database-init.sh:77-78`, `docker-database-init.sh:124-127`

---

### 4. `/var/run/redis/sonic-db/database_global.json` (グローバル設定)

- **参照タイミング**: `SonicDBConfig::initializeGlobalConfig()` 呼び出し時
- **依存内容**: マルチ ASIC / SmartSwitch 環境で namespace 付き DB 接続を行う場合に必要。
  `database_global.json` は各 namespace の `database_config.json` を INCLUDES セクションで列挙する。
  namespace 付き API (`getDbId(..., netns)` 等) を呼ぶ前に
  `initializeGlobalConfig()` が実行されていなければ `SWSS_LOG_THROW` で即クラッシュ
- **evidence**: `dbconnector.cpp:228-231`, `database_global.json.j2` 全体

---

### 5. `NAMESPACE_COUNT` / `NUM_DPU` 環境変数

- **参照タイミング**: `docker-database-init.sh` 起動時 (L104)
- **依存内容**: `NAMESPACE_COUNT > 1` または `NUM_DPU > 1` の場合、`database_global.json` を生成する。
  これらは `sonic-cfggen` / SONiC 起動フレームワークが設定する環境変数
- **evidence**: `docker-database-init.sh:104-110`

---

### 6. `/etc/sonic/database_global.json` (オーバーライドグローバル設定)

- **参照タイミング**: `docker-database-init.sh` 起動時 (L106)
- **依存内容**: `/etc/sonic/database_global.json` が存在する場合、テンプレートレンダリングをスキップして
  そのままコピーする。存在しない場合のみ `database_global.json.j2` でレンダリング
- **evidence**: `docker-database-init.sh:106-109`

---

## CONFIG_DB テーブルとの関係

`database_config.json` 自体は CONFIG_DB に格納されない独立ファイルであるため、
他 CONFIG_DB テーブルを leafref として参照することはない。

ただし `SonicDBConfig` によって定義された DB ID / インスタンス情報は、
SONiC の全デーモン (swss, syncd, mgmt, snmp 等) が起動時に依存する基盤層であり、
間接的にすべての CONFIG_DB テーブル操作の前提条件となる。

---

## 証拠リンク

- `sonic-swss-common/common/dbconnector.cpp:89-180` — `initializeGlobalConfig()` 実装
- `sonic-swss-common/common/dbconnector.cpp:182-204` — `initialize()` 実装
- `sonic-swss-common/common/dbconnector.cpp:220-260` — namespace バリデーション (SWSS_LOG_THROW 分岐)
- `sonic-buildimage/dockers/docker-database/docker-database-init.sh:55-128` — ファイル生成ロジック全体
- `sonic-buildimage/dockers/docker-database/database_global.json.j2` — グローバル設定テンプレート
