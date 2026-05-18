# TC_TO_PRIORITY_GROUP_MAP — Phase B 書込み順依存スキャンノート

対象ページ: `docs/reference/config-db/tc-to-priority-group-map.md`
対象テーブル: `CONFIG_DB.TC_TO_PRIORITY_GROUP_MAP`
Producer: `qosorch` (`TcToPgHandler`), `qos_config.j2`
スキャン範囲: `orchagent/qosorch.cpp:124-201, 884-934`, `orchagent/tunneldecaporch.cpp:230-243`

---

## 検出した順序依存・タイミング依存

### 1. PORT_QOS_MAP.tc_to_pg_map → TC_TO_PRIORITY_GROUP_MAP の前方参照依存

`handlePortQosMapTable` (qosorch.cpp:2118-2134) は各フィールドを `resolveFieldRefValue` で解決する。`tc_to_pg_map` フィールドが指すマップが `m_qos_maps[CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME]` に未登録の場合、`resolveFieldRefValue` は failure を返し、直ちに `task_need_retry` を返す (qosorch.cpp:2124-2130)。

**順序依存（強制）**: `PORT_QOS_MAP|<port>.tc_to_pg_map` の適用は、対応する `TC_TO_PRIORITY_GROUP_MAP|<name>` が `QosOrch` によって SAI に登録された後でなければ実行されない。CONFIG_DB に両テーブルを同時書き込みしても、orchagent の処理順によっては `PORT_QOS_MAP` が先に来て `task_need_retry` を繰り返す可能性がある。

evidence: `qosorch.cpp:2121-2130`

### 2. TUNNEL_DECAP_TABLE.decap_tc_to_pg_map → TC_TO_PRIORITY_GROUP_MAP の前方参照依存

`TunnelDecapOrch::doTask` (tunneldecaporch.cpp:230-243) は `decap_tc_to_pg_map` フィールドを `gQosOrch->resolveTunnelQosMap()` で解決する。マップが未登録の場合 `SAI_NULL_OBJECT_ID` が返り、`SWSS_LOG_NOTICE("QoS map %s is not ready yet", ...)` ログ後 `task_need_retry` が返る。

**順序依存（強制）**: トンネルエントリは `TC_TO_PRIORITY_GROUP_MAP` の SAI 登録完了後でないと適用されない。`config load` 等で一括投入する場合も、テーブル処理順によりトンネルが先に評価されると retry が発生する。マップが登録されると次のイテレーションで自動解消される。

evidence: `tunneldecaporch.cpp:230-243`

### 3. TC_TO_PRIORITY_GROUP_MAP DEL 時の参照チェック保留

`processWorkItem` (qosorch.cpp:181-186) の DEL ハンドラは `isObjectBeingReferenced()` で PORT_QOS_MAP または TUNNEL_DECAP_TABLE からの参照を確認する。参照が残っている場合は `m_pendingRemove = true` をセットして `task_need_retry` を返し、SAI `remove_qos_map()` を実行しない。

**順序依存（強制）**: マップを DEL するには、先に `PORT_QOS_MAP|<port>.tc_to_pg_map` フィールドの削除（または別マップへの変更）と `TUNNEL_DECAP_TABLE|<name>.decap_tc_to_pg_map` フィールドの削除を済ませる必要がある。参照が解放されると次の処理で DEL が実行される（ただし orchagent 再実行が必要で自動的ではない）。

evidence: `qosorch.cpp:181-186`

### 4. pending_remove 中の SET は拒否

`processWorkItem` (qosorch.cpp:136-139) は `m_pendingRemove = true` 状態のマップに SET が来た場合、`task_need_retry` を返す。DEL が完了するまで新しい値での上書きはできない。

**順序依存**: DEL → SET のシーケンスは、参照解放 → DEL 完了 → SET の順に実行されるまで SET が保留される。運用上は参照を外してから DEL し、DEL 完了を確認後に新マップで SET することが推奨される。

evidence: `qosorch.cpp:136-139`

### 5. qos_config.j2 展開順序: TC_TO_PRIORITY_GROUP_MAP は PORT_QOS_MAP より先に生成

`config qos reload` は `qos_config.j2` を sonic-cfggen で一括展開する。JSON 構造上 `TC_TO_PRIORITY_GROUP_MAP` セクションは `PORT_QOS_MAP` セクションより前に記述される（buildimage `files/build_templates/qos_config.j2` の典型的なセクション順）。orchagent への投入は CONFIG_DB の table ごとのサブスクリプション順に依存するが、QoS 系は単一の `QosOrch` が複数テーブルを処理するため内部でテーブル間の優先度はなく、上記の `task_need_retry` メカニズムで自動調停される。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `TC_TO_PRIORITY_GROUP_MAP` SAI 登録 → `PORT_QOS_MAP.tc_to_pg_map` 適用 | 強制先行 | PORT_QOS_MAP は `task_need_retry` で自動待機、マップ登録後に自動解消 |
| 2 | `TC_TO_PRIORITY_GROUP_MAP` SAI 登録 → `TUNNEL_DECAP_TABLE.decap_tc_to_pg_map` 適用 | 強制先行 | TunnelDecapOrch は `task_need_retry` で自動待機 |
| 3 | PORT_QOS_MAP / TUNNEL_DECAP_TABLE 参照解除 → `TC_TO_PRIORITY_GROUP_MAP` DEL | 強制先行 | 参照中は `m_pendingRemove=true` でブロック |
| 4 | マップ DEL 完了 → 同名マップへの SET | 強制先行 | pending_remove 中の SET は `task_need_retry` |

---

## ページ反映方針

- `<!-- ordering -->` ブロックを `<!-- defaults -->` ブロックの直前に挿入する。
- サマリ表 + 主要依存の散文（特に依存 #1, #2 の tunnel との関係）を含める。
- 既存の `<!-- cdb-exceptions -->` に書込み順依存の記述が一部あるが、`<!-- ordering -->` はより構造化された形式で補完する。
