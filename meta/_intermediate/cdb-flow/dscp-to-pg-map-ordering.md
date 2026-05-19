# dscp-to-pg-map — ordering 調査メモ

## 対象ページ
`docs/reference/config-db/dscp-to-pg-map.md`

## 結論
`DSCP_TO_PG_MAP` テーブル自体は存在しない。DSCP→PG マッピングは DSCP_TO_TC_MAP → TC_TO_PRIORITY_GROUP_MAP の 2 段構成で実現される。
PORT_QOS_MAP がこれら 2 テーブルを参照するため、PORT_QOS_MAP 書き込みには両テーブルが先行している必要がある。

## ソース

### qosorch.cpp — PORT_QOS_MAP の参照解決
- `qosorch.cpp:2124`: `resolveFieldRefValue` で `dscp_to_tc_field_name` の OID を解決。未解決なら `task_need_retry`
- `qosorch.cpp:2129`: `task_need_retry` を返す → orchtask は自動リトライ
- `qosorch.cpp:2021`: グローバル (PORT_NAME_GLOBAL) でも同様の解決処理
- `qosorch.cpp:2026`: グローバルでも `task_need_retry`

### qosorch.cpp — map テーブル自体の書き込み順序
- `qosorch.cpp:80-96`: `m_qos_maps` 初期化リストに DSCP_TO_TC_MAP, TC_TO_PRIORITY_GROUP_MAP, PORT_QOS_MAP が登録される
- DSCP_TO_TC_MAP, TC_TO_PRIORITY_GROUP_MAP は独立した SET 処理で PORT 依存なしに SAI オブジェクトを作成可能
- PORT_QOS_MAP は PORT が PortInitDone 済みであること + 参照 QoS マップが SAI 登録済みであることの両方を要求

### qosorch.cpp — PORT 依存
- `qosorch.cpp:2180`: `gPortsOrch->getPort(port_name, port)` でポート存在確認。未存在時はスキップ（エラーログのみ、リトライなし）

## 書込み順の結論

```
DSCP_TO_TC_MAP エントリ作成 ←─┐
TC_TO_PRIORITY_GROUP_MAP エントリ作成 ←─┤ 先行必須
PORT (PortInitDone 済み) ←─────────────┘
  ↓
PORT_QOS_MAP エントリ書き込み → QosOrch が OID 解決 → SAI 適用
```

参照マップが未存在の場合は `task_need_retry` で自動リトライされるため、
順序違反があっても最終的には適用されるが、起動時のタイムアウトリスクがある。
