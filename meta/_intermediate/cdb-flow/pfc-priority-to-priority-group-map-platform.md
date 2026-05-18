# PFC_PRIORITY_TO_PRIORITY_GROUP_MAP — Phase H Platform 調査

調査日: 2026-05-18

## 調査対象

- `sonic-buildimage/files/build_templates/qos_config.j2`
- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 発見事項

### 1. qos_config.j2 の ASIC 限定生成

`qos_config.j2:163` にて ASIC タイプごとのサポートリストを定義:

```jinja
{%- set pfc_to_pg_map_supported_asics = ['mellanox', 'barefoot'] -%}
```

`qos_config.j2:395-410`:
```jinja
{% if asic_type in pfc_to_pg_map_supported_asics %}
    "PFC_PRIORITY_TO_PRIORITY_GROUP_MAP": {
        "AZURE": {
            "3": "3",
            "4": "4"
        }
    },
{% endif %}
```

つまり `config qos reload` 時に `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` テーブルが CONFIG_DB に投入されるのは **Mellanox (NVIDIA) と Barefoot (Intel Tofino) プラットフォームのみ**。Broadcom / Marvell / Cisco-8000 / VS では本テーブルは生成されない。

### 2. PORT_QOS_MAP への参照も同様に制限

`qos_config.j2:456-461`:
```jinja
{% if asic_type in pfc_to_pg_map_supported_asics %}
    "pfc_to_pg_map": "AZURE",
{% endif %}
```

`PORT_QOS_MAP` の `pfc_to_pg_map` フィールドも Mellanox / Barefoot のみ設定される。

### 3. QosOrch 登録は platform 非依存

`orchdaemon.cpp:377` で `CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME` は無条件に QosOrch に登録される。つまりテーブルが存在するプラットフォームでのみ実際に処理が走る設計。

### 4. PfcPrioToPgHandler 内に platform 分岐なし

`qosorch.cpp:957-988` の `PfcPrioToPgHandler::addQosItem()` および `handlePfcPrioToPgTable()` にベンダー固有分岐なし。SAI `create_qos_map` / `remove_qos_map` を直接呼ぶだけ。

### 5. DualToR 向け AZURE_DUALTOR マップ

`qos_config.j2:397-403` で DualToR ポートが存在する場合 (`port_names_list_extra_queues|length > 0`) は追加で AZURE_DUALTOR マップも生成:

```json
"AZURE_DUALTOR": {
    "2": "2",
    "3": "3",
    "4": "4",
    "6": "6"
}
```

これは Mellanox DualToR 構成専用の追加エントリ。

## 結論

本テーブルは **Mellanox (NVIDIA) と Barefoot (Intel Tofino) ASIC 専用**。他の ASIC ベンダーでは `qos_config.j2` が本テーブルを生成しないため事実上不使用。orchagent 側の処理自体はプラットフォーム非依存。
