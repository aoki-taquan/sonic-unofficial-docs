---
title: 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/acl-qos/copp-manager-redesign-test-plan.md
  - docs/acl-qos/copp-neighbor-miss-trap-and-enhancements.md
  - docs/acl-qos/dash-acl-tags.md
  - docs/acl-qos/port-access-control-in-sonic.md
  - docs/acl-qos/dhcp-dos-mitigation-in-sonic.md
---

# 発展トピック

このページは、ACL / CoPP / mirror の基本線から少し外れるが、同じ「分類、保護、観測、rate limit」の考え方で読める機能への案内です。通常運用の入口は前ページまでで足りることが多く、ここでは境界だけを整理します。

## CoPP Manager Redesign

CoPP Manager 再設計は、`COPP_TRAP` と `FEATURE` の整合性を見直し、feature が disabled または存在しない場合は trap を install しない、ただし `always_enabled=true` の trap は常に install する、というルールに整理します。

これは ACL rule の priority 問題ではなく、CPU bound trap をいつ hostif trap として作るかの問題です。BGP、ARP、LACP、UDLD、IP2ME などの trap が feature 状態とどう連動するかを読むときに参照します。

## CoPP Neighbor Miss と Capability

Neighbor miss trap は、ARP / ND 解決前の IP packet が CPU に集中して他の control plane traffic を巻き込む問題を避けるため、`SAI_HOSTIF_TRAP_TYPE_NEIGHBOR_MISS` を個別 policer に分離する拡張です。同時に、SAI enum capability query でサポート trap 一覧を STATE_DB に公開し、未対応 trap の install 失敗を可視化します。

CoPP のトラブルシュートでは、`show copp configuration` で trap が hardware に入っているかを見る入口になります。

## DASH ACL Tags

DASH ACL tags は、DASH の ACL rule でサービスを IP prefix 群として扱うための仕組みです。通常 ACL の `ACL_TABLE` / `ACL_RULE` ではなく、`DASH_PREFIX_TAG_TABLE` と `DASH_ACL_RULE_TABLE` の拡張として読みます。

通常 ACL との共通点は、match 対象を抽象化し、rule 生成時に展開することです。違いは、DASH pipeline と APP_DB schema が別系統であり、SONiC の data plane ACL 設定と同じ運用コマンドでは扱わないことです。

## Port Access Control

PAC は 802.1x / MAB / RADIUS によるポート単位の認証です。認証結果に応じて MAC、VLAN、learning mode、host trap を制御するため、ACL に似た「許可 / 不許可」の話に見えますが、主体は authentication manager、hostapd、mabd、RADIUS です。

ACL 章では、物理ポート単位の access 制御であり、LAG / VLAN への ACL bind とは別の設計として位置付けます。

## DHCP DoS 緩和

DHCP DoS 緩和は、従来 CoPP のシステム全体 DHCP rate limit では単一ポートの flood が他ポートの正規 DHCP を巻き込む問題を、ポート単位の Linux TC rate limit で局所化する設計です。

ただし既存ページでは discrepancy-found とされており、データ層や CLI は取り込まれている一方、HLD が要求する `portmgrd` の TC 投入ロジックや CoPP 側の完全な置き換えは未確認です。設計参考として扱い、実装判断では現行コードと platform 動作を確認します。

## 関連ページ

- [CoPP Manager 再設計テストプラン](../../acl-qos/copp-manager-redesign-test-plan.md)
- [CoPP Neighbor Miss trap と enum capability query](../../acl-qos/copp-neighbor-miss-trap-and-enhancements.md)
- [DASH ACL タグ](../../acl-qos/dash-acl-tags.md)
- [Port Access Control](../../acl-qos/port-access-control-in-sonic.md)
- [DHCP DoS 緩和](../../acl-qos/dhcp-dos-mitigation-in-sonic.md)
