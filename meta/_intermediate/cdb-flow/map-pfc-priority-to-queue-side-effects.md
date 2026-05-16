# MAP_PFC_PRIORITY_TO_QUEUE — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-16 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/map-pfc-priority-to-queue.md` 配下の CONFIG_DB `MAP_PFC_PRIORITY_TO_QUEUE` テーブル変更時に、`QosOrch` (`PfcToQueueHandler`) が ASIC_DB / APPL_DB / STATE_DB / COUNTERS_DB / APPL_STATE_DB へ何らかの書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/qosorch.cpp` (主購読者: `QosOrch` / `PfcToQueueHandler`)
- `PfcToQueueHandler::addQosItem()` (L1011–L1035)
- `QosOrch::handlePortQosMapTable()` (L2113–L2228、ポートへの副次適用)

## 走査コマンドと結果

### 1. `PfcToQueueHandler` での DB 書込検索

```bash
grep -n "ASIC_DB|APPL_DB|STATE_DB|COUNTERS_DB|ProducerStateTable|set(|hset|publish" qosorch.cpp
```

結果:
- **ASIC_DB**: `sai_qos_map_api->create_qos_map()` (L1029) を通じて syncd 経由で ASIC_DB に SAI qos_map オブジェクト (`SAI_OBJECT_TYPE_QOS_MAP`) が書き込まれる。直接 DB API 呼出はなく、すべて SAI API 経由で syncd が仲介する。
- **APPL_DB**: 書込なし
- **STATE_DB**: 書込なし
- **COUNTERS_DB**: 書込なし
- **APPL_STATE_DB**: 書込なし

### 2. PORT_QOS_MAP 経由のポート副次反映

`PORT_QOS_MAP.pfc_to_queue_map` にマップ名が設定されたとき、`QosOrch::handlePortQosMapTable()` が `sai_port_api->set_port_attribute(port.m_port_id, SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP, oid)` を呼び出す (L2193)。これにより:

- **ASIC_DB**: syncd 経由でポートオブジェクト (`SAI_OBJECT_TYPE_PORT`) の属性 `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP` が更新される。
- 他の副次 DB: なし

### 3. APPL_STATE_DB / STATE_DB の確認

```bash
grep -n "APPL_STATE_DB|appl_state_db|AppStateTable|STATE_DB" qosorch.cpp
```

結果: **マッチ 0 件**。`qosorch.cpp` には STATE_DB / APPL_STATE_DB への直接参照は存在しない。

## 結論

CONFIG_DB `MAP_PFC_PRIORITY_TO_QUEUE` テーブルの変更に伴う副次 DB 書込は以下の通り:

| 副次 DB | 書込有無 | 内容 |
|---|---|---|
| ASIC_DB (syncd 経由) | **あり** | SAI `SAI_OBJECT_TYPE_QOS_MAP` オブジェクト作成 (`create_qos_map`) |
| ASIC_DB (syncd 経由、間接) | **あり (PORT_QOS_MAP から参照時)** | ポートの `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP` 属性更新 |
| APPL_DB | なし | — |
| STATE_DB | なし | — |
| COUNTERS_DB | なし | — |
| APPL_STATE_DB | なし | — |

## 根拠サマリ

| 検証項目 | ファイル/行 | 結果 |
|---|---|---|
| `PfcToQueueHandler::addQosItem()` SAI 呼出 | `qosorch.cpp:1029` | `sai_qos_map_api->create_qos_map()` → ASIC_DB (syncd 経由) |
| `handlePortQosMapTable()` ポート属性設定 | `qosorch.cpp:2193` | `sai_port_api->set_port_attribute(SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP)` → ASIC_DB |
| APPL_STATE_DB / STATE_DB 参照 | `qosorch.cpp` 全体 | 0 件 |
| 直接 DB API 書込 (ProducerStateTable 等) | `qosorch.cpp` 全体 | 0 件 |
