---
title: config qos サブコマンド
description: "config qos サブコマンド — config qos は QoS と buffer 関連テンプレートを再生成して CONFIG_DB に反映する CLI グループ。"
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - PORT_QOS_MAP
    - BUFFER_PORT_INGRESS_PROFILE_LIST
    - BUFFER_PORT_EGRESS_PROFILE_LIST
    - BUFFER_PG
    - BUFFER_QUEUE
    - DEVICE_METADATA
  cli:
    - config qos
  yang: []
---

# config qos サブコマンド

## 概要

`config qos` は QoS と buffer 関連テンプレートを再生成して CONFIG_DB に反映する CLI グループ。`clear` は既存 QoS 設定を削除し、`reload` は platform/HWSKU の `qos.json.j2` と `buffers*.json.j2` を `sonic-cfggen` で展開する[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config qos clear [--verbose]` | QoS 設定を削除 |
| `config qos reload [options]` | QoS/buffer 設定をテンプレートから再投入 |

## `config qos reload`

**用法**:

```
config qos reload [--ports <port[,port...]>]
                  [--no-dynamic-buffer]
                  [--dry_run <file-prefix>]
                  [--json-data <json>]
                  [--verbose]
```

`--ports` がある場合は、対象 port に関連する table だけを再計算する `_qos_update_ports()` に進む。対象 table は port 単独 key の `PORT_QOS_MAP`, `BUFFER_PORT_INGRESS_PROFILE_LIST`, `BUFFER_PORT_EGRESS_PROFILE_LIST` と、複合 key の `QUEUE`, `BUFFER_PG`, `BUFFER_QUEUE`[^2]。

`--ports` がない場合、既存 QoS を clear してから HWSKU 配下の template を展開する。Mellanox/Barefoot で `--no-dynamic-buffer` が無い場合は `buffers_dynamic.json.j2` を使い、`DEVICE_METADATA|localhost` の `buffer_model` を `dynamic` に更新する。そうでない場合は `buffers.json.j2` を使い、対応 ASIC では `traditional` に更新する[^3]。

`--dry_run` を指定すると CONFIG_DB に書かず、展開後 JSON をファイルへ出力する。

## 関連する CONFIG_DB

| テーブル | 操作 |
|----------|------|
| `DEVICE_METADATA` | `buffer_model` を `dynamic` / `traditional` に更新 |
| `PORT_QOS_MAP` | port 別 QoS map |
| `BUFFER_PORT_INGRESS_PROFILE_LIST` | ingress buffer profile list |
| `BUFFER_PORT_EGRESS_PROFILE_LIST` | egress buffer profile list |
| `BUFFER_PG` / `BUFFER_QUEUE` | port + PG/queue 単位の buffer 設定 |

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`PORT_QOS_MAP`](../config-db/port-qos-map.md) / [`BUFFER_PORT_INGRESS_PROFILE_LIST`](../config-db/buffer-port-ingress-profile-list.md) / [`BUFFER_PORT_EGRESS_PROFILE_LIST`](../config-db/buffer-port-egress-profile-list.md) / [`BUFFER_PG`](../config-db/buffer-pg.md) / [`BUFFER_QUEUE`](../config-db/buffer-queue.md) / [`DEVICE_METADATA`](../config-db/device-metadata.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `config qos` グループ、`clear`、`reload` 定義。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L3631>

[^2]: `_qos_update_ports()` の対象 table。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L3715>

[^3]: `reload()` 内の buffer template 選択と `DEVICE_METADATA` 更新。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L3666>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->
