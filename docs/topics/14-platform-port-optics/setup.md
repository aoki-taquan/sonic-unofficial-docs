---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/config-interface.md
  - docs/reference/cli/config-platform-firmware.md
  - docs/reference/cli/show-platform.md
  - docs/platform/sonic-fw-utility.md
  - docs/platform/platform-capability-file-enhancement.md
  - docs/reference/config-db/port.md
  - docs/reference/yang/sonic-port.md
---

# 設定

ここでは、port 設定と platform 関連設定を、CLI / CONFIG_DB / YANG のどれから入るかという観点で整理します。全オプションは個別リファレンスに任せ、この章では入口の対応関係を示します。

## 入口の対応

| やりたいこと | CLI | CONFIG_DB | YANG |
|---|---|---|---|
| port の speed / FEC / autoneg | [config interface](../../reference/cli/config-interface.md) | [PORT](../../reference/config-db/port.md) | [sonic-port](../../reference/yang/sonic-port.md) |
| breakout モード変更 | [config interface](../../reference/cli/config-interface.md) (breakout サブコマンド) | `PORT` の lanes / speed | [sonic-port](../../reference/yang/sonic-port.md) |
| platform firmware の更新 | [config platform firmware](../../reference/cli/config-platform-firmware.md) | - | - |
| platform 情報の確認 | [show platform](../../reference/cli/show-platform.md) | `DEVICE_METADATA`、`CHASSIS_INFO` 等 | - |

CONFIG_DB を直接いじる場面は限られますが、CLI が未対応のカラムを設定するときは `sonic-cfggen` か `redis-cli` で `PORT` テーブルを更新します。

## 典型操作の最小例

これらはイメージです。実環境の正確な引数は CLI リファレンスを必ず確認してください。

```bash
# admin 状態
config interface startup Ethernet0
config interface shutdown Ethernet0

# 速度と FEC
config interface speed Ethernet0 100000
config interface fec Ethernet0 rs

# auto-negotiation
config interface autoneg Ethernet0 enabled
config interface advertised-speeds Ethernet0 25000,100000

# breakout
config interface breakout Ethernet0 "4x25G"
```

speed や FEC を変更すると、buffer profile や ACL bind が影響を受ける場合があります。QoS / ACL 章とあわせて読んでください。

## Platform firmware

`config platform firmware` 系コマンドは、装置内の各種 firmware (BIOS、CPLD、FPGA、SSD、optics) の表示・アップデート・スケジュール管理を扱います。

- [config platform firmware](../../reference/cli/config-platform-firmware.md): CLI の構造。
- [SONiC fw-utility](../../platform/sonic-fw-utility.md): 内部の `fw-util` がどう platform 実装を呼ぶかの設計。

CLI から呼ばれる `fw-util` は、`platform.json` と platform 実装が公開する component に依存して動きます。

## Platform capability ファイル

ASIC や platform が「何ができるか」を宣言する capability ファイルは、port 設定や機能の可否を実行前に判別するために使われます。詳細は [platform capability file enhancement](../../platform/platform-capability-file-enhancement.md) を参照してください。capability に書かれていない機能を設定で要求した場合、orchagent / SAI 層で reject されます。

## 関連ページ

- [config interface](../../reference/cli/config-interface.md)
- [config platform firmware](../../reference/cli/config-platform-firmware.md)
- [show platform](../../reference/cli/show-platform.md)
- [PORT テーブル](../../reference/config-db/port.md)
- [sonic-port YANG](../../reference/yang/sonic-port.md)
- [SONiC fw-utility](../../platform/sonic-fw-utility.md)
- [platform capability file enhancement](../../platform/platform-capability-file-enhancement.md)
