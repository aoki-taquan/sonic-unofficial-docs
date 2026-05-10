---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/acl-qos/enhancements-on-show-acl-commands.md
  - docs/acl-qos/sonic-port-mirroring-hld.md
  - docs/acl-qos/everflow-test-plan.md
  - docs/acl-qos/configurable-drop-counters-in-sonic.md
  - docs/acl-qos/sonic-test-ingress-discards-hld.md
  - docs/architecture/port-illegal-packets-drop-design.md
---

# 運用

ACL / CoPP / mirror の調査では、設定が存在するか、ASIC に反映されたか、counter が増えるかを分けて確認します。CONFIG_DB に見えていることと、実際に hardware に作られていることは同じではありません。

## ACL の状態確認

最初に `show acl table` と `show acl rule` で table / rule の存在と status を見ます。show ACL 強化により、`AclOrch` が STATE_DB の `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` に Active / Inactive を出すため、リソース不足や SAI 失敗で作成できなかった場合を CLI 側から判別できます。

次に `aclshow` で rule counter を見ます。counter が期待通り増えない場合は、traffic が match していない、priority で別 rule に先に当たっている、counter polling が止まっている、ASIC に rule が入っていない、の順に切り分けます。

## Mirror の確認

Mirror は session と ACL action の 2 段で確認します。`MIRROR_SESSION` が有効になっているか、collector への経路があるか、SPAN の `dst_port` が正しいかを先に見ます。その後、mirror 用 ACL table / rule が Active で、該当 rule counter が増えるかを見ます。

Everflow では LAG、ECMP、neighbor MAC 変更、IPv6、egress ACL などが絡みます。mirror packet が出ない場合、ACL の match 失敗だけでなく、collector 経路や egress mirror capability も疑います。

## Drop 調査の入口

drop 調査では、何を落としているかで見る counter が変わります。

| 見たいもの | 主な入口 | 代表コマンド / DB |
|------------|----------|-------------------|
| ACL rule で drop したか | ACL counter | `aclshow` |
| port ingress discard | port counter | `portstat` |
| RIF / L3 error | interface counter | `intfstat` |
| drop reason 別の ASIC drop | debug counter | `show dropcounters counts` |
| CPU punt の量 | trap flow counter | `show flowcnt trap` |

不正パケットの ingress discard テストでは Ethernet 層、IP 層、ACL 層で期待 counter が異なります。`SMAC=DMAC` のような L2 drop と、TTL 0 や壊れた IP header のような L3 error と、ACL `DROP` は同じ場所に出ません。

## Debug Counter

設定可能な drop counter は SAI debug counter を使い、drop reason の組み合わせをユーザが定義します。`show dropcounters capabilities` で type ごとの残スロットとサポート理由を確認し、`config dropcounters install` で必要な counter を作ります。

drop counter は「なぜ落ちたか」を見る道具です。ACL counter は「どの rule に hit したか」を見る道具です。両方を同時に使うと、ACL で期待通り drop しているのか、別の ASIC reason で落ちているのかを分けられます。

## SNMP / MIB から見る場合

port illegal packets drop design は、RIF / VLAN など L3 側の SAI counter を Interface MIB へどう集約するかを扱います。SNMP で `ifInErrors` や `ifOutErrors` を監視している環境では、L2 port counter と RIF counter の集約方針がトラブルシュート結果に影響します。

## 関連ページ

- [show acl 強化](../../acl-qos/enhancements-on-show-acl-commands.md)
- [SONiC Port Mirroring](../../acl-qos/sonic-port-mirroring-hld.md)
- [Everflow テストプラン](../../acl-qos/everflow-test-plan.md)
- [設定可能な Drop Counter](../../acl-qos/configurable-drop-counters-in-sonic.md)
- [ingress discards テスト計画](../../acl-qos/sonic-test-ingress-discards-hld.md)
- [ポート不正パケットドロップ設計](../../architecture/port-illegal-packets-drop-design.md)
