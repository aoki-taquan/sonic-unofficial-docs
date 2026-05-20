---
title: S3IP sysfs 仕様（platform 情報を /sys_switch/ で公開）
description: S3IP sysfs 仕様（platform 情報を /sys_switch/ で公開） — S3IP (Switch State 系の
  sysfs 仕様) は、platform hardware（温度・電圧・電流・FAN・PSU・xcvr・FPGA・CPLD・watchdog・slot・syseeprom・LED）…
area: platform
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/s3ip_sysfs/s3ip_sysfs_specification.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  _no_related_cdb: true
  cli:
  - show platform
  yang:
  - sonic-asic-sensors
  - sonic-chassis-module
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 14 章: Platform / Port / Optics](../topics/14-platform-port-optics/index.md) を参照。
<!-- /topics-tip -->

!!! info "裏取りステータス: code-verified"
    `sonic-buildimage/platform/s3ip-sysfs/` 直下に kernel module フレームワーク (`s3ip_sysfs_frame/`: `cpld_sysfs.c`, `temp_sensor_sysfs.c`, `vol_sensor_sysfs.c`, `curr_sensor_sysfs.c`, `fan_sysfs.c`, `psu_sysfs.c`, `transceiver_sysfs.c`, `sysled_sysfs.c`, `slot_sysfs.c`, `watchdog_sysfs.c`, `fpga_sysfs.c`, `switch.c`)、リファレンス driver (`demo_driver/`)、Makefile、init スクリプト (`scripts/s3ip-sysfs.service`, `s3ip_load.py`, `s3ip_sysfs_conf.json`) を確認。PDDF 経由でも `pddf_s3ip.py` が `/sys_switch/temp_sensor` 等を作成する。S3IP 仕様の `/sys_switch/` ツリー設計は SONiC 側に取り込み済み。

# S3IP sysfs 仕様（platform 情報を /sys_switch/ で公開）

## 概要

S3IP (Switch State 系の sysfs 仕様) は、platform hardware（温度・電圧・電流・FAN・PSU・xcvr・[FPGA](../reference/glossary.md#term-fpga)・CPLD・watchdog・slot・syseeprom・LED）の情報を **`/sys_switch/` 配下の決まったパスで公開する** 標準仕様[^1]。SONiC platform plugin が直接プラットフォーム driver を叩くのではなく **kernel が事前に sysfs を整える** ことで、vendor 別の plugin コードを薄くし、共通の platform monitor logic で扱えるようにする。本ページは仕様（path / 値域 / 型）の引き写しではなく、**カテゴリ毎に何が読めるか / どこが書ける（R/W）か** を整理する。

## 動作仕様

### 共通ルール

- すべての path は `/sys_switch/<category>/...` のフラット階層
- `number` は対象カテゴリの個数（例: `/sys_switch/temp_sensor/number`）
- 番号付き要素は `temp[n]`, `fan[n]`, `psu[n]` の様に角括弧表記の **0 始まり整数** index
- 単位は明示（millidegree Celsius / mV / mA / RPM 等）
- LED の値域は **enum 0..8**（dark / green / yellow / red / blue + flashing 系）[^1]

### LED 値域

| Value | 状態 |
|------:|------|
| 0 | dark |
| 1 | green |
| 2 | yellow |
| 3 | red |
| 4 | blue |
| 5-8 | 上記の flashing 版 |

### カテゴリ一覧

| カテゴリ | path | 主な属性 |
|---------|------|----------|
| 温度 | `/sys_switch/temp_sensor/temp[n]/` | `alias`, `type`, `max` (R/W), `min` (R/W), `value`（millidegree C）|
| 電圧 | `/sys_switch/vol_sensor/vol[n]/` | `alias`, `type`, `max` (R/W), `min` (R/W), `range`, `nominal_value`, `value` (mV) |
| 電流 | `/sys_switch/curr_sensor/curr[n]/` | `alias`, `type`, `max` (R/W), `min` (R/W), `value` (mA) |
| Syseeprom | `/sys_switch/syseeprom` | ONIE 形式の binary を直接読める |
| FAN | `/sys_switch/fan/fan[n]/` | metadata + `direction` (F2B/B2F), `ratio` (R/W 0-100), motor 配下に `speed` / `speed_target` / `speed_tolerance` / `speed_max` / `speed_min`、`status` (`0=absent / 1=normal / 2=abnormal`), `led_status` |
| PSU | `/sys_switch/psu/psu[n]/` | metadata + `type` (`0=DC / 1=AC`), `present`, `power_good`, voltage / current / power / temp 系（[HLD](../reference/glossary.md#term-hld) 後半）|
| Transceiver | `/sys_switch/transceiver/eth[n]/` | optic 情報 |
| System LED | `/sys_switch/sys_led/` | location / sys / fan / psu LED 群 |
| FPGA | `/sys_switch/fpga/fpga[n]/` | name / version / 各種 sub register |
| CPLD | `/sys_switch/cpld/cpld[n]/` | 同上 |
| Watchdog | `/sys_switch/watchdog/` | enable / timeout / current_state |
| Slot (modular) | `/sys_switch/slot/slot[n]/` | LC slot 情報 |

### Permission の傾向

- **Read-only (RO)**: metadata（model, serial, part_number, hardware_version, type, alias）、現在値（value, speed, status, led_status の一部）、定数（nominal_value, range, speed_target/max/min）
- **Read/Write (R/W)**: 警告閾値（temp/vol/curr の `max`, `min`）、FAN の `ratio`、`led_status`（書込可な場合）

`max` / `min` を **userspace から書き換えられる** ことで、policy 層（thermal-control / pmon）が hardware 寄りに閾値を埋め込める設計。

### Status enum（FAN 例）

```text
0: not present
1: present and normal
2: present and abnormal
```

PSU でも同様に `present` / `power_good` を独立に持つことで psud の状態判定を sysfs 経由で実装可能[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/s3ip_sysfs/s3ip_sysfs_specification.md#L33-L74 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  /sys_switch/temp_sensor/number RO int Total number of temperature sensors
  /sys_switch/temp_sensor/temp[n]/max R/W int Alarm threshold, unit: millidegree Celsius
reasoning: 仕様の path 規約と permission 表記の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/s3ip_sysfs/s3ip_sysfs_specification.md#L33-L74 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/s3ip_sysfs/s3ip_sysfs_specification.md#L33-L74 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    /sys_switch/temp_sensor/number RO int Total number of temperature sensors
    /sys_switch/temp_sensor/temp[n]/max R/W int Alarm threshold, unit: millidegree Celsius
    ```

    **判断根拠**: 仕様の path 規約と permission 表記の根拠。

<!-- evidence-rendered:end -->

## SONiC との関係

- **`s3ip_sysfs_framework_hld.md`** が SONiC platform API plugin 側の取込み方を扱う（本仕様と対）
- `psud` / `thermal_control` / `pmon` がここから読む形に置き換わると vendor plugin が大幅に薄くなる
- 既存の vendor 専用 sysfs（`/sys/bus/i2c/...` 直叩き等）を抽象する位置づけ

## 制限事項

- 本仕様は **kernel 側の sysfs 提供仕様**。userspace API は別途設計
- 数値の更新頻度や atomicity は仕様で規定されていない（driver 実装依存）
- modular switch / Smart Switch 等の階層は `slot` / 別途 namespace 化が必要

## 干渉する機能

- **psud / thermal_control / pmon-enhancement**: 主要消費者
- **xcvrd / sfp-refactor**: transceiver sysfs を介した optic 情報
- **system-eeprom / decode-syseeprom**: `/sys_switch/syseeprom` の ONIE 形式を共有
- **vendor 既存 sysfs**: 移行期間に併存

## 関連 reference

- [HLD: s3ip-sysfs-specification-and-framework](../architecture/s3ip-sysfs-specification-and-s3ip-sysfs-framework-hld.md)
- [Topics: Platform / Port / Optics](../topics/14-platform-port-optics/index.md)
- [CLI: show platform](../reference/cli/show-platform.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/s3ip_sysfs/s3ip_sysfs_specification.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- /sys_switch/ tree の現行 vendor 採用状況（platform/<vendor>/sonic_platform/）確認
- s3ip_sysfs_framework HLD と本仕様の対応 / SONiC 側 plugin 取り込み確認
- temp/vol/curr の max/min の R/W がどの consumer から書かれるか整合確認
- modular / Smart Switch slot への namespace 拡張の整合確認
- 仕様文書の数値型 (millidegree / mV / mA / RPM) と SONiC platform API の単位整合確認
-->

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Platform / Port / Optics / PHY](../topics/14-platform-port-optics/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: d12a6eddadee -->
