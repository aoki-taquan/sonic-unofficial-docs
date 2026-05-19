# DSCP_TO_PG_MAP — Phase H プラットフォーム差スキャンノート

対象テーブル: `DSCP_TO_PG_MAP`（非実在）— 2 段マッピング代替 (`DSCP_TO_TC_MAP` / `TC_TO_PRIORITY_GROUP_MAP` / `PORT_QOS_MAP`)
Consumer: `QosOrch` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: qosorch.cpp L32, L1637, L1715, L1772, L1950-2040; qos_config.j2 L163, L170-205, L265-360, L395-480

---

## 1. QosOrch コード内のプラットフォーム分岐

### DSCP_TO_TC_MAP / TC_TO_PRIORITY_GROUP_MAP ハンドラ本体

`DscpToTcMapHandler::convertFieldValuesToAttributes()` (L235-253) と `TcToPgHandler::convertFieldValuesToAttributes()` (L884-910) は `gMySwitchType` / `platform` / ASIC ベンダー参照を**一切含まない**。
全 switch_type 共通でマップ SAI オブジェクトを作成する。

### switch_type による分岐（スケジューラ・キュー系のみ）

`gMySwitchType == "voq"` の条件分岐は以下の 3 箇所のみ:
- `applySchedulerToQueueSchedulerGroup()` (L1637): VOQ システムポートの場合は local port に変換してからキューを取得
- `applyWredProfileToQueue()` (L1715): VOQ の場合は `getPortVoQIds()` を使用
- `handleQueueTable()` (L1772): VOQ の場合はキー形式が 4 トークン

これらはすべて `QUEUE` / `WRED_PROFILE` / `SCHEDULER` ハンドラであり、`DSCP_TO_TC_MAP` および `TC_TO_PRIORITY_GROUP_MAP` の処理経路には影響しない。

### switch_type="fabric" (FabricOrchDaemon)

`FabricOrchDaemon` (`orchdaemon.cpp:1060+`) は `QosOrch` を初期化しない。ファブリックスイッチでは `DSCP_TO_TC_MAP` / `TC_TO_PRIORITY_GROUP_MAP` の CONFIG_DB 購読自体が行われない。

### SAI switch-level DSCP_TO_TC map — capability gate

`applyDscpToTcMapToSwitch()` (L1950-1975) は SAI capability クエリで事前確認する:

```cpp
bool rv = gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP);
if (rv == false) {
    SWSS_LOG_ERROR("Switch level DSCP to TC QoS map configuration is not supported");
    return true;  // 失敗ではなく「サポートなし」として上位に返す
}
```

`SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` をスイッチレベルで設定できる ASIC（例: 一部の Broadcom プラットフォーム）のみ `PORT_QOS_MAP|global` が有効に機能する。非対応 ASIC では `applyDscpToTcMapToSwitch()` がエラーログを出力してスキップし、`PORT_QOS_MAP|global` の設定は実質 no-op となる。

---

## 2. qos_config.j2 — テンプレート初期値のプラットフォーム差

### TC_TO_PRIORITY_GROUP_MAP — DPU ポート (PORT_DPC)

```jinja
{% if PORT_DPC %}
    "AZURE_DPC": {
        "0": "0",  "1": "0",  "2": "0",  "3": "0",
        "4": "0",  "5": "0",  "6": "0",  "7": "7"
    },
{% endif %}
```

`PORT_DPC`（DPU接続ポート）が存在する構成では `TC_TO_PRIORITY_GROUP_MAP|AZURE_DPC` が追加される。TC 0-6 がすべて PG 0、TC 7 のみ PG 7 に割り当てられる。通常の `AZURE` マップ（TC 3→PG3, TC 4→PG4 が lossless）とは異なる。

### TC_TO_PRIORITY_GROUP_MAP — SKU カスタムマクロ

`generate_tc_to_pg_map` マクロが定義されている構成（tunnel_qos_remap_enable または BackEndToRRouter/BackEndLeafRouter で resource_type=ComputeAI）では `generate_tc_to_pg_map()` が呼ばれ、AZURE デフォルトの代わりにプラットフォーム固有の TC→PG マッピングが生成される。`generate_tc_to_pg_map_per_sku` が定義されている場合も同様。

### DSCP_TO_TC_MAP — BackEndToRRouter storage_device=true

```jinja
{# storage_device=true の Backend デバイスでは DSCP_TO_TC_MAP を使わず DOT1P_TO_TC_MAP を使う #}
{% if DEVICE_METADATA['localhost']['type'] in backend_device_types and
      DEVICE_METADATA['localhost']['storage_device'] == 'true' %}
    "DOT1P_TO_TC_MAP": { "AZURE": {...} }
    {%- set require_global_dscp_to_tc_map = false %}
```

ストレージバックエンドデバイスでは `DSCP_TO_TC_MAP` の初期投入が行われず、`DOT1P_TO_TC_MAP` が代わりに使われる。`PORT_QOS_MAP` フィールドも `dot1p_to_tc_map` に切り替わる。

### PORT_QOS_MAP の tc_to_pg_map フィールド — DPU ポート

```jinja
{% if port not in PORT_DPC %}
    "tc_to_pg_map": "AZURE"
{% else %}
    "tc_to_pg_map": "AZURE_DPC"
{% endif %}
```

DPU 接続ポートは `tc_to_pg_map=AZURE_DPC` が設定される。

### PFC_TO_PG_MAP — mellanox / barefoot のみ

```jinja
{%- set pfc_to_pg_map_supported_asics = ['mellanox', 'barefoot'] -%}
{% if asic_type in pfc_to_pg_map_supported_asics %}
    "PFC_PRIORITY_TO_PRIORITY_GROUP_MAP": { "AZURE": {...} }
{% endif %}
```

`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` テーブルおよび `PORT_QOS_MAP.pfc_to_pg_map` フィールドは mellanox / barefoot ASIC 専用。その他の ASIC ではこのフィールドは設定されない。

---

## 3. サマリ

| 側面 | プラットフォーム差 | 備考 |
|------|----------------|------|
| `DSCP_TO_TC_MAP` / `TC_TO_PRIORITY_GROUP_MAP` ハンドラ本体 | **なし** | gMySwitchType 参照なし |
| `PORT_QOS_MAP|global` switch-level | **あり** (`SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` capability) | 非対応 ASIC では no-op |
| `TC_TO_PRIORITY_GROUP_MAP` の初期マップ内容 | **あり** (DPU: AZURE_DPC、カスタム: generate_tc_to_pg_map) | qos_config.j2 テンプレート |
| `DSCP_TO_TC_MAP` の初期投入有無 | **あり** (BackEnd storage_device=true: DOT1P_TO_TC_MAP に置換) | qos_config.j2 テンプレート |
| `PORT_QOS_MAP.tc_to_pg_map` フィールド値 | **あり** (DPU ポート: AZURE_DPC) | qos_config.j2 テンプレート |
| `switch_type="fabric"` | **あり** (QosOrch 未初期化) | FabricOrchDaemon は QosOrch を持たない |
