# APPL_DB FIXED_MIRROR_SESSION_TABLE — Phase B 書込み順依存スキャンノート

対象テーブル: `FIXED_MIRROR_SESSION_TABLE` (APPL_DB / P4RT)
Consumer: `MirrorSessionManager` (`sonic-swss/orchagent/p4orch/mirror_session_manager.cpp`)
ref: `4305596156d70e9797e8a881b3d19b46de0bce0d`
スキャン範囲: `drain()`, `prepareSaiAttrs()`, `processAddRequest()`, `processUpdateRequest()`, `processDeleteRequest()`, `deserializeP4MirrorSessionAppDbEntry()` 全行精読

参考に `sonic-swss/orchagent/mirrororch.cpp` (CONFIG_DB `MIRROR_SESSION` 経路) の `doTask()` / `createEntry()` / `validateDstPort()` / `validateSrcPortList()` も読み、**FIXED_MIRROR_SESSION_TABLE 経路には存在しない依存** を明示する。

---

## 検出した順序依存・タイミング依存

### 1. dst port readiness — PortsOrch::getPort() 先行必須（fail-fast、リトライなし）

- `prepareSaiAttrs()` は最初に `gPortsOrch->getPort(mirror_session_entry.port, port)` を呼び、失敗時は `SWSS_RC_NOT_FOUND` を返す (`mirror_session_manager.cpp:125-129`)。
- `processAddRequest()` はこの戻り値を `RETURN_IF_ERROR` 系マクロで受け、エラー時はそのまま APPL_DB 経由で publish して中断する (`mirror_session_manager.cpp:378-388`)。
- **MirrorOrch (CONFIG_DB) との差異**:
  - `mirrororch.cpp:1571-1574` は `gPortsOrch->allPortsReady()` が false なら `doTask()` 全体を即 return（後で再 drain される）。
  - `MirrorSessionManager::drain()` には `allPortsReady()` ガードが**ない**。`m_entries.pop_front()` で即時取り出して処理し、失敗したら `m_publisher->publish()` で結果を返してから `break` するだけで、**自動リトライがない** (`mirror_session_manager.cpp:62-119`)。
- **順序依存**: `param/port` で指定する物理ポートが `PortsOrch` に登録済み (PORT 初期化完了後) であることが必須。
- **緩和策なし**: P4RT クライアント側で port readiness を確認した上で `FIXED_MIRROR_SESSION_TABLE` SET を発行する必要がある。port 未登録時の SET は `SWSS_RC_NOT_FOUND` で失敗確定し、再送なしでは復活しない。
- evidence: `mirror_session_manager.cpp:62-119`, `mirror_session_manager.cpp:122-136`, `mirror_session_manager.cpp:378-388`

### 2. PHY 型固定 — LAG / VLAN は再試行しても回復不可

- `prepareSaiAttrs()` は `port.m_type != Port::Type::PHY` の場合 `SWSS_RC_INVALID_PARAM` を返す (`mirror_session_manager.cpp:130-136`)。
- LAG メンバ追加待ちなどの「順序依存で後から PHY に変わる」遷移は存在しない（port の type は同一 alias で変動しない）。
- **MirrorOrch との差異**: `mirrororch.cpp:282-287` の `validateDstPort()` も PHY 限定だが、こちらは CONFIG_DB レベルで `task_invalid_entry` を返し `consumer.m_toSync.erase(it++)` で破棄される (`mirrororch.cpp:1603-1606`)。P4RT 経路でも結果は同様（リトライしない）。
- **依存ではないが注意**: `validateSrcPortList()` (MirrorOrch) のような LAG メンバ整合チェックは P4RT 経路には存在しない（そもそも src_port フィールドがないため）。
- evidence: `mirror_session_manager.cpp:130-136`

### 3. drain() の head-of-line blocking — エラー発生で同一 drain 内の以降エントリが滞留

- `drain()` のメインループは `if (!status.ok()) { break; }` で**最初の失敗時点で打ち切る** (`mirror_session_manager.cpp:114-116`)。
- 残った `m_entries` のエントリは `drainWithNotExecuted()` (`mirror_session_manager.cpp:58-60`, `p4orch_util.cpp drainMgmtWithNotExecuted`) で「未実行」として publisher に応答するのみで、SAI への書込みは行われない。
- **順序依存（バッチ内）**: 同一 P4RT トランザクション内で 2 つ以上のセッションを SET する場合、**先頭エントリでエラーが出ると後続セッションは全て未処理** になる。port readiness のばらつきがあるバッチは特に注意。
- **MirrorOrch との差異**: `mirrororch.cpp:1576-1607` の `doTask()` は各エントリを独立に処理し、`task_need_retry` のみ `it++` で残し、それ以外（`task_invalid_entry` 含む）は erase して次へ進む。head-of-line blocking はない。
- evidence: `mirror_session_manager.cpp:62-120`

### 4. ACL_RULE での mirror_session_id 参照 — FIXED_MIRROR_SESSION_TABLE 先行必須

- P4RT ACL の `AclRuleManager` は `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS` / `_EGRESS` アクション処理で `m_p4OidMapper->getOID(SAI_OBJECT_TYPE_MIRROR_SESSION, key, &mirror_session_oid)` を呼び、未登録なら `SWSS_RC_NOT_FOUND` で即失敗する (`acl_rule_manager.cpp:1403-1419`)。
- **MirrorOrch との差異**: CONFIG_DB 経路の `AclRuleMirror::createCounter()`/`activate()` (`aclorch.cpp:2331-2350`) は `m_pMirrorOrch->sessionExists()` チェックで存在しなければ `SWSS_LOG_ERROR` を返すが、`AclRuleMirror::create()` は `state==false`（未 activate）の場合に `pending` ルールとして保留し、`SUBJECT_TYPE_MIRROR_SESSION_CHANGE` 通知で後から activate される (`mirrororch.cpp:1095-1096, 1110-1111`)。
- p4orch の `AclRuleManager` には**同等の遅延 activate 機構がない**。`OidMapper` への登録は `MirrorSessionManager::processAddRequest()` 完了直後 (`mirror_session_manager.cpp:387` 周辺) なので、ACL_RULE 側の P4RT 書込みは `FIXED_MIRROR_SESSION_TABLE` 処理完了**後**でなければならない。
- **順序依存**: P4RT クライアントは「`FIXED_MIRROR_SESSION_TABLE` SET → publish 成功確認 → `ACL_*_TABLE` SET（mirror action 付き）」の順で発行すること。
- evidence: `mirror_session_manager.cpp:339-398`, `acl_rule_manager.cpp:1403-1419`

### 5. processUpdateRequest の port 切替 — 新 port も readiness 必須・ref count 移管

- `processUpdateRequest()` で `port` フィールドが変わる場合、`gPortsOrch->getPort(new_port_name, new_port)` を呼ぶ (`mirror_session_manager.cpp:493`)。失敗時は `SWSS_RC_NOT_FOUND` で即返り、SAI 属性更新も ref count 移管も行われず**旧 port が保持される**。
- 成功時のみ `decreasePortRefCount(old)` → `increasePortRefCount(new)` の順で実行 (`mirror_session_manager.cpp:517-518`)。
- **順序依存**: port 切替時は新 port が PortsOrch に登録済みであること。新 port を作成してから UPDATE を発行する順序を守る。
- evidence: `mirror_session_manager.cpp:399-520`

### 6. policer 先行依存は不在（CONFIG_DB との差異）

- `FIXED_MIRROR_SESSION_TABLE` には `policer` フィールドが**存在しない**。`P4MirrorSessionAppDbEntry` 構造体 (`p4orch_util.h:253-279`) は ttl/tos/src_ip/dst_ip/src_mac/dst_mac/port のみ保持。
- `prepareSaiAttrs()` も `SAI_MIRROR_SESSION_ATTR_POLICER` を設定しない (`mirror_session_manager.cpp:122-188`)。
- **MirrorOrch (CONFIG_DB) との差異**: `mirrororch.cpp:432-443` の `MIRROR_SESSION_POLICER` フィールドは `m_policerOrch->policerExists()` を確認し、存在しなければ `task_need_retry` で待機する（POLICER テーブルが先行必須）。FIXED_MIRROR_SESSION_TABLE 経路ではこの依存は**ない**。
- **書込み順への含意**: P4RT 側で QoS 制御が必要な場合は ACL_RULE の meter（`getMeterSaiAttrs`, `acl_rule_manager.cpp:124-`）側で行う設計。MIRROR_SESSION 自体への policer attach は P4RT では対象外。
- evidence: `mirror_session_manager.cpp:122-188`, `p4orch_util.h:253-279`, `mirrororch.cpp:432-443`

### 7. routeOrch / neighbor 解決依存は不在（ERSPAN 固定）

- `MirrorSessionManager::processAddRequest()` は SAI 属性をその場で全て設定し、`SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE` で create する (`mirror_session_manager.cpp:339-398`, `prepareSaiAttrs()` L145-150)。
- **MirrorOrch との差異**: CONFIG_DB ERSPAN セッションは `m_routeOrch->attach(this, entry.dstIp)` (`mirrororch.cpp:517`) で `dst_ip` の next hop 解決を待ち、`SUBJECT_TYPE_NEXTHOP_CHANGE`/`NEIGH_CHANGE`/`FDB_CHANGE`/`LAG_MEMBER_CHANGE` 通知で `updateSession()` を回す動的解決機構を持つ (`mirrororch.cpp:160-198, 760-808`)。P4RT 経路は `dst_mac` を**APPL_DB の必須フィールドとして直接受け取る**ため、neighbor / fdb / route の動的解決は行われない。
- **書込み順への含意**: P4RT クライアントが事前に dst の MAC を解決して `param/dst_mac` で渡す責務を負う。MAC が変わった場合は `FIXED_MIRROR_SESSION_TABLE` の UPDATE を発行し直す必要がある（自動追従しない）。
- evidence: `mirror_session_manager.cpp:339-398`, `mirrororch.cpp:160-198, 760-808`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | PORT 初期化 → `FIXED_MIRROR_SESSION_TABLE` SET (`param/port`) | 強制先行（fail-fast、リトライなし） | P4RT クライアント側で再送 |
| 2 | port は PHY 型 | 強制（LAG/VLAN 不可、回復不能） | 設計時に PHY を選定 |
| 3 | drain() head-of-line — 失敗時に同一 drain の以降エントリが滞留 | バッチ順注意 | エラー発生ロットは個別再送 |
| 4 | `FIXED_MIRROR_SESSION_TABLE` SET 完了 → ACL_RULE (mirror action) SET | 強制先行（pending 機構なし） | P4RT クライアントが SET 順序を保証 |
| 5 | 新 port が PortsOrch 登録済み → UPDATE 発行 | 強制先行 | 新 port 作成後に UPDATE |
| 6 | policer 先行依存は**不在** | (CONFIG_DB との差異) | — |
| 7 | routeOrch / neighbor / fdb / lag 動的解決は**不在** | (CONFIG_DB との差異、`dst_mac` を直接受け取る) | クライアント側で MAC 再解決して UPDATE |
