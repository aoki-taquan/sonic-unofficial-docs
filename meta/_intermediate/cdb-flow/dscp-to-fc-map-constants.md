# DSCP_TO_FC_MAP — Phase E ハードコード定数スキャンノート

対象ページ: `docs/reference/config-db/dscp-to-fc-map.md`
対象テーブル: `DSCP_TO_FC_MAP`
Consumer: `QosOrch::handleDscpToFcTable()` / `DscpToFcMapHandler` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: `qosorch.cpp` 全行精読、`cbf/nhgmaporch.cpp:299-325`、`tests/test_qos_map.py:300-374`

---

## 検出したハードコード定数

### 1. DSCP 値上限 — `DSCP_MAX_VAL = 63`

- `qosorch.cpp:119`: `#define DSCP_MAX_VAL 63`
- `DscpToFcMapHandler::convertFieldValuesToAttributes()` L1062: `value > DSCP_MAX_VAL` で reject
- YANG 定義 (`sonic-dscp-fc-map.yang`) の `type uint8 { range "0..63"; }` と一致。
- YANG と実装の両側で上限 63 は固定。

### 2. `max_num_fcs` — SAI capability 照会・静的キャッシュ

- `cbf/nhgmaporch.cpp:299-325`: `NhgMapOrch::getMaxNumFcs()`
  - `static int max_num_fcs = -1;` で初回のみ SAI クエリ
  - SAI 属性: `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES`
  - 成功時: `attr.value.u8` を返す（`uint8_t`、最大 255）
  - 失敗時: `SWSS_LOG_WARN("Switch does not support FCs")` + `max_num_fcs = 0`
- テスト値: `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES = 63`（`test_qos_map.py:314`）→ FC 0..62 が有効
- フォールバック値 `0` は YANG / CONFIG_DB には現れない純粋なランタイム定数。

### 3. SAI map タイプ定数 — `SAI_QOS_MAP_TYPE_DSCP_TO_FORWARDING_CLASS`

- `qosorch.cpp:1104`: `qos_map_attr.value.u32 = SAI_QOS_MAP_TYPE_DSCP_TO_FORWARDING_CLASS`
- `DscpToFcMapHandler::addQosItem()` が `sai_qos_map_api->create_qos_map()` に渡す SAI enum 値。
- CONFIG_DB / YANG には露出しないが、`DSCP_TO_FC_MAP` テーブルを SAI QoS map として登録する際に固定で使用される。

### 4. ポート属性定数 — `SAI_PORT_ATTR_QOS_DSCP_TO_FORWARDING_CLASS_MAP`

- `qosorch.cpp:71`: `{dscp_to_fc_field_name, SAI_PORT_ATTR_QOS_DSCP_TO_FORWARDING_CLASS_MAP}`
- `PORT_QOS_MAP.dscp_to_fc_map` フィールドを介してポートバインド時に使用。
- `handlePortQosMapTable()` が `sai_port_api->set_port_attribute()` に渡す SAI enum 値。

### 5. フィールド名文字列 — `dscp_to_fc_field_name`

- `qosorch.h` 経由で `"dscp_to_fc_map"` と定義（`PORT_QOS_MAP` フィールド名と対応）。
- CONFIG_DB の YANG スキーマにも `dscp_to_fc_map` として明示されており、YANG と実装の間に差異はない。

---

## 定数サマリ

| 定数名 | 値 | 管理場所 | YANG 一致 |
|--------|-----|----------|-----------|
| `DSCP_MAX_VAL` | `63` | `qosorch.cpp:119` (#define) | ✅ (`range "0..63"`) |
| `max_num_fcs` フォールバック | `0` (FC 非対応 ASIC) | `nhgmaporch.cpp:320` (runtime) | なし（runtime のみ） |
| `max_num_fcs` テスト値 | `63` | `test_qos_map.py:314` (テスト mock) | なし（テスト固定値） |
| `SAI_QOS_MAP_TYPE_DSCP_TO_FORWARDING_CLASS` | SAI enum | `qosorch.cpp:1104` | なし（SAI 内部） |
| `SAI_PORT_ATTR_QOS_DSCP_TO_FORWARDING_CLASS_MAP` | SAI enum | `qosorch.cpp:71` | なし（SAI 内部） |

---

## ページ反映方針

- `<!-- constants -->` ブロックを `<!-- /failure -->` と `<!-- defaults -->` の間に挿入する。
- `DSCP_MAX_VAL = 63` と `max_num_fcs` の 2 定数を主軸とする表形式で記述。
- SAI enum 定数（`SAI_QOS_MAP_TYPE_*`、`SAI_PORT_ATTR_*`）はユーザが直接触れないため補足として記載。
