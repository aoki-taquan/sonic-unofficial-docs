# RESTAPI — Phase G pubsub 調査ノート

## 調査日: 2026-05-19
## 調査対象: sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh, supervisord.conf, sonic-host-services/scripts/hostcfgd

## 結論: RESTAPI テーブルを購読する常駐デーモンは存在しない

`RESTAPI` テーブルは「起動時一括読み取り」モデルを採用しており、`ConfigDBConnector.subscribe()` / `swsscommon.SubscriberStateTable` / `swsscommon.ConsumerStateTable` のいずれも使用しない。

### 証拠

1. `rest-server.sh:13`: 起動時に `MGMT_VARS=$(sonic-cfggen -d -t $MGMT_VARS_FILE)` を一度だけ実行し `RESTAPI|config` / `RESTAPI|certs` の値を変数に取り込む。その後 Redis への subscribe は一切行わない。

2. `supervisord.conf:39-47`: `rest-server.sh` は supervisord が管理する単一プロセスであり、常駐後は Redis イベントを受け取る仕組みを持たない。

3. `hostcfgd` の subscribe 登録テーブル (`sonic-host-services/scripts/hostcfgd:2454-2520` 周辺) を grep すると `RESTAPI` テーブルは登録リストに含まれない。

4. `hostcfgd` が `FIPS_CFG` 変更時に `restapi` サービスを再起動することがあるが、これは `RESTAPI` テーブルの subscribe ではなく `FIPS_CFG` テーブル変更に起因する副作用である。

### CONFIG_DB 読み取りのフロー

```
supervisord 起動
  ├─ rsyslogd  (priority=1)
  ├─ start.sh  (priority=2, wait_for=rsyslogd:running)
  └─ rest-server.sh  (priority=3, wait_for=start:exited)
       └─ MGMT_VARS=$(sonic-cfggen -d -t /usr/share/sonic/templates/mgmt_vars.j2)
            ├─ REST_SERVER = RESTAPI|config の値一括取得
            └─ X509 = DEVICE_METADATA|localhost.x509 の値一括取得 (cert フォールバック用)
            → 取得値を rest_server 起動引数に組み込んで 1 回起動
```

起動後は CONFIG_DB への接続を維持せず、subscribe / keyspace 通知受信も行わない。`RESTAPI` テーブルを変更しても実行中の `rest_server` には一切通知されない。

### 変更を反映する唯一の方法

`docker restart mgmt-framework` または `systemctl restart docker-sonic-mgmt-framework` によるコンテナ再起動のみ。
