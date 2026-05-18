# TC_TO_PRIORITY_GROUP_MAP — Phase F 副作用スキャンノート

対象ページ: `docs/reference/config-db/tc-to-priority-group-map.md`
対象テーブル: `CONFIG_DB.TC_TO_PRIORITY_GROUP_MAP`
Consumer: `QosOrch::handleTcToPgTable()` / `TunnelDecapOrch::doTask()`
スキャン範囲: `orchagent/qosorch.cpp:884-934`, `orchagent/qosorch.cpp:2060-2175`, `orchagent/tunneldecaporch.cpp:230-243`

---

## 検出した副作用

### 1. SAI QoS map オブジェクト生成（ASIC 側）

`TcToPgHandler::addQosItem()` (qosorch.cpp:904-928) が `sai_qos_map_api->create_qos_map()` を呼ぶ。`SAI_QOS_MAP_ATTR_TYPE = SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP` と `SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` を設定したオブジェクトが syncd 経由で ASIC に生成される。

**副作用**: ASIC の QoS map テーブルにエントリが追加される。ただしこの時点ではポート・トンネルへの適用はない（マップ OID を `m_qos_maps` に保存するだけ）。

evidence: `qosorch.cpp:904-928`

### 2. PORT_QOS_MAP 経由でのポート ingress PG 割り当て変更

`PORT_QOS_MAP|<port>.tc_to_pg_map` が本テーブルのマップ名を参照している場合、`handlePortQosMapTable()` (qosorch.cpp:2060-2175) が `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` をポートに設定する。これによりポートの ingress バッファ割り当て（PG への TC マッピング）が ASIC で即時変更される。

**副作用**:
- TC ごとの ingress パケットが異なる PG に振り分けられる
- PFC の動作対象 PG が変わる（lossless PG 3, 4 への TC 割り当てを変えると PFC が機能しなくなる）
- BUFFER_PG で lossless profile が割り当てられた PG に TC が割り当てられていないと、lossless パス全体が無効化される

evidence: `qosorch.cpp:2060-2175`

### 3. TUNNEL_DECAP_TABLE 経由でのトンネル decap PG 割り当て変更

`TUNNEL_DECAP_TABLE|<name>.decap_tc_to_pg_map` が本テーブルのマップ名を参照している場合、`TunnelDecapOrch::doTask()` (tunneldecaporch.cpp:230-243) が `SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` をトンネルオブジェクトに設定する。decap パケットの内部ヘッダ TC から PG へのマッピングが変わる。

**副作用**: トンネルデカプセル後のパケットが異なる PG に割り当てられる。VxLAN / GRE decap 経路で QoS が変化する。

evidence: `tunneldecaporch.cpp:230-243`

### 4. 既存マップの上書き（modify）

既に SAI に登録済みのマップを SET した場合、`modifyQosItem()` (qosorch.cpp:204-213) が `sai_qos_map_api->set_qos_map_attribute()` を呼ぶ。**参照中のポート・トンネルに即時反映される**（新しい TC→PG マッピングが稼働中のトラフィックに適用される）。修正中のトラフィックはバッファ割り当てが一時的に不整合になる可能性がある。

evidence: `qosorch.cpp:204-213`

### 5. マップ削除（remove）による参照解放

DEL 時に `removeQosItem()` → `sai_qos_map_api->remove_qos_map()` が呼ばれる。事前に PORT_QOS_MAP / TUNNEL_DECAP_TABLE の参照が解放されている（`m_pendingRemove` 解消後）ため、削除時点では ASIC ポート・トンネルへの紐付けはなくなっている。マップ OID が `m_qos_maps` から削除される。

evidence: `qosorch.cpp:188-195`

---

## STATE_DB / 通知チャネルへの副作用

| 副作用先 | 内容 |
|---------|------|
| STATE_DB | **書き込みなし**。TC_TO_PRIORITY_GROUP_MAP は STATE_DB テーブルを持たない |
| APPL_DB | **書き込みなし**。CONFIG_DB → SAI ダイレクトルートであり APPL_DB は中間経路として使用されない |
| ERROR_TABLE | なし |
| 通知チャネル | なし（syslog のみ） |

---

## 副作用サマリ

| # | 副作用 | トリガー | 影響範囲 |
|---|--------|---------|---------|
| 1 | ASIC に SAI QoS map オブジェクト生成 | SET（新規） | ASIC QoS map テーブル |
| 2 | ポートの ingress TC→PG マッピング変更 | PORT_QOS_MAP 参照時に適用 | 対象ポートの ingress バッファ・PFC 動作 |
| 3 | トンネル decap の TC→PG マッピング変更 | TUNNEL_DECAP_TABLE 参照時に適用 | decap パケットの PG 割り当て |
| 4 | 参照中ポート・トンネルへの即時反映 | SET（上書き）の modify | 稼働中トラフィックの QoS |
| 5 | SAI QoS map オブジェクト削除 | DEL（参照解放後） | ASIC QoS map テーブル |

---

## ページ反映方針

- `<!-- side-effects -->` ブロックを `<!-- constants -->` の直後に挿入する。
- SAI QoS map 生成・ポート/トンネルへの適用・modify 時の即時反映・STATE_DB 無しを明記する。
- PFC lossless 動作への影響を特に強調する（運用上のリスクが高い）。
