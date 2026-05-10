---
title: PCIe Monitoring Services（pcied / pcieinfo / lnkSta / AER）
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/pcie-mon/pcie-monitoring-services-hld.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli:
    - show platform pcieinfo
  yang: []
---

!!! warning "裏取りステータス: code-verified"
    pcied / pcieinfo の現行 sonic-platform-daemons 実装状況、AER 取得経路は未確認。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: `sonic-platform-daemons/sonic-pcied/scripts/pcied` に PCIe monitoring daemon 実装、`pytest.ini` / `setup.py` でパッケージング。STATE_DB の `PCIE_DEVICE` 系テーブルへの書き込みは pcied の本体ロジックで確認できる。

# PCIe Monitoring Services（pcied / pcieinfo / lnkSta / AER）

## 概要

`pcied` は **ASIC / NPU や peripheral が PCIe バス上に期待通り存在し、リンクが正しく確立しているか** を監視する pmon 系 daemon[^1]。CPU マザー上の PCIe デバイス inventory・現在の link speed/width・AER（Advanced Error Reporting）を STATE_DB に出す。

主目的:

- 起動時に **存在すべきデバイスがすべて見えているか** を確認（platform 別 manifest と照合）
- リンク速度劣化（Gen4 で繋がるはずが Gen2 等）の検知
- AER による correctable / fatal error の集計と通知
- `show platform pcieinfo` 等で運用者が状態を簡易確認できるようにする

## 動作仕様

```mermaid
flowchart LR
    PD[pcied] --> PLAT[platform plugin\n(/usr/share/sonic/device/<plat>/pcie.yaml)]
    PD --> SYSFS[/sys/bus/pci/devices/...]
    SYSFS --> PD
    PD --> AER[/sys/.../aer_dev_*]
    PD --> STATE[STATE_DB\nPCIE_DEVICE / PCIE_DETACH / PCIE_AER]
    SHOW[show platform pcieinfo] --> STATE
```

主な観測項目[^1]:

- **device list** と manifest との一致（vendor/device id、function、bus）
- **link state**（current speed / max speed / current width / max width）
- **AER**: correctable error count、non-fatal、fatal
- **detach**: 期待デバイスが消失しているケースの検知

## 関連 STATE_DB

| Table | 説明 |
|-------|------|
| `PCIE_DEVICE` | 観測された device リスト |
| `PCIE_DETACH` | 期待されていたが消失している device |
| `PCIE_AER` | エラーカウンタ |

## 関連 CLI

| Command | 用途 |
|---------|------|
| `show platform pcieinfo` | 期待 device との照合と現在状態 |
| `show platform pcieinfo -c` | 詳細（capability）情報 |

## 制限事項

- **manifest が無いと差分が判定できない**: `pcie.yaml` の整備が前提
- **AER の有効化**: kernel cmdline / BIOS で AER を有効にしておかないとカウンタが進まない
- **hot-plug**: 通常 SONiC のスイッチング platform で使う場面は少ない
- **NUMA / lane swap**: BIOS 段階の挙動は本機構の対象外

## 干渉する機能

- **system health monitor**: PCIe AER fatal を critical に昇格させる経路
- **pcieinfo-design**: 既存の pcieinfo CLI / 機能との関係（同 area / platform 周辺）
- **show techsupport**: PCIe 状態を含めた dump

## トラブルシューティング

- `show platform pcieinfo` で device 不足 → manifest と実装の差、kernel ログの enumeration エラー
- link speed 劣化 → cable / connector / 仕様、`lnkSta` の current vs max を比較
- AER カウンタ増加 → `dmesg` の `pcieport` メッセージ、device 側 firmware

## 引用元

[^1]: `sonic-net/SONiC` `doc/pcie-mon/pcie-monitoring-services-hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- pcied daemon の現行 sonic-platform-daemons 取り込みと systemd 起動経路の確認
- platform 別 pcie.yaml manifest の現行整備状況確認
- STATE_DB PCIE_DEVICE / PCIE_DETACH / PCIE_AER スキーマの現行値確認
- show platform pcieinfo CLI の sonic-utilities 取り込み確認
- AER 取得の現行実装（sysfs 直 / aer_inject の使用有無）の確認
- system health monitor / show techsupport との連携確認
-->
