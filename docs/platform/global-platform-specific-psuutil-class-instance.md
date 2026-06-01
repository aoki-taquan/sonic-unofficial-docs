---
title: 新 Platform API（sonic_platform / Chassis / PSU/Fan/Sfp の Python クラス階層）
description: 新 Platform API（sonic_platform / Chassis / PSU/Fan/Sfp の Python クラス階層） — 旧設計では psuutil.py / sfputil.py / eeprom.py 等を 独立した Python plugin としてベンダーが個別に実装していたが、新設計で…
area: platform
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/platform_api/new_platform_api.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  - DPU
  - PORT
  - PORTCHANNEL
  - BREAKOUT_CFG
  cli:
  - show platform
  - show interfaces
  yang:
  - sonic-asic-sensors
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 14 章: Platform / Port / Optics](../topics/14-platform-port-optics/index.md) を参照。
<!-- /topics-tip -->

!!! info "裏取りステータス: code-verified / 旧設計から現行への移行記述"
    `sonic-platform-common/sonic_platform_base/` を直読して `chassis_base.py` (`class ChassisBase`)、`psu_base.py` (`class PsuBase`)、`fan_base.py` (`class FanBase`)、`sfp_base.py` (`class SfpBase`)、`module_base.py` (`class ModuleBase`)、`component_base.py` (`class ComponentBase`)、`device_base.py`、`fan_drawer_base.py`、`platform_base.py`、`sensor_base.py`、`bmc_base.py`、`liquid_cooling_base.py` 等の基底クラス階層を確認。HLD の "Current Solution" 節は **旧 plugin 形式から新階層への移行時** の説明であり、現行 master では新 API が普及済み。本ページは HLD の設計意図を中心に書かれている点に注意（移行前の細部記述は現行と異なる）。

# 新 Platform API（sonic_platform / Chassis / PSU/Fan/Sfp の Python クラス階層）

## 概要

旧設計では `psuutil.py` / `sfputil.py` / `eeprom.py` 等を **独立した Python plugin** としてベンダーが個別に実装していたが、新設計では **すべてを 1 つの object-oriented パッケージ `sonic_platform` に統一** する[^1]。共通属性は `DeviceBase` 系の基底クラスにまとめ、ベンダーは具象クラス階層を一括で実装する。

これにより：

- 新規 device 追加時の plugin 増設が不要
- 共通属性（Presence / Model # / Serial #）はベース継承で済む
- 抽象メソッドはデフォルトで `NotImplementedError` を投げる「未実装 OK」設計で、ベース拡張で既存実装を壊さない

## 動作仕様

### クラス階層

```text
Platform
└── Chassis
    ├── base MAC / serial / EEPROM info / reboot cause / hw watchdog
    ├── env sensors / front-panel LEDs / status LEDs
    ├── PSU[0..p-1]
    ├── Fan[0..f-1]
    ├── SFP cage[0..s-1]
    └── Module[0..m-1]   (line card / supervisor card)
        ├── env sensors / LEDs
        ├── PSU[...] / Fan[...] / SFP cage[...]
```

### パッケージ構成

- 共通定義: `sonic-platform-common/sonic_platform_base/` （`Platform`, `Chassis`, `PsuBase`, `FanBase`, `SfpBase`, `ModuleBase` 等）
- ベンダー実装: 各 platform リポジトリの `platform/<vendor>/.../sonic_platform/` 配下に Python wheel として収まる

### 配置とロード

```mermaid
flowchart LR
    BUILD[Build time] -->|wheel| HOST[/usr/share/sonic/device/<PLATFORM>/sonic_platform-*.whl/]
    INSTALL[First boot] -->|pip install| HSYS[Host system]
    HOST -->|mount| PMON[pmon container]
    PMON -->|check installed?| INSTALL2[install if missing]
    PMON -->|update| SDB[(STATE_DB)]
    CLI[show CLI] --> SDB
```

- ベンダーは build 時に `sonic_platform` パッケージを wheel にコンパイル。
- 初回ブート時、対応プラットフォーム用 wheel を `/usr/share/sonic/device/<PLATFORM>/` にコピー。
- pmon コンテナ起動時、`sonic_platform` が未インストールなら wheel をインストール。
- `pmon` 内の各デーモンが Platform API 経由でハードを読み、結果を [STATE_DB](../reference/glossary.md#term-state_db) に書く。
- ホスト側 CLI は STATE_DB を引いて表示。
- リアルタイム値（光モジュール光信号など）は CLI が DB に「読め」と書いて pmon デーモンが読み直す[^1]。

### 旧 → 新 API のサンプル比較

旧（`psuutil.py` plugin の動的ロード）：

```python
import imp, subprocess
# get platform/hwsku via sonic-cfggen
module = imp.load_source('psuutil', '/usr/share/sonic/device/.../plugins/psuutil.py')
platform_psuutil = module.PsuUtil()
print(platform_psuutil.get_psu_presence(1))
```

新：

```python
import sonic_platform
chassis = sonic_platform.platform.Platform().get_chassis()
psu1 = chassis.get_psu(1)
print(psu1.get_presence())
```

## 設定

### 関連する CONFIG_DB

[HLD](../reference/glossary.md#term-hld) には [CONFIG_DB](../reference/glossary.md#term-config_db) エントリの記述は無い。

### 関連する CLI

新 API は CLI を直接定義しない。`pmon` 内のデーモンが書き込んだ STATE_DB を、既存の `show platform`、`show interfaces transceiver` 等の CLI が読み出す。

### 関連する YANG

HLD に [YANG](../reference/glossary.md#term-yang) モデルの記述は無い。

### 設定例

ベンダー実装側の最小例（`sonic_platform/chassis.py`）：

```python
from sonic_platform_base.chassis_base import ChassisBase
from sonic_platform.psu import Psu

class Chassis(ChassisBase):
    def __init__(self):
        ChassisBase.__init__(self)
        for i in range(self.PSU_NUM):
            self._psu_list.append(Psu(i))
```

## 制限事項

- HLD 自体は移行設計の初期段階で、現行 master の `sonic-platform-common` のクラス階層と完全に一致するわけではない（後継 PR で多数のクラスが追加されている）。
- 旧 `psuutil.py` 等の plugin はしばらく後方互換のために残ったが、現行 master ではほぼ移行済み。
- `pmon` の wheel 自動インストール挙動はプラットフォームの初回ブートに依存する。

## 干渉する機能

- **xcvrd / pmon-d / fancontrold**: pmon コンテナ内の各デーモンが `sonic_platform` を import して使う。
- **`show platform` 系 CLI**: STATE_DB 経由で値を読むため、新 API 対応 platform でないと一部値が空になる。
- **fastboot / warm reboot**: pmon の再起動シーケンスで `sonic_platform` の再ロードが走る。

## トラブルシューティング

- `show platform psu` で値が出ない → pmon コンテナ内で `sonic_platform` が import できるか確認 (`docker exec pmon python3 -c 'import sonic_platform'`)。
- `NotImplementedError` が出る → ベンダー実装が当該メソッドを提供していない。`sonic-platform-common` の対応メソッドに対する placeholder 実装が必要。
- 新 plugin が読まれない → `/usr/share/sonic/device/<PLATFORM>/sonic_platform-*.whl` の存在と pmon の起動ログを確認。

### コマンド例

PSU の状態と daemon を確認する。

```bash
# PSU
show platform psustatus
redis-cli -n 6 keys 'PSU_INFO|*'
redis-cli -n 6 hgetall 'PSU_INFO|PSU 1'
ps aux | grep -E 'psud|pmon'
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/platform_api/new_platform_api.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Platform / Port / Optics / PHY](../topics/14-platform-port-optics/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 4e4b0dab1086 -->
