---
title: VRF / ECMP / RIB-FIB パイプライン
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/sonic-vrf-support-design-spec-draft.md
  - docs/routing/static-ip-route-configuration.md
  - docs/routing/routing-and-next-hop-table-enhancement.md
  - docs/routing/sonic-fine-grained-ecmp.md
  - docs/routing/sonic-weighted-ecmp.md
---

# VRF / ECMP / RIB-FIB パイプライン

この章は、SONiC の L3 転送を「VRF と interface を作る」「route が FRR から APP_DB に来る」「orchagent が RIF / next hop / route object を ASIC に作る」「ECMP の種類を選ぶ」という順番で読み直す入口です。

既存ページは VRF、static route、RIF counter、ECMP 拡張などの HLD 単位で分かれています。この章では、運用者や実装を追う読者が実際に持つ質問の順に並べ替え、詳細なスキーマやコード裏取りは各ページの関連リンクへ譲ります。

## この章で答える質問

- VRF、interface、static route、next hop group はどの順番で理解すればよいか。
- `CONFIG_DB` / FRR / `APPL_DB` / orchagent / `ASIC_DB` のどこで route の形が変わるか。
- ECMP、WCMP、Fine Grained ECMP、Ordered ECMP、Class Based Forwarding は何が違うか。
- route counter、RIF counter、flow counter、loopback action は運用中にどこを見るか。
- VRRP、SAG、TSA、path tracing のような周辺機能はこの章のどこまでを前提にしているか。

## 読む順番

1. [概念](concept.md): VRF、RIF、static route、IPv6 link-local、management VRF を L3 の読み順として整理する。
2. [アーキテクチャ](architecture.md): FRR から `ROUTE_TABLE`、`NEXT_HOP_GROUP_TABLE`、RouteOrch、SAI route object までの流れを追う。
3. [設定](setup.md): `config vrf`、`config route`、CONFIG_DB、YANG を使った VRF 付き route の最小例を扱う。
4. [運用](operations.md): route / FIB / interface / RIF counter / route flow counter の確認順をまとめる。
5. [ECMP family](ecmp.md): ECMP、WCMP、FG ECMP、Ordered ECMP、Generic Hash、CBF の選び方を比較する。
6. [発展トピック](advanced.md): VRRP、SAG、TSA、他章への橋渡しを整理する。

## 統合した既存ページ

この章は routing / architecture / internals / reference の既存ページ 32 件を横断しています。個別コマンド、テーブル、YANG、HLD の詳細は各サブページ末尾の「関連ページ」から参照してください。

