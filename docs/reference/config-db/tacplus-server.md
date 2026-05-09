---
title: TACPLUS_SERVER テーブル
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-system-tacacs.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - TACPLUS_SERVER
    - TACPLUS
    - AAA
  cli:
    - config tacacs
  yang:
    - sonic-system-tacacs
---

# TACPLUS_SERVER テーブル

## 概要

TACACS+ 認証サーバの一覧と global TACACS+ クライアント設定を保持する。最大 8 サーバ。`hostcfgd` が CONFIG_DB を購読して `/etc/pam.d/*`, `/etc/nss-tacplus.conf`, `/etc/tacplus_nss.conf` を生成する[^1]。

## key 構造

```
TACPLUS_SERVER|<ipaddress>
TACPLUS|global
```

`<ipaddress>` は `inet:host` (FQDN または IPv4/IPv6)。

## TACPLUS_SERVER

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `priority` | uint8 (1..64) | 1 | サーバ選択優先度 (大きいほど先) |
| `tcp_port` | inet:port-number | 49 | TACACS+ サーバ TCP ポート |
| `timeout` | uint16 (1..60) | 5 | per-server 応答 timeout [秒] |
| `auth_type` | enum `pap`/`chap`/`mschap`/`login` | `pap` | per-server 認証プロトコル |
| `key_encrypt` | boolean | false | passkey 暗号化保存フラグ |
| `passkey` | string (1..256, no SPACE/`#`/`,`) | - | per-server 共有秘密 |
| `vrf` | string `mgmt`/`default` | - | サーバ到達 VRF |

## TACPLUS|global

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `auth_type` | enum (同上) | `pap` | デフォルト認証プロトコル |
| `timeout` | uint16 (1..60) | 5 | デフォルト timeout |
| `key_encrypt` | boolean | false | passkey 暗号化保存フラグ |
| `passkey` | string (1..256) | - | デフォルト共有秘密 |
| `src_intf` | union leafref `PORT`/`PORTCHANNEL`/`LOOPBACK_INTERFACE`/`MGMT_PORT` または Vlan pattern | - | TACACS+ パケット送信元 interface |

## 購読者

- `hostcfgd`: CONFIG_DB → PAM / NSS 設定の再生成
- 関連: `pam_tacplus`, `libnss_tacplus`

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `AAA`、`LDAP_SERVER`、`RADIUS_SERVER`
- 関連 CLI: `config tacacs add/delete/passkey/timeout/authtype/default`、`show tacacs`
- 関連 YANG: `sonic-system-tacacs`、`sonic-system-aaa`

## 引用元

[^1]: YANG 定義: `sonic-system-tacacs.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-system-tacacs.yang>
