---
title: sonic-restapi YANG
description: "sonic-restapi YANG — RESTAPI YANG Module for SONiC OS。REST API サーバの TLS 証明書 (certs) と connection 設定 (config) を持つ。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-restapi.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [RESTAPI]
  cli: []
  yang: []
  _no_related_cli: true
  _no_related_yang: true
---

# sonic-restapi YANG

## 概要

- module: `sonic-restapi`
- namespace: `http://github.com/sonic-net/sonic-restapi`
- revision: `2022-10-05`
- import: なし
- top container: `sonic-restapi`

RESTAPI [YANG](../../reference/glossary.md#term-yang) Module for SONiC OS[^1]。REST API サーバの TLS 証明書 (certs) と connection 設定 (config) を持つ。

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-restapi"]
  C1[("CONFIG_DB<br/>RESTAPI")]
  Y --> C1
  D1["restapi"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## ツリー

```
module: sonic-restapi
  +--rw sonic-restapi
     +--rw RESTAPI
        +--rw certs
        |  +--rw ca_crt?             string
        |  +--rw server_crt?         string
        |  +--rw client_crt_cname?   string
        |  +--rw server_key?         string
        +--rw config
           +--rw client_auth?      boolean
           +--rw log_level?        string
           +--rw allow_insecure?   boolean
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `ca_crt` | `sonic-restapi/RESTAPI/certs/ca_crt` | `string` |  |  |  | Local path for ca_crt |
| `server_crt` | `sonic-restapi/RESTAPI/certs/server_crt` | `string` |  |  |  | Local path for server_crt |
| `client_crt_cname` | `sonic-restapi/RESTAPI/certs/client_crt_cname` | `string` |  |  |  | Client cert common name |
| `server_key` | `sonic-restapi/RESTAPI/certs/server_key` | `string` |  |  |  | Local path for server_key |
| `client_auth` | `sonic-restapi/RESTAPI/config/client_auth` | `boolean` |  | true |  | Enable client authentication |
| `log_level` | `sonic-restapi/RESTAPI/config/log_level` | `string` |  | trace |  | container log level for restapi |
| `allow_insecure` | `sonic-restapi/RESTAPI/config/allow_insecure` | `boolean` |  | false |  | Allow insecure connection |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `RESTAPI`
- CLI: なし（[config_db.json](../../reference/glossary.md#term-config_db.json) で直接設定）

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`RESTAPI`](../config-db/restapi.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-restapi.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: 896d391185a9 -->
