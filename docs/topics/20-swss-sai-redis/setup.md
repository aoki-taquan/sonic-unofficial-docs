---
title: 設定
description: 設定 — SWSS / SAI / Redis レイヤの「設定」は、機能 CLI のように config bgp で投入できる対象ではなく、SONiC
  の起動構成そのものを決めるファイル群です。
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
related:
  cli:
  - show feature
  - show platform
  - config bgp
  - show ip
  - show interfaces
  - show bgp
  config_db:
  - FEATURE
  - VOQ_INBAND_INTERFACE
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  yang:
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-bgp-bbr
  - sonic-bgp-peerrange
  - sonic-bgp-device-global
  - sonic-bgp-sentinel
  - sonic-bgp-monitor
---

# 設定

SWSS / [SAI](../../reference/glossary.md#term-sai) / [Redis](../../reference/glossary.md#term-redis) レイヤの「設定」は、機能 CLI のように `config bgp` で投入できる対象ではなく、[SONiC](../../reference/glossary.md#term-sonic) の起動構成そのものを決めるファイル群です。具体的には Redis instance のレイアウト、[Multi-ASIC](../../reference/glossary.md#term-multi-asic) namespace、FEATURE による daemon 起動制御、event-driven な config reload、container health probe の 5 つで、いずれも `/etc/sonic/` 配下のファイルと [CONFIG_DB](../../reference/glossary.md#term-config_db) の `FEATURE` テーブルで制御されます。

本ページでは「単一 [ASIC](../../reference/glossary.md#term-asic)」「[COUNTERS_DB](../../reference/glossary.md#term-counters_db) の Redis 分割」「Multi-ASIC / [VOQ](../../reference/glossary.md#term-voq) chassis」「FEATURE と config reload 遅延」「container health probe」の 5 シナリオで、ファイル例 + CLI + 確認手順をまとめます。

## 設定対象ファイルとテーブル一覧

| 対象 | 場所 | 役割 |
| --- | --- | --- |
| `database_config.json` | `/var/run/redis/sonic-db/database_config.json` | DB 名 → Redis instance / socket / db_number のマッピング |
| `database_global.json` | `/etc/sonic/database_global.json` (Multi-ASIC) | namespace ごとの `database_config.json` の集約 |
| `FEATURE` テーブル | CONFIG_DB | container 単位の state / auto_restart / delayed |
| `init_cfg.json` | `/etc/sonic/init_cfg.json` | 工場出荷時の CONFIG_DB 初期値 |
| `config_db.json` | `/etc/sonic/config_db.json` | 永続化された運用 CONFIG_DB |
| systemd unit | `/etc/systemd/system/*.service` | container 起動順 / dependency / probe |

## シナリオ 1: 単一 ASIC + 単一 Redis instance (既定)

ホワイトボックス 1 台に SONiC を入れたときの既定構成です。何もしなくてもこの形になります。

### database_config.json (既定)

!!! note "簡略化例"
    以下は読み解き用に主要 DB のみを抜粋した簡略例です。実機 (VS platform `sonic-buildimage/platform/vs/docker-sonic-vs/database_config.json`) では `GB_COUNTERS_DB` / `GB_FLEX_COUNTER_DB` / `CHASSIS_APP_DB` / `APPL_STATE_DB` / `DPU_APPL_DB` / `DPU_APPL_STATE_DB` / `DPU_STATE_DB` / `DPU_COUNTERS_DB` などの SmartSwitch / VOQ chassis 向け追加 DB が含まれ、`LOGLEVEL_DB` / `RESTAPI_DB` / `persistence_for_warm_boot` フィールドは存在しません。

```json
{
  "INSTANCES": {
    "redis": {
      "hostname": "127.0.0.1",
      "port": 6379,
      "unix_socket_path": "/var/run/redis/redis.sock",
      "persistence_for_warm_boot": "yes"
    }
  },
  "DATABASES": {
    "APPL_DB":          { "id": 0, "separator": ":",  "instance": "redis" },
    "ASIC_DB":          { "id": 1, "separator": ":",  "instance": "redis" },
    "COUNTERS_DB":      { "id": 2, "separator": ":",  "instance": "redis" },
    "LOGLEVEL_DB":      { "id": 3, "separator": ":",  "instance": "redis" },
    "CONFIG_DB":        { "id": 4, "separator": "|",  "instance": "redis" },
    "PFC_WD_DB":        { "id": 5, "separator": ":",  "instance": "redis" },
    "FLEX_COUNTER_DB":  { "id": 5, "separator": ":",  "instance": "redis" },
    "STATE_DB":         { "id": 6, "separator": "|",  "instance": "redis" },
    "SNMP_OVERLAY_DB":  { "id": 7, "separator": "|",  "instance": "redis" },
    "RESTAPI_DB":       { "id": 8, "separator": "|",  "instance": "redis" },
    "GB_ASIC_DB":       { "id": 9, "separator": ":",  "instance": "redis" }
  },
  "VERSION": "1.0"
}
```

### 確認

```bash
# Redis instance の状態
redis-cli ping
redis-cli INFO server | grep ^redis_version

# 各 DB が見えるか
redis-cli -n 4 KEYS 'DEVICE_METADATA|*'
redis-cli -n 1 DBSIZE
redis-cli -n 2 DBSIZE

# DB マッピングの確認
cat /var/run/redis/sonic-db/database_config.json | jq '.DATABASES | keys'
```

## シナリオ 2: COUNTERS_DB を別 Redis instance に切り出す

大規模 SKU で COUNTERS_DB の書き込みが他 DB の応答時間を圧迫するときに使う構成です。設計の前提は [複数 Redis インスタンスのユーザ定義](../../internals/support-multiple-user-defined-redis-database-instances.md) を読んでください。

### database_config.json

```json
{
  "INSTANCES": {
    "redis":          { "unix_socket_path": "/var/run/redis/redis.sock",          "port": 6379 },
    "redis_counters": { "unix_socket_path": "/var/run/redis/redis_counters.sock", "port": 6380 }
  },
  "DATABASES": {
    "APPL_DB":         { "id": 0, "instance": "redis" },
    "ASIC_DB":         { "id": 1, "instance": "redis" },
    "COUNTERS_DB":     { "id": 2, "instance": "redis_counters" },
    "FLEX_COUNTER_DB": { "id": 5, "instance": "redis_counters" },
    "CONFIG_DB":       { "id": 4, "instance": "redis" },
    "STATE_DB":        { "id": 6, "instance": "redis" }
  },
  "VERSION": "2.0"
}
```

### 反映手順

```bash
# 編集後に database container 再起動
sudo systemctl restart database

# ソケットが両方できているか
ls -l /var/run/redis/redis.sock /var/run/redis/redis_counters.sock

# COUNTERS_DB が新 instance に来ているか
redis-cli -s /var/run/redis/redis_counters.sock DBSIZE
redis-cli -s /var/run/redis/redis.sock DBSIZE
```

DB 名で参照する API (`SonicDBConfig::getDbInst()`) は変わらないため、ユーザ daemon は instance 構成を意識せずに済みます。

## シナリオ 3: Multi-ASIC / VOQ chassis (namespace 切り替え)

VOQ chassis や 2 ASIC SKU では、ASIC ごとに別の Redis 名前空間を持ちます。詳細は [Multi-ASIC 名前空間の Redis](../../internals/support-redis-databases-in-multiple-namespaces.md) を読んでください。

### database_global.json

```json
{
  "INCLUDES": [
    { "include": "database_config.json" },
    { "namespace": "asic0", "include": "asic0/database_config.json" },
    { "namespace": "asic1", "include": "asic1/database_config.json" }
  ],
  "VERSION": "1.0"
}
```

### namespace を指定した redis-cli

```bash
# host namespace
redis-cli -n 4 HGETALL 'DEVICE_METADATA|localhost'

# asic0 の Redis socket は別ファイル
sudo ip netns exec asic0 redis-cli -n 4 HGETALL 'DEVICE_METADATA|localhost'
sudo ip netns exec asic1 redis-cli -n 1 DBSIZE

# sonic-cfggen を namespace 付きで使う
sonic-cfggen -d -v 'DEVICE_METADATA["localhost"]["asic_id"]' -n asic0
```

### 確認

```bash
show platform summary           # Multi-ASIC platform か
show ip bgp summary -n asic0    # namespace 付き CLI
ip netns list                   # asic0 asic1 が存在
```

## シナリオ 4: FEATURE による daemon 制御と config reload 遅延

`FEATURE` テーブルは container 単位の有効/無効、自動再起動、起動遅延を一元管理します。

### CONFIG_DB スキーマ

```json
{
  "FEATURE|bgp": {
    "state": "enabled",
    "auto_restart": "enabled",
    "delayed": "True",
    "has_global_scope": "True",
    "has_per_asic_scope": "False",
    "high_mem_alert": "disabled",
    "set_owner": "local",
    "support_syslog_rate_limit": "true"
  },
  "FEATURE|telemetry": {
    "state": "disabled",
    "auto_restart": "enabled",
    "delayed": "False"
  }
}
```

### CLI

```bash
# state 切り替え
sudo config feature state bgp enabled
sudo config feature state telemetry disabled

# auto restart
sudo config feature autorestart bgp enabled

# 永続化
sudo config save -y

# 確認
show feature status
show feature autorestart
```

### config reload と delayed container

`delayed: True` の container は、PortInitDone を待ってから起動されます。これは [BGP](../../reference/glossary.md#term-bgp) などが「ASIC 上の port がまだない」状態で route を流し始めることを避ける設計です。詳細は [config reload の event-driven 化](../../management/config-reload-enhancement.md) を読んでください。

```bash
# config reload を投げる
sudo config reload -y

# STATE_DB で PortInitDone を待つ
redis-cli -n 6 HGETALL "PORT_TABLE|PortInitDone"

# delayed container がその後に起動したか
systemctl status bgp
journalctl -u bgp -n 50
```

## シナリオ 5: container health probe (k8s readiness)

各機能 container は `monit` 検査結果を 1 つの判定に集約する health-check を持ちます。k8s に乗せた SONiC では readiness probe としても使われます。意義は [コンテナ health-check](../../internals/why-need-health-check.md) を読んでください。

```bash
# container の health 状態
docker inspect bgp --format '{{.State.Health.Status}}'
docker inspect swss --format '{{json .State.Health}}' | jq

# monit の状態
sudo monit status

# health-check スクリプトの直接実行
docker exec swss /usr/bin/healthcheck.sh
```

`Health.Status` は `starting` / `healthy` / `unhealthy` を返します。`unhealthy` が継続すると `auto_restart=enabled` 時に container が再起動されます。

## よくある設定エラーと対処

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| `redis-cli` が `Connection refused` | `database` container が落ちている / socket 権限 | `systemctl status database`、`ls -l /var/run/redis/*.sock`、`/var/run/redis-chassis/` パーミッション確認 |
| `database_config.json` 変更が反映されない | container 再起動忘れ / JSON 構文エラー | `jq . /var/run/redis/sonic-db/database_config.json`、`systemctl restart database`、`config reload -y` |
| 新 instance を追加したが daemon が古い socket を掴む | daemon プロセスが既にロード済みの SonicDBConfig をキャッシュ | 影響 daemon を再起動 (`systemctl restart swss` 等)、必要なら `config reload -y` |
| Multi-ASIC で `redis-cli` が host を見てしまう | `ip netns exec` 無しで実行 | `sudo ip netns exec asic0 redis-cli ...` か、`-n asic0` 付き sonic-cli を使う |
| `config feature state` の変更が次回起動で消える | `config save` 忘れ | `sudo config save -y` で `config_db.json` を永続化 |
| delayed container が起動しない | PortInitDone が来ていない / [portmgrd](../../reference/glossary.md#term-portmgrd) 異常 | `redis-cli -n 6 KEYS 'PORT_TABLE*'`、`journalctl -u portmgrd`、`show interfaces status` で port が UP か |
| `docker inspect` で `Health.Status` 欄が空 | healthcheck が Dockerfile に未定義の古い image | image を最新化、または `monit` 経由の判定にフォールバック |
| Multi-ASIC で [APPL_DB](../../reference/glossary.md#term-appl_db) の更新が片側 ASIC にしか反映されない | 書き手が namespace を指定せず host Redis を更新 | `swsscommon.SonicV2Connector(namespace='asic0')` を使う、scripts は `-n asic<N>` フラグを通す |
| COUNTERS_DB を別 instance に分けたら CLI が値を返さない | CLI 側が socket をハードコード | `swsscommon` 経由の CLI を使う、`database_config.json` の socket と CLI の参照先を一致 |

## 確認に使う show / redis コマンドまとめ

```bash
# Redis レイアウト
cat /var/run/redis/sonic-db/database_config.json | jq
cat /etc/sonic/database_global.json | jq

# FEATURE
show feature status
show feature autorestart
redis-cli -n 4 KEYS 'FEATURE|*'

# container 健全性
docker ps --format 'table {{.Names}}\t{{.Status}}'
sudo monit summary

# Multi-ASIC
show platform summary
ip netns list
```

## 関連ページ

- [複数 Redis インスタンスのユーザ定義 (database_config.json で DB を分散)](../../internals/support-multiple-user-defined-redis-database-instances.md)
- [Multi-ASIC 名前空間の Redis (database_global.json と SonicDBConfig)](../../internals/support-redis-databases-in-multiple-namespaces.md)
- [FEATURE テーブルによるオプショナル機能の有効/無効制御](../../system/sonic-optional-feature-control-enhancement.md)
- [config reload の event-driven 化 (FEATURE.delayed + PortInitDone)](../../management/config-reload-enhancement.md)
- [コンテナ health-check (k8s readiness probe)](../../internals/why-need-health-check.md)
- [SWSS / SAI / Redis の概要](concept.md)
- [SWSS / SAI / Redis のアーキテクチャ](architecture.md)
- [SWSS / SAI / Redis の運用](operations.md)
- [SWSS / SAI / Redis の internals](internals.md)

<!-- glossary-links-injected: 5c9b3765d470 -->
