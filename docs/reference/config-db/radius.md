---
title: RADIUS テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-system-radius.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - RADIUS
    - RADIUS_SERVER
    - AAA
  cli:
    - config radius
  yang:
    - sonic-system-radius
---

# RADIUS テーブル

## 概要

RADIUS クライアントのグローバル設定を保持するシングルトンテーブル[^1]。`hostcfgd` の AAA ハンドラが読み、PAM (`/etc/pam.d/common-auth`) と NSS、`/etc/pam_radius_auth.conf` を生成する。サーバ固有の設定は `RADIUS_SERVER` 側にある。

## key 構造

```
RADIUS|global
```

固定キー `global` のみのシングルトン container (`RADIUS.global`)。

## フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `passkey` | string (1..65 chars、SPACE/`#`/`,` 不可) | なし | 既定の共有秘密鍵 (RADIUS shared secret) |
| `auth_type` | enum `pap`/`chap`/`mschapv2` | `pap` | 既定の認証プロトコル |
| `src_ip` | `inet:ip-address` | なし | RADIUS パケット送信元アドレス |
| `nas_ip` | `inet:ip-address` | なし | NAS-IP-Address / NAS-IPv6-Address 属性に乗せる値 |
| `statistics` | boolean | なし | サーバ統計収集の有効化 |
| `timeout` | uint16 (1..60 秒) | `5` | 既定の応答待ちタイムアウト |
| `retransmit` | uint8 (0..10) | `3` | 既定の再送回数 |

## 制約

- `passkey` は印字可能 ASCII から SPACE/`#`/`,` を除外 (`pattern '[^ #,]*'`)
- `timeout` 範囲外は `RADIUS timeout must be 1..60` エラー
- container 名 `RADIUS` / 内部 container 名 `global`

## 購読者

- `hostcfgd` (`sonic-host-services` の AAA ハンドラ): CONFIG_DB → PAM / nsswitch / pam_radius 設定の再生成
- `AAA.authentication.login` が `radius` を含むとき、PAM 経由でログイン認証時に参照される

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `RADIUS_SERVER` (※サーバごとのエントリ、YANG: `sonic-system-radius` の同名 list), [`AAA`](aaa.md)
- 関連 CLI: `config radius { passkey | timeout | retransmit | authtype | nasip | sourceip | statistics }`
- 関連 YANG: `sonic-system-radius`

## 引用元

[^1]: `src/sonic-yang-models/yang-models/sonic-system-radius.yang` (container `RADIUS` / `global`、typedef `auth_type_enumeration`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-system-radius.yang>

## 関連ページ
- [CONFIG_DB: AAA](aaa.md)
