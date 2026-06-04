---
title: SfpUtilBase の EEPROM 解析欠損
area: platform
tags: [sfp, eeprom, platform-common, xcvrd, api]
description: SfpUtilBase（sonic-platform-common, legacy sonic_sfp パッケージ）に残るモジュール制御系抽象メソッドと、xcvrd 経由アクセスへ統合すべきとされた設計方針を、該当ファイル・関数を引用して解説する。
source_issues:
  - https://github.com/sonic-net/sonic-platform-common/issues/179
verification: issue-confirmed
last_verified: 2026-05-20
---

# SfpUtilBase の EEPROM 解析欠損

## 概要

`sonic-platform-common` の legacy インタフェース `SfpUtilBase`（`sonic_platform_base/sonic_sfp/sfputilbase.py`）には、EEPROM 解析を行う `get_transceiver_*_dict()` 系メソッドが具象実装される一方、モジュール制御系（`reset` / `set_low_power_mode` / `get_transceiver_change_event` 等）は `@abc.abstractmethod` 宣言のままで、プラットフォームプラグイン側に実装責任が残されている。

加えて、新世代の `SfpBase`（`sonic_platform_base/sfp_base.py`）で導入された `tx_disable()` / `tx_disable_channel()` / `set_lpmode()` / `set_power_override()` といったモジュール制御 API は `SfpUtilBase` 側には存在せず、両クラスのカバレッジに非対称が生じている。Issue #179 はこのギャップと、`SfpUtilBase` 直接呼び出しから `xcvrd` 経由 API へ移行すべきという設計方針について議論している[^issue-179]。

## SfpUtilBase に残る抽象メソッド

`sfputilbase.py` 末尾に並ぶ `@abc.abstractmethod` 宣言は以下の 5 個である[^sfputilbase-abstract]。

| メソッド | 行 | 役割 |
|---|---|---|
| `get_presence(port_num)` | L1381 | トランシーバー実装の有無 |
| `get_low_power_mode(port_num)` | L1389 | LPMode 状態取得 |
| `set_low_power_mode(port_num, lpmode)` | L1397 | LPMode 設定 |
| `reset(port_num)` | L1406 | モジュールリセット |
| `get_transceiver_change_event(timeout=0)` | L1414 | プラグイン/プラグアウトイベント |

これらは `SfpUtilBase` 自身には実装されておらず、各プラットフォーム（`device/<vendor>/<platform>/plugins/sfputil.py`）でオーバーライドされる前提である。

<!-- evidence: .cache/sonic-sources/sonic-platform-common/sonic_platform_base/sonic_sfp/sfputilbase.py L1380-L1429 -->

## SfpBase 側のみに存在する制御 API

新規プラットフォームが従うべき `SfpBase`（`sfp_base.py`）には、`SfpUtilBase` に対応物のない以下のメソッドが定義されている[^sfpbase-methods]。

| メソッド | 行 | SfpUtilBase 側の対応 |
|---|---|---|
| `tx_disable(tx_disable)` | L353 | なし |
| `tx_disable_channel(channel, disable)` | L366 | なし |
| `set_lpmode(lpmode)` | L381 | `set_low_power_mode(port_num, lpmode)` (粒度がポート単位) |
| `set_power_override(power_override, power_set)` | L406 | なし |
| `get_tx_disable()` | L250 | なし |
| `get_tx_disable_channel()` | L262 | なし |

つまり TX Disable やレーン粒度の制御は `SfpBase` 経由でしか提供されておらず、`SfpUtilBase` のみを実装した古いプラットフォームではこれらの操作は不可能である。

<!-- evidence: .cache/sonic-sources/sonic-platform-common/sonic_platform_base/sfp_base.py L250-L420 -->

## DOM 閾値取得の OSFP 未実装パス

`SfpUtilBase.get_transceiver_dom_threshold_info_dict()` は QSFP / SFP については EEPROM 直読みで閾値を返すが、OSFP ポートについては以下のコメントとともに `N/A` 埋めの辞書を返すだけになっている[^osfp-stub]。

```python
if port_num in self.osfp_ports:
    # Below part is added to avoid fail xcvrd, shall be implemented later
    return transceiver_dom_threshold_info_dict
```

OSFP モジュールの DOM 閾値が必要な場合、legacy パスではなく `SfpBase` 系（CMIS 対応の `sonic_xcvr` パッケージ）に切り替えることが事実上必須となる。

<!-- evidence: .cache/sonic-sources/sonic-platform-common/sonic_platform_base/sonic_sfp/sfputilbase.py L1254-L1256 -->

## 設計上の留意点

### xcvrd 経由のアクセスを推奨

`reset()` や `set_lpmode()` のようなモジュール制御操作は、プラットフォームプラグインを直接呼ぶのではなく、`xcvrd` を介して [STATE_DB](../reference/glossary.md#term-state_db) / [Redis](../reference/glossary.md#term-redis) 経由で発行することが推奨される。

理由は以下である。

- `xcvrd` がポート初期化・CMIS state machine・トランシーバー状態変化イベントのハンドリングを担う
- 直接操作と `xcvrd` の操作が競合すると、CMIS state machine の状態と物理状態が乖離する
- マルチ [ASIC](../reference/glossary.md#term-asic) 環境では `xcvrd` がポート⇔物理ポートのマッピングを保持しており、直接 plugin 呼び出しではこのコンテキストが失われる

### xcvrd と SfpUtil の役割分担

```text
アプリケーション (sfputil / CLI / SNMP / gNMI)
    │  STATE_DB / CONFIG_DB
    ▼
xcvrd (PMON コンテナ内デーモン)
    │  SfpBase / SfpUtilBase API
    ▼
プラットフォームプラグイン (device/<vendor>/.../sfputil.py)
    │  i2c / sysfs
    ▼
EEPROM / 制御レジスタ
```

プラットフォームプラグイン実装者は `xcvrd` が呼ぶ抽象 API（`SfpBase` を推奨、新規での `SfpUtilBase` 実装は非推奨）の実装に集中し、上位アプリケーションは `xcvrd` のインターフェースを通じてアクセスするのが正しい設計である。

## プラットフォームプラグイン実装者への注意

既存の `SfpUtilBase` 派生プラットフォームを保守する際の優先順位は以下となる。

1. EEPROM raw アクセス（`_read_eeprom_specific_bytes()` / `_write_eeprom_specific_bytes()`、L334 / L378）が正しく動くこと
2. 上記表の 5 個の `@abc.abstractmethod` を漏れなくオーバーライドすること
3. OSFP / CMIS 世代のサポートが必要なら、`SfpUtilBase` での拡張ではなく `SfpBase` への移植を検討する

## 関連

- [xcvrd クラッシュ（MediaInterfaceIDApp 未定義）](xcvrd-cmis-mediainterface-crash.md)
- [SFF-8472 Rx パワーキャリブレーション問題](sfp-sff8472-rx-power-calibration.md)
- GitHub Issue: [sonic-net/sonic-platform-common#179](https://github.com/sonic-net/sonic-platform-common/issues/179)

[^issue-179]: [sonic-net/sonic-platform-common Issue #179 — SfpUtilBase の get/set 関数の議論](https://github.com/sonic-net/sonic-platform-common/issues/179)
[^sfputilbase-abstract]: `sonic-platform-common` `sonic_platform_base/sonic_sfp/sfputilbase.py` L1380-L1429（`@abc.abstractmethod` ブロック）。
[^sfpbase-methods]: `sonic-platform-common` `sonic_platform_base/sfp_base.py` L250-L420（`tx_disable` / `tx_disable_channel` / `set_lpmode` / `set_power_override` / `get_tx_disable` / `get_tx_disable_channel`）。
[^osfp-stub]: `sonic-platform-common` `sonic_platform_base/sonic_sfp/sfputilbase.py` L1254-L1256（OSFP ポートでは `N/A` 埋めの dict を返すスタブ）。

<!-- glossary-links-injected: 9d739814db16 -->
