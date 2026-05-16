# QUEUE — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/queue.md` Phase C 追加分。
YANG leafref は `scheduler → SCHEDULER.name`、`wred_profile → WRED_PROFILE.name`、`ifname → PORT.name` の 3 件が定義されている。以下に示す他テーブルへの依存は全て実装レベルの暗黙参照。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/qosorch.cpp` | `handleQueueTable()` — SET/DEL ハンドラ、OID 解決、SAI 呼び出し |
| `sonic-swss/orchagent/qosorch.cpp` | `applySchedulerToQueueSchedulerGroup()` — SCHEDULER OID を scheduler group に適用 |
| `sonic-swss/orchagent/qosorch.cpp` | `applyWredProfileToQueue()` — WRED_PROFILE OID を queue に適用 |
| `sonic-swss/orchagent/qosorch.cpp` | `doTask()` (L2231) — 実行順序制御（参照先テーブル → PORT_QOS_MAP → QUEUE） |

## YANG leafref

| フィールド | leafref 先 |
|-----------|-----------|
| `scheduler` | `SCHEDULER.name` |
| `wred_profile` | `WRED_PROFILE.name` |
| `ifname` (key) | `PORT.name` または文字列 `CPU` |

## 暗黙参照 (実装レベル)

### 1. SCHEDULER（スケジューラ OID 解決）

- **参照先テーブル**: `SCHEDULER`（CONFIG_DB）
- **参照方向**: OID 解決（`resolveFieldRefValue`）
- **条件**: `scheduler` フィールドが指定されたとき（SET コマンド）
- **参照元 (qosorch.cpp)**:
  - L1822–1824 — `resolveFieldRefValue(m_qos_maps, scheduler_field_name, qos_to_ref_table_map.at(scheduler_field_name), tuple, sai_scheduler_profile, scheduler_profile_name)`
  - L1829–1832 — `ref_resolve_status::not_resolved` のとき `SWSS_LOG_INFO("Missing or invalid scheduler reference")` → `task_need_retry`
  - L1834–1835 — その他エラー → `SWSS_LOG_ERROR("Resolving scheduler reference failed")` → `task_failed`
  - L1852 — 解決成功時 `setObjectReference(m_qos_maps, CFG_QUEUE_TABLE_NAME, key, scheduler_field_name, scheduler_profile_name)` で参照追跡
  - L1841–1843 — フィールドが消去された場合（`field_not_found` かつ既存参照あり）: `removeMeFromObjsReferencedByMe(...)` → `sai_scheduler_profile = SAI_NULL_OBJECT_ID`
- **意味**: SCHEDULER エントリが未存在の場合は `task_need_retry`。SCHEDULER が登録されると doTask の実行順序制御により直ちに再試行される。`scheduler` フィールドを省略すると scheduler group に何も設定しない（ASIC デフォルト動作）。

### 2. WRED_PROFILE（WRED OID 解決）

- **参照先テーブル**: `WRED_PROFILE`（CONFIG_DB）
- **参照方向**: OID 解決（`resolveFieldRefValue`）
- **条件**: `wred_profile` フィールドが指定されたとき（SET コマンド）
- **参照元 (qosorch.cpp)**:
  - L1857–1859 — `resolveFieldRefValue(m_qos_maps, wred_profile_field_name, qos_to_ref_table_map.at(wred_profile_field_name), tuple, sai_wred_profile, wred_profile_name)`
  - L1864–1867 — `ref_resolve_status::not_resolved` のとき `SWSS_LOG_INFO("Missing or invalid wred profile reference")` → `task_need_retry`
  - L1869–1870 — その他エラー → `SWSS_LOG_ERROR("Resolving wred profile reference failed")` → `task_failed`
  - L1886 — 解決成功時 `setObjectReference(m_qos_maps, CFG_QUEUE_TABLE_NAME, key, wred_profile_field_name, wred_profile_name)` で参照追跡
  - L1875–1877 — フィールド消去時: `removeMeFromObjsReferencedByMe(...)` → `sai_wred_profile = SAI_NULL_OBJECT_ID`
- **意味**: WRED_PROFILE エントリが未存在の場合は `task_need_retry`。`scheduler` が未解決の間は WRED_PROFILE の確認・適用も保留される（順序依存）。`wred_profile` フィールドを省略すると実質 tail-drop（WRED なし）。

### 3. PORT（ポート OID 解決）

- **参照先テーブル**: `PORT`（CONFIG_DB）、実体は `gPortsOrch` 経由
- **参照方向**: OID 取得（`gPortsOrch->getPort()`）および PortInitDone ゲート
- **条件**: 常時。PORT が PortsOrch に登録されていない場合 `task_invalid_entry`（リトライなし）
- **参照元 (qosorch.cpp)**:
  - L2258 — `doTask()` 冒頭の `gPortsOrch->allPortsReady()` チェック。全ポート初期化完了まで処理を保留
  - L1911–1914 — `gPortsOrch->getPort(port_name, port)` 失敗 → `SWSS_LOG_ERROR("Port with alias:%s not found")` → `task_invalid_entry`
  - L1645 — VOQ モード: `gPortsOrch->getPort(port.m_system_port_info.local_port_oid, port)` でローカルポートを解決
  - L1717 — VOQ WRED 適用時: `gPortsOrch->getPortVoQIds(port)` で VoQ OID リストを取得
- **意味**: PORT が PortsOrch に未登録の場合 `task_invalid_entry`（retry なし、恒久スキップ）。portsyncd が PortInitDone を発行した後に QUEUE エントリを投入すること。

### 4. PORT_QOS_MAP（実行順序依存）

- **参照先テーブル**: `PORT_QOS_MAP`（CONFIG_DB）
- **参照方向**: 処理順序の先行依存（直接 OID 参照なし）
- **条件**: doTask() の実行順序制御ロジックによる暗黙依存
- **参照元 (qosorch.cpp)**:
  - L2231–2260 — `doTask()` のカスタム実行順序: `SCHEDULER` / `WRED_PROFILE` などの参照先テーブルを drain → `PORT_QOS_MAP` を drain → 最後に `QUEUE` を drain
  - L2235 — `auto *port_qos_map_cfg_exec = getExecutor(CFG_PORT_QOS_MAP_TABLE_NAME)` で PORT_QOS_MAP の executor を取得し優先 drain
- **意味**: QUEUE の doTask 実行前に PORT_QOS_MAP のエントリが処理されることが保証される。直接的な OID 参照はないが、処理順序上の先行依存として QUEUE エントリの SAI 適用タイミングに影響する。

## まとめ

| 参照先テーブル | YANG leafref | 参照種別 | 非充足時の挙動 |
|---------------|:------------:|---------|--------------|
| `SCHEDULER` | ✅ (`scheduler` フィールド) | 必須: OID 解決 → `SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID` 設定 | `task_need_retry` / 解決不可なら `task_failed` |
| `WRED_PROFILE` | ✅ (`wred_profile` フィールド) | 必須: OID 解決 → `SAI_QUEUE_ATTR_WRED_PROFILE_ID` 設定 | `task_need_retry` / 解決不可なら `task_failed` |
| `PORT` | ✅ (`ifname` key の leafref) | 必須: OID 取得 + PortInitDone ゲート | `task_invalid_entry`（retry なし） |
| `PORT_QOS_MAP` | ✗ | 実行順序先行依存: doTask() で PORT_QOS_MAP を先に drain | 直接エラーなし。処理タイミングに影響 |
