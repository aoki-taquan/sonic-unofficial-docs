---
title: 設定
description: 設定 — PINS は SONiC 上に P4RT サービスを追加することで、外部の SDN コントローラから P4Runtime gRPC
  で ASIC を直接制御できるようにする機能です。
area: topics
verification: meta
last_verified: 2026-05-11
sources:
- docs/management/pins-hld.md
- docs/management/p4rt-application-hld.md
- docs/management/send-to-ingress-hld.md
related:
  cli:
  - config route
  - show platform
  - show feature
  - config acl
  - show interfaces
  - config vrf
  - show acl
  config_db:
  - VRF
  - ACL_RULE
  - ACL_TABLE
  - COPP_GROUP
  - COPP_TRAP
  - CRM
  - TELEMETRY
  yang:
  - sonic-copp
  - sonic-vrf
  - sonic-crm
---

# 設定

[PINS](../../reference/glossary.md#term-pins) は [SONiC](../../reference/glossary.md#term-sonic) 上に [P4RT](../../reference/glossary.md#term-p4rt) サービスを追加することで、外部の SDN コントローラから P4Runtime gRPC で [ASIC](../../reference/glossary.md#term-asic) を直接制御できるようにする機能です。本ページでは、PINS を実用的に動かすための設定フローを「P4RT を起動する」「コントローラ接続を許可する」「Send to Ingress / PacketIO を有効化する」の 3 フェーズで示し、よくある詰まりどころと対処も併記します。

CLI / [CONFIG_DB](../../reference/glossary.md#term-config_db) の reference 整備が PINS では他機能より薄いため (後述の「現時点で不足している reference」節を参照)、本ページの CONFIG_DB スキーマは [HLD](../../reference/glossary.md#term-hld) と既存実装（`sonic-buildimage/dockers/docker-sonic-p4rt`、`sonic-pins/`）から推定したものを示します。実機では必ず `redis-cli HGETALL` で実際のキーを確認してから運用に組み込んでください。

## このページの読み方: PINS は controller-driven 系

PINS は「運用者が `config p4rt ...` で 1 ルートずつ [ACL](../../reference/glossary.md#term-acl) / route / nexthop を入れる」プロダクトではありません。**人手で CLI を打つのは P4RT 自体の起動 / 証明書配備 / feature toggle あたりまで**で、データプレーンの設定 (route, ACL, nexthop, mirror, [VRF](../../reference/glossary.md#term-vrf) など) は基本的に外部の **P4 controller** が P4Runtime gRPC で直接 ASIC に書き込みます。本ページの CLI / `redis-cli` 例は「P4RT を立ち上げる側」と「障害時の状態確認」を中心に据え、データプレーンの flow 投入は controller 側の責務であることを念頭に読んでください。

代表的な設定経路は次の通りです。

| 経路 | 用途 | 投入先 |
|---|---|---|
| P4 controller (P4Runtime gRPC) | 本番。ForwardingPipelineConfig + Write RPC で flow を大量投入 | `p4rt-app` 経由で `APPL_DB:P4RT_TABLE` → [SAI](../../reference/glossary.md#term-sai) |
| [gNMI](../../reference/glossary.md#term-gnmi) (`/openconfig-interfaces:interfaces` 等) | port / VRF / interface の基盤側 | `CONFIG_DB` 各種 |
| `config feature state p4rt enabled` / `redis-cli` | 初期セットアップ、証明書配置、コンテナ起動 | `CONFIG_DB:FEATURE`、`CONFIG_DB:P4RT` |
| `config route` 等の通常 SONiC CLI | **PINS と併用するモードでは原則使わない**（P4 controller の所有権と競合） | — |

典型的な投入フローは次の形になります。

```text
P4 Controller
  └─ SetForwardingPipelineConfig (P4Info + p4_device_config)
       └─ p4rt-app (P4Runtime server on SONiC)
            └─ APPL_DB:P4RT_TABLE
                 └─ p4orch
                      └─ SAI (ACL, route, nexthop, mirror, ...)
                           └─ ASIC

  └─ Write RPC (TableEntry / PacketOut)
       └─ p4rt-app
            └─ (PacketOut の場合) genetlink (psample) → kernel → send_to_ingress hostif → ASIC
            └─ (TableEntry の場合) APPL_DB → SAI → ASIC
                                    ↑
                                 反映エラーは StreamMessageResponse / WriteResponse で controller に返る
```

確認も「controller 側で Read RPC を叩いて ForwardingPipelineConfig と TableEntry を取得する」が一次手段で、`show` CLI は副次的です (そもそも PINS 専用 `show` CLI はほぼ未整備)。エラーは **gRPC status code (`INVALID_ARGUMENT`, `UNAUTHENTICATED`, `RESOURCE_EXHAUSTED`, `FAILED_PRECONDITION` 等) と P4Runtime のメッセージ単位エラー** で controller に通知されます。

## controller-driven 系のエラー対処

PINS で controller 側が出すエラーは、層ごとに切り分けると見通しが良くなります。

| 層 | 代表的な症状 (gRPC status) | 一次切り分け |
|---|---|---|
| トランスポート | `UNAVAILABLE`、`DEADLINE_EXCEEDED` | `ss -lntp \| grep 9559`、`docker ps \| grep p4rt`、ファイアウォール / ACL |
| 認証 | `UNAUTHENTICATED`、`PERMISSION_DENIED` | mTLS の CA chain、`server_cert` / `client_auth`、証明書期限 |
| 仲裁 | `ALREADY_EXISTS` / master 切替後の `PERMISSION_DENIED` | controller の `election_id`、`p4rt-app` ログの "Master arbitration" |
| パイプライン | `INVALID_ARGUMENT` on `SetForwardingPipelineConfig` | P4Info と SAI capability 不整合、`--p4info` ログ |
| フロー書込 | `WriteResponse` 内の per-entry `INVALID_ARGUMENT` / `RESOURCE_EXHAUSTED` | テーブル / アクションが SKU でサポートされているか、テーブル容量 |
| PacketIO | PacketIn が来ない、PacketOut が ASIC に届かない | [CoPP](../../reference/glossary.md#term-copp) trap install、`psample` genl、`send_to_ingress` netdev |

```bash
# controller 視点に近い確認 (NPU 上で代替)
docker logs p4rt 2>&1 | tail -100
redis-cli -n 0 KEYS 'P4RT_TABLE*' | head
redis-cli -n 1 KEYS 'ASIC_STATE:SAI_OBJECT_TYPE_ACL_ENTRY:*' | wc -l

# 反映失敗の SAI status
grep -E 'SAI_STATUS_(NOT_SUPPORTED|FAILURE|TABLE_FULL)' /var/log/swss/sairedis.rec | tail

# PacketIO 経路 (kernel 側の genetlink)
ip link show send_to_ingress
sudo tcpdump -i psample -n -c 5
```

CLI で「読むだけ」したいときは `show feature status p4rt` / `docker logs p4rt` / `redis-cli -n 0 HGETALL P4RT_TABLE:...` が中心で、`config` 系は **P4 controller の所有権と競合させない**ことが鉄則です。controller が管理しているテーブルに `config route add` や `config acl add` で書き込むと、controller 側の reconciliation で上書きされたり、逆に SONiC 側の view と SAI の view が乖離します。

## 全体フロー

```text
1. FEATURE.p4rt.state = enabled で p4rt container を起動
2. P4RT_TABLE で gRPC port / TLS / 認証パラメータを設定
3. (任意) APPL_DB に SEND_TO_INGRESS_PORT を投入し再注入 hostif を作成
4. (任意) COPP_TRAP_GROUP の genetlink_* を設定し PacketIO Receive を有効化
5. controller から P4Runtime で接続、ForwardingPipelineConfig を流し込み
```

## シナリオ 1: 単一コントローラ + plaintext gRPC (lab)

評価環境で、認証なし TCP gRPC でコントローラを 1 台つなぐ最小構成です。本番では使わないこと。

### 設定手順

```bash
# p4rt feature を有効化
sudo config feature state p4rt enabled

# config reload で container を起動 (または systemctl で個別起動)
sudo systemctl start p4rt

# 起動を確認
docker ps | grep p4rt
sudo docker exec p4rt netstat -lnt | grep 9559
```

### CONFIG_DB (P4RT|p4rt)

```json
{
  "P4RT|p4rt": {
    "grpc_port": "9559",
    "use_genetlink": "true",
    "tls": "false"
  }
}
```

```bash
# redis-cli で直接投入する例 (CLI が未整備のため)
redis-cli -n 4 HSET "P4RT|p4rt" grpc_port 9559 use_genetlink true tls false
sudo systemctl restart p4rt
```

### 確認

```bash
# gRPC port が listen しているか
sudo ss -lntp | grep 9559

# p4rt-app のログ
docker logs p4rt 2>&1 | tail -50

# CONFIG_DB の現在値
redis-cli -n 4 HGETALL "P4RT|p4rt"
```

## シナリオ 2: 二重化コントローラ + mTLS (本番想定)

複数 SDN コントローラから election ID で master/standby を切り替える本番運用。mTLS で証明書認証を行います。

### 証明書配備

```bash
# /etc/sonic/credentials/ に CA 証明書とサーバ証明書を配置
sudo mkdir -p /etc/sonic/credentials
sudo cp ca.crt server.crt server.key /etc/sonic/credentials/
sudo chmod 600 /etc/sonic/credentials/server.key
```

### CONFIG_DB

```json
{
  "P4RT|p4rt": {
    "grpc_port": "9559",
    "tls": "true",
    "server_cert": "/etc/sonic/credentials/server.crt",
    "server_key": "/etc/sonic/credentials/server.key",
    "ca_cert": "/etc/sonic/credentials/ca.crt",
    "client_auth": "require",
    "use_genetlink": "true"
  }
}
```

### controller 接続テスト

```bash
# gRPC reflection が拒否されることを確認 (mTLS 必須)
grpcurl -plaintext switch:9559 list  # → 失敗するはず

# クライアント証明書を提示すれば応答する
grpcurl -cacert ca.crt -cert client.crt -key client.key \
  switch:9559 list
```

二重化時の election ID 競合と arbitration の振る舞いは [P4RT App HLD](../../management/p4rt-application-hld.md) の "Master arbitration" 節を参照してください。SONiC 側で election ID を強制する CONFIG_DB エントリは現在無く、コントローラ側の SetMasterArbitrationUpdate に委ねる設計です。

## シナリオ 3: PacketIO + Send to Ingress を有効化

PINS でデータプレーン punt (PacketIn) と CPU 注入 (PacketOut / Send to Ingress) を使う場合の追加設定です。

### Send to Ingress hostif

`SEND_TO_INGRESS_PORT` を [APPL_DB](../../reference/glossary.md#term-appl_db) に宣言すると `PortsOrch` が `send_to_ingress` netdev を生成します。CONFIG_DB ではなく APPL_DB なので注意:

```bash
# APPL_DB は db number 0
redis-cli -n 0 HSET "SEND_TO_INGRESS_PORT_TABLE:send_to_ingress" NULL NULL

# hostif が作られたか確認
ip link show send_to_ingress
```

`ip link show send_to_ingress` で `state UP` の netdev が見えれば、`PortsOrch::addSendToIngressHostIf()` が `SAI_HOSTIF_TYPE_NETDEV` で hostif を作成済みです。

### CoPP trap group (genetlink)

`copp_cfg.j2` の `queue2_group1` を再利用するか、独自の trap group を作って `genetlink_name` / `genetlink_mcgrp_name` を設定します:

```json
{
  "COPP_GROUP|p4rt_punt": {
    "queue": "2",
    "trap_action": "trap",
    "trap_priority": "2",
    "genetlink_name": "psample",
    "genetlink_mcgrp_name": "packets",
    "meter_type": "packets",
    "mode": "sr_tcm",
    "cir": "6000",
    "cbs": "6000",
    "red_action": "drop"
  }
}
```

```bash
redis-cli -n 4 HSET "COPP_GROUP|p4rt_punt" \
  queue 2 trap_action trap trap_priority 2 \
  genetlink_name psample genetlink_mcgrp_name packets \
  meter_type packets mode sr_tcm cir 6000 cbs 6000 red_action drop
```

詳細は [PacketIO HLD](../../management/packetio.md) と [Send to Ingress HLD](../../management/send-to-ingress-hld.md) を参照してください。

## show / 確認コマンド

PINS 固有の show CLI は未整備のため、汎用 SONiC コマンド + redis-cli + docker exec で代替します。

```bash
# p4rt container の health
docker inspect p4rt --format '{{.State.Health.Status}}'

# CONFIG_DB の P4RT 系
redis-cli -n 4 KEYS 'P4RT*'
redis-cli -n 4 KEYS 'COPP_*' | grep -i p4rt

# APPL_DB の SEND_TO_INGRESS / hostif
redis-cli -n 0 KEYS 'SEND_TO_INGRESS*'
redis-cli -n 0 KEYS 'HOSTIF_TABLE*'

# ASIC_DB の hostif object (実際に SAI に降りたか)
redis-cli -n 1 KEYS 'ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:*'

# CoPP trap group の SAI 反映
redis-cli -n 1 KEYS 'ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP:*'

# 統計
show platform summary
show interfaces counters
```

## よくある設定エラーと対処

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| `docker ps` に p4rt がいない | `FEATURE\|p4rt` が `disabled` または image に同梱されていない | `config feature state p4rt enabled` + `config save -y` + image が `INCLUDE_P4RT=y` でビルドされているか確認 |
| controller から `Unavailable: Connection refused` | gRPC port が listen していない / container 内で bind 失敗 | `docker logs p4rt`、`grpc_port` の重複、ACL で 9559 が落ちていないか確認 |
| controller から `Unauthenticated` | TLS 不一致、CA chain の検証失敗 | `server_cert` / `ca_cert` パスが container に mount されているか、`docker exec p4rt openssl x509 -in /etc/sonic/credentials/server.crt -noout -dates` で期限確認 |
| `send_to_ingress` netdev が現れない | APPL_DB エントリが反映されていない / [VS](../../reference/glossary.md#term-vs) で SAI 対応外 | `redis-cli -n 0 KEYS 'SEND_TO_INGRESS*'`、`PortsOrch` ログ、ASIC が SAI_HOSTIF_TYPE_NETDEV + send_to_ingress を実装しているか確認 |
| PacketIn が来ない | CoPP trap が install されていない、policer drop | `redis-cli -n 1 KEYS 'ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:*'`、`show platform copp` (実装あれば)、`tcpdump -i psample` でカーネル側 genl の到達確認 |
| `swssconfig` が COPP_GROUP の `genetlink_*` を無視する | キー名 typo / hostif table channel 未対応 | `genetlink_name` `genetlink_mcgrp_name` のスペルと、ASIC ベンダの SAI capability `SAI_HOSTIF_TABLE_ENTRY_CHANNEL_TYPE_GENETLINK` 対応有無を確認 |
| ForwardingPipelineConfig push で `INVALID_ARGUMENT` | P4Info と SAI capability の不整合 | controller 側で対象 SKU 向け P4Info を使用、p4rt-app の `--p4info` ログを確認 |

## reference との対応

PINS 系の reference 整備は他機能より薄く、ここで使った CONFIG_DB / APPL_DB スキーマは HLD と実装から推定したものです。CI で機械的に裏取りされていないため、必ず実機の `redis-cli` 出力と突き合わせてください。間接的に参照できる reference:

- [reference/config-db/port.md](../../reference/config-db/port.md) — hostif / netdev 関連
- [reference/config-db/copp-group.md](../../reference/config-db/copp-group.md) — CoPP の trap group
- [reference/config-db/copp-trap.md](../../reference/config-db/copp-trap.md) — trap 個別
- [reference/yang/sonic-copp.md](../../reference/yang/sonic-copp.md) — CoPP [YANG](../../reference/glossary.md#term-yang) (schema 側の正本)

## 現時点で不足している reference

PINS 系は `reference/cli/*`、`reference/config-db/p4rt.md`、`reference/yang/sonic-p4rt.md` が未整備で、HLD の `config_db: []` / `cli: []` / `yang: []` が空のまま残っています。今後の reference batch で以下を補完予定:

- `reference/config-db/p4rt.md`: `P4RT` テーブルの key / field 一覧
- `reference/cli/p4rt.md`: `config feature state p4rt` 以外の専用 CLI (現状ほぼ無し)
- `reference/yang/sonic-p4rt.md`: YANG が定義されたら追従

それまでは本ページと HLD 群 ([PINS HLD](../../management/pins-hld.md)、[P4RT App HLD](../../management/p4rt-application-hld.md)、[PacketIO HLD](../../management/packetio.md)、[Send to Ingress HLD](../../management/send-to-ingress-hld.md)) を一次資料として運用してください。

## 関連ページ

- [PINS の概要](concept.md)
- [PINS のアーキテクチャ](architecture.md)
- [PINS の運用](operations.md)
- [PINS の internals](internals.md)
- [P4RT App HLD](../../management/p4rt-application-hld.md)
- [PacketIO HLD](../../management/packetio.md)
- [Send to Ingress HLD](../../management/send-to-ingress-hld.md)

<!-- glossary-links-injected: 9fb3fca99a59 -->
