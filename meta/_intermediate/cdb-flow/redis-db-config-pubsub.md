# redis-db-config — Phase G: 通信メカニズム

## 結論

`database_config.json` は CONFIG_DB テーブルではなくインフラ層ファイルであるため、
通常の CONFIG_DB テーブルが用いる Redis PUBLISH/SUBSCRIBE メカニズムは **一切使用しない**。

`SonicDBConfig` クラスはファイルを起動時に一度読み込んでインメモリキャッシュに格納するのみであり、
変更通知・keyspace notification の発行も受信も行わない。

## 関連する通信経路

`database_config.json` の変更が波及する経路は Redis pub/sub ではなく
**コンテナ再起動 + ファイル再読み込み** のシーケンスを経由する:

```
管理者が /etc/sonic/database_config.json を更新
  ↓
docker restart database  (または config reload 経由)
  ↓
docker-database-init.sh が再実行されファイルを /var/run/redis/sonic-db/ に展開
  ↓
各アプリが再起動 → SonicDBConfig::initialize() でファイルを再読み込み
```

Redis pub/sub チャンネルや keyspace notification は介在しない。

## 証跡

- `sonic-net/sonic-swss-common` `common/dbconnector.cpp` — `SonicDBConfig` クラス全体に PUBLISH / SUBSCRIBE 呼び出しが存在しないことを確認
- `sonic-net/sonic-buildimage` `dockers/docker-database/docker-database-init.sh` — 設定ファイル生成・配置ロジック (pub/sub 不使用)
