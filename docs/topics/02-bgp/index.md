---
title: BGP と FRR 制御プレーン
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# BGP と FRR 制御プレーン

この章は、SONiC の BGP を「設定を書く場所」「FRR へ渡る経路」「ASIC に入るまでの経路」「運用中に見る場所」の順に読み直すための入口である。既存ページは HLD 単位で詳しいが、BGP を運用する人が最初に知りたい境界は HLD の境界ではない。

主な問いは次の 4 つ。

- BGP neighbor、peer group、address family、policy はどこで設定し、誰が FRR に反映するのか。
- bgpd、zebra、fpmsyncd、orchagent、syncd は経路処理でどこまで責任を持つのか。
- BGP loading optimization、PIC、Suppress FIB Pending は、どの遅さや不整合を減らす機能なのか。
- BMP、CiscoBgp4MIB、dynamic peer、FRR upgrade、FRR-SONiC 通信チャネル変更は運用上どこに効くのか。

## 読む順番

1. [概要](concept.md): SONiC の BGP 制御プレーンを、設定面と経路面に分けて見る。
2. [アーキテクチャ](architecture.md): bgpd/zebra から fpmsyncd、orchagent、ASIC までの経路フローを追う。
3. [設定](setup.md): CONFIG_DB、CLI、YANG のどれを入口にするかを決める。
4. [運用](operations.md): 状態確認、BMP/MIB 監視、FIB 未導入時の切り分けを扱う。
5. [内部実装](internals.md): 大量経路ロード、PIC、Suppress FIB Pending、dynamic peer を比較する。
6. [発展トピック](advanced.md): VoQ、BFD for BGP、EVPN へ進む。

## 統合した既存ページ

この章は routing の HLD 派生ページ 20 件と reference ページ 19 件を横断している。細部のスキーマ、CLI、実装裏取りは各サブページ末尾の「関連ページ」から参照する。
