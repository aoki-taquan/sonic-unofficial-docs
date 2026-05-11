---
title: LOSSLESS_TRAFFIC_PATTERN テーブル
description: "LOSSLESS_TRAFFIC_PATTERN テーブル — ロスレスフロー (PFC で守るフロー) のトラフィックパターンを記述する設定テーブル。 ヘッドルームサイズの動的計算 (buffermgrd の dynamic-buffer モード) において、平均パケットサイズや小パケット比率を入力として使う。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-lossless-traffic-pattern.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - LOSSLESS_TRAFFIC_PATTERN
    - BUFFER_PROFILE
    - DEFAULT_LOSSLESS_BUFFER_PARAMETER
  yang:
    - sonic-lossless-traffic-pattern
---

# LOSSLESS_TRAFFIC_PATTERN テーブル

## 概要

ロスレスフロー (PFC で守るフロー) のトラフィックパターンを記述する設定テーブル[^1]。
ヘッドルームサイズの動的計算 (`buffermgrd` の dynamic-buffer モード) において、平均パケットサイズや小パケット比率を入力として使う。

## key 構造

```
LOSSLESS_TRAFFIC_PATTERN|<name>
```

`<name>`: 1–32 文字。通常は `AZURE` の 1 件のみ。

## フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|----|------|
| `mtu` | uint16 (1..9216) | yes | ロスレスパケットの最大サイズ。ヘッドルームの XOFF サイズ計算に使う |
| `small_packet_percentage` | uint8 (0..100) | yes | 小パケット (`<= mtu/2` 想定) の比率。これが大きいほどヘッドルームを増やす |

## 購読者

- `buffermgrd` (dynamic buffer モード)。`headroom-pool-calculation` Jinja マクロ系で参照

## 関連 CONFIG_DB / YANG

- 関連 CONFIG_DB: `DEFAULT_LOSSLESS_BUFFER_PARAMETER`, `BUFFER_PROFILE`, `BUFFER_POOL`
- 関連 YANG: `sonic-lossless-traffic-pattern`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: `sonic-lossless-traffic-pattern`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-lossless-traffic-pattern.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-lossless-traffic-pattern.yang>

## 関連ページ
- [CONFIG_DB: DEFAULT_LOSSLESS_BUFFER_PARAMETER](default-lossless-buffer-parameter.md)
- [CONFIG_DB: BUFFER_PROFILE](buffer-profile.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key: `LOSSLESS_TRAFFIC_PATTERN|AZURE` (通常 1 件のみ)。
- `mtu`: `1500` または `9216` (jumbo)。
- `small_packet_percentage`: 経験的に `50` 程度。

### よくある誤設定

- `mtu` を実 MTU と乖離した値にし、ヘッドルームが過小/過大になる。
- dynamic-buffer モード以外でこのテーブルを変更しても効かない (`buffermgrd` の動的モードのみ参照)。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'LOSSLESS_TRAFFIC_PATTERN|AZURE'
show buffer profile
```
<!-- /ops-hint -->
