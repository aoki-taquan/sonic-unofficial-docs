# PFC_PRIORITY_TO_PRIORITY_GROUP_MAP — Phase A: 暗黙デフォルト調査

## 調査対象フィールド

| フィールド | 所属 |
|-----------|------|
| `name` | 外側 list の key |
| `pfc_priority` | 内側 list の key |
| `pg` | 内側 list の value フィールド |

## YANG デフォルト確認

`sonic-pfc-priority-priority-group-map.yang` (revision 2021-04-15) に `default` 文は一切なし。

- `name`: デフォルト値なし
- `pfc_priority`: デフォルト値なし（pattern `[0-7]?`）
- `pg`: デフォルト値なし（pattern `[0-7]?`、mandatory 指定なし）

## コード由来デフォルト (qos_config.j2)

`sonic-buildimage/files/build_templates/qos_config.j2:395-409`

```jinja
{% if asic_type in pfc_to_pg_map_supported_asics  %}
    "PFC_PRIORITY_TO_PRIORITY_GROUP_MAP": {
{% if port_names_list_extra_queues|length > 0 %}
        "AZURE_DUALTOR": {
            "2": "2",
            "3": "3",
            "4": "4",
            "6": "6"
        },
{% endif %}
        "AZURE": {
            "3": "3",
            "4": "4"
        }
    },
{% endif %}
```

`pfc_to_pg_map_supported_asics` の定義 (`qos_config.j2:163`):

```jinja
{%- set pfc_to_pg_map_supported_asics = ['mellanox', 'barefoot'] -%}
```

**ハードコードデフォルト**:
- `AZURE` map: `pfc_priority "3" → pg "3"`, `pfc_priority "4" → pg "4"` (lossless traffic の 2 優先度のみ)
- `AZURE_DUALTOR` map (dualtor 構成かつ extra queues が存在する場合のみ): `"2"→"2"`, `"3"→"3"`, `"4"→"4"`, `"6"→"6"` (4 優先度)
- **投入条件**: `asic_type` が `mellanox` または `barefoot` のときのみ。それ以外の ASIC では PFC_PRIORITY_TO_PRIORITY_GROUP_MAP テーブルが生成されない。

プラットフォーム独自の `qos_config_t1.j2` (例: Celestica DS2000、Dell E3224F 等) でも同一パターンを採用している。

## convertFieldValuesToAttributes — 暗黙変換

`sonic-swss/orchagent/qosorch.cpp:937-955` `PfcPrioToPgHandler::convertFieldValuesToAttributes`

```cpp
pfc_prio_to_pg_map_list.list[ind].key.prio = (uint8_t)stoi(fvField(*i));
pfc_prio_to_pg_map_list.list[ind].value.pg = (uint8_t)stoi(fvValue(*i));
```

- `stoi()` で変換: try/catch なし。空文字・非数値は **uncaught `std::invalid_argument`** → orchagent プロセス例外（実質 task_invalid_entry）
- `(uint8_t)` キャストで 0..255 範囲に切り捨て。YANG が 0..7 を保証するため実運用では問題なし
- MAP_PFC_PRIORITY_TO_QUEUE の `PfcToQueueHandler` と同様のパターン（try/catch なし）

## dead field / silent drop 検査

- `pg` フィールド: YANG に mandatory 指定なし。CONFIG_DB の hash に `pg` field が欠落した場合、`fvValue(*i)` が空文字列 → `stoi("")` で例外 → `task_invalid_entry` 相当
- AZURE マップでは priority 0,1,2,5,6,7 はマッピングなし → これらの priority の PFC フレームは PG binding なし（best-effort 扱い）

## YANG-実装 discrepancy

| 点 | YANG | 実装 |
|---|---|---|
| `pfc_priority` pattern | `"[0-7]?"` (空文字も許容) | `stoi()` 空文字 → 例外 → task_invalid_entry |
| `pg` pattern | `"[0-7]?"` (空文字も許容) | `stoi()` 空文字 → 例外 → task_invalid_entry |
| `pg` mandatory | 非 mandatory | 欠落時は例外で処理中断 |
| ASIC 条件 | 記載なし | `mellanox`/`barefoot` のみテーブル生成（qos_config.j2 条件）|

## dead consumer

なし。`QosOrch` は `initTableHandlers()` で無条件に `CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME` を登録 (`orchdaemon.cpp:377`)。テーブルが存在しない ASIC でも購読は有効（CONFIG_DB に entry がないだけ）。

## 結論・デフォルト一覧

| フィールド | YANG default | コード由来デフォルト | 備考 |
|-----------|-------------|---------------------|------|
| `name` | なし | `"AZURE"` (mellanox/barefoot ASIC) / `"AZURE_DUALTOR"` (dualtor 構成のみ追加) | qos_config.j2:405,398 |
| `pfc_priority` | なし | `"3"`, `"4"` (AZURE); `"2"`,`"3"`,`"4"`,`"6"` (AZURE_DUALTOR) | lossless 優先度のみ投入 |
| `pg` | なし | `pfc_priority` と同値 (identity mapping) | `"3"→"3"`, `"4"→"4"` 等 |

## evidence

- `sonic-buildimage/files/build_templates/qos_config.j2:163,395-409`
- `sonic-swss/orchagent/qosorch.cpp:937-955` (PfcPrioToPgHandler::convertFieldValuesToAttributes)
- `sonic-swss/orchagent/qosorch.cpp:957-982` (PfcPrioToPgHandler::addQosItem)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pfc-priority-priority-group-map.yang`
- platform examples: `device/celestica/x86_64-cel_ds2000-r0/DS2000/qos_config_t1.j2:154-159`
