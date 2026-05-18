# EXP_TO_FC_MAP — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/exp-to-fc-map.md` Phase C 追加分。
対象テーブル: `CONFIG_DB EXP_TO_FC_MAP`。Consumer: `QosOrch::handleExpToFcTable()` / `QosMapHandler::processWorkItem()` (`qosorch.cpp`)。

スキャン範囲:
- `sonic-swss/orchagent/qosorch.cpp`: `QosMapHandler::processWorkItem()` (L124-201), `handleExpToFcTable()` (L1292-), `handlePortQosMapTable()` (L2046-2230), `doTask()` (L2231-2260)
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp`: `NhgMapOrch::getMaxNumFcs()` (L299-325), `validateFc()` (L346-370)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port-qos-map.yang`: PORT_QOS_MAP leafref 一覧

---

## YANG leafref 分析

### EXP_TO_FC_MAP 側

`sonic-exp-fc-map.yang` には leafref が一切存在しない。マップエントリは自己完結しており、他テーブルへの YANG 制約依存はない。

### PORT_QOS_MAP 側（参照元）

`sonic-port-qos-map.yang` の `PORT_QOS_MAP_LIST` を確認した結果、**`exp_to_fc_map` フィールドの YANG leafref は存在しない**。他の QoS マップフィールド（`tc_to_pg_map`, `tc_to_queue_map`, `pfc_to_queue_map`, `dscp_to_tc_map`, `dot1p_to_tc_map` 等）はそれぞれの YANG モジュールへ leafref が定義されているが、`exp_to_fc_map` は YANG 制約なし（実装レベルのみで依存を強制）。

---

## 実装レベルの暗黙参照

### 1. PORT_QOS_MAP — EXP_TO_FC_MAP を参照する唯一のテーブル

- **参照先テーブル**: `CONFIG_DB PORT_QOS_MAP`
- **参照方向**: `PORT_QOS_MAP` が `EXP_TO_FC_MAP` を**名前参照（consumer）**する
- **解決方向**: `EXP_TO_FC_MAP|<name>` の SAI オブジェクトが `m_qos_maps[CFG_EXP_TO_FC_MAP_TABLE_NAME]` に登録されていない状態で `PORT_QOS_MAP` の `exp_to_fc_map` フィールドが処理されると `resolveFieldRefValue()` が `ref_resolve_status::not_resolved` を返し、`handlePortQosMapTable()` は `task_need_retry` を返す（`qosorch.cpp:2124-2131`）
- **YANG leafref**: **なし**（実装専用）
- **evidence**: `qosorch.cpp:112` (`qos_to_ref_table_map` での `exp_to_fc_field_name → CFG_EXP_TO_FC_MAP_TABLE_NAME` マッピング); `qosorch.cpp:2124-2131` (`resolveFieldRefValue` と `task_need_retry`)

### 2. NhgMapOrch — FC 上限値の外部依存

- **参照先**: `NhgMapOrch::getMaxNumFcs()` → SAI `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES`
- **参照方向**: `ExpToFcMapHandler::convertFieldValuesToAttributes()` が FC 値の検証時に `NhgMapOrch::getMaxNumFcs()` を呼ぶ
- **意味**: `max_num_fcs` の値はプラットフォーム依存（`static int max_num_fcs = -1` で初期化、初回 SAI 問い合わせで確定）。`max_num_fcs = -1` のまま（未初期化状態）では `fc >= max_num_fcs` が真になり全 FC 値が reject される（実質、SAI 起動前の投入は不可）
- **evidence**: `nhgmaporch.cpp:299-325` (`getMaxNumFcs()`); `nhgmaporch.cpp:346-370` (`validateFc()` 内の範囲チェック)

### 3. doTask() 実行順序 — EXP_TO_FC_MAP は PORT_QOS_MAP より先に drain

- **参照先**: `QosOrch::doTask()` の実行順序制御
- **参照方向**: 内部スケジューリング（間接）
- **意味**: `QosOrch::doTask()` (L2231-2260) は `PORT_QOS_MAP` と `QUEUE` の executor を最後に drain し、その他（`EXP_TO_FC_MAP` を含む全 QoS マップ）を先に drain する。これにより `EXP_TO_FC_MAP` → `PORT_QOS_MAP` の参照解決は自然に正しい順序で実行される（同一イテレーションで `task_need_retry` が最小化される）
- **evidence**: `qosorch.cpp:2231-2260`

### 4. gPortsOrch（PortsOrch）— allPortsReady() ゲート

- **参照先**: `PortsOrch::allPortsReady()`
- **参照方向**: `QosOrch::doTask(Consumer&)` (L2253) の冒頭ガード
- **意味**: `allPortsReady()` が false の間は QoS テーブルの処理を一切進めない。EXP_TO_FC_MAP エントリが CONFIG_DB に投入されても PortsOrch の初期化完了前は orchagent で処理されない
- **evidence**: `qosorch.cpp:2253-2258`

---

## 参照関係サマリ

```
CONFIG_DB EXP_TO_FC_MAP
  被参照 (referencedBy):
  └─ [実装のみ] CONFIG_DB PORT_QOS_MAP.exp_to_fc_map
         → resolveFieldRefValue() でOID解決、未解決時は task_need_retry

  依存 (dependsOn):
  ├─ [実装] NhgMapOrch::getMaxNumFcs() → SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES
  │       (FC値上限の動的取得。初期化前は全エントリ reject)
  └─ [実装] PortsOrch::allPortsReady()
          (false の間は orchagent で処理がブロックされる)
```

| 参照先テーブル / コンポーネント | YANG leafref | 参照種別 | evidence |
|---|:---:|---|---|
| `PORT_QOS_MAP.exp_to_fc_map` | ✗ | `EXP_TO_FC_MAP` OID の名前参照元（被参照） | `qosorch.cpp:112`, `qosorch.cpp:2124-2131` |
| `NhgMapOrch::getMaxNumFcs()` | ✗ | FC 値上限の動的クエリ（SAI 経由） | `nhgmaporch.cpp:299-325` |
| `PortsOrch::allPortsReady()` | ✗ | 起動順序ガード（false の間は全 QoS 処理停止） | `qosorch.cpp:2253-2258` |

---

## ページ反映方針

- `<!-- cross-refs -->` ブロックを `<!-- ordering -->` ブロックの**直後**（ファイル末尾）に追加する。
- YANG leafref なし・実装専用参照のみであることを明示する。
- `PORT_QOS_MAP` が `exp_to_fc_map` を参照する方向（被参照）と、`NhgMapOrch` への依存方向（FC 上限）を表形式で示す。
