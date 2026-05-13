# port-qos-map 例外条件エビデンス

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port-qos-map.yang`
- `sonic-swss/orchagent/qosorch.cpp`

## 例外条件まとめ

### スキーマ検証 (YANG)
- sonic-port-qos-map.yang に `must` / `mandatory` 制約なし。各フィールドは optional。
- 各 `*_map` フィールドは leafref だが YANG ファイル上では string のみで参照チェックなし (orch 側でランタイム検証)。

### consumer (qosorch) 例外動作
- 参照先 QoS map が存在しない: `Object with name:%s not found.` → SWSS_LOG_ERROR、設定適用中断 (qosorch.cpp:178)
- SAI `sai_qos_map_api` SET 失敗: `Failed to set [%s:%s]` → SWSS_LOG_ERROR (qosorch.cpp:153)
- SAI `sai_qos_map_api` CREATE 失敗: `Failed to create [%s:%s]` → SWSS_LOG_ERROR (qosorch.cpp:164)
- 不明な operation type: `Unknown operation type %s` → SWSS_LOG_ERROR (qosorch.cpp:198)
- ハンドラ未初期化: `Task %s handler is not initialized` → SWSS_LOG_ERROR (qosorch.cpp:2270)
- 先に PORT_QOS_MAP を DEL してから参照 QoS map を DEL しないと SAI 参照カウントで失敗する (順序依存)。
