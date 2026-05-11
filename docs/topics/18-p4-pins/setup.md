---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/management/pins-hld.md
  - docs/management/p4rt-application-hld.md
  - docs/management/send-to-ingress-hld.md
---

# 設定

PINS の設定は「P4RT サービスを起動する」「controller 接続の認証 / port を確認する」「PacketIO / Send to Ingress 用のポートを宣言する」の 3 段で読みます。CLI / CONFIG_DB の reference ページが現時点で薄いため、ここでは HLD と既存実装を起点に最小構成を示し、足りない参照は後続章とリンクします。

## P4RT サービスの起動

p4rt-app は専用 Docker（`docker-sonic-p4rt`）で動き、`p4rt.service.j2` から systemd unit が生成されます。デフォルトでは TCP port **9559** で gRPC を待ち受け、SDN コントローラからの接続を受け付けます。`p4rt.sh` / `p4rt_vars.j2` で port や TLS 関連の起動引数を制御します。

設定の起点になる項目:

- gRPC port（既定 9559）
- TLS 証明書 / mTLS（コントローラ認証）
- AppDb / APPL_STATE_DB の接続先（同一ホスト上の Redis）

詳細は [P4RT App HLD](../../management/p4rt-application-hld.md) を参照してください。

## P4RT CONFIG_DB エントリ

`P4RT` table は controller との接続パラメータ系で、p4rt-app の起動引数として読まれます。schema は [P4RT App HLD](../../management/p4rt-application-hld.md) の `related.config_db` に示されています。SONiC 標準の `config db` CLI から P4RT 専用のサブコマンドは現時点で薄く、reference 章が追従していないため、運用では `redis-cli -n 4 HGETALL "P4RT|..."` で直接確認するのが現実的です。

## Send to Ingress ポート

ASIC の ingress pipeline 再注入を有効化するには、`SEND_TO_INGRESS_PORT` を APPL_DB に宣言します。

```
APP_SEND_TO_INGRESS_PORT_TABLE:send_to_ingress
    NULL = NULL
```

`PortsOrch` がこのエントリを検出すると `addSendToIngressHostIf()` で `SAI_HOSTIF_TYPE_NETDEV` 属性を設定した hostif を作成し、`send_to_ingress` netdev がホスト側に現れます。CONFIG_DB → APPL_DB の経路は `cfgmgr/portmgrd.cpp` 側でも扱われます。詳細は [Send to Ingress HLD](../../management/send-to-ingress-hld.md) を参照してください。

## CoPP の generic netlink trap group

PacketIO Receive はベンダ kernel module（`genl_packet` 系）と CoPP trap group の `genetlink_name` / `genetlink_mcgrp_name` 設定で動きます。`copp_cfg.j2` の `queue2_group1` には次のような設定が入っています:

```
"queue2_group1": {
    "genetlink_mcgrp_name": "packets",
    "genetlink_name": "psample",
    ...
}
```

controller 側で punt flow を install すると、対応する trap group が hostif type `SAI_HOSTIF_TABLE_ENTRY_CHANNEL_TYPE_GENETLINK` で作成され、p4rt-app に generic netlink でパケットが届きます。詳細は [PacketIO HLD](../../management/packetio.md) を参照してください。

## 現時点で不足している reference

PINS 系は `reference/cli/*`、`reference/config-db/*`、`reference/yang/*` の整備が他機能より薄く、`config_db: []` / `cli: []` / `yang: []` のままの HLD が多い状況です。reference を引きたい場合は、`docs/reference/config-db/` の `port.md`、`copp-group.md`、`copp-trap.md`、および `docs/reference/yang/` の `sonic-copp.md` が間接的な参照として使えます。
