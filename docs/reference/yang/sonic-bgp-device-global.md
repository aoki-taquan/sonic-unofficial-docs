---
title: sonic-bgp-device-global YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-device-global.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BGP_DEVICE_GLOBAL]
  cli: ["config bgp", "show bgp"]
  yang: [sonic-bgp-global]
---

# sonic-bgp-device-global YANG

## 概要

- module: `sonic-bgp-device-global`
- namespace: `http://github.com/sonic-net/sonic-bgp-device-global`
- revision: `2024-01-28` (Weighted ECMP using BGP link bandwidth), `2022-06-26` (initial)
- import: なし
- top container: `sonic-bgp-device-global`

デバイスレベル BGP のグローバル設定。TSA (Traffic Shift Away)、 WCMP (Weighted ECMP)、 IDF isolation 状態、および BGP confederation 設定を保持する[^1]。

## ツリー

```
module: sonic-bgp-device-global
  +--rw sonic-bgp-device-global
     +--rw BGP_DEVICE_GLOBAL
        +--rw STATE
        |  +--rw tsa_enabled?           boolean
        |  +--rw wcmp_enabled?          boolean
        |  +--rw idf_isolation_state?   enumeration
        +--rw CONFED
           +--rw asn?     uint32
           +--rw peers?   string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `tsa_enabled` | `sonic-bgp-device-global/BGP_DEVICE_GLOBAL/STATE/tsa_enabled` | `boolean` |  | false |  | When true, traffic is shifted away (TSA); BGP routes are not advertised to neighbors |
| `wcmp_enabled` | `sonic-bgp-device-global/BGP_DEVICE_GLOBAL/STATE/wcmp_enabled` | `boolean` |  | false |  | Enable Weighted ECMP using BGP link bandwidth |
| `idf_isolation_state` | `sonic-bgp-device-global/BGP_DEVICE_GLOBAL/STATE/idf_isolation_state` | `enumeration` |  |  | isolated_no_export, isolated_withdraw_all, unisolated | IDF (Internet-Facing Datacenter Fabric) isolation state |
| `asn` | `sonic-bgp-device-global/BGP_DEVICE_GLOBAL/CONFED/asn` | `uint32` |  |  | range 1..4294967295 | Autonomous System Number for BGP confederation |
| `peers` | `sonic-bgp-device-global/BGP_DEVICE_GLOBAL/CONFED/peers` | `string` |  |  |  | List of sub-ASNs in the confederation separated by semi-colon |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `BGP_DEVICE_GLOBAL`
- CLI: `config bgp` (`tsa`/`wcmp`/`idf`), `show bgp`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`BGP_DEVICE_GLOBAL`](../config-db/bgp-device-global.md)
- CLI: [`config bgp`](../cli/config-bgp.md) / [`show bgp`](../cli/show-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-bgp-device-global.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
