# dot1p-to-pg-map platform 調査証跡

## 調査対象

`DOT1P_TO_PG_MAP` テーブルは SONiC に存在しないが、等価な 2 段マッピング経路
(`DOT1P_TO_TC_MAP` → `TC_TO_PRIORITY_GROUP_MAP` → `PORT_QOS_MAP`) を処理する
`QosOrch` のコードパスにプラットフォーム依存分岐が存在するかを調査した。

## 調査手順

### 1. gMySwitchType 分岐のスキャン

```bash
grep -n "gMySwitchType\|voq\|dpu\|smart" sonic-swss/orchagent/qosorch.cpp
```

結果:
- L32: `extern string gMySwitchType;` — 外部変数宣言のみ
- L1637: `if (gMySwitchType == "voq")` — `applySchedulerToQueueSchedulerGroup()` 内
- L1715: `if (gMySwitchType == "voq")` — `applyWredProfileToQueue()` 内
- L1772: `if (gMySwitchType == "voq")` — `handleQueueTable()` 内

### 2. Dot1pToTcMapHandler のコードパス確認

`Dot1pToTcMapHandler::convertFieldValuesToAttributes()` (L360-397) および
`Dot1pToTcMapHandler::addQosItem()` (L399-420) の双方に `gMySwitchType` 参照なし。

`TcToPgHandler::addQosItem()` (L905-930) も同様に platform 分岐なし。

### 3. handlePortQosMapTable の確認

`QosOrch::handlePortQosMapTable()` (L2046-2156) に `gMySwitchType` 参照なし。
`dot1p_to_tc_map` および `tc_to_pg_map` フィールドの処理は全 switch_type で同一経路。

### 4. qos_config.j2 のプラットフォーム依存初期設定

`sonic-buildimage/files/build_templates/qos_config.j2` L240-252:

```jinja2
{% if 'type' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['type'] in backend_device_types and 'storage_device' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['storage_device'] == 'true' %}
    "DOT1P_TO_TC_MAP": {
        "AZURE": {
            "0": "1",
            "1": "0",
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "5",
            "6": "6",
            "7": "7"
        }
    },
```

同ファイル L435:

```jinja2
{% if ... backend_device_types ... storage_device == 'true' %}
    "dot1p_to_tc_map" : "AZURE",
```

ストレージバックエンドプラットフォーム（`backend_device_types` かつ `storage_device=true`）でのみ
`DOT1P_TO_TC_MAP|AZURE` エントリと `PORT_QOS_MAP.<port>.dot1p_to_tc_map=AZURE` が自動注入される。

## 結論

- `Dot1pToTcMapHandler` / `TcToPgHandler` の `addQosItem()` / `convertFieldValuesToAttributes()` は
  すべての switch_type（standard / voq / dpu）で同一 SAI 経路（`sai_qos_map_api->create_qos_map()`）を実行する。
- `gMySwitchType == "voq"` 分岐は `handleQueueTable` / `applySchedulerToQueueSchedulerGroup` /
  `applyWredProfileToQueue` にのみ存在し、dot1p 関連ハンドラには存在しない。
- プラットフォーム差異は orchagent の実行時コードパスではなく、
  **初期設定注入（`qos_config.j2`）** レベルにのみ存在する。

## Evidence

- `sonic-swss/orchagent/qosorch.cpp:360-427` (Dot1pToTcMapHandler, no platform branch)
- `sonic-swss/orchagent/qosorch.cpp:880-934` (TcToPgHandler, no platform branch)
- `sonic-swss/orchagent/qosorch.cpp:2046-2156` (handlePortQosMapTable, no platform branch)
- `sonic-swss/orchagent/qosorch.cpp:1637,1715,1772` (voq branch only in Queue/Wred/Scheduler)
- `sonic-buildimage/files/build_templates/qos_config.j2:240-252,435` (storage backend only injection)
