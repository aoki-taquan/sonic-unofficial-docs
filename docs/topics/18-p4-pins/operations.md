---
title: 運用
description: 運用 — PINS の運用で確認したいのは「コントローラの Write は ASIC に届いているか」「PacketIO / Send to
  Ingress の経路は活きているか」「Read が遅いときキャッシュは効いているか」の 3 点です。
area: topics
verification: meta
last_verified: 2026-05-11
sources:
- docs/management/packetio.md
- docs/management/send-to-ingress-hld.md
- docs/management/p4rt-read-cache-hld.md
related:
  cli:
  - show platform
  - show ip
  - show acl
  - config acl
  config_db:
  - ACL_RULE
  - ACL_TABLE
  - COPP_GROUP
  - COPP_TRAP
  - CRM
  - P4RT_TABLE
  - DEVICE_METADATA
  yang:
  - sonic-copp
  - sonic-crm
---

# 運用

[PINS](../../reference/glossary.md#term-pins) の運用で確認したいのは「コントローラの Write は [ASIC](../../reference/glossary.md#term-asic) に届いているか」「PacketIO / Send to Ingress の経路は活きているか」「Read が遅いときキャッシュは効いているか」の 3 点です。本ページでは出口（show / DB / ログ / kernel netlink）を実例で並べ、よくある異常と復旧手順を整理します。

## Write が ASIC に届いているかの確認

P4Orch は同期書き込みなので、コントローラの RPC レスポンス（gRPC `WriteResponse`）がそのまま成否を表します。レスポンスが OK にも関わらず ASIC に効いていないと感じる場合は、APPL_STATE_DB と [ASIC_DB](../../reference/glossary.md#term-asic_db) を直接見て切り分けます。

```bash
admin@sonic:~$ redis-cli -n 0 KEYS "P4RT_TABLE:*" | head
1) "P4RT_TABLE:FIXED_ROUTER_INTERFACE_TABLE:{...}"
2) "P4RT_TABLE:FIXED_NEIGHBOR_TABLE:{...}"
admin@sonic:~$ redis-cli -n 14 KEYS "P4RT_TABLE:*" | wc -l
12
admin@sonic:~$ redis-cli -n 14 HGETALL "P4RT_TABLE:FIXED_ROUTER_INTERFACE_TABLE:{...}"
1) "err_str"
2) "SWSS_RC_SUCCESS"
admin@sonic:~$ redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_ROUTER_INTERFACE:*" | wc -l
3
```

切り分けの目安は次のとおりです。

| [APPL_DB](../../reference/glossary.md#term-appl_db) | APPL_STATE_DB | ASIC_DB | 判定 |
| --- | --- | --- | --- |
| あり | `SWSS_RC_SUCCESS` | あり | 正常 |
| あり | `SWSS_RC_*` で失敗 | なし | P4Orch / [SAI](../../reference/glossary.md#term-sai) で拒否。`err_str` と [orchagent](../../reference/glossary.md#term-orchagent) ログを見る |
| あり | 無 | なし | P4Orch が pending（依存未解決）。例: route の前に nexthop 未 install |
| 無 | 無 | なし | p4rt-app が controller の write を受けていない。p4rt-app プロセスと gRPC を疑う |

p4rt-app と P4Orch のログは次で。

```bash
admin@sonic:~$ docker logs p4rt 2>&1 | tail
admin@sonic:~$ docker exec swss supervisorctl tail orchagent | grep -i p4orch
```

詳細な責務分担は [P4Orch HLD](../../internals/p4-orchagent.md) と [P4RT App HLD](../../management/p4rt-application-hld.md) を参照してください。

## CPU packet path（PacketIO Receive）の確認

PacketIO Receive は generic netlink + [CoPP](../../reference/glossary.md#term-copp) trap group が両方そろわないと届きません。次の順で確認します。

### 1. CoPP の trap group に genetlink が設定されているか

```bash
admin@sonic:~$ redis-cli -n 4 HGETALL "COPP_GROUP|queue2_group1"
1) "queue"
2) "2"
3) "genetlink_name"
4) "psample"
5) "genetlink_mcgrp_name"
6) "packets"
```

### 2. SAI hostif が genetlink チャネルで作られているか

```bash
admin@sonic:~$ redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:*" | head
admin@sonic:~$ redis-cli -n 1 HGETALL "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:oid:0x..." | grep -A1 CHANNEL_TYPE
SAI_HOSTIF_ATTR_TYPE
SAI_HOSTIF_TABLE_ENTRY_CHANNEL_TYPE_GENETLINK
```

`copporch.cpp` の `createGenetlinkHostIf()` 経路が走ったかは syslog で `CoppOrch.*genetlink` を grep します。

### 3. generic netlink family が kernel に登録されているか

```text
admin@sonic:~$ genl-ctrl-list | grep -i psample
psample
```

### 4. controller の punt flow に match する trap が発火しているか

```bash
admin@sonic:~$ aclshow -a
admin@sonic:~$ show ip access-lists
admin@sonic:~$ redis-cli -n 6 KEYS "USER_WATERMARKS|COPP_*"
```

`aclshow` で punt 用 [ACL](../../reference/glossary.md#term-acl) の counter が増えるか、CoPP queue の counter が増えるかを見ます。

### よくある罠

- ベンダ側 kernel の `genl_packet` filter 実装が無い ASIC では [HLD](../../reference/glossary.md#term-hld) どおりには動かない。`docker exec syncd dmesg | grep genl_packet` で確認。
- CoPP の policer に潰されて p4rt-app に届かない。`show platform inventory copp` や trap group の `cir` / `cbs` を見る。

詳細は [PacketIO HLD](../../management/packetio.md) を参照してください。

## Send to Ingress の使い分け

Send to Ingress は **ASIC の ingress pipeline にパケットを再注入する** モードです。

- **使う**: controller が宛先を決め切れず、[ECMP](../../reference/glossary.md#term-ecmp) / WCMP を ASIC に判定させたい。テスト用途で「CPU 起点で ingress に入れたパケットの ASIC ルーティングを観察したい」。
- **使わない**: 送信先 port がすでに決まっている。Direct transmit（対応 netdev のソケット）で十分。

確認手順:

```bash
admin@sonic:~$ ip link show send_to_ingress
42: send_to_ingress: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9100 qdisc noqueue state UNKNOWN
admin@sonic:~$ redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF:*" \
  | xargs -I{} redis-cli -n 1 HGET {} SAI_HOSTIF_ATTR_NAME 2>/dev/null \
  | grep -i send_to_ingress
```

`PortsOrch::addSendToIngressHostIf()` がコールされた痕跡は orchagent ログにあります。netdev が見えない場合は [CONFIG_DB](../../reference/glossary.md#term-config_db) の有効化、ASIC の対応、[syncd](../../reference/glossary.md#term-syncd) ログ（`SAI_STATUS_NOT_SUPPORTED`）を順に見ます。

詳細は [Send to Ingress HLD](../../management/send-to-ingress-hld.md) を参照してください。

## Read が遅いときの確認

Read の遅さは AppDb への `HGETALL` 大量発行が支配的でした。entity_cache_（旧 table_entry_cache_）が効いていれば 16,000 フローでも約 40ms に収まる想定です。

```bash
admin@sonic:~$ docker logs p4rt 2>&1 | grep -i "Read took"
admin@sonic:~$ docker logs p4rt 2>&1 | grep VerifyState
```

- p4rt-app のログで Read 時間が 1 秒オーダーで残っていれば、キャッシュが回避されている経路を疑う（直近の Write で AppDb 整合 mismatch、warm boot 直後でキャッシュ未充填、など）。
- Write 中の整合不一致は `P4RuntimeImpl::VerifyState()` が `VerifyP4rtTableWithCacheEntities` で検出する。エラーが出るなら controller 側の reconcile が必要。
- warm boot 時の事前充填は `warm_boot_state_adapter_` がフレームワーク化済み。warm boot 後最初の Read だけ遅い場合は、この充填が走ったかをログで確認。

詳細は [Read キャッシュ HLD](../../management/p4rt-read-cache-hld.md) を参照してください。

## ログの場所まとめ

| 経路 | ログ | grep キーワード |
| --- | --- | --- |
| p4rt-app | `docker logs p4rt` | `Write`、`Read took`、`VerifyState`、`genl` |
| orchagent (P4Orch) | `docker exec swss supervisorctl tail orchagent` | `P4Orch`、`SWSS_RC_` |
| syncd | `docker exec syncd supervisorctl tail syncd` | `SAI_STATUS`、`HOSTIF`、`HOSTIF_TABLE_ENTRY` |
| CoPP | `/var/log/syslog` | `CoppOrch`、`genetlink` |
| kernel | `dmesg` | `psample`、`genl_packet` |

## 異常検出パターン

| 観測 | 疑う状態 | 一次切り分け |
|---|---|---|
| controller の `WriteResponse` が `INVALID_ARGUMENT` | p4info 不一致、未対応 table、key 重複 | p4rt-app log の `Translate` 失敗、コントローラ側 p4info hash |
| `WriteResponse` OK だが `APPL_STATE_DB` に `err_str` 失敗 | P4Orch / SAI で reject | orchagent log の `P4Orch`、SAI status |
| `send_to_ingress` netdev が無い | platform 未対応、または有効化不足 | syncd の `SAI_STATUS_NOT_SUPPORTED`、CONFIG_DB の `SEND_TO_INGRESS` |
| PacketIO punt がコントローラに届かない | CoPP queue で drop、genetlink family 未登録 | `psample` family、CoPP counter、policer cir |
| Read 応答が秒オーダー | キャッシュ未充填、または VerifyState で再構築 | p4rt-app の `Read took`、`VerifyState` |
| controller 再接続後に flow が消える | session lifetime / role 設定の取り違え | controller 側 role config、Election ID |

## 対応コマンド早見表

| 目的 | コマンド |
|---|---|
| P4Orch 処理状況 | `redis-cli -n 14 KEYS "P4RT_TABLE:*"`、`HGETALL <key>` |
| ASIC 反映確認 | `redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_*"` |
| p4rt-app ログ | `docker logs p4rt` |
| orchagent (P4Orch) ログ | `docker exec swss supervisorctl tail orchagent` |
| send_to_ingress netdev | `ip link show send_to_ingress` |
| genetlink family | `genl-ctrl-list \| grep psample` |
| CoPP counter | `show platform inventory copp`、`aclshow -a` |
| process 状態 | `docker ps`、`docker exec p4rt supervisorctl status` |

## 典型的な運用シナリオ

1. **新規コントローラ接続** — gRPC 接続後、`SetForwardingPipelineConfig` で p4info を投入し、`WriteResponse` が OK になるかを確認します。`INVALID_ARGUMENT` が返るなら p4info と P4Orch 対応 table の差分を疑います。
2. **PacketIO punt 確認** — controller 側からの punt 設定後、テストフローを流して `aclshow -a` の counter が増えること、p4rt-app log で受信が見えることを順に確認します。届かないなら `psample` 経路と CoPP policer を順に切り分けます。
3. **warm boot 後の Read 性能確認** — `docker logs p4rt | grep "Read took"` で Read latency を確認し、warm boot 直後だけ遅い場合は `warm_boot_state_adapter_` の事前充填ログが出ているかを見ます。
4. **依存未解決 pending の解消** — APPL_DB にあるが APPL_STATE_DB に無い entry が残る場合、route の前提となる nexthop / router_interface が install されているかを順に確認します。controller 側 reconcile で順序を整え直します。
5. **コントローラ切替（standby → primary）** — Election ID と role config を確認し、新 primary が `SetForwardingPipelineConfig` を再投入する必要があるか、reconcile だけで済むかを判断します。

## 関連ページ

- [P4Orch HLD](../../internals/p4-orchagent.md)
- [P4RT App HLD](../../management/p4rt-application-hld.md)
- [PacketIO HLD](../../management/packetio.md)
- [Send to Ingress HLD](../../management/send-to-ingress-hld.md)
- [Read キャッシュ HLD](../../management/p4rt-read-cache-hld.md)
- [ACL / CoPP / Mirror 章](../07-acl-copp-mirror/index.md)（trap group / policer の詳細）
- [SWSS / SAI / Redis 章](../20-swss-sai-redis/index.md)（SAI 失敗観察）

<!-- glossary-links-injected: c006405759d8 -->
