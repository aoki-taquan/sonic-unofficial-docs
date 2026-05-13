# pfc-priority-to-priority-group-map 例外条件エビデンス

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pfc-priority-priority-group-map.yang`
- `sonic-swss/orchagent/qosorch.cpp`

## 例外条件まとめ

### スキーマ検証 (YANG)
- `pfc_priority` は pattern `[0-7]?`。空文字も YANG 上は許容するが、orch は数値として処理するため実質 0..7 必須。
- `pg_index` は同様の pattern。

### consumer (qosorch) 例外動作
- SAI `sai_qos_map_api` create 失敗: `Failed to create pfc_priority_to_queue map. status:%d` → SWSS_LOG_ERROR (qosorch.cpp:977,1032 で類似パターン)
- QoS map object が存在しない名前で PORT_QOS_MAP から参照された場合: `Object with name:%s not found.` → SWSS_LOG_ERROR + 処理中断 (qosorch.cpp:178)
- DEL 時 SAI remove 失敗: `Failed to remove map, status:%d` → `return false` で再試行 (qosorch.cpp:223)
- `PORT_QOS_MAP` からの参照が解除される前にマップ DEL は、SAI 参照カウントで失敗する可能性がある。
