---
title: sonic-buffer-queue YANG
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-queue.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BUFFER_QUEUE]
  cli: []
  yang: [sonic-port, sonic-buffer-profile]
---

# sonic-buffer-queue YANG

## 概要

- module: `sonic-buffer-queue`
- namespace: `http://github.com/sonic-net/sonic-buffer-queue`
- revision: `2021-07-01`
- import: `sonic-port`, `sonic-buffer-profile`, `sonic-device_metadata`, `sonic-types`
- top container: `sonic-buffer-queue`

Egress queue buffer configuration per port.[^1]

## ツリー

```
module: sonic-buffer-queue
  +--rw sonic-buffer-queue
     +--rw BUFFER_QUEUE
        +--rw BUFFER_QUEUE_LIST* [port qindex]
        |  +--rw port       -> /prt:sonic-port/PORT/PORT_LIST/name
        |  +--rw qindex     string
        |  +--rw profile?   -> /bpf:sonic-buffer-profile/BUFFER_PROFILE/BUFFER_PROFILE_LIST/name
        +--rw VOQ_BUFFER_QUEUE_LIST* [hostname asic_name port qindex]
           +--rw hostname     stypes:hostname
           +--rw asic_name    stypes:asic_name
           +--rw port         string
           +--rw qindex       string
           +--rw profile?     -> /bpf:sonic-buffer-profile/BUFFER_PROFILE/BUFFER_PROFILE_LIST/name
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `port` | `sonic-buffer-queue/BUFFER_QUEUE/BUFFER_QUEUE_LIST/port` | `leafref` | yes |  | /prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name | Port on which the egress queue buffer is configured. |
| `qindex` | `sonic-buffer-queue/BUFFER_QUEUE/BUFFER_QUEUE_LIST/qindex` | `string` | yes |  | pattern `(1[0-5]|[0-9])((-)(1[0-5]|[0-9]))?` | Egress queue index or range (e.g. 0-3) on the port. |
| `profile` | `sonic-buffer-queue/BUFFER_QUEUE/BUFFER_QUEUE_LIST/profile` | `leafref` |  | 0 | /bpf:sonic-buffer-profile/bpf:BUFFER_PROFILE/bpf:BUFFER_PROFILE_LIST/bpf:name | Buffer profile applied to this egress queue. |
| `hostname` | `sonic-buffer-queue/BUFFER_QUEUE/VOQ_BUFFER_QUEUE_LIST/hostname` | `stypes:hostname` | yes |  |  | VOQ chassis hostname owning this port. |
| `asic_name` | `sonic-buffer-queue/BUFFER_QUEUE/VOQ_BUFFER_QUEUE_LIST/asic_name` | `stypes:asic_name` | yes |  |  | ASIC instance name within the VOQ chassis. |
| `port` | `sonic-buffer-queue/BUFFER_QUEUE/VOQ_BUFFER_QUEUE_LIST/port` | `string` | yes |  | length 1..128 | Port name on the VOQ chassis linecard. |
| `qindex` | `sonic-buffer-queue/BUFFER_QUEUE/VOQ_BUFFER_QUEUE_LIST/qindex` | `string` | yes |  | pattern `(1[0-5]|[0-9])((-)(1[0-5]|[0-9]))?` | Egress queue index or range (e.g. 0-3) on the port. |
| `profile` | `sonic-buffer-queue/BUFFER_QUEUE/VOQ_BUFFER_QUEUE_LIST/profile` | `leafref` |  | 0 | /bpf:sonic-buffer-profile/bpf:BUFFER_PROFILE/bpf:BUFFER_PROFILE_LIST/bpf:name | Buffer profile applied to this egress queue. |

## leafref / 依存

- `sonic-buffer-queue/BUFFER_QUEUE/BUFFER_QUEUE_LIST/port` → `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name`
- `sonic-buffer-queue/BUFFER_QUEUE/BUFFER_QUEUE_LIST/profile` → `/bpf:sonic-buffer-profile/bpf:BUFFER_PROFILE/bpf:BUFFER_PROFILE_LIST/bpf:name`
- `sonic-buffer-queue/BUFFER_QUEUE/VOQ_BUFFER_QUEUE_LIST/profile` → `/bpf:sonic-buffer-profile/bpf:BUFFER_PROFILE/bpf:BUFFER_PROFILE_LIST/bpf:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `BUFFER_QUEUE`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`BUFFER_QUEUE`](../config-db/buffer-queue.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-buffer-queue.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`


<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->
