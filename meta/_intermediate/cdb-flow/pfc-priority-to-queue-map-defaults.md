# MAP_PFC_PRIORITY_TO_QUEUE — Phase A: 暗黙デフォルト調査

## 調査対象フィールド

| フィールド | 所属 |
|-----------|------|
| `name` | 外側 list の key |
| `pfc_priority` | 内側 list の key |
| `qindex` | 内側 list の value フィールド |

## YANG デフォルト確認

`sonic-pfc-priority-queue-map.yang` (revision 2021-04-15) に `default` 文は一切なし。

- `name`: デフォルト値なし
- `pfc_priority`: デフォルト値なし
- `qindex`: デフォルト値なし (mandatory ではないが `default` も指定なし)

## コード由来デフォルト (qos_config.j2)

`sonic-buildimage/files/build_templates/qos_config.j2:209-220`

```jinja
{% if (generate_pfc_to_queue_map is defined) %}
    {{- generate_pfc_to_queue_map() }}
{% else %}
    "MAP_PFC_PRIORITY_TO_QUEUE": {
        "AZURE": {
            "0": "0",
            "1": "1",
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "5",
            "6": "6",
            "7": "7"
        }
    },
{% endif %}
```

**ハードコードデフォルト**: `config qos reload` 時に platform 側で `generate_pfc_to_queue_map` マクロが未定義の場合、`AZURE` という名前のマップが identity mapping (priority N → queue N) で自動生成される。これは YANG には記載なく qos_config.j2 のみに存在するビルド時デフォルト。

platform 側（HWSKU の j2 テンプレート等）が `generate_pfc_to_queue_map` を定義している場合はそちらが優先されるため、**プラットフォーム依存の値差異**が発生する。

## convertFieldValuesToAttributes — 暗黙変換

`sonic-swss/orchagent/qosorch.cpp:991-1009` `PfcToQueueHandler::convertFieldValuesToAttributes`

```cpp
pfc_to_queue_map_list.list[ind].key.prio = (uint8_t)stoi(fvField(*i));
pfc_to_queue_map_list.list[ind].value.queue_index = (uint8_t)stoi(fvValue(*i));
```

- `stoi()` で変換: 例外処理 (try/catch) なし。空文字・非数値は **uncaught `std::invalid_argument`** → 呼び出し元 `processWorkItem` が `task_invalid_entry` を返す
- 他の Handler (Dot1pToTcMapHandler 等) と異なり try/catch を持たないため、例外は std::terminate に至る可能性があるが、orchagent はプロセス全体を再起動する仕組みのため実害は限定的
- `(uint8_t)` キャストにより 0..255 の範囲で切り捨て。YANG 制約が 0..7 を保証するため実運用では問題なし

## dead field / silent drop 検査

- `qindex`: YANG に mandatory 指定なし。CONFIG_DB に `pfc_priority` キーが存在し `qindex` フィールドが存在しない場合、`kfvFieldsValues(tuple)` に `qindex` が含まれないため SAI 側へは queue_index = 0 が送られるか、エントリ数 0 の list として create_qos_map が呼ばれる可能性がある。
  - 実際には key が `pfc_priority` で value が `qindex` という CONFIG_DB hash 構造のため、`fvField(*i) = "3", fvValue(*i) = "3"` のような形で格納される
  - `qindex` が存在しないエントリは field-value pair 自体が存在しない → list に含まれず → 欠落した priority のマッピングが SAI に登録されない (silent skip)

## 書き込み順依存

なし。MAP は原子的に全エントリを list として SAI に渡す。部分更新は set_qos_map_attribute で既存 object を更新するが、変更前後で一時的に不整合が生じる可能性はある（SAI レベルの atomic 保証は ASIC ベンダ依存）。

## YANG-実装 discrepancy

| 点 | YANG | 実装 |
|---|---|---|
| `pfc_priority` pattern | `"[0-7]?"` (空文字も許容) | `stoi()` 空文字 → 例外 → task_invalid_entry (silent reject) |
| `qindex` pattern | `"[0-7]?"` (空文字も許容) | `stoi()` 空文字 → 例外 → task_invalid_entry |
| `qindex` mandatory | 非 mandatory | 欠落時は silent skip (その priority がマッピングされない) |
| try/catch | N/A | 他 Handler は try/catch あり、PfcToQueue は**なし** — uncaught exception リスク |

## dead consumer

なし。`QosOrch` は `initTableHandlers()` で無条件に `CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME` を登録 (`orchdaemon.cpp:1344`)。platform 非依存で常時有効。

## 結論・デフォルト一覧

| フィールド | YANG default | コード由来デフォルト | 備考 |
|-----------|-------------|---------------------|------|
| `name` | なし | `"AZURE"` (qos_config.j2 fallback) | platform が `generate_pfc_to_queue_map` を定義しない場合のみ |
| `pfc_priority` | なし | `"0"`..`"7"` (AZURE identity map) | qos_config.j2 fallback 時。platform 依存で変わる可能性あり |
| `qindex` | なし | `pfc_priority` と同値 (identity map `"N": "N"`) | qos_config.j2 AZURE fallback のみ。欠落時は silent skip |

## evidence

- `sonic-buildimage/files/build_templates/qos_config.j2:206-221`
- `sonic-swss/orchagent/qosorch.cpp:991-1009` (PfcToQueueHandler::convertFieldValuesToAttributes)
- `sonic-swss/orchagent/qosorch.cpp:1011-1037` (PfcToQueueHandler::addQosItem)
- `sonic-swss/orchagent/qosorch.cpp:124-201` (QosMapHandler::processWorkItem)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pfc-priority-queue-map.yang`
