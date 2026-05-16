# DOT1P_TO_TC_MAP — Phase B 書込み順依存スキャンノート

対象テーブル: `DOT1P_TO_TC_MAP`
Consumer: `QosOrch::handleDot1pToTcTable()` / `QosOrch::handlePortQosMapTable()` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: `QosMapHandler::processWorkItem()` (L124-201)、`handlePortQosMapTable()` (L2046-2235)、`handleDot1pToTcTable()` (L422-427)、`Dot1pToTcMapHandler::convertFieldValuesToAttributes()` (L360-398)

---

## 検出した順序依存・タイミング依存

### 1. DOT1P_TO_TC_MAP 先行登録 → PORT_QOS_MAP 参照（強制先行）

- `handlePortQosMapTable()` (qosorch.cpp:2120-2130) は `resolveFieldRefValue()` で `PORT_QOS_MAP.dot1p_to_tc_map` が参照するマップ名を `m_qos_maps[CFG_DOT1P_TO_TC_MAP_TABLE_NAME]` 内で照合する。
- 参照先 `DOT1P_TO_TC_MAP|<name>` が orchagent 内部マップ未登録の場合、`status != ref_resolve_status::success` → `"Port QoS map %s is not yet created"` LOG_INFO → `task_need_retry` を返し Consumer キューへ再投入される。
- **順序依存**: `PORT_QOS_MAP|<port>` に `dot1p_to_tc_map = <name>` を設定する前に `DOT1P_TO_TC_MAP|<name>` が CONFIG_DB に書き込まれ orchagent に処理済みであること。
- 未登録でも `task_need_retry` により自動再試行されるため最終的に適用されるが、中間状態ではポートに QoS マップが未適用となる。
- evidence: `qosorch.cpp:2120-2130`

### 2. DEL 時の参照ブロック（pending_remove ロック）

- `QosMapHandler::processWorkItem()` (qosorch.cpp:174-186): DEL 操作時に `isObjectBeingReferenced()` で `PORT_QOS_MAP` から参照中か確認。参照中の場合 `m_pendingRemove = true` を立て `task_need_retry` を返す（参照解除まで削除をブロック）。
- DEL が完遂されるには、先に参照元 `PORT_QOS_MAP|<port>` の `dot1p_to_tc_map` フィールドを削除（または NULL 化）し、参照カウントを 0 にする必要がある。
- **順序依存（DEL）**: `PORT_QOS_MAP|<port>` の `dot1p_to_tc_map` フィールド削除 → `DOT1P_TO_TC_MAP|<name>` DEL の順序が必須。
- evidence: `qosorch.cpp:174-186`

### 3. pending_remove 中の SET ブロック

- `QosMapHandler::processWorkItem()` (qosorch.cpp:136-139): `m_pendingRemove == true` かつ `op == SET_COMMAND` の場合、`"Entry %s %s is pending remove, need retry"` LOG_NOTICE → `task_need_retry` を返す。
- DEL がブロック中（参照解除待ち）の間は、同名エントリへの SET も受け付けられない。
- **順序依存**: `DOT1P_TO_TC_MAP|<name>` を更新する場合、先に参照元の PORT_QOS_MAP から参照を解除して pending_remove を解消してから再 SET すること。
- evidence: `qosorch.cpp:136-139`

### 4. convertFieldValuesToAttributes の stoi 例外とサイレント脱落

- `Dot1pToTcMapHandler::convertFieldValuesToAttributes()` (qosorch.cpp:360-397): dot1p フィールド値を `stoi()` で整数変換。`std::invalid_argument` / `std::out_of_range` は `catch` ブロックで `continue` されるため、不正エントリが**サイレントに脱落**して残りエントリで SAI マップを生成する。
- SET 操作自体は `return true` で成功扱いのため呼び出し元にエラーが伝播しない。
- **順序との関係**: 不正エントリが混在した SET を送った場合、CONFIG_DB には全エントリが記録されるが SAI には有効エントリのみ反映される（後から正しい値で上書きすることで解消）。
- evidence: `qosorch.cpp:360-397`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DOT1P_TO_TC_MAP\|<name>` 登録 → `PORT_QOS_MAP\|<port>` SET | 先行推奨（未登録でも retry で最終適用） | `task_need_retry` 自動再試行 (`qosorch.cpp:2120-2130`) |
| 2 | `PORT_QOS_MAP\|<port>` 参照解除 → `DOT1P_TO_TC_MAP\|<name>` DEL | **先行必須**（参照中は DEL ブロック） | `m_pendingRemove=true` + `task_need_retry` ロック (`qosorch.cpp:174-186`) |
| 3 | pending_remove 解消 → 同名エントリへの SET | **先行必須** | pending_remove 中の SET は即 `task_need_retry` (`qosorch.cpp:136-139`) |
| 4 | 不正 dot1p 値のサイレント脱落 | SET 後に上書きで解消 | 正しい値で再 SET (`qosorch.cpp:360-397`) |
