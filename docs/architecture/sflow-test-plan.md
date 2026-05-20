---
title: sFlow テストプラン（hsflowd + 2 collector / sampling rate / agent-id / counter polling）
description: sFlow テストプラン（hsflowd + 2 collector / sampling rate / agent-id / counter
  polling） — T0 上で SONiC sFlow 機能を機能検証するテスト。
area: architecture
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/sflow/Sflow_test_plan.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - SFLOW
  - SFLOW_COLLECTOR
  - SFLOW_SESSION
  - PORTCHANNEL_MEMBER
  - PORTCHANNEL
  - PORTCHANNEL_INTERFACE
  - PORT
  cli:
  - config sflow
  - show sflow
  - config portchannel
  yang:
  - sonic-portchannel
  - sonic-sflow
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 09 章: Telemetry / SNMP / ログ](../topics/09-telemetry-snmp/index.md) を参照。
<!-- /topics-tip -->

!!! note "裏取りステータス: code-verified（CLI / docker layout）"
    verifier-batch-18 で確認:

    - `sonic-utilities/config/main.py:9040-9070` 付近に `config sflow` group / `enable` / `disable` 等のコマンド定義（`SFLOW` table の `global` エントリを `admin_state` で更新）
    - `sonic-buildimage/dockers/docker-sflow/` に Dockerfile.j2、`port_index_mapper.py`、`supervisord.conf` を確認
    - collector 数上限 2 の強制ロジック / agent-id del 挙動 / config save→reboot 永続化 / sonic-mgmt 配下の test ケース実体については本リポでは追跡していない（必要なら sonic-mgmt 側で別途裏取り）

# sFlow テストプラン（`hsflowd` + 2 collector / sampling rate / agent-id / counter polling）

## 概要

T0 上で [SONiC](../reference/glossary.md#term-sonic) sFlow 機能を機能検証するテスト[^1]。4 [PortChannel](../reference/glossary.md#term-portchannel) から各 1 ポートを sFlow 有効化、Vlan1000 の 2 ポートを使って PTF docker の collector へ繋ぐ構成。`sflowtool` を PTF docker にインストールし、counter sampling と flow sampling の出力をテキストに落として parse する。

## 動作仕様

### 6 つのテスト項目

| TC | 観点 |
|----|------|
| 1 | `SFLOW_COLLECTOR` の add/del を `hsflowd` が処理する |
| 2 | counter polling 間隔の変更（既定 20s → 0 で disable → 60s） |
| 3 | agent-id 変更（Loopback / eth0） |
| 4 | `SFLOW_SESSION` 単位の interface enable/disable |
| 5 | per-interface sampling rate 変更（512 / 256 / 1024） |
| 6 | config save + reboot / fast-reboot 横断保持 |

### TC1 の詳細

1. 4 IF で sflow 有効化 + collector 1 (default port 6343) + global enable → 両方の確認
2. collector 削除 → trafffic で sample なし → 再追加で復活
3. **2 つ目の collector** を非 default port (6344) で追加 → 両 collector が受信
4. 2 つ目を削除 → 1 つ目だけが受信
5. 2 つ目を復活 → 両者受信
6. **3 つ目を追加 → エラー**: collector は **最大 2 個**[^1]
7. 1 つ目を削除 → 2 つ目だけが受信を継続

### TC2 の詳細[^1]

| ステップ | 期待 |
|---------|------|
| 既定 20s | 両 collector が 20s ごとに counter sample を受信 |
| 0s に設定 | counter polling disable、counter sample 受信なし |
| 60s に設定 | 60s ごとに受信 |

### TC3: agent-id

`config sflow agent-id add Loopback0` 等で **agent-id を sample に乗せる**。delete すると **直前値が残る**（未設定状態に戻らない）[^1]。

### TC4 / TC5: per-interface 制御

`SFLOW_SESSION` テーブル add/del で IF 単位 enable/disable。`sample_rate` フィールドで sampling rate を IF ごとに変更可能。一括変更も可能[^1]。

### TC6: 永続化

- `config save` → `reboot` → 復元: collector / sampling / polling interval が再現
- 同 → `fast-reboot` でも再現
- 最終 sFlow disable + save + reboot → collector に sample が来ないことの逆検証

## 関連 CLI

```bash
config sflow enable | disable
config sflow polling-interval <seconds>
config sflow agent-id add <if> | del
config sflow collector add <name> <ip> [--port <udp_port>]
config sflow collector del <name>
config sflow interface enable <if> | disable <if>
config sflow interface sample-rate <if> <rate>

show sflow
show sflow interface
```

## 制限事項

- collector **最大 2 個**[^1]
- counter polling 0 秒で disable（負値 / 範囲外は CLI 拒否のはず）
- t0 トポロジ前提
- `sflowtool` を PTF docker にインストールしておくこと

## 干渉する機能

- **`hsflowd` ホストデーモン**: `SFLOW*` テーブルを実装する中核
- **[CONFIG_DB](../reference/glossary.md#term-config_db) / [sonic-utilities](../reference/glossary.md#term-sonic-utilities)**: テスト対象 CLI が依存
- **fast/warm-reboot**: 永続化テストが対象

## 引用元

[^1]: [sonic-net/SONiC doc/sflow/Sflow_test_plan.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/sflow/Sflow_test_plan.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
