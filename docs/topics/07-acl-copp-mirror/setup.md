---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/config-acl.md
  - docs/reference/cli/show-acl.md
  - docs/reference/config-db/acl-table.md
  - docs/reference/config-db/acl-rule.md
  - docs/reference/config-db/policer.md
  - docs/reference/config-db/mirror-session.md
  - docs/reference/config-db/copp-group.md
  - docs/reference/config-db/copp-trap.md
  - docs/reference/yang/sonic-copp.md
  - docs/reference/yang/sonic-mirror-session.md
---

# 設定

ACL の最小設定は、table を作り、rule JSON を流し、show で確認する流れです。`config acl` は table の作成・削除と JSON の一括投入を提供しますが、個別 rule を CLI 引数で追加するインタフェースではありません。rule は JSON に書いて `config acl update full` または `incremental` で投入します。

## 最小 ACL

例として `Ethernet0` に入ってくる特定送信元を drop する L3 ACL を考えます。

```bash
config acl add table DATAACL L3 -p Ethernet0 -s ingress -d "drop selected sources"
```

rule は JSON で定義します。

```json
{
  "ACL_RULE": {
    "DATAACL|DROP_SRC_10_0_0_1": {
      "PRIORITY": "1000",
      "SRC_IP": "10.0.0.1/32",
      "PACKET_ACTION": "DROP"
    }
  }
}
```

投入は次の形です。

```bash
config acl update incremental acl-rules.json
show acl table DATAACL
show acl rule DATAACL
```

設定を読むときは `ACL_TABLE|DATAACL` の `type`、`stage`、`ports` を先に見ます。その後に `ACL_RULE|DATAACL|DROP_SRC_10_0_0_1` の `PRIORITY`、match、action を見ます。

## ACL_RULE の基本

`PRIORITY` は値が大きいほど優先です。match は `SRC_IP` / `DST_IP`、`SRC_IPV6` / `DST_IPV6`、`IP_PROTOCOL`、`L4_SRC_PORT` / `L4_DST_PORT`、`ETHER_TYPE`、`TCP_FLAGS` などを組み合わせます。action は `PACKET_ACTION`、`REDIRECT_ACTION`、mirror action、`POLICER`、DSCP 書換などです。

table type が action の可否を制限するため、rule JSON だけを別 table に移すと失敗することがあります。特に egress stage、mirror、DSCP 書換、packet trimming のような action は ASIC capability の影響を受けます。

## Policer

`POLICER` は単独で packet を分類しません。ACL rule、CoPP group、mirror session などから参照される rate limiting 部品です。`METER_TYPE`、`MODE`、`CIR` / `CBS`、`PIR` / `PBS`、色別 action を持ちます。

ACL で使う場合は rule の action として policer 名を参照します。CoPP では `COPP_GROUP` 内に queue、trap action、meter、rate を持つ形で control plane traffic に適用されます。

## Mirror Session

`MIRROR_SESSION` は SPAN または ERSPAN のセッション定義です。SPAN はローカル `dst_port` へコピーし、ERSPAN は `src_ip`、`dst_ip`、GRE type、DSCP、TTL などの outer header を持って collector へ送ります。

ACL と組み合わせる場合、先に mirror session を作り、`ACL_RULE` から `MIRROR_ACTION`、`MIRROR_INGRESS_ACTION`、`MIRROR_EGRESS_ACTION` で参照します。ポート単位で常時 mirror したい場合は `MIRROR_SESSION.src_port` / `direction` 側を読む方が近道です。

## CoPP

CoPP は `COPP_TRAP` が trap ID 群を定義し、`COPP_GROUP` が CPU queue と policer を定義します。`COPP_TRAP.trap_group` が `COPP_GROUP` を参照し、`coppmgr` が APPL_DB の `COPP_TABLE` に変換し、`CoppOrch` が SAI hostif trap / trap group / policer に反映します。

YANG の正本は `sonic-copp` で、`COPP_GROUP` と `COPP_TRAP` の tree、leaf、leafref を確認できます。mirror session の YANG は `sonic-mirror-session` で、ERSPAN / SPAN の必須条件や `POLICER` への leafref を確認できます。

## 関連ページ

- [config acl サブコマンド](../../reference/cli/config-acl.md)
- [show acl サブコマンド](../../reference/cli/show-acl.md)
- [ACL_TABLE テーブル](../../reference/config-db/acl-table.md)
- [ACL_RULE テーブル](../../reference/config-db/acl-rule.md)
- [POLICER テーブル](../../reference/config-db/policer.md)
- [MIRROR_SESSION テーブル](../../reference/config-db/mirror-session.md)
- [COPP_GROUP テーブル](../../reference/config-db/copp-group.md)
- [COPP_TRAP テーブル](../../reference/config-db/copp-trap.md)
- [sonic-copp YANG](../../reference/yang/sonic-copp.md)
- [sonic-mirror-session YANG](../../reference/yang/sonic-mirror-session.md)
