---
title: DSCP_TO_TC_MAP テーブル
description: "DSCP_TO_TC_MAP テーブル — DSCP 値 (0..63) を Traffic Class へマップする ingress QoS 分類定義。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dscp-tc-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DSCP_TO_TC_MAP
    - PORT_QOS_MAP
  cli: []
  yang:
    - sonic-dscp-tc-map
---

# DSCP_TO_TC_MAP テーブル

## 概要

[DSCP](../../reference/glossary.md#term-dscp) 値 (0..63) を Traffic Class へマップする ingress [QoS](../../reference/glossary.md#term-qos) 分類定義[^1]。`qosorch` が [SAI](../../reference/glossary.md#term-sai) [QoS](../../reference/glossary.md#term-qos) map (`SAI_QOS_MAP_TYPE_DSCP_TO_TC`) を生成し、ポートにバインドする (`PORT_QOS_MAP.dscp_to_tc_map`)。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>DSCP_TO_TC_MAP")]
  DM["QosOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_qos_map_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
DSCP_TO_TC_MAP|<name>|<dscp>
```

`<name>` はマップ名（1..32 文字、`[a-zA-Z0-9][-a-zA-Z0-9_]*`）。`<dscp>` は 0..63。

## フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `name` (key) | string (1..32) | ✅ | マップ名 |
| `dscp` (key) | string `0..63` | ✅ | [DSCP](../../reference/glossary.md#term-dscp) 値 |
| `tc` | `tc_type` (0..7) | - | 対応 TC |

[YANG](../../reference/glossary.md#term-yang) 上は親子 list 構造。[Redis](../../reference/glossary.md#term-redis) に展開すると `DSCP_TO_TC_MAP|<name>` の hash field として `<dscp>: <tc>` ペアが格納される。

<!-- value-behavior -->
## 値依存挙動マトリクス

### `dscp` (key: string 0..63)

| 値 | 挙動 |
|----|------|
| `0`..`63` | qosorch が SAI_QOS_MAP_TYPE_DSCP_TO_TC エントリを生成 |
| 範囲外 | YANG 違反で reject |

### `tc` (tc_type: 0..7)

| 値 | 挙動 |
|----|------|
| `0`..`7` | [SAI](../../reference/glossary.md#term-sai) QoS map オブジェクトの Traffic Class 値として設定 |
| 8 以上 | ASIC が拒否（SAI エラー） |

> 明示的な enum 制約なし（スパース定義可能）。PORT_QOS_MAP.dscp_to_tc_map から参照されない限り SAI に反映されない。未定義 [DSCP](../../reference/glossary.md#term-dscp) はデフォルト TC=0 になるのが一般的。

<!-- /value-behavior -->

## 購読者

- `qosorch`: [SAI](../../reference/glossary.md#term-sai) [QoS](../../reference/glossary.md#term-qos) map 生成
- `bufferorch` 経由でポート PG への影響あり

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `PORT_QOS_MAP`、`TC_TO_QUEUE_MAP`、`TC_TO_PRIORITY_GROUP_MAP`
- 関連 CLI: なし
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-dscp-tc-map`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-dscp-tc-map`](../yang/sonic-dscp-tc-map.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-dscp-tc-map.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-dscp-tc-map.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `DSCP_TO_TC_MAP|<name>` (例 `AZURE`)。
- 値: `0:0`, `8:1`, `16:0`, `24:3`, `48:6` 等の dscp→TC マップ。

### よくある誤設定

- TC を 8 以上に書くと ASIC が拒否（TC は 0..7）。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'DSCP_TO_TC_MAP|AZURE'
show qos map dscp-tc
```
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| consumer | 条件 | 挙動 |
|---|---|---|
| [orchagent](../../reference/glossary.md#term-orchagent) | DEL 時に PORT / TUNNEL から参照中 | `m_pendingRemove=true` を立てて `task_need_retry` を返す（qosorch.cpp:181-186） |
| [orchagent](../../reference/glossary.md#term-orchagent) | スイッチに DSCP→TC map 適用前の capability 確認 | `querySwitchCapability(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` で未対応の場合はスイッチレベルへの適用をスキップ（qosorch.cpp:1956） |
| [orchagent](../../reference/glossary.md#term-orchagent) | スイッチレベルで DSCP map 解除 (null 設定) | `SAI_NULL_OBJECT_ID` を渡して解除可能（qosorch.cpp:1993） |
| orchagent | SAI 生成・変更・削除失敗 | `task_failed` を返す。DOT1P_TO_TC_MAP と同一の `QosMapHandler` を使用（qosorch.cpp:151-191） |

> **Evidence**: [sonic-swss](../../reference/glossary.md#term-sonic-swss) `orchagent/qosorch.cpp:1956,1993`; `orchagent/tunneldecaporch.cpp:831-834`
<!-- /cdb-exceptions -->

<!-- glossary-links-injected: 9e94f614fc2c -->
