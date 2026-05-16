# TC_TO_QUEUE_MAP — Phase A: 暗黙デフォルト調査結果

## 調査対象ファイル

- `sonic-swss/orchagent/qosorch.cpp` (TcToQueueMapHandler)
- `sonic-swss/orchagent/qosorch.h`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-tc-queue-map.yang`
- `sonic-buildimage/files/build_templates/qos_config.j2`

## フィールド一覧と暗黙デフォルト

### `qindex` フィールド

- **YANG デフォルト**: なし（`default` 文なし）。必須宣言もなく省略可能だが、省略時の fallback はコード側で未定義。
- **コード挙動**: `TcToQueueMapHandler::convertFieldValuesToAttributes()` は `stoi(fvValue(*i))` で変換。`qindex` が空文字列または非数値の場合、`stoi()` が `std::invalid_argument` または `std::out_of_range` 例外を投げる → `task_invalid_entry` が返され、**エントリ全体が silent drop** される。
- **YANG-実装 discrepancy**: YANG では pattern `[0-9]?` で 0〜9 の 1 桁のみ許可しているが、コード側では単に `stoi()` で整数変換するだけで上限チェックなし。SAI 側での拒否に委ねられる。

### `tc` フィールド（key）

- **YANG 型**: `stypes:tc_type`（0..7）。
- **コード**: `stoi(fvField(*i))` で uint8_t にキャスト。例外なし処理なし（try-catch なし）。無効値は `stoi()` 例外 → `task_invalid_entry`。

## ビルド時デフォルト（プラットフォーム依存）

`qos_config.j2` の `TC_TO_QUEUE_MAP` セクション（L227-238）：

```jinja
{% if (generate_tc_to_queue_map is defined) and tunnel_qos_remap_enable %}
    {{- generate_tc_to_queue_map() }}
{% elif (generate_tc_to_queue_map_per_sku is defined) %}
    {{ generate_tc_to_queue_map_per_sku() }}
{% else %}
    "TC_TO_QUEUE_MAP": {
        "AZURE": {
            "0": "0", "1": "1", "2": "2", "3": "3",
            "4": "4", "5": "5", "6": "6", "7": "7"
        }
    }
{% endif %}
```

**経路依存乖離**:
1. `generate_tc_to_queue_map` 関数定義あり **かつ** `tunnel_qos_remap_enable=true` → プラットフォーム固有関数が生成（例: AZURE_UPLINK マップ追加）
2. `generate_tc_to_queue_map_per_sku` 定義あり → SKU 別マップ
3. **フォールバック（デフォルト）**: TC 0-7 → queue 0-7 の恒等写像（`AZURE` マップ名）

## PORT_QOS_MAP 参照時の分岐

`qos_config.j2` L450-455:

```jinja
{% if different_tc_to_queue_map and tunnel_qos_remap_enable and port in port_names_list_extra_queues %}
    "tc_to_queue_map": "AZURE_UPLINK",
{% else %}
    "tc_to_queue_map": "AZURE",
{% endif %}
```

- uplink ポート + DualToR + tunnel_qos_remap_enable 有効時のみ `AZURE_UPLINK` マップが適用
- それ以外は `AZURE`（デフォルト恒等写像）

## ハードコード / SAI MAP TYPE

`TcToQueueMapHandler::addQosItem()` にて SAI map type が **ハードコード**:

```cpp
qos_map_attr.value.s32 = SAI_QOS_MAP_TYPE_TC_TO_QUEUE;
```

CONFIG_DB のテーブル名から動的決定ではなく、ハンドラクラスに静的に埋め込まれている。

## dead consumer / 書込み順依存

- dead consumer なし。QosOrch は常時 `TC_TO_QUEUE_MAP` を購読。
- **書込み順依存**: `TC_TO_QUEUE_MAP` を作成する前に `PORT_QOS_MAP` で参照した場合、`PORT_QOS_MAP` 処理が `task_need_retry` となり参照解決まで待機する（swss Consumer の retry キューで実現）。
- **DEL 保留**: `PORT_QOS_MAP` 参照中は DEL が `m_pendingRemove=true` でキューイングされる。参照解放まで SAI remove は呼ばれない。

## 発見サマリ

| 分類 | 詳細 |
|------|------|
| YANG デフォルトなし | `qindex` に YANG `default` 文なし。省略時の fallback なし |
| silent drop | `qindex` が非数値/空の場合 `stoi()` 例外 → entry 全体破棄。ログなし |
| YANG-実装乖離 | YANG は 1 桁 (0-9) のみ許可だが実装は上限チェックなし（SAI 委任） |
| ハードコード | SAI map type `SAI_QOS_MAP_TYPE_TC_TO_QUEUE` がクラス内にハードコード |
| ビルド時デフォルト | `qos_config.j2` fallback: TC 0-7 → queue 0-7 の恒等写像 (`AZURE` マップ) |
| 経路依存乖離 | `tunnel_qos_remap_enable` フラグで別マップ関数を呼ぶ分岐あり |
| 書込み順依存 | PORT_QOS_MAP 参照前に TC_TO_QUEUE_MAP が必要。逆順は retry |
