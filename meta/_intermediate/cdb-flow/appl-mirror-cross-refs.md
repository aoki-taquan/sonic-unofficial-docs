# APPL_DB FIXED_MIRROR_SESSION_TABLE — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/appl-mirror.md` Phase C 追加分。
APPL_DB `FIXED_MIRROR_SESSION_TABLE` は P4RT 経由で `MirrorSessionManager` (`sonic-swss/orchagent/p4orch/mirror_session_manager.cpp`) が処理する。
比較対照として CONFIG_DB `MIRROR_SESSION` を処理する `MirrorOrch` (`sonic-swss/orchagent/mirrororch.cpp`) の依存も精査し、P4RT 経路で「ない依存」を**negative evidence** として明示する。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/p4orch/mirror_session_manager.cpp` | `drain()` / `prepareSaiAttrs()` / `processAddRequest()` / `processUpdateRequest()` / `setPort()` |
| `sonic-swss/orchagent/p4orch/p4orch_util.h` | `P4MirrorSessionAppDbEntry` 構造体定義（policer フィールドの不在を確認） |
| `sonic-swss/orchagent/mirrororch.cpp` | CONFIG_DB 経路の依存比較 (`m_routeOrch->attach()` / `m_policerOrch->policerExists()` / `m_neighOrch->getNeighborEntry()` / `m_fdbOrch->getPort()`) |

## YANG leafref

`FIXED_MIRROR_SESSION_TABLE` は P4RT 専用 APPL_DB テーブルで YANG モデルを持たない。すべて実装レベルの暗黙参照。

## 暗黙参照（P4RT 経路）

### 1. PORT テーブル（`param/port` matchfield）

- **参照先**: `PORT`（`PortsOrch` 管理）
- **参照方向**: OID 解決 + refcount
- **条件**: 常時（必須フィールド）。`param/port` で指定された物理ポート名を解決する
- **参照元**:
  - `mirror_session_manager.cpp:125` (`gPortsOrch->getPort(mirror_session_entry.port, port)`) — ADD 時の最初の解決
  - L214 — `deserializeP4MirrorSessionAppDbEntry()` でも port 存在を確認
  - L387 (`gPortsOrch->increasePortRefCount(...)`) — ADD 成功時に refcount を増やす
  - L493 (`gPortsOrch->getPort(new_port_name, new_port)`) — UPDATE 時の新 port 解決
  - L518 (`gPortsOrch->increasePortRefCount(new_port.m_alias)`) — UPDATE 時 ref count 移管
- **意味**: 未登録 port → `SWSS_RC_NOT_FOUND` で fail-fast、リトライなし。`port.m_type != PHY` → `SWSS_RC_INVALID_PARAM`（LAG/VLAN は不可）。CONFIG_DB 側の `allPortsReady()` ガードに相当する機構はなく、P4RT クライアントの再送に依存。

### 2. （否定）NEXTHOP / NEIGH / ROUTE 動的解決は不在

- **参照先**: なし（CONFIG_DB 側との差異）
- **負の evidence**: `mirror_session_manager.cpp` 全文に `m_neighOrch` / `m_routeOrch` / `m_fdbOrch` への参照は存在しない（grep 結果 0 件）。`MirrorSessionManager` は `Observer` を継承せず、`PortsOrch::attach` / `NeighOrch::attach` / `RouteOrch::attach` を呼ばない。
- **意味**: P4RT 経路は `param/dst_mac` を APPL_DB の必須フィールドとして直接受領するため、neighbor / fdb / route の動的解決を行わない。トポロジ変化で MAC が変わっても自動追従しない（P4RT クライアントが UPDATE を再発行する責務）。
- **CONFIG_DB 側との対比**: `mirrororch.cpp:93-95` (`m_portsOrch->attach(this)` / `m_neighOrch->attach(this)` / `m_fdbOrch->attach(this)`), L517 (`m_routeOrch->attach(this, entry.dstIp)`), L656-732 (`m_neighOrch->getNeighborEntry()` / `m_fdbOrch->getPort()`) — CONFIG_DB ERSPAN は next-hop 解決を待ち、`SUBJECT_TYPE_NEXTHOP_CHANGE` / `NEIGH_CHANGE` / `FDB_CHANGE` 通知で `updateSession()` を回す動的解決機構を持つ。

### 3. （否定）POLICER 参照は不在

- **参照先**: なし（CONFIG_DB 側との差異）
- **負の evidence**: `P4MirrorSessionAppDbEntry` 構造体 (`p4orch_util.h:253-279`) は `port` / `src_ip` / `dst_ip` / `src_mac` / `dst_mac` / `ttl` / `tos` のみ保持し、`policer` フィールドを持たない。`prepareSaiAttrs()` (`mirror_session_manager.cpp:122-188`) は `SAI_MIRROR_SESSION_ATTR_POLICER` を一切設定しない。`m_policerOrch` への参照も同ファイル内に存在しない。
- **意味**: P4RT 経路では MIRROR_SESSION への policer attach はサポートされない。QoS 制御が必要な場合は ACL_RULE の meter (`p4orch/acl_rule_manager.cpp::getMeterSaiAttrs`) 側で実施する設計。
- **CONFIG_DB 側との対比**: `mirrororch.cpp:434-441` (`m_policerOrch->policerExists()` で未登録なら `task_need_retry`、L1055 で `getPolicerOid()` を SAI 属性に設定) — POLICER 先行を強制する。

### 4. MIRROR_SESSION → ACL_RULE 逆参照（参照される側）

- **参照元テーブル**: P4RT `ACL_RULE`（`AclRuleManager`）
- **参照方向**: 参照される側（refcount 監視）
- **条件**: ACL_RULE の `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS` / `MIRROR_EGRESS` で `mirror_session_id` が指定されたとき
- **参照元 evidence**:
  - `p4orch/acl_rule_manager.cpp` L1403-1419 — `m_p4OidMapper->getOID(SAI_OBJECT_TYPE_MIRROR_SESSION, key, &oid)` で参照、未登録なら `SWSS_RC_NOT_FOUND`
  - `mirror_session_manager.cpp:752-757` — DEL 時に `m_p4OidMapper->getRefCount()` が > 0 なら `SWSS_RC_IN_USE` で削除拒否
- **意味**: ACL_RULE が mirror アクションを使う場合は `FIXED_MIRROR_SESSION_TABLE` SET の publish 成功確認が先行必須（CONFIG_DB の `AclRuleMirror` のような遅延 activate 機構は p4orch の `AclRuleManager` に存在しない）。逆方向では、参照中の MIRROR_SESSION を削除しようとすると `SWSS_RC_IN_USE` で拒否される。

## 参照関係サマリ

```
APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT)
  ├─ [暗黙] PORT.alias                  (param/port — OID 解決 + refcount、PHY のみ)
  ├─ [なし] NEXTHOP / NEIGH / ROUTE     (CONFIG_DB との差異: 動的解決機構なし)
  ├─ [なし] POLICER                     (CONFIG_DB との差異: APP_DB スキーマに存在しない)
  └─ [被参照] P4RT ACL_RULE             (mirror_session_id 経由、refcount で削除拒否)
```

## evidence

- `mirror_session_manager.cpp`:
  - L122-136 (`prepareSaiAttrs()` の port 解決 + PHY 制約)
  - L213-225 (`deserializeP4MirrorSessionAppDbEntry()` の port 解決)
  - L387 / L518 (`increasePortRefCount()` ADD / UPDATE)
  - L492-497 (`setPort()` 新 port 解決)
  - L122-188 (`prepareSaiAttrs()` 全体 — SAI_MIRROR_SESSION_ATTR_POLICER 不在)
  - L752-757 (DEL の refcount チェック)
- `p4orch_util.h`: L253-279 (`P4MirrorSessionAppDbEntry` — policer フィールドなし)
- `mirrororch.cpp` (CONFIG_DB 比較):
  - L83-95 (`m_routeOrch` / `m_neighOrch` / `m_fdbOrch` / `m_policerOrch` の attach)
  - L434-441 (`policerExists()` / `increaseRefCount()`)
  - L517 (`m_routeOrch->attach(this, entry.dstIp)`)
  - L656-732 (`m_neighOrch->getNeighborEntry()` / `m_fdbOrch->getPort()`)
  - L1055 (`m_policerOrch->getPolicerOid()`)
- `p4orch/acl_rule_manager.cpp`: L1403-1419 (`SAI_OBJECT_TYPE_MIRROR_SESSION` OID 解決)
