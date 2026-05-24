---
title: SFF-8472 外部キャリブレーション SFP の Rx パワー変換誤り
area: platform
tags: [sfp, eeprom, diagnostics, sff-8472, calibration, platform-common]
description: 外部キャリブレーション方式の SFP モジュールで Rx 受信パワーの変換値が誤る問題と修正内容。
source_issues:
  - https://github.com/sonic-net/sonic-platform-common/issues/449
verification: issue-confirmed
last_verified: 2026-05-20
---

# SFF-8472 外部キャリブレーション SFP の Rx パワー変換誤り

## 概要

SFF-8472 準拠の光モジュールのうち、**外部キャリブレーション（Externally Calibrated）** 方式を採用した SFP では、`sonic-platform-common` の DOM（Digital Optical Monitoring）変換関数が誤った Rx 受信パワー値を返す問題が報告されている。

## 背景：内部キャリブレーション vs 外部キャリブレーション

SFF-8472 では、DOM 測定値（温度・電圧・電流・光パワー）の数値変換方式として 2 種類が規定されている。

| 方式 | 説明 |
|------|------|
| **内部キャリブレーション**（Internally Calibrated） | EEPROM に格納された生データが直接物理量を表す。変換式は固定 |
| **外部キャリブレーション**（Externally Calibrated） | EEPROM に校正係数（スロープ・オフセット）が格納されており、変換時にこれらを掛け合わせる必要がある |

## 問題の詳細

外部キャリブレーション方式の場合、Rx 受信パワー（Rx Power）の変換は以下の式で行う必要がある。

```
Rx_Power [μW] = Rx_Power_raw × Rx_Power_Slope / 256 + Rx_Power_Offset
```

しかし、`sonic-platform-common` の実装では校正係数（スロープ・オフセット）を適用せずに生データをそのまま返していた（または誤った係数を使用していた）。

この結果、外部キャリブレーション方式の SFP を使用した場合、`show interfaces transceiver` や DOM 読み取りコマンドで表示される Rx パワー値が実際の受信パワーと大きく乖離する。

## 修正

PR [sonic-net/sonic-platform-common#479](https://github.com/sonic-net/sonic-platform-common/pull/479) で修正が行われた。

修正内容：
- EEPROM の外部キャリブレーションフラグ（Byte 92 bit 4 = 1）を確認
- 外部キャリブレーション時に Byte 56–91 から校正係数を読み出して変換を実施

## 確認方法

```bash
# SFP の DOM 情報を確認
show interfaces transceiver detail Ethernet0

# raw EEPROM データを確認（外部キャリブレーション判定: Byte 92 bit 4=1、内部: bit 3=1）
sudo sfputil show eeprom -p Ethernet0
```

Byte 92（Diagnostic Monitoring Type）で：
- Bit 4 = 1 → 外部キャリブレーション（Externally Calibrated）
- Bit 3 = 1 → 内部キャリブレーション（Internally Calibrated）

なお Bit 4 と Bit 3 は排他であり、「Bit 4=0 → 内部」ではなく Bit 3 の値で判定する点に注意。

## 注意事項

- 外部キャリブレーション SFP は主にコスト重視の汎用品や古い SFP で見られる
- 最近の SFP は内部キャリブレーションが主流であり、多くの環境では問題が発生しない
- 修正前のバージョンを使用している場合、光パワー監視・アラート閾値が信頼できない

## 関連

- [xcvrd クラッシュ（MediaInterfaceIDApp 未定義）](xcvrd-cmis-mediainterface-crash.md)
- [SFP EEPROM 解析の欠損](sfp-eeprom-parsing-gaps.md)
- GitHub Issue: [sonic-net/sonic-platform-common#449](https://github.com/sonic-net/sonic-platform-common/issues/449)
- GitHub PR: [sonic-net/sonic-platform-common#479](https://github.com/sonic-net/sonic-platform-common/pull/479)
