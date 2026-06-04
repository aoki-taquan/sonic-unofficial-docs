---
title: 内部実装
description: 内部実装 — ここでは「SAI / syncd 層の整合性」「counter 系の性能改善」「debug / dump 基盤」を、改善が狙っている問題で比較する。機能章で「flex
  counter が…」「bulk counter が…」「CRM が…」と単発で出てきた話を、内部実装側で並べると棲み分けが見える。
area: topics
verification: meta
last_verified: 2026-06-04
sources:
- repo: sonic-net/sonic-sairedis
  path: syncd/Syncd.cpp
  ref: 88bc51ae95df66977601957515e5527119ffd4c5
- repo: sonic-net/sonic-sairedis
  path: syncd/SaiDiscovery.cpp
  ref: 88bc51ae95df66977601957515e5527119ffd4c5
- repo: sonic-net/sonic-sairedis
  path: syncd/ComparisonLogic.cpp
  ref: 88bc51ae95df66977601957515e5527119ffd4c5
- repo: sonic-net/sonic-sairedis
  path: syncd/FlexCounter.cpp
  ref: 88bc51ae95df66977601957515e5527119ffd4c5
- repo: sonic-net/sonic-sairedis
  path: lib/RedisRemoteSaiInterface.cpp
  ref: 88bc51ae95df66977601957515e5527119ffd4c5
- repo: sonic-net/sonic-sairedis
  path: lib/sairediscommon.h
  ref: 88bc51ae95df66977601957515e5527119ffd4c5
- repo: sonic-net/sonic-swss
  path: orchagent/orchdaemon.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/SONiC
  path: doc/architecture/sonic_architecture.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  cli:
  - show techsupport
  - show bfd
  - show acl
  - config acl
  - config vnet
  config_db: []
  yang: []
  _no_related_config_db: true
  _no_related_yang: true
---

# 内部実装

ここでは「[SAI](../../reference/glossary.md#term-sai) / [syncd](../../reference/glossary.md#term-syncd) 層の整合性」「counter 系の性能改善」「debug / dump 基盤」を、改善が狙っている問題で比較する。機能章で「flex counter が…」「bulk counter が…」「[CRM](../../reference/glossary.md#term-crm) が…」と単発で出てきた話を、内部実装側で並べると棲み分けが見える。

## SWSS / SAI / Redis のデータフロー

```mermaid
flowchart LR
  CFG[(CONFIG_DB)] --> MGR[*mgrd / cfgmgr]
  MGR --> APPL[(APPL_DB)]
  MGR --> KERNEL[Linux kernel]
  KERNEL -->|netlink| SYNCDAEMONS[*syncd<br/>portsyncd / fdbsyncd / fpmsyncd / natsyncd / teamsyncd]
  SYNCDAEMONS --> APPL
  APPL --> ORCH[orchagent<br/>per-feature Orch]
  ORCH --> ASIC[(ASIC_DB)]
  ASIC --> SAIREDIS[sairedis client<br/>in syncd]
  SAIREDIS --> SAILIB[SAI library<br/>libsai]
  SAILIB --> CHIP[(ASIC SDK)]
  ORCH --> STATE[(STATE_DB)]
  SAILIB -->|FLEX_COUNTER polling| COUNT[(COUNTERS_DB)]
  SAILIB -->|notification| ASICNOTIFY[ASIC notification channel]
  ASICNOTIFY --> ORCH
```

## 主要 Orch / daemon の責務（早見表）

| 層 | 代表 | 主実体 |
| --- | --- | --- |
| cfgmgr | `vlanmgrd`、`intfmgrd`、`teammgrd`、`vrfmgrd`、`buffermgrd`、`natmgr`、`portmgrd`、`vxlanmgrd`、`tunnelmgrd` | `cfgmgr/*.cpp` |
| sync | `portsyncd`、`fdbsyncd`、`fpmsyncd`、`teamsyncd`、`natsyncd` | `<sync>/<sync>.cpp` |
| Orch ([orchagent](../../reference/glossary.md#term-orchagent) process) | `PortsOrch`、`RouteOrch`、`NhgOrch`、`NeighOrch`、`AclOrch`、`QosOrch`、`BufferOrch`、`VxlanOrch`、`VNetOrch`、`NatOrch`、`FdbOrch`、`MirrorOrch`、`PolicerOrch`、`CrmOrch`、`SwitchOrch`、`Srv6Orch`、`MuxOrch`、`MACsecOrch`、`P4Orch`、`DashOrch` 系 | `orchagent/*.cpp` |
| syncd | `syncd`、`SAIRedis`、`flexcounter`、`SaiAttributeList`、`MetaInit` | `syncd/*.cpp` |
| sairedis | `RedisClient`、`AsicView`、`SaiRedisServer` | `lib/sai_redis_*.cpp` |
| swsscommon | `ProducerStateTable`、`ConsumerStateTable`、`SubscriberStateTable`、`NotificationConsumer`、`ZmqClient/Server`、`DBConnector` | `sonic-swss-common/` |

## SAI / Redis pub/sub 概観

| 経路 | 用途 |
| --- | --- |
| `__keyspace@N__:*` | CONFIG/APPL/STATE/COUNTERS の各 key 変更通知 |
| `ASIC_STATE` テーブル + `REDIS_ASIC_STATE_COMMAND_*` op | orchagent → syncd への [ASIC_DB](../../reference/glossary.md#term-asic_db) write/get/flush コマンド[^channel] |
| `NotificationProducer`（`RedisNotificationProducer` / `ZeroMQNotificationProducer`） | syncd → orchagent への notification（[FDB](../../reference/glossary.md#term-fdb) event / port state / [BFD](../../reference/glossary.md#term-bfd) 等）[^ntf] |
| ZMQ | 大量 push 経路（[VNET](../../reference/glossary.md#term-vnet) ZMQ、[DASH](../../reference/glossary.md#term-dash) SWBUS、gnmi-native-write） |

<!-- evidence
source: sonic-net/sonic-sairedis/lib/sairediscommon.h#L13
note: `#define ASIC_STATE_TABLE "ASIC_STATE"` で、ASIC_DB の hash テーブル名は固定の `ASIC_STATE`。専用の pub/sub チャネル名ではない。
-->
<!-- evidence
source: sonic-net/sonic-sairedis/lib/RedisRemoteSaiInterface.cpp#L860-L1150
note: orchagent から見た sairedis は `m_communicationChannel->set/del/wait` を `REDIS_ASIC_STATE_COMMAND_CREATE/SET/REMOVE/GET/FLUSH` の op 文字列で叩く。チャネル名ではなく op 種別で識別する。
-->
<!-- evidence
source: sonic-net/sonic-sairedis/syncd/Syncd.cpp#L141-L182
note: syncd→sairedis の notification は ZMQ endpoint があれば `ZeroMQNotificationProducer`、なければ `RedisNotificationProducer` を選択。`NotificationProcessor` がこれを駆動する。
-->


## 既知の実装上の制約（章末でも触れる）

- `redis-server` が単一スレッドで、APPL/CONFIG/STATE/COUNTERS を集約すると hot spot。複数インスタンス化が選択肢。
- sairedis async モードで「ASIC_DB write 成功」と「SAI 実反映」が分離。確認は notification か [COUNTERS_DB](../../reference/glossary.md#term-counters_db) で。
- SAI capability の問い合わせを起動時に行う設計（`sai_query_api_version` / `sai_query_attribute_capability` / `sai_query_stats_capability`）が増えており、起動時間が [ASIC](../../reference/glossary.md#term-asic) capability の数に比例して伸びる。
- 大量 route loading で `gRingBuffer` + assistant thread（`OrchDaemon::popRingBuffer`）が入ったが、orchagent main loop の lock contention は完全には消えていない[^ring]。

## SAI / syncd 整合性の三本柱

| 機能 | 改善する問題 | 主な層 | 設定面 |
| --- | --- | --- | --- |
| SAI API バージョン検査 | runtime SAI と build SAI のヘッダ不整合 | syncd / build | ビルド時 + `sai_query_api_version` |
| sai_query_stats_capability | counter のサポート差を起動ごとに探る | syncd / flexcounter | API 拡張のみ |
| Generic SAI Extension CRM | ベンダ拡張テーブルの resource 監視 | orchagent / CRM | `CRM_EXT_TABLE` |

### SAI API バージョン整合

[SONiC](../../reference/glossary.md#term-sonic) のビルドは `libsai` のヘッダに依存する。同じ syncd バイナリが古い libsai と新しいヘッダで組まれた状態で動くと、関数ポインタや enum 値のずれが silent な誤動作になりやすい。`sai_query_api_version` を起動時に呼び、ビルド時記録と突き合わせて mismatch を検知する設計が入っている。詳細は [SAI API バージョン整合チェック](../../platform/sai-api-version-check.md) を読む。

### stats capability の動的問い合わせ

counter のサポートはベンダ・ASIC・SAI バージョンで違う。すべての counter を試して失敗を拾うのは非効率なので、`sai_query_stats_capability` でサポートされる counter id 群を一括取得し、flexcounter の対象集合を起動時に決める設計である。詳細は [sai_query_stats_capability による Counter Capability 一括取得](../../platform/query-stats-capability-new-sai-api-indroduction.md) を読む。

### CRM の拡張テーブル

CRM はもともと SONiC 知識のあるリソース（route、neighbor、nexthop、[ACL](../../reference/glossary.md#term-acl) 等）を監視する。ベンダ拡張のテーブルが増えると、これに同じ仕組みで乗せたい。`CRM_EXT_TABLE` を `STATE_DB` 系に置き、ベンダから渡される resource キーを汎用に扱う設計が入っている。詳細は [Generic SAI Extension テーブルの CRM](../../system/generic-sai-extension-critical-resource-monitoring-crm.md) を読む。

## counter の改善

| 機能 | 改善する問題 | 主な層 | 設定面 |
| --- | --- | --- | --- |
| Bulk Counter | port 数 N に比例した個別 SAI 呼び出しの遅さ | syncd / sairedis | chunk size のみ |
| [FlexCounter](../../reference/glossary.md#term-flexcounter) Refactor | counter group 増加に伴うコード重複と性能ばらつき | syncd / flexcounter | 既存 API 維持 |
| Counter 初期化最適化 | 起動直後の counter 一斉登録による spike | syncd / flexcounter | 既存 API 維持 |

Bulk Counter は `sai_bulk_object_get_stats` により、1 回の SAI 呼び出しで複数 object の counter を取得し、chunk size を運用条件で調整する設計である。詳細は [Bulk Counter（sai_bulk_object_get_stats / chunk size）](../../architecture/sonic-bulk-counter-design.md) を読む。

FlexCounter Refactor は、port、queue、PG、buffer pool、ACL のように counter group ごとに肥大化していた個別実装を、`CounterContext` テンプレートに揃え直すリファクタである。詳細は [FlexCounter リファクタ（CounterContext テンプレート化）](../../internals/sonic-flexcounter-refactor.md) を読む。

Counter 初期化最適化は、`pending_sai_objects` に登録 object を一時集約してから `bulk_get_stats` で初期化する設計で、起動直後のレイテンシ spike を抑える。詳細は [flex counter 初期化最適化（pending_sai_objects + バッチ bulk_get_stats）](../../internals/sonic-counter-initialization-optimization.md) を読む。

## debug / dump の二系統

「テクサポ採取のため」と「能動的な調査のため」で、debug / dump は性格が違う。

| 機能 | 何を集めるか | 起点 |
| --- | --- | --- |
| Debug Framework | コンポーネント単位で登録された内部状態 dump、assert 拡張 | `show techsupport` / 障害時 |
| dump utility | モジュール（port、vrf 等）に紐づく複数 DB の key 集合 | オペレータの能動調査 |
| SAI failure dump | syncd の SAI 失敗時に SAI/ASIC_DB を snapshot | SAI 失敗の自動採取 |

Debug Framework と dump utility はオペレータ目線、SAI failure dump はベンダ調査目線で読むと整理しやすい。

## syncd の処理モデル

`syncd` は SAI を呼び出す唯一のプロセスで、内部で以下のスレッド構成を持つ。

| スレッド | 役割 |
| --- | --- |
| main | `ASIC_DB` の `_temp` key を読み、SAI API 呼び出しを順序通り発行 |
| notification | SAI からの notification（fdb_event、port_state_change、switch_shutdown）を [Redis](../../reference/glossary.md#term-redis) pub/sub に転送 |
| flexcounter | counter group ごとに polling し、`COUNTERS_DB` に書き込む（→ 09 章）[^flex] |
| dump | `SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP` 受信時に SAI / ASIC_DB を snapshot[^dump] |

sairedis library 側で async / sync モードが選べ、SONiC master はデフォルト async（pipeline で複数 op をまとめる）を採用する。sync モードは SAI 失敗の即時検知に有用だが throughput が落ちる。

## orchagent が ASIC_DB に接続する仕組み

orchagent は `DBConnector` で [APPL_DB](../../reference/glossary.md#term-appl_db) を直接読むが、ASIC_DB には **直接書かない**。代わりに `sairedis` クライアントライブラリ（`libsairedis`）が間に入り、SAI API 呼び出しを ASIC_DB の `ASIC_STATE:*` key に変換してから publish する（issue #466 の解説より）。

```
orchagent
  └─ sairedis API (create/set/remove/get)
       └─ libsairedis (redis pipeline)
            └─ ASIC_DB (ASIC_STATE:*)
                 └─ syncd (subscribe → SAI library → ASIC)
```

orchagent から見ると「SAI 関数を呼んでいる」が、実際は libsairedis が Redis にシリアライズして syncd に渡す非同期設計になっている[^sairedis]。[SONiC architecture](https://github.com/sonic-net/SONiC/wiki/Architecture) および [sonic_architecture.md](https://github.com/sonic-net/SONiC/blob/master/doc/architecture/sonic_architecture.md) の sairedis の項を参照。

## SaiDiscovery と applyViewTransition の役割

**SaiDiscovery** は syncd が warm reboot 復帰時に既存の ASIC 状態を Redis (ASIC_DB) に再構築するコンポーネントである[^discovery]：

1. `switch` オブジェクトを起点に、port・neighbor・route などの全 SAI object を再帰的に walk する（`SaiDiscovery::discover`）。
2. 各 object の `RID`（Real ID）と `VID`（Virtual ID）の対応を `VIDTORID` / `RIDTOVID` マップに登録する。
3. `applyViewTransition`（`Syncd::applyView` から呼び出される）がこの RID セットを「current view」として用いる。

**applyViewTransition** は[^applyview]：

- orchagent が送り込んだ再設定要求を「temporary view」として受け取り、
- SaiDiscovery で作った「current view」との diff を計算し、
- 差分（追加・削除・更新）だけを SAI に流す。

SaiDiscovery で列挙した RID（switch/port）は削除対象から除外されるため、これらのオブジェクトは warm reboot を跨いで保持される。

## ベンダ SAI と sai_query_attribute_capability

syncd は起動時に `sai_query_attribute_capability` を呼び、各 SAI object の attribute がそのベンダ SAI でサポートされるかを確認する。ベンダが libsai.so でこの関数を公開していない場合、syncd-vs や thirdparty syncd のビルド時にリンクエラーになる（issue #780）：

```
error: 'sai_query_attribute_capability' method is missing from libsai.so
```

対処: ベンダ SAI のヘッダ・実装が最新 SAI spec に追従していることを確認する。[VS](../../reference/glossary.md#term-vs) ビルドでは `sai_query_attribute_capability` のスタブ実装が必要な場合がある。

## 関連ページ

- [SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査）](../../platform/sai-api-version-check.md)
- [sai_query_stats_capability による Counter Capability 一括取得](../../platform/query-stats-capability-new-sai-api-indroduction.md)
- [Generic SAI Extension テーブルの CRM（CRM_EXT_TABLE）](../../system/generic-sai-extension-critical-resource-monitoring-crm.md)
- [Bulk Counter（sai_bulk_object_get_stats / chunk size）](../../architecture/sonic-bulk-counter-design.md)
- [FlexCounter リファクタ（CounterContext テンプレート化）](../../internals/sonic-flexcounter-refactor.md)
- [flex counter 初期化最適化（pending_sai_objects + バッチ bulk_get_stats）](../../internals/sonic-counter-initialization-optimization.md)
- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../../architecture/debug-framework-in-sonic.md)
- [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](../../internals/dump-utility-for-easy-debugging.md)
- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../../platform/dump-on-sai-failure.md)

## 引用元

[^channel]: ASIC_DB の hash テーブル名は `ASIC_STATE` 固定。`sonic-net/sonic-sairedis/lib/sairediscommon.h` L13: `#define ASIC_STATE_TABLE "ASIC_STATE"`。orchagent→syncd 方向の制御は専用 channel 名ではなく `REDIS_ASIC_STATE_COMMAND_CREATE / SET / REMOVE / GET / FLUSH / NOTIFY` などの op 文字列で識別する（`lib/RedisRemoteSaiInterface.cpp` L860-L1150）。
[^ntf]: syncd→orchagent の notification は ZMQ endpoint が構成されていれば `ZeroMQNotificationProducer`、そうでなければ `RedisNotificationProducer` を使う（`sonic-net/sonic-sairedis/syncd/Syncd.cpp` L141-L182、`NotificationProducer.cpp` L11-L51）。
[^flex]: counter group ごとに 1 つの `FlexCounter` インスタンスが起動し、`startFlexCounterThread` で `flexCounterThreadRunFunction` を spawn する（`sonic-net/sonic-sairedis/syncd/FlexCounter.cpp` L3031-L3577）。
[^dump]: `Syncd::processNotifySyncdInRedis` が `SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP` を受けて dump シェル（`syncd_dump.sh` 系）を起動する（`sonic-net/sonic-sairedis/syncd/Syncd.cpp` L4491-L4493、`syncd/scripts/sai_failure_dump.sh`）。
[^sairedis]: `RedisRemoteSaiInterface` が SAI create/set/remove/get を `ASIC_STATE` テーブルへの key/values と op 文字列に変換して publish し、syncd 側で順次取り出して `VendorSai` 経由で実 SAI を叩く（`sonic-net/sonic-sairedis/lib/RedisRemoteSaiInterface.cpp` L860-L970、`syncd/VendorSai.cpp` L52-L56）。
[^discovery]: `sonic-net/sonic-sairedis/syncd/SaiDiscovery.cpp` L22-L114 の `SaiDiscovery::discover` が switch RID を起点に attribute を走査して discovered set に追加する。
[^applyview]: `sonic-net/sonic-sairedis/syncd/ComparisonLogic.cpp` L123 の `applyViewTransition(current, temp)` および L3075 以降の同関数本体で diff を計算する。`Syncd::applyView`（`syncd/Syncd.cpp` L4790）から呼ばれ、entry point は `Syncd.cpp` L4641。
[^ring]: `OrchDaemon::popRingBuffer` と `gRingBuffer` の初期化・終了制御（`sonic-net/sonic-swss/orchagent/orchdaemon.cpp` L103-L150）。PR #4400 以前は SIGTERM 時に ring thread が exit せずハングする経路があった旨が同コードのコメントで言及されている。

<!-- glossary-links-injected: 9fb3fca99a59 -->
