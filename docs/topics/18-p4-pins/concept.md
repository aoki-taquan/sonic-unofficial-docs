---
title: 概念
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/management/pins-hld.md
  - docs/management/p4rt-application-hld.md
---

# 概念

PINS は SONiC に「外部の SDN コントローラが **P4Runtime gRPC** を経由して forwarding を直接書く」経路を opt-in で足す仕組みです。BGP や orchagent といった従来の制御パスは残ったままで、コントローラが必要なテーブルだけを上書きする設計のため、`APPL_DB` の従来テーブル群と並んで `P4RT_TABLE` 系が増えると考えると掴みやすくなります。

## P4 / P4Runtime / PINS の関係

- **P4**: forwarding pipeline を記述するデータプレーン言語。pipeline の構造（テーブル、match、action、metadata）を `P4Info` として外部化できる。
- **P4Runtime**: コントローラと switch の間で P4Info を渡し、テーブルエントリを CRUD する **gRPC API**（v1.3.0）。
- **PINS**: SONiC で P4Runtime を受けるための実装一式。`p4rt-app` Docker、`P4Orch`、`APPL_STATE_DB`、`send_to_ingress`、generic netlink PacketIO で構成される。

P4 で表現する pipeline は SAI を模した形になっており、コントローラ側からは「SAI を P4 で書いている」ように見えます。これによりベンダ間 SAI 実装差の縮小と、controller の学習コストの低減を狙います。詳細は [PINS HLD](../../management/pins-hld.md) を参照してください。

## opt-in であることの意味

PINS は SONiC の動作モードを切り替えるものではなく、**コントローラが書いたテーブルだけ ASIC に追加で反映する** 構成です。BGP route と P4 route が同じ宛先に向くケースでは、どちらを優先するかは pipeline の P4 定義と P4Orch の SAI 呼び出し順に委ねられます。「PINS を入れた = 従来 SONiC が止まる」ではないため、運用上は両系統が同居していることを意識します。

## 同期書き込みと APPL_STATE_DB

通常の orchagent は `APPL_DB` を購読して SAI を非同期に呼び、結果は内部状態としか同期しません。一方 P4Orch は **同期実行** で SAI 応答を待ち、成否を **`APPL_STATE_DB`**（schema 上 DB 14）に書き戻すことで P4RT App がコントローラに正しいステータスを返せるようにします。これが「P4Orch だけ別物」と感じる根本理由です。詳細は [P4Orch HLD](../../internals/p4-orchagent.md) を参照してください。

## Send to Ingress と PacketIO の違い

- **PacketIO**: controller が install した punt flow にマッチしたパケットを **generic netlink** 経由でコントローラに届け、また controller から ASIC への送信も受ける機構。Receive と Transmit の両方を扱う。
- **Send to Ingress**: PacketIO の Transmit のうち、**ASIC の ingress pipeline にパケットを再注入する** モード。ECMP / WCMP の判定を ASIC に任せたいケースで使う。専用の `SEND_TO_INGRESS_PORT` テーブルと SAI hostif で実現する。

詳細は [PacketIO HLD](../../management/packetio.md) と [Send to Ingress HLD](../../management/send-to-ingress-hld.md) を参照してください。
