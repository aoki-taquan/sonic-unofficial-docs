# DSCP_TO_TC_MAP — Phase B 書込み順依存スキャンノート

対象テーブル: `DSCP_TO_TC_MAP`
Consumer: `QosOrch::handleDscpToTcTable()` / `QosOrch::handlePortQosMapTable()` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: qosorch.cpp 全行精読、tunneldecaporch.cpp:101-302、db_migrator.py:700-715

---

## 検出した順序依存・タイミング依存

### 1. PORT_QOS_MAP が DSCP_TO_TC_MAP より先行必須（ポートバインド）

- `handlePortQosMapTable()` qosorch.cpp:2124-2129: `resolveFieldRefValue()` が `ref_resolve_status::success` を返さない場合（対象マップ名が type_map に未登録）、`task_need_retry` を返す。
- PORT_QOS_MAP のエントリ (`dscp_to_tc_map: <name>`) を書いた時点で対応する `DSCP_TO_TC_MAP|<name>` の SAI オブジェクトが存在しない場合は、Consumer が完了するまで自動的に再試行する。
- **推奨順序**: `DSCP_TO_TC_MAP|<name>` を先に書き → 次に `PORT_QOS_MAP|<port>` で参照する。
- evidence: `qosorch.cpp:2124-2129`

### 2. PORT_QOS_MAP|global が DSCP_TO_TC_MAP より先行必須（スイッチレベル適用）

- `handleGlobalQosMap()` qosorch.cpp:2021-2026: `resolveFieldRefValue()` 失敗時（対象 DSCP_TO_TC_MAP が未作成）、`task_need_retry` を返す。
- Broadcom ASIC では `db_migrator.migrate_port_qos_map_global()` が DSCP_TO_TC_MAP の **最初の 1 件**を自動的に `PORT_QOS_MAP|global` へ登録する（db_migrator.py:707-714）。
- 複数の DSCP_TO_TC_MAP がある場合、`get_keys()` の返却順（未定義）の先頭が選ばれる。
- **推奨順序**: マップを 1 件に絞るか、`PORT_QOS_MAP|global` に明示的に書く。
- evidence: `qosorch.cpp:2021-2026`, `db_migrator.py:700-715`

### 3. DEL 時の参照先確認（pending_remove ロック）

- `handleDscpToTcTable()` qosorch.cpp:181-186: DEL コマンド処理時、`isObjectBeingReferenced()` が true（PORT_QOS_MAP または tunnel から参照中）なら `m_pendingRemove = true` を立てて `task_need_retry` を返す。
- pending_remove 中の SET（再書き込み）も `task_need_retry` で即返却され実行されない（qosorch.cpp:136-139）。
- **推奨 DEL 順序**: `PORT_QOS_MAP|<port>` の `dscp_to_tc_map` 参照を先に除去 → 次に `DSCP_TO_TC_MAP|<name>` を DEL。
- evidence: `qosorch.cpp:136-139`, `181-191`

### 4. Tunnel decap 経路での DSCP_TO_TC_MAP 解決順序

- `tunneldecaporch.cpp:217-221`: `resolveTunnelQosMap()` で DSCP_TO_TC_MAP の SAI OID を解決し、`SAI_NULL_OBJECT_ID` を返した場合（未作成）は `task_need_retry`。
- tunnel エントリの SET 時に `TUNNEL_DECAP_TABLE|<name>` の `dscp_to_tc_map` フィールドが指すマップが未作成なら、Tunnel 作成自体がブロックされる。
- tunneldecaporch.cpp:831-836: `dscp_to_tc_map_id == SAI_NULL_OBJECT_ID` の場合はトンネル作成時に DSCP→TC MAP を設定せず（silent skip）。これはマップを指定しないケースの正常パスで、不在エラーとは区別される。
- **推奨順序**: `DSCP_TO_TC_MAP|<name>` を先に作成 → `TUNNEL_DECAP_TABLE|<name>` で参照する。
- evidence: `tunneldecaporch.cpp:217-221`, `831-836`

### 5. pending_remove 中の SET ブロック

- `handleDscpToTcTable()` qosorch.cpp:136-139: pending_remove フラグが立っている状態で SET が来ると `task_need_retry` を即返す。
- DEL の参照解除が完了するまで SET も実行できない（更新操作全体がブロック）。
- ロールバック・入れ替えシナリオ（旧マップ DEL → 新マップ SET）は、旧マップへの参照を全ポートから除去するまで実行できない。
- evidence: `qosorch.cpp:136-139`

### 6. SAI 操作失敗（task_failed）と retry なし

- CREATE / SET / DELETE で SAI エラーが発生した場合、`task_failed` を返し自動 retry は行われない（qosorch.cpp:153-155, 162-166, 188-191）。
- `DscpToTcMapHandler` は dscp 文字列を `stoi()` で変換する際に例外処理なし（qosorch.cpp:245）。非数値文字列を書くと `std::invalid_argument` → `task_failed`。
- evidence: `qosorch.cpp:151-191`, `245`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | DSCP_TO_TC_MAP SAI 作成完了 → PORT_QOS_MAP SET | 強制先行（自動 retry） | task_need_retry で自動再試行 |
| 2 | DSCP_TO_TC_MAP 作成 → PORT_QOS_MAP\|global（Broadcom） | 強制先行（自動 retry）or db_migrator 自動生成 | 複数マップ時は順序未定義のため明示推奨 |
| 3 | PORT_QOS_MAP / Tunnel の参照解除 → DSCP_TO_TC_MAP DEL | 強制先行（pending_remove ロック） | 参照ポートの qos_map 設定削除が必要 |
| 4 | DSCP_TO_TC_MAP 作成 → TUNNEL_DECAP_TABLE SET | 強制先行（自動 retry）| 未指定は silent skip（エラーではない） |
| 5 | pending_remove 解消 → SET 実行 | 強制先行（ロック） | 参照除去が先 |
| 6 | 数値 dscp 文字列 → SET 実行 | 必須（非数値は task_failed） | 例外処理なし |
