---
title: Portable Console Device 設計（USB ベンダー console デバイスの抽象化）
area: management
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/console/Portable-Console-Device-High-Level-Design.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - CONSOLE_SWITCH
  cli: []
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    HLD は v0.1 / 2022-12 改訂。`sonic_platform_common/sonic_console/` 配下の API クラス階層、`CONSOLE_SWITCH` テーブルへのフィールド追加、ベンダー .deb パッケージの自動インストール経路が現行 master でこの仕様どおりかは未確認。

# Portable Console Device 設計（USB ベンダー console デバイスの抽象化）

## 概要

SONiC のホストにプラグインされる **USB 接続のポータブル console デバイス** に対して、ベンダー横断の抽象 API を定義する設計[^1]。ベンダーは `<vendor>-<model>.deb` パッケージで driver と udev rules を提供し、Python の Platform 層で `PortableConsoleDeviceBase` を継承した実装クラスを `/sonic_platform_common/sonic_console/<vendor>/console_<model>.py` に置く。

## 動作仕様

### 前提

- USB のみサポート（v0.1）。
- 同時に動かせるのは **同一モデル 1 種類だけ**。異なるモデルが混在し、`vendor_name` / `model_name` の手動指定もない場合は機能しない[^1]。
- 同一ベンダー・同一モデルの複数台 daisy-chain は可（最大数はベンダー実装依存）。

### セットアップフロー

```mermaid
flowchart LR
    USB[USB plug-in] --> UDEV[udev rules]
    UDEV --> MAP[/dev/ttyUSB<id> → /dev/console-<line>/]
    BUILD[sonic-buildimage] --> DEB[<vendor>-<model>.deb]
    DEB -->|install| RULES[/etc/udev/rules.d/50-<vendor>-<model>.rules]
    POSTINST[postinst hook] -->|udevadm trigger -c add| UDEV
```

ベンダー側 deb には `50-<vendor>-<model>.rules` を `/etc/udev/rules.d/` に配置し、postinst で `udevadm trigger -c add` を呼ぶ運用が標準とされる[^1]。優先度番号 50 はベンダー間衝突を避ける慣例。

### CONFIG_DB

```text
CONSOLE_SWITCH|console_mgmt
    autodetect   = "enable" | "disable"
    vendor_name  = string    ; autodetect=enable のとき空必須
    model_name   = string    ; autodetect=enable のとき空必須
```

`autodetect=disable` のときに `vendor_name` / `model_name` を読んで factory 関数が対応クラスをインスタンス化する設計[^1]。

### Python API（`sonic_platform_common/sonic_console/`）

```text
sonic_console/
├── console_base.py    # PortableConsoleDeviceBase
├── factory.py         # vendor/model から具象クラスを返す
├── line_info.py       # ConsoleLineInfo
├── microsoft/
│   └── console_simulator.py
└── <vendor>/
    └── console_<model>.py
```

`ConsoleLineInfo` は 1 つの console 回線を表現するレコードで、`device_index` / `port_name` / `virtual_device_path` を持つ[^1]。`PortableConsoleDeviceBase` の派生クラスがベンダー固有挙動を実装する。

### Factory Function

```python
# factory.py（概念）
def create(vendor=None, model=None):
    if vendor is None or model is None:
        # autodetect: 既知ベンダー一覧で USB 列挙して特定
        vendor, model = autodetect()
    mod = importlib.import_module(f"sonic_console.{vendor}.console_{model}")
    return mod.create()
```

autodetect 時に複数ベンダーの USB を同時検出した場合は失敗させる仕様（前述の前提）。

## 設定

### 関連する CONFIG_DB

| Table | 説明 |
|-------|------|
| `CONSOLE_SWITCH` | console-switch 機能設定。ポータブルデバイス制御用に `autodetect` / `vendor_name` / `model_name` フィールド追加 |

### 関連する CLI

HLD には新規 CLI の正式定義は含まれない。既存の `config console` 系で `vendor_name` / `model_name` を設定すると示唆される。

### 関連する YANG

HLD に YANG モデルの記述は無い。

### 設定例

```bash
# autodetect モード
sudo config console-switch autodetect enable

# 手動指定
sudo config console-switch autodetect disable
sudo config console-switch vendor microsoft
sudo config console-switch model simulator
```

## 制限事項

- **USB 専用**。シリアル直結の console 拡張デバイスは対象外。
- 異なるモデルの混在は不可（autodetect では 1 種類だけ動く）。
- daisy-chain サポート可否はベンダー実装依存（HLD では台数制限を規定しない）。
- ベンダー実装は **`sonic-platform-common`** に貢献する形で取り込まれることを想定（独立 plugin ではない）。

## 干渉する機能

- **新 Platform API（sonic_platform）**: 同じく Python クラス階層で抽象化される設計思想を共有する。
- **udev**: console line ↔ /dev mapping は udev に依存。他の udev rules との優先順位衝突に注意。
- **`show line` / `config line`（既存 console-switch CLI）**: ポータブルデバイス追加で行数が動的に変わるため、既存 CLI 側でラインインデックスを再計算する必要がある（HLD では明示なし、要確認）。

## トラブルシューティング

- USB 装着時にラインが見えない → `lsusb` でデバイス認識を確認、`udevadm monitor` で rules 発火を確認。
- 異なるモデル混在時に動かない → 仕様。1 種類だけプラグインするか、autodetect を disable にして手動指定する。
- daisy-chain で奥のデバイスが見えない → ベンダー実装の最大段数を確認。

## 引用元

[^1]: `sonic-net/SONiC` `doc/console/Portable-Console-Device-High-Level-Design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
