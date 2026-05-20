---
title: SfpUtilBase の EEPROM 解析欠損
area: platform
tags: [sfp, eeprom, platform-common, xcvrd, api]
description: SfpUtilBase クラスに実装されていない get/set 関数が残存する問題と、xcvrd 経由アクセスへの設計方針。
source_issues:
  - https://github.com/sonic-net/sonic-platform-common/issues/179
verification: issue-confirmed
last_verified: 2026-05-20
---

# SfpUtilBase の EEPROM 解析欠損

## 概要

`sonic-platform-common` の `SfpUtilBase` クラスには、EEPROM データを解析するハンドラが定義されているにもかかわらず、対応する get/set 関数が未実装のまま残存している。

## 未実装の関数

`SfpUtilBase` クラスには以下のような関数が宣言されているが、EEPROM パーサーとの対応付けが不完全な状態にある。

- ベンダー固有の拡張フィールドを読み取る関数群
- 一部の DOM（Digital Optical Monitoring）フィールドの書き込み関数
- 特定のコントロールレジスタ（TX Disable、Rate Select 等）の細粒度操作

## 設計上の留意点

この問題の議論において、重要な設計方針が示されている。

### xcvrd 経由のアクセスを推奨

`reset()` や `set_xxx()` のようなモジュール制御操作は、**直接 `SfpUtilBase` を呼ぶのではなく、`xcvrd` 経由で行うことが推奨される**。

理由：
- `xcvrd` はポート初期化やトランシーバー状態変化イベントのハンドリングを担当するデーモンである
- 直接操作と `xcvrd` 経由操作が競合すると、状態の不整合が生じる可能性がある
- マルチ ASIC 環境では、`xcvrd` がポートとトランシーバーのマッピングを管理しており、直接操作ではこのコンテキストが失われる

### xcvrd と SfpUtil の役割分担

```
アプリケーション
    ↓ (Redis / D-Bus 経由)
xcvrd (デーモン)
    ↓
SfpUtil (プラットフォームプラグイン)
    ↓
EEPROM / ハードウェアレジスタ
```

プラットフォームプラグイン（`SfpUtil`）を実装するベンダーは、`xcvrd` が使用する API の実装に集中し、アプリケーションは `xcvrd` のインターフェースを通じてアクセスするのが正しい設計である。

## プラットフォームプラグイン実装者への注意

新規プラットフォームで `SfpUtilBase` を実装する際：

1. `get_transceiver_info_dict()` および `get_transceiver_dom_info_dict()` を優先して実装する
2. `reset()` / `tx_disable()` 等の制御関数も `xcvrd` が使用するため実装が必要
3. EEPROM の raw アクセス（`read_eeprom()` / `write_eeprom()`）を正確に実装することで、上位ハンドラが動作する

## 関連

- [xcvrd クラッシュ（MediaInterfaceIDApp 未定義）](xcvrd-cmis-mediainterface-crash.md)
- [SFF-8472 Rx パワーキャリブレーション問題](sfp-sff8472-rx-power-calibration.md)
- GitHub Issue: [sonic-net/sonic-platform-common#179](https://github.com/sonic-net/sonic-platform-common/issues/179)
