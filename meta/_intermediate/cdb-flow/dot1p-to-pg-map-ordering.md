# DOT1P_TO_PG_MAP — Phase B 書込み順依存スキャンノート

対象テーブル: `DOT1P_TO_PG_MAP`（非実在）/ 等価 2 段構成: `DOT1P_TO_TC_MAP` → `TC_TO_PRIORITY_GROUP_MAP` → `PORT_QOS_MAP`
Consumer: `QosOrch` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: `handlePortQosMapTable()`, `handleDot1pToTcTable()`, `handleTcToPgTable()`, `m_qos_maps` 初期化, `resolveFieldRefValue()` 全行精読

---

## DOT1P_TO_PG_MAP は存在しない

`qosorch.cpp:80-96` の `m_qos_maps` 初期化リストに `DOT1P_TO_PG_MAP` エントリはない。
dot1p → PG の経路は `DOT1P_TO_TC_MAP` + `TC_TO_PRIORITY_GROUP_MAP` + `PORT_QOS_MAP` の 3 テーブル構成。

## 検出した順序依存

### 1. `PORT_QOS_MAP` は参照マップが全て生成済みでないと `task_need_retry` を返す

- `handlePortQosMapTable()` (qosorch.cpp:2046) は各フィールドに対して `resolveFieldRefValue(m_qos_maps, map_type_name, ...)` を呼ぶ。
- `DOT1P_TO_TC_MAP` オブジェクトが `m_qos_maps` に登録される前に `PORT_QOS_MAP.dot1p_to_tc_map` を書くと `ref_resolve_status != success` → `task_need_retry` 返却。
- Consumer が自動再キューするため、後からマップを追加すれば自動適用される。
- evidence: `qosorch.cpp:2077-2083`, `qosorch.cpp:2122-2126`

### 2. `TC_TO_PRIORITY_GROUP_MAP` も同様の先行必須

- `PORT_QOS_MAP.tc_to_pg_map` の解決に `TC_TO_PRIORITY_GROUP_MAP` が必要。
- 未生成なら `task_need_retry`。
- evidence: `qosorch.cpp:2077-2083`

### 3. SAI 適用はフィールド全解決後に順次実行

- `update_list` に `<sai_port_attr_t, sai_object_id_t>` を積んでから `sai_port_api->set_port_attribute` を順次呼ぶ。
- `SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP` と `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` は独立した `set_port_attribute` 呼び出し。
- evidence: `qosorch.cpp:2132-2156`

### 4. `DOT1P_TO_TC_MAP` と `TC_TO_PRIORITY_GROUP_MAP` は相互に独立

- 両マップは `handleDot1pToTcTable()` と `handleTcToPgTable()` でそれぞれ独立処理。
- 先に作成する順序は自由。`PORT_QOS_MAP` が参照する時点で両方揃えばよい。
- evidence: `qosorch.cpp:1331-1342`

---

## 結論

`PORT_QOS_MAP` を `dot1p_to_tc_map` または `tc_to_pg_map` フィールドつきで書き込む場合、参照先マップが先に CONFIG_DB に存在していること。逆順でも Consumer の retry 機構で自動的に再試行されるが、中間状態で SAI に不完全な設定が当たる可能性はない（`task_need_retry` で全フィールド揃うまでマップ未適用）。
