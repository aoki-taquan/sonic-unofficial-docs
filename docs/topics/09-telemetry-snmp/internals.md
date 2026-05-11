---
title: 内部実装
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/internals/sonic-flexcounter-refactor.md
  - docs/internals/sonic-counter-initialization-optimization.md
  - docs/internals/byte-packet-rates-port-utilization-in-sonic.md
  - docs/system/sonic-logging-system-dumps-arch-spec.md
---

# 内部実装

このページは、observability のうち SONiC 内部で「いつ何のスレッドが値を書いているか」を整理します。設定や運用の入口は前後のページで十分なので、ここは挙動の理由を読みたい人向けです。

## FlexCounter Group の仕事分担

syncd 内部に flex counter infrastructure があり、group ごとに次の項目を持ちます。

- 対象 SAI object（port、queue、PG、buffer pool、ACL counter、route flow、trap flow など）
- polling interval
- 対象 stat ID のリスト
- 有効化フラグ

`FLEX_COUNTER_TABLE|PORT` のような CONFIG_DB entry がこれらを制御します。group をまたぐ counter は同じ thread に乗らないため、port counter の interval を短くしても queue counter には影響しません。Refactor 以前は orchagent main loop に counter polling を抱えていたため、ACL や route 操作との競合がありました。

## Counter Initialization の bulk 化

起動直後、SONiC は全 port / queue / PG / ACL に対して flex counter を install しようとします。1 件ずつ install する古い実装では数百 port のシステムで数分かかることがあったため、bulk install API でまとめて登録するように変更されています。

Bulk 化の前後で外向きの API は変わりませんが、起動直後の `show interfaces counters` が空に見える時間が短くなり、`COUNTERS_PORT_NAME_MAP` の生成タイミングも早まります。Debug でこの map が空のときは、syncd が bulk 登録途中の可能性があります。

## Byte / Packet Rate の出どころ

ポート利用率を出す `show interfaces counters --rates` は、COUNTERS_DB の累積値そのものではなく、`portstat` ユーティリティが直前のスナップショットと現在値の差分を計算しています。一方、`RATES:` 系の table を期待するクエリは flex counter group `RATES` の更新に依存します。

「使用率の表示が止まる」原因は、累積値ではなく rate 計算側の polling、または `portstat` の cache `/tmp/portstat-*` の rotate です。累積 counter が動いているのに rate が出ないときは、まず group `RATES` の state を見ます。

## Logging Pipeline

syslog は container ごとの rsyslogd と host の rsyslogd が二段でつながります。Container の rsyslogd は `omfwd` で host の `/dev/log` 相当に転送し、host 側がさらに `SYSLOG_SERVER` で設定された外部宛先に送ります。`SYSLOG_CONFIG_FEATURE` は container 単位の severity 切替を許し、不要な debug を本番で抑えられます。

Auto-techsupport は、`coredump_gen_handler` が core 生成イベントを受け、`SystemReady` 達成後かつ rate limit 内であれば `show techsupport` を非同期で実行します。ディスク使用量とメモリ使用量の threshold を満たさないと skip し、syslog に reason を残します。

## SNMP Subagent の構造

SONiC SNMP は `snmp` container 内で snmpd と Python 実装の AgentX subagent (`sonic_ax_impl`) が動きます。subagent は Redis を購読し、IF-MIB / IF-X-TABLE / Entity MIB / RFC1213 / SONIC-LLDP 系などの OID 群を Redis の値から組み立てます。

OID から Redis path への mapping は subagent 内のクラスに分散しており、新しい MIB を増やすには subagent 側に MIB-specific クラスを書く必要があります。MIB を新設しない範囲では、Redis 側の table 構造を変えると subagent が古い key を見ようとして空値を返す挙動になる点に注意します。

## Telemetry Agent の subscribe path

`telemetry` / `gnmi` container は SONiC native YANG / OpenConfig を Redis path にマップし、gNMI Subscribe を CDB / SDB / APPL_DB の event listener に変換します。`ON_CHANGE` は Redis keyspace notifications に依存し、`SAMPLE` は内部の polling timer で current value を返します。

加えて telemetry-agent には、process / docker 統計、memory 統計、reboot cause のように「Redis に元々無い情報」を取り込んで gNMI で publish する拡張があり、これらは subscribe path として現れます（発展トピックで扱います）。

## 関連ページ

- [FlexCounter refactor](../../internals/sonic-flexcounter-refactor.md)
- [Counter initialization optimization](../../internals/sonic-counter-initialization-optimization.md)
- [Byte / packet rate と port utilization](../../internals/byte-packet-rates-port-utilization-in-sonic.md)
- [Logging と system dump 仕様](../../system/sonic-logging-system-dumps-arch-spec.md)
