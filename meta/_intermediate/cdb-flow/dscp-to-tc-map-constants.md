# DSCP_TO_TC_MAP — Phase E ハードコード定数

ソース: `sonic-swss/orchagent/qosorch.cpp`、`sonic-swss/orchagent/qosorch.h`

## 抽出定数一覧

| 定数名 | 値 | 定義箇所 | 説明 |
|--------|----|---------|------|
| `DSCP_MAX_VAL` | `63` | `qosorch.cpp:119` | DSCP 値の最大値。超過時は `task_failed` |
| `dscp_to_tc_field_name` | `"dscp_to_tc_map"` | `qosorch.h:11` | PORT_QOS_MAP フィールド名 |
| `decap_dscp_to_tc_field_name` | `"decap_dscp_to_tc_map"` | `qosorch.h:34` | Tunnel decap 用フィールド名 |
| `SAI_QOS_MAP_TYPE_DSCP_TO_TC` | SAI 定数 | `qosorch.cpp:265` | SAI qos_map_type — DSCP→TC マップ種別 |
| `SAI_QOS_MAP_ATTR_TYPE` | SAI 定数 | `qosorch.cpp:264` | SAI create 時の type 属性 ID |
| `SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` | SAI 定数 | `qosorch.cpp:249,268` | SAI マップエントリリスト属性 ID |
| `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` | SAI 定数 | `qosorch.cpp:61` | ポートへのバインド属性 ID |
| `SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` | SAI 定数 | `qosorch.cpp:1993,2030` | スイッチレベルバインド属性 ID |
| `CFG_DSCP_TO_TC_MAP_TABLE_NAME` | `"DSCP_TO_TC_MAP"` | swsscommon (swsscommon.CFG_DSCP_TO_TC_MAP_TABLE_NAME) | CONFIG_DB テーブル名定数 |

## DSCP/TC 範囲

| パラメータ | 範囲 | 根拠 |
|-----------|------|------|
| DSCP key | 0 .. 63 | `DSCP_MAX_VAL = 63` (`qosorch.cpp:119`); 超過は `task_failed` |
| TC value | 0 .. 7 (実運用) / 0 .. 15 (YANG) | YANG `tc_type = uint8 range "0..15"` だが ASIC は 0..7 のみ受け付ける |

## デフォルトマップ名

| マップ名 | 用途 | 出典 |
|---------|------|------|
| `"AZURE"` | 標準 DSCP→TC マップ (`qos_config.j2` フォールバック) | `test_qos_map.py:7,326` |
| `"AZURE_TUNNEL"` | Tunnel QoS 用 (decap_dscp_to_tc_map) | `test_mux.py:40` |

## 型変換・例外処理

- `qosorch.cpp:245`: `(uint8_t)stoi(fvField(*i))` — 非数値文字列で `std::invalid_argument` → `task_failed`（try/catch なし）
- `qosorch.cpp:246`: `(uint8_t)stoi(fvValue(*i))` — TC 値も同様

## SAI API 呼び出し

| 操作 | SAI 関数 | 箇所 |
|------|---------|------|
| マップ作成 | `sai_qos_map_api->create_qos_map()` | `qosorch.cpp:273` |
| マップ更新 | `sai_qos_map_api->set_qos_map_attribute()` | `qosorch.cpp:207` |
| マップ削除 | `sai_qos_map_api->remove_qos_map()` | `qosorch.cpp:220,289` |
| スイッチ能力確認 | `querySwitchCapability(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` | `qosorch.cpp:1956` |
