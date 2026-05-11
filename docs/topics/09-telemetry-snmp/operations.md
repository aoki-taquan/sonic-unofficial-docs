---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/show-system-health.md
  - docs/reference/cli/show-techsupport.md
  - docs/reference/cli/show-platform.md
  - docs/system/event-driven-techsupport-invocation-coredump-mgmt.md
  - docs/system/dump-sfp-eeprom-page-data-in-show-techsupport-command.md
  - docs/system/kdump.md
  - docs/system/kdump-remote-ssh.md
  - docs/internals/dump-utility-for-easy-debugging.md
---

# 運用

障害調査では「どこまで生きているか」「いつから壊れたか」「保全は取れたか」の順で見ます。SONiC は調べる対象によって CLI が分かれているので、調査順をルーチン化しておくと迷いません。

## 起動直後の確認

`show system-health summary` と `show system-health detail` で、システム全体の health monitor 状態と監視対象 daemon / service / docker の up/down を見ます。配下では `system-health` monitor が `system_health_monitoring_config.json` に従い、container や critical process、user defined check を polling しています。

`show system-health monitor-list` で「いま何を見ているか」、`show system-health events` で過去 24 時間のステータス変化を確認します。`system-ready` の HLD と組み合わせると、起動 sequence の途中で詰まっているのか、起動後に壊れたのかを切り分けられます。

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

## 障害時の保全: techsupport

`show techsupport` は `/var/dump/sonic_dump_*.tar.gz` を生成します。中身は CLI 一式、`/var/log/` 配下、core dump、syslog、Redis dump、journal などです。容量が大きいので、調査では `--since "2 hours ago"` のような時間窓制限を付けます。

Event-driven techsupport は coredump や critical event を契機に `show techsupport` を自動実行する仕組みです。`AUTO_TECHSUPPORT_FEATURE` で feature 単位の rate limit を制御し、同じ問題で tarball が爆発するのを防ぎます。

光モジュール障害の調査では、`show techsupport` が SFP EEPROM page の dump を含むため、`sfputil` で取り直さなくても tarball から transceiver state を読めます。

## Dump utility で個別 object を深掘り

`sonic-dump -m PORT -i Ethernet0` のように、object と instance を指定すると、全 DB と対応 CLI 出力を 1 つの JSON にまとめます。「この port は CONFIG_DB / APPL_DB / STATE_DB / COUNTERS_DB / ASIC_DB のどこまで反映されているか」を 1 コマンドで横断確認できます。`show techsupport` よりも軽く、object と DB の整合性チェックに向きます。

## Platform を疑うとき

`show platform summary` / `show platform syseeprom` / `show platform psustatus` / `show platform fan` / `show platform temperature` / `show platform transceiver` / `show platform fwutil status` で、それぞれ PSU、fan、temp、optics、firmware を見ます。PMON コンテナと platform daemon (`psud` / `thermalctld` / `xcvrd` / `pcied` / `ssdmon`) が値を STATE_DB に書き、CLI が表示する構造です。

Platform 系の詳細（CMIS、thermal、PSU、SSD、PCIe）は別途 platform 章にまとまります。observability 章ではあくまで「show platform で health 系を読む入口」として扱います。

## Kernel が壊れたとき: kdump

カーネル panic / oops を保全するには kdump を有効化します。`config kdump enable` と memory 予約後 reboot で kdump kernel が常駐し、panic 時に `/var/crash/` に vmcore を残します。

Remote SSH 機能を使うと、`/etc/default/kdump-tools` を経由して vmcore を SSH 越しに別ホストへ送れます。ローカルディスクが limited な platform で活きる選択肢ですが、SSH 鍵と remote 側 directory の準備が前提です。

## 調査の典型シーケンス

1. `show system-health summary` で全体把握。
2. 個別 daemon / docker が落ちていれば `docker logs` と syslog。
3. data plane の counter / drop は `show interfaces counters` と章 [07](../07-acl-copp-mirror/operations.md) の counter。
4. 設定整合性は `sonic-dump` で object 単位に深掘り。
5. 状況保全は `show techsupport`、kernel 壊れていれば kdump 確保。

## 関連ページ

- [show system-health](../../reference/cli/show-system-health.md)
- [show techsupport CLI](../../reference/cli/show-techsupport.md)
- [show platform CLI](../../reference/cli/show-platform.md)
- [Event-driven techsupport](../../system/event-driven-techsupport-invocation-coredump-mgmt.md)
- [techsupport に SFP EEPROM を含める](../../system/dump-sfp-eeprom-page-data-in-show-techsupport-command.md)
- [kdump](../../system/kdump.md)
- [kdump remote SSH](../../system/kdump-remote-ssh.md)
- [Dump utility](../../internals/dump-utility-for-easy-debugging.md)
