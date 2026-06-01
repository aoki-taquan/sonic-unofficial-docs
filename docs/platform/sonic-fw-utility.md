---
title: fwutil（platform component firmware の install / update / show）
description: "BIOS・CPLD・FPGA・BMC・SSD などのプラットフォームコンポーネントのファームウェアを統一 CLI（fwutil install / update / show）で管理するためのユーティリティ設計を解説する。"
area: platform
verification: code-verified
last_verified: 2026-05-10
sources:
- repo: sonic-net/SONiC
  path: doc/fwutil/fwutil.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli:
  - fwutil
  - show platform firmware
  - show platform
  yang:
  - sonic-versions
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 14 章: Platform / Port / Optics](../topics/14-platform-port-optics/index.md) を参照。
<!-- /topics-tip -->

!!! info "裏取りステータス: code-verified"
    `sonic-utilities/fwutil/{main,lib,log}.py` と `sonic-platform-common/sonic_platform_base/component_base.py`（`get_firmware_version` / `install_firmware` 等）の存在を確認。各 platform plugin と `platform_components.json` の正確な記述差はベンダ依存のため範囲外。

# fwutil（platform component firmware の install / update / show）

## 概要

BIOS、CPLD、[FPGA](../reference/glossary.md#term-fpga)、BMC、SSD などのプラットフォームコンポーネントの **ファームウェアを統一 CLI から操作** するためのユーティリティ[^1]。狙い:

- ベンダ固有 utility に頼らず [SONiC](../reference/glossary.md#term-sonic) 標準コマンドで firmware を扱う
- バージョン情報の取得・install・update（次回起動時反映）を共通インタフェース化
- platform 側の plugin で実機固有の install ロジックを吸収する

## 動作仕様

```mermaid
flowchart LR
    USER[管理者] --> CLI[fwutil CLI]
    CLI --> PLAT["/usr/share/sonic/device/<platform>/\nplatform_components.json"]
    CLI --> PLUG["plugin\n(platform/chassis/component の Python class)"]
    PLUG -->|read version| HW[("BIOS / CPLD / FPGA / BMC / SSD")]
    PLUG -->|install| HW
```

主要要素[^1]:

- **`platform_components.json`**: platform ごとに **install 可能な component と既定 firmware path** を宣言する manifest
- **plugin API**: `Chassis.get_component_list()` / `Component.install_firmware(image_path)` / `Component.get_firmware_version()` 等を platform 実装が提供
- **CLI サブコマンド**: `show` / `install` / `update` / `show status` 等を統一フォーマットで提供

### 主な操作

| CLI | 用途 |
|-----|------|
| `fwutil show status` | 各 component の現行 firmware version |
| `fwutil show updates` | 利用可能な update（manifest 由来） |
| `fwutil install chassis component <name> fw <path>` | image を直接 install |
| `fwutil update` | manifest に従って一括 update |

### Boot type による動作差

ファームウェア書き換えは多くの platform で **再起動を伴う**。`fwutil` は cold reboot を要求するもの、warm reboot を許容するもの、即時反映するものを **plugin の declaration** で区別する設計。詳細な順序制御は platform plugin に委ねられる。

## 制限事項

- **platform plugin が必要**: plugin 未実装の component は `fwutil` から触れない
- **[ASIC](../reference/glossary.md#term-asic) 本体の firmware は対象外**: [SAI](../reference/glossary.md#term-sai)/SDK 経由で扱う想定（fwutil は周辺コンポーネント向け）
- **手動 image 指定 vs manifest**: 両者で受け付ける引数フォーマットが異なる
- **書き換え失敗の rollback**: 多くは hardware 側保証（dual-bank） に依存

## 干渉する機能

- **secure-upgrade / secure-boot**: 署名検証や TPM 連携が必要な platform では fwutil の install 経路にも影響
- **show platform**: `show platform firmware` で同じ情報を見られる platform もある
- **smart-switch [DPU](../reference/glossary.md#term-dpu) graceful shutdown**: DPU 側 firmware 更新時のシャットダウン整合
- **kdump / fast-reboot**: firmware install で求められる reboot 種別との相性

## トラブルシューティング

- component が表示されない → `platform_components.json` と plugin 実装の存在を確認
- `install` が失敗 → image 形式（vendor-specific binary）と plugin の対応版を確認
- 反映されない → 再起動種別（cold が必要）を満たしているか確認

### コマンド例

firmware ユーティリティを確認する。

```bash
# Firmware
sudo fwutil show status
sudo fwutil show version
ls /usr/share/sonic/device/*/fw/ 2>/dev/null | head
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/fwutil/fwutil.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- sonic-utilities/fwutil/ の現行 master 取り込みと CLI subcommand 一覧確認
- platform_components.json スキーマと現行 platform 実装での記述差分確認
- Chassis / Component plugin API の現行 sonic-platform-common での定義確認
- secure-upgrade / secure-boot との install 検証統合の現行実装確認
- smart-switch / DPU 環境での fwutil 拡張（DPU 個別更新）の現行実装確認
- ASIC 本体 firmware の扱い境界（fwutil / SAI / vendor SDK）の整理状況確認
-->

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Platform / Port / Optics / PHY](../topics/14-platform-port-optics/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: ec18b66e3507 -->
