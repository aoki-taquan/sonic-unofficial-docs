# TC_TO_QUEUE_MAP 暗黙参照スキャン (Phase C)

`docs/reference/config-db/tc-to-queue-map.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/qosorch.cpp`。`TC_TO_QUEUE_MAP` テーブル変更時に `QosOrch` が連鎖して参照・依存する CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -n "TC_TO_QUEUE_MAP\|PORT_QOS_MAP\|SCHEDULER\|DSCP_TO_TC_MAP\|qos_to_ref_table_map\|qos_to_attr_map" \
    .cache/sonic-sources/sonic-swss/orchagent/qosorch.cpp | head -60
```

`qos_to_ref_table_map` (qosorch.cpp:100-116) で `tc_to_queue_field_name` → `CFG_TC_TO_QUEUE_MAP_TABLE_NAME` のマッピングが定義される。`PORT_QOS_MAP` エントリの `tc_to_queue_map` フィールドが `TC_TO_QUEUE_MAP` の name を参照し、`resolveFieldRefValue()` で OID に解決する。

## 検出された暗黙参照テーブル

### 上流参照元 (TC_TO_QUEUE_MAP を参照するテーブル)

| テーブル | フィールド | 参照タイミング | 用途 | evidence |
|---|---|---|---|---|
| `PORT_QOS_MAP` | `tc_to_queue_map` | SET 処理時 `resolveFieldRefValue()` | ポートに bind する TC→Queue マップ名を指定。未解決なら `task_need_retry` | qosorch.cpp:L103,L2077-2133 |

`PORT_QOS_MAP` の `handlePortQosMapTable()` が `qos_to_ref_table_map` の `tc_to_queue_field_name` エントリを参照し、`TC_TO_QUEUE_MAP` 内のオブジェクト名を解決して SAI port attribute `SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` にセットする (qosorch.cpp:L64)。

### 下流参照先 (TC_TO_QUEUE_MAP が依存するテーブル)

TC_TO_QUEUE_MAP ハンドラ自体は他テーブルを直接読み出さない。ただし `QosOrch` の `m_qos_maps` 参照カウンタ管理を通じて以下との間接連動がある。

| テーブル | 連動メカニズム | 用途 | evidence |
|---|---|---|---|
| `PORT_QOS_MAP` | 参照カウンタ (`object_reference_map`) | TC_TO_QUEUE_MAP が DEL 対象になったとき PORT_QOS_MAP からの参照が残っていれば `m_pendingRemove=true` で保留 | qosorch.cpp:L84,L87 |

### 同一 `QosOrch` 内の処理連鎖

`QosOrch` は以下の QoS マップテーブルを同一ハンドラマップで購読し、`m_qos_handler_map` (qosorch.cpp:L1329-L1335) に登録する。TC_TO_QUEUE_MAP の適用前提として以下の順序依存がある。

| テーブル | 役割 | TC_TO_QUEUE_MAP との依存関係 | evidence |
|---|---|---|---|
| `DSCP_TO_TC_MAP` | DSCP → TC 変換マップ | 上流。DSCP を TC に変換後、TC_TO_QUEUE_MAP が TC → Queue に変換する | qosorch.cpp:L61,L81,L100,L1329 |
| `SCHEDULER` | キューのスケジューラプロファイル | 下流。`QUEUE` テーブルが `SCHEDULER` を参照し、TC_TO_QUEUE_MAP が決定した queue index に適用される | qosorch.cpp:L70,L85,L109,L1333 |
| `PORT_QOS_MAP` | ポートへの QoS マップ一括適用 | TC_TO_QUEUE_MAP の OID を `tc_to_queue_map` フィールドで参照し、ポートに bind | qosorch.cpp:L87,L1335 |

### トンネル QoS での利用

`qos_to_ref_table_map` (qosorch.cpp:L116) に `encap_tc_to_queue_field_name` → `CFG_TC_TO_QUEUE_MAP_TABLE_NAME` が登録されている。tunnel encap 用の TC→Queue マップも同じ `TC_TO_QUEUE_MAP` テーブルを参照する。

| フィールド (PORT_QOS_MAP) | 参照テーブル | 用途 |
|---|---|---|
| `tc_to_queue_map` | `TC_TO_QUEUE_MAP` | 通常ポート用 TC→Queue マップ |
| `encap_tc_to_queue_map` | `TC_TO_QUEUE_MAP` | トンネル encap 用 TC→Queue マップ |

## まとめ — `tc-to-queue-map.md` Phase C 記載対象

| カテゴリ | テーブル |
|---|---|
| 上流参照元 (TC_TO_QUEUE_MAP を参照) | `PORT_QOS_MAP` (`tc_to_queue_map` / `encap_tc_to_queue_map` フィールド) |
| パイプライン上流 (TC 生成源) | `DSCP_TO_TC_MAP` (DSCP → TC → Queue の前段) |
| パイプライン下流 (Queue 消費先) | `SCHEDULER` (queue index に対してスケジューラが適用される) |
| 参照カウンタ連動 | `PORT_QOS_MAP` (DEL 保留メカニズム) |

## 検証コマンド

```bash
grep -n "tc_to_queue_field_name\|CFG_TC_TO_QUEUE_MAP\|tc_to_queue_map" \
    .cache/sonic-sources/sonic-swss/orchagent/qosorch.cpp

grep -n "qos_to_ref_table_map\|qos_to_attr_map\|m_qos_maps" \
    .cache/sonic-sources/sonic-swss/orchagent/qosorch.cpp | head -30
```

このスキャン結果から派生して `docs/reference/config-db/tc-to-queue-map.md` の `<!-- cross-refs -->` ブロックを生成する。
