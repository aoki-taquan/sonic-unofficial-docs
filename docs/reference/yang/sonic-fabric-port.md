---
title: sonic-fabric-port YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-fabric-port.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [FABRIC_PORT]
  cli: ["show fabric"]
  yang: [sonic-types]
---

# sonic-fabric-port YANG

## 概要

- module: `sonic-fabric-port`
- namespace: `http://github.com/sonic-net/sonic-fabric-port`
- revision: `2023-03-14`
- import: `sonic-types`
- top container: `sonic-fabric-port`

VOQ chassis におけるラインカード間ファブリックリンクの port 設定を保持する。隔離状態、 alias、 lanes、強制 unisolate 状態などを定義する[^1]。

## ツリー

```
module: sonic-fabric-port
  +--rw sonic-fabric-port
     +--rw FABRIC_PORT
        +--rw FABRIC_PORT_LIST* [name]
           +--rw name                    string
           +--rw isolateStatus?          stypes:boolean_type
           +--rw alias?                  string
           +--rw lanes                   string
           +--rw forceUnisolateStatus?   uint32
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-fabric-port/FABRIC_PORT/FABRIC_PORT_LIST/name` | `string` | yes |  |  | Fabric port name identifier (例: `Fabric0`) |
| `isolateStatus` | `sonic-fabric-port/FABRIC_PORT/FABRIC_PORT_LIST/isolateStatus` | `stypes:boolean_type` |  |  | true, false | Isolation status of the fabric port |
| `alias` | `sonic-fabric-port/FABRIC_PORT/FABRIC_PORT_LIST/alias` | `string` |  |  |  | Alias of the fabric port |
| `lanes` | `sonic-fabric-port/FABRIC_PORT/FABRIC_PORT_LIST/lanes` | `string` | yes |  |  | Lanes of the fabric port |
| `forceUnisolateStatus` | `sonic-fabric-port/FABRIC_PORT/FABRIC_PORT_LIST/forceUnisolateStatus` | `uint32` |  |  |  | Force unisolate status of the fabric port |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `FABRIC_PORT`
- CLI: `show fabric`

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-fabric-port.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
