---
title: 概要
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 概要

SONiC は「設定の入口」「制御プレーン daemon」「ASIC への橋渡し」が別プロセスで分かれており、これらを Redis 上の名前付き DB で結んでいる。機能章を読むときの共通語彙はこの章でまとめる。

## 内部実装章のスコープ

この章は機能（BGP、L2、ACL、VRF など）を語らない。代わりに、機能章のどこにでも出てくる次の要素を扱う。

| 要素 | 主に出てくる場面 | この章での扱い |
| --- | --- | --- |
| Redis DB 群 | 各機能章の「設定どこ」「状態どこ」 | DB の責務分担と命名規約 |
| orchagent | 機能ごとの sub-Orch（PortsOrch、RouteOrch、AclOrch、VxlanOrch 等） | APPL_DB → ASIC_DB の共通インタフェース |
| syncd / sairedis | 各機能章の「ASIC に書く」「offload する」 | ASIC_DB の async 適用と SAI 呼び出し |
| SAI | ベンダ間の差異吸収 | バージョン整合、capability 問い合わせ、失敗ハンドリング |
| Counter / Debug | telemetry、observability、ASIC 計数 | bulk/flex counter、dump、ERROR_DB |

機能章で個別に出てきた話を「内部実装側の共通テーマ」に揃え直すための章である。スキーマの全カラム表や CLI の細則は [`docs/reference/`](../../reference/index.md) が引き受け、個別 HLD は `docs/internals/` / `docs/architecture/` / `docs/platform/` / `docs/system/` 配下に残す。

## 機能章との重複を避けるための切り分け

機能章は「特定機能を運用するためにどの DB を見て、どの daemon を疑うか」を読み手の目的順で書く。この章は「DB と daemon そのものがどう設計されているか」を書く。

- 例: BGP route が ASIC に入るまでの経路は [BGP アーキテクチャ](../02-bgp/architecture.md) で読む。一方、ROUTE_TABLE 全般がどう APPL_DB と ASIC_DB に流れるか、ProducerStateTable とは何か、view switching とは何か、はここで読む。
- 例: ACL の SAI 呼び出し失敗を切り分けるときは [ACL 運用](../07-acl-copp-mirror/operations.md) で読む。一方、SAI 失敗そのものの ERROR_DB / handleSai*Status 設計はここで読む。

## DB の責務（早見表）

| DB | 役割 | 主な書き手 | 主な読み手 |
| --- | --- | --- | --- |
| `CONFIG_DB` | 永続化された設定 | CLI、gNMI、Mgmt Framework、bgpcfgd | 各 *cfgd、orchagent、起動スクリプト |
| `APPL_DB` | 制御プレーンが望む状態（intent） | bgpcfgd、fpmsyncd、portsyncd、teamsyncd、各 *mgrd | orchagent の各 sub-Orch |
| `STATE_DB` | 実際の状態と監視のヒント | 各 daemon、syncd | CLI（show）、監視 |
| `COUNTERS_DB` | ASIC からの counter 集計 | flexcounter / bulk counter | telemetry、show CLI |
| `ASIC_DB` | SAI 呼び出し直前の object 表現 | orchagent | syncd（sairedis 経由） |
| `ERROR_DB` | SAI 失敗を app に伝える | syncd（handleSai*Status） | orchagent、Error Handling Framework |
| `LOGLEVEL_DB` 他 | ログ等の補助 | 各 daemon | swssloglevel など |

スキーマの一次ソースは [swss-schema](../../internals/swss-schema.md) を読む。

## この章での読み方

DB と daemon の地図がほしい人は [アーキテクチャ](architecture.md) を先に読む。multi-namespace（Multi-ASIC）や独自 Redis instance を構成したい人は [設定](setup.md) に進む。SAI 失敗の見方を覚えたい人は [運用](operations.md) と [内部実装](internals.md) を続けて読む。bulk/flex counter、debug、dump の設計差は [内部実装](internals.md) を読む。startup や warm reboot の view switching は [発展トピック](advanced.md) に置いた。

## 関連ページ

- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](../../internals/swss-schema.md)
- [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md)
- [ZMQ ProducerStateTable / ConsumerStateTable 設計](../../internals/zmq-producer-consumer-state-table-design.md)
