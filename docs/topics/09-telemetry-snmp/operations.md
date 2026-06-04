---
title: 運用
description: 運用 — 障害調査では「どこまで生きているか」「いつから壊れたか」「保全は取れたか」の順で見ます。SONiC は調べる対象によって CLI
  が分かれているので、調査順をルーチン化しておくと迷いません。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show platform
  - show techsupport
  - show interfaces
  - show queue
  - config kdump
  - show acl
  - config snmp
  config_db:
  - SNMP
  - AUTO_TECHSUPPORT_FEATURE
  - SNMP_AGENT_ADDRESS_CONFIG
  - ACL_RULE
  - ACL_TABLE
  - PORT
  - PORTCHANNEL
  yang:
  - sonic-snmp
---

# 運用

障害調査では「どこまで生きているか」「いつから壊れたか」「保全は取れたか」の順で見ます。[SONiC](../../reference/glossary.md#term-sonic) は調べる対象によって CLI が分かれているので、調査順をルーチン化しておくと迷いません。

## 起動直後の確認

`show system-health summary` と `show system-health detail` で、システム全体の health monitor 状態と監視対象 daemon / service / docker の up/down を見ます。配下では `system-health` monitor が `system_health_monitoring_config.json` に従い、container や critical process、user defined check を polling しています。

`show system-health monitor-list` で「いま何を見ているか」、`show system-health events` で過去 24 時間のステータス変化を確認します。`system-ready` の [HLD](../../reference/glossary.md#term-hld) と組み合わせると、起動 sequence の途中で詰まっているのか、起動後に壊れたのかを切り分けられます。

```text
admin@sonic:~$ show system-health summary
System status summary

  System status LED  green
  Services:
    Status: OK
  Hardware:
    Status: OK

admin@sonic:~$ show system-health detail
System services and devices monitor list
Name                  Status    Type
--------------------  --------  -----------
bgp                   OK        Process
swss                  OK        Process
syncd                 OK        Process
teamd                 OK        Process
PSU 1                 OK        Device
Fan Tray 1            OK        Device
```

`Not OK` が見えた場合は対応する `Type` が手がかりです。Process なら docker と critical process、Device なら PMON / `pmon-daemon-control.json` を見ます。

```text
admin@sonic:~$ show system-health events
Name              Status    Last_Change_Time
----------------  --------  -------------------
bgp               OK        2026-05-10 02:13:11
swss              Failed    2026-05-10 04:01:00
swss              OK        2026-05-10 04:02:08
```

`Failed → OK` の遷移時刻が syslog の事象と一致するかを照合します。

## Counter で「いま」を見る

```text
show interfaces counters         # port basic
show queue counters              # queue
show priority-group counters     # PG
show acl counters                # ACL rule
show counters interface          # 拡張
counterpoll show                 # 各 flex counter group の状態
```

`counterpoll` group が `disable` の場合、対応する `COUNTERS:` table は更新されません。新しい port を増やしたあと、counter が空の場合は polling 設定を疑います。

異常検出パターン:

| 症状 | counter / DB | 典型原因 |
|------|--------------|----------|
| `show queue counters` が空 | `COUNTERS_QUEUE_NAME_MAP` 空 | `counterpoll queue` disable / [syncd](../../reference/glossary.md#term-syncd) 未起動 |
| `aclshow` が更新されない | `COUNTERS_DB` [ACL](../../reference/glossary.md#term-acl) counter | `counterpoll acl` disable |
| `portstat` の数字が増えない | `COUNTERS:Ethernet*` | syncd / [orchagent](../../reference/glossary.md#term-orchagent) stuck、[SAI](../../reference/glossary.md#term-sai) hang |
| すべての counter が止まる | flexcounterd | `docker ps` で syncd / flexcounter 確認 |

## 障害時の保全: techsupport

`show techsupport` は `/var/dump/sonic_dump_*.tar.gz` を生成します。中身は CLI 一式、`/var/log/` 配下、core dump、syslog、[Redis](../../reference/glossary.md#term-redis) dump、journal などです。容量が大きいので、調査では `--since "2 hours ago"` のような時間窓制限を付けます。

Event-driven techsupport は coredump や critical event を契機に `show techsupport` を自動実行する仕組みです。`AUTO_TECHSUPPORT_FEATURE` で feature 単位の rate limit を制御し、同じ問題で tarball が爆発するのを防ぎます。

光モジュール障害の調査では、`show techsupport` が SFP EEPROM page の dump を含むため、`sfputil` で取り直さなくても tarball から transceiver state を読めます。

```bash
# 直近 2 時間に絞る
sudo show techsupport --since "2 hours ago"

# 生成された tarball を確認
ls -lh /var/dump/sonic_dump_*.tar.gz

# tarball 内の概要を見る
tar tzf /var/dump/sonic_dump_sw01_20260510_120000.tar.gz | head -40
```

典型的に時間がかかるのは `redis dump` と SAI dump です。`/etc/sonic/sonic_dump_*.conf` でセクションを絞ることもできますが、原則はデフォルトで取り、不要部分を後段で削るほうが安全です。

Event-driven techsupport の rate-limit を見るには:

```text
admin@sonic:~$ redis-cli -n 4 hgetall "AUTO_TECHSUPPORT_FEATURE|bgp"
1) "state"
2) "enabled"
3) "rate_limit_interval"
4) "600"

admin@sonic:~$ show auto-techsupport-feature
Feature  State    Rate Limit Interval
-------  -------  -------------------
bgp      enabled  600
swss     enabled  600
```

`rate_limit_interval` (秒) 以内に再発した同 feature の coredump では tarball を作りません。

## Dump utility で個別 object を深掘り

`sonic-dump -m PORT -i Ethernet0` のように、object と instance を指定すると、全 DB と対応 CLI 出力を 1 つの JSON にまとめます。「この port は [CONFIG_DB](../../reference/glossary.md#term-config_db) / [APPL_DB](../../reference/glossary.md#term-appl_db) / [STATE_DB](../../reference/glossary.md#term-state_db) / [COUNTERS_DB](../../reference/glossary.md#term-counters_db) / [ASIC_DB](../../reference/glossary.md#term-asic_db) のどこまで反映されているか」を 1 コマンドで横断確認できます。`show techsupport` よりも軽く、object と DB の整合性チェックに向きます。

## Platform を疑うとき

`show platform summary` / `show platform syseeprom` / `show platform psustatus` / `show platform fan` / `show platform temperature` / `show platform transceiver` / `show platform fwutil status` で、それぞれ PSU、fan、temp、optics、firmware を見ます。PMON コンテナと platform daemon (`psud` / `thermalctld` / `xcvrd` / `pcied` / `ssdmon`) が値を STATE_DB に書き、CLI が表示する構造です。

Platform 系の詳細（CMIS、thermal、PSU、SSD、PCIe）は別途 platform 章にまとまります。observability 章ではあくまで「show platform で health 系を読む入口」として扱います。

## Kernel が壊れたとき: kdump

カーネル panic / oops を保全するには kdump を有効化します。`config kdump enable` と memory 予約後 reboot で kdump kernel が常駐し、panic 時に `/var/crash/` に vmcore を残します。

Remote SSH 機能を使うと、`/etc/default/kdump-tools` を経由して vmcore を SSH 越しに別ホストへ送れます。ローカルディスクが limited な platform で活きる選択肢ですが、SSH 鍵と remote 側 directory の準備が前提です。

```text
admin@sonic:~$ show kdump status
Kdump Administrative Mode:  Enabled
Kdump Operational State:    Ready
Memory Reserved:            512M
Number of Kernel Core Files Stored:  0
```

`Operational State: Not Ready` のときは `dmesg | grep -i crashkernel` で起動オプションを確認します。`config kdump memory 512M` 後、reboot が必須です。

## SNMP 経路の確認

snmpd (`docker exec snmp ...`) と sonic_ax_impl が [SNMP](../../reference/glossary.md#term-snmp) を担います。MIB のうち、IF-MIB は port counter、ENTITY-MIB は platform inventory、SNMPv2-MIB の sysName 等が基本です。

```bash
# 外部ホストから
snmpwalk -v 2c -c public sw01 IF-MIB::ifInOctets
snmpwalk -v 2c -c public sw01 IF-MIB::ifInErrors

# 装置内で
docker exec -it snmp snmpwalk -v 2c -c public 127.0.0.1 SNMPv2-MIB::sysDescr
```

community / v3 user は CONFIG_DB の `SNMP_COMMUNITY` / `SNMP_USER` です。設定変更後は `systemctl restart snmp` が必要です。

## 調査の典型シーケンス

1. `show system-health summary` で全体把握。
2. 個別 daemon / docker が落ちていれば `docker logs` と syslog。
3. data plane の counter / drop は `show interfaces counters` と章 [07](../07-acl-copp-mirror/operations.md) の counter。
4. 設定整合性は `sonic-dump` で object 単位に深掘り。
5. 状況保全は `show techsupport`、kernel 壊れていれば kdump 確保。

## 対応コマンド早見表

| 症状 | 最初に叩くコマンド | 次に見る場所 |
|------|--------------------|--------------|
| 何かおかしい (漠然) | `show system-health summary` | events、daemon up/down |
| docker が落ちる | `docker ps -a` + `docker logs <name>` | `/var/log/swss/*` |
| counter が動かない | `counterpoll show` | `docker logs syncd` |
| 後から原因を調べたい | `show techsupport --since` | `/var/dump/`、coredump |
| kernel panic を保全したい | `show kdump status` | `/var/crash/`、remote ssh |
| SNMP で値が来ない | `snmpwalk` + `docker logs snmp` | CONFIG_DB `SNMP_*` |
| object と DB の整合確認 | `sonic-dump -m PORT -i Ethernet0` | 各 DB の差分 |

## 関連章

- 章 [07 ACL / CoPP / mirror](../07-acl-copp-mirror/operations.md) — data plane drop の counter
- 章 [08 QoS / Buffer](../08-qos-buffer/operations.md) — queue / PG counter polling
- 章 [10 gNMI / OpenConfig](../10-gnmi-openconfig/operations.md) — telemetry を [gNMI](../../reference/glossary.md#term-gnmi) で取る
- 章 [11 Reboot](../11-reboot/operations.md) — reboot-cause / techsupport 連携

## 関連ページ

- [show system-health](../../reference/cli/show-system-health.md)
- [show techsupport CLI](../../reference/cli/show-techsupport.md)
- [show platform CLI](../../reference/cli/show-platform.md)
- [Event-driven techsupport](../../system/event-driven-techsupport-invocation-coredump-mgmt.md)
- [techsupport に SFP EEPROM を含める](../../system/dump-sfp-eeprom-page-data-in-show-techsupport-command.md)
- [kdump](../../system/kdump.md)
- [kdump remote SSH](../../system/kdump-remote-ssh.md)
- [Dump utility](../../internals/dump-utility-for-easy-debugging.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
