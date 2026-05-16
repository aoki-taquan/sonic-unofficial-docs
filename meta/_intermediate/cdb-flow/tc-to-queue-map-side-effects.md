# tc-to-queue-map — Phase F 副次 DB 書込調査

**対象テーブル**: `TC_TO_QUEUE_MAP`
**ソース**: `sonic-swss/orchagent/qosorch.cpp`
**調査日**: 2026-05-16

---

## 1. ASIC_DB への書込

`TcToQueueMapHandler::addQosItem()` (qosorch.cpp L449-473) が
`sai_qos_map_api->create_qos_map()` を呼び出す。

syncd はこの SAI 呼び出しを受けて `ASIC_DB` の `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP:<oid>` を
自動生成する（orchagent → syncd → ASIC_DB 経路）。

```
ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP:<oid>
  SAI_QOS_MAP_ATTR_TYPE             = SAI_QOS_MAP_TYPE_TC_TO_QUEUE
  SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST = [(tc=0,queue=0), (tc=1,queue=1), ...]
```

既存マップ更新時は `QosMapHandler::modifyQosItem()` (qosorch.cpp L204-213) が
`sai_qos_map_api->set_qos_map_attribute()` を呼び出し、ASIC_DB の同エントリを更新する。

DEL 時は `QosMapHandler::removeQosItem()` (qosorch.cpp L216-230) が
`sai_qos_map_api->remove_qos_map()` を呼び出し、ASIC_DB から当該エントリを削除する。

---

## 2. APPL_STATE_DB への書込

**書込なし。**

QosOrch は `TC_TO_QUEUE_MAP` 処理において APPL_STATE_DB または APPL_DB への
書き込みを一切行わない。CONFIG_DB → SAI (ASIC_DB) の直接経路のみ。

---

## 3. PORT への副次反映（SAI port 属性書込）

`PORT_QOS_MAP` テーブルで `tc_to_queue_map=<name>` が設定されると、
`QosOrch::handlePortQosMapTable()` (qosorch.cpp L2115-2204) が実行される。

```
qos_to_attr_map["tc_to_queue_map"] = SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP
```
(qosorch.cpp L64)

`PORT_QOS_MAP` で参照されたポート全てに対して以下を呼び出す:

```cpp
sai_attribute_t attr;
attr.id = SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP;
attr.value.oid = <TC_TO_QUEUE_MAP の SAI OID>;
sai_port_api->set_port_attribute(port.m_port_id, &attr);  // qosorch.cpp L2193
```

これにより `ASIC_DB` の `ASIC_STATE:SAI_OBJECT_TYPE_PORT:<port_oid>` に
`SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` 属性が書き込まれる（syncd 経由）。

### encap 経路（Tunnel QoS Remap）

`encap_tc_to_queue_map` フィールドも同テーブル (`TC_TO_QUEUE_MAP`) を参照する
(qosorch.cpp L116)。Tunnel QoS remap 有効時は Tunnel encap 経路でも同 map OID が
port / tunnel SAI 属性として設定される。

---

## 4. 副次反映サマリ

| 副次書込先 | 書込タイミング | SAI 属性 / キー | 備考 |
|-----------|--------------|----------------|------|
| `ASIC_DB` `SAI_OBJECT_TYPE_QOS_MAP` | `TC_TO_QUEUE_MAP` SET 時 | `SAI_QOS_MAP_ATTR_TYPE`, `SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` | syncd 経由 |
| `ASIC_DB` `SAI_OBJECT_TYPE_PORT` | `PORT_QOS_MAP.tc_to_queue_map` 設定時 | `SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` | 参照ポート全台 |
| APPL_STATE_DB | — | なし | 書込経路なし |
| APPL_DB | — | なし | 書込経路なし |

---

## 5. evidence

- `sonic-swss/orchagent/qosorch.cpp` L64, L103, L116, L204-230, L449-473, L2115-2204
