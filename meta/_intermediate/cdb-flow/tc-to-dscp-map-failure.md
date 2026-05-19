# TC_TO_DSCP_MAP — Phase D 失敗挙動 中間ファイル

生成日: 2026-05-19 (Task F Phase D)

## 調査元

- `sonic-swss/orchagent/qosorch.cpp` (ref: 4305596)
- 既存ページ: `docs/reference/config-db/tc-to-dscp-map.md`（cdb-exceptions・value-behavior・defaults セクション）

## task_process_status 分類

`QosOrch` は 4 種類のタスクステータスを返す。TC_TO_DSCP_MAP に関連する失敗パスを整理する。

### task_invalid_entry（永久破棄）

以下の条件で `false` を返し呼び出し元が `task_invalid_entry` として扱う:

1. `dscp` が負値 — 明示的なエラーログ後 `false` 返却 (qosorch.cpp:1219-1223)
2. `dscp` が `DSCP_MAX_VAL=63` 超 — 上限チェックで明示エラーログ後 `false` 返却 (qosorch.cpp:1225-1229)
3. `dscp` が非数値文字列 — `stoi()` / `stoul()` による `invalid_argument` 例外を try-catch → `false` 返却 (qosorch.cpp:1216-1260)
4. `tc` (key) が非数値 — key 解析失敗 → `task_invalid_entry`

### task_need_retry（自動リトライ）

1. SET 時：`PORT_QOS_MAP.tc_to_dscp_map` が本マップを参照しているが SAI OID 未解決（マップ未存在）→ `resolveFieldRefValue` が失敗 → `task_need_retry`
2. DEL 時：`PORT_QOS_MAP` または `TUNNEL` から参照中 → `isObjectBeingReferenced()` が `true` → `m_pendingRemove=true` → `task_need_retry` (qosorch.cpp:181-186)

### task_failed（キューから除去、再試行なし）

1. `sai_qos_map_api->create_qos_map()` が SAI エラーを返した場合 (qosorch.cpp:162-166)
2. `sai_qos_map_api->set_qos_map_attribute()` 失敗（更新時）
3. `sai_qos_map_api->remove_qos_map()` 失敗（DEL 時、参照解除後）

### STATE_DB / ERROR_TABLE フィードバック

`QosOrch` は失敗を `SWSS_LOG_ERROR` で syslog に記録するのみ。STATE_DB や ERROR_TABLE への書き込みは行わない。

## 結論テーブル

| 失敗種別 | 条件 | ステータス | 再試行 |
|---------|------|-----------|--------|
| `dscp` 負値 | dscp < 0 | task_invalid_entry | なし（破棄） |
| `dscp` 範囲超過 | dscp > 63 | task_invalid_entry | なし（破棄） |
| `dscp` 非数値 | 文字列解析失敗 | task_invalid_entry | なし（破棄） |
| SAI map 作成失敗 | SAI API エラー | task_failed | なし（破棄） |
| DEL 中に参照残留 | PORT_QOS_MAP/TUNNEL 参照中 | task_need_retry | 自動リトライ |
