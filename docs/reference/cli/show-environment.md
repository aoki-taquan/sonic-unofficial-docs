---
title: show environment サブコマンド
description: show environment サブコマンド — show environment は 電圧・ファン・温度センサの状態を lm-sensors
  経由で表示する click コマンド。実装は sudo sensors を起動するだけの薄いラッパ。
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
- repo: sonic-net/sonic-utilities
  path: show/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
  - show environment
  - show platform temperature
  - show platform fan
  - show platform psu
  yang: []
---

# show environment サブコマンド

## 概要

`show environment` は **電圧・ファン・温度センサ**の状態を `lm-sensors` 経由で表示する click コマンド。実装は `sudo sensors` を起動するだけの薄いラッパ[^1]。

## シグネチャ

```bash
show environment [--verbose]
```

| オプション | 意味 |
|---|---|
| `--verbose` | 起動コマンド文字列を echo |

## 実装

```python
@cli.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def environment(verbose):
    """Show environmentals (voltages, fans, temps)"""
    cmd = ['sudo', 'sensors']
    run_command(cmd, display_cmd=verbose)
```

出力内容は `/etc/sensors3.conf` および platform 提供の `sensors.conf` に依存する。プラットフォームベンダが lm-sensors 用設定を持ち込まない（あるいは `pmon` コンテナ経由でしか温度を出さない）場合、`show environment` の出力は CPU 側の汎用センサ（`coretemp-isa-*` 等）だけになる。

## 関連 / 代替

[SONiC](../../reference/glossary.md#term-sonic) では **platform_daemons (`pmon` コンテナ)** が `STATE_DB` の `TEMPERATURE_INFO` / `FAN_INFO` / `PSU_INFO` 等にスイッチハードウェア側のセンサ値を集約しており、そちらは `show platform temperature` / `show platform fan` / `show platform psu` から閲覧できる。lm-sensors 単独の出力に出ないスイッチ [ASIC](../../reference/glossary.md#term-asic) 温度や前面ファントレイ情報はこちらで取得すること。

## CONFIG_DB との接点

なし（`sensors(1)` 経由で `/sys/class/hwmon` を読むのみ）。

<!-- cli-mermaid -->
### データフロー (手動作成)

```mermaid
flowchart LR
  CLI["show environment"]
  SE["sudo sensors<br/>(lm-sensors)"]
  HW["I2C / hwmon ドライバ"]
  CLI --> SE
  SE --> HW
```

!!! note "凡例"
    show 系 (CLI → lm-sensors → HW) のミニ図。CONFIG_DB を直接介さないコマンドのため手動で記述。
<!-- /cli-mermaid -->

<!-- ref-triangle:start -->

## 関連リファレンス

- CLI: [show platform](show-platform.md) / [show system-health](show-system-health.md)
- Topic: [プラットフォーム / ポート / 光モジュール](../../topics/14-platform-port-optics/index.md)

CONFIG_DB / YANG への参照はなし (`sensors(1)` 経由で `/sys/class/hwmon` を読むのみ)。

<!-- ref-triangle:end -->

## 引用元

[^1]: `environment` コマンドの実装は `show/main.py` L1756-L1761。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L1756>

<!-- cli-sibling -->
### 関連 CLI コマンド

- [`config banner`](config-banner.md) — config banner サブコマンド
- [`config clock`](config-clock.md) — config clock サブコマンド
- [`config kdump`](config-kdump.md) — config kdump サブコマンド
- [`config ntp`](config-ntp.md) — config ntp サブコマンド
- [`config platform firmware`](config-platform-firmware.md) — config platform firmware サブコマンド

<!-- /cli-sibling -->

<!-- glossary-links-injected: ec18b66e3507 -->
