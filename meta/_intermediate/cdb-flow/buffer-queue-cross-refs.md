# BUFFER_QUEUE — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/buffer-queue.md` Phase C 追加分。
YANG leafref は `profile → BUFFER_PROFILE.name` および `port → PORT.name` の 2 件のみ定義。以下に示す他テーブルへの依存は全て実装レベルの暗黙参照。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/cfgmgr/buffermgrdyn.cpp` | `handleSingleBufferQueueEntry()` / `checkBufferProfileDirection()` / `handlePortTable()` |
| `sonic-swss/orchagent/bufferorch.cpp` | `processQueue()` — SAI 書き込み直前の BUFFER_PROFILE + PORT OID 解決 |

## YANG leafref

| フィールド | leafref 先 |
|-----------|-----------|
| `profile` | `BUFFER_PROFILE.name` |
| `port` (key) | `PORT.name` |

## 暗黙参照 (実装レベル)

### 1. BUFFER_PROFILE（profile 値解決・direction チェック）

- **参照先テーブル**: `BUFFER_PROFILE`
- **参照方向**: 存在確認 + direction 属性取得
- **条件**: `profile` フィールドが指定されたとき（SET コマンド）
- **参照元 (buffermgrdyn)**:
  - `buffermgrdyn.cpp` L3275 — `checkBufferProfileDirection(fvValue(i), BUFFER_EGRESS)` でプロファイルの direction を検証
  - `buffermgrdyn.cpp` L3283 — `m_bufferProfileLookup.find(profileName)` 未発見 → `task_need_retry`
  - `buffermgrdyn.cpp` L3290 — `dir != profileObj.direction` → `task_failed`（ingress profile は BUFFER_QUEUE に使用不可）
  - `buffermgrdyn.cpp` L3320 — `handleSingleBufferQueueEntry()` 内で `BUFFER_EGRESS` を期待する direction として渡す
- **参照元 (orchagent)**:
  - `bufferorch.cpp` L961–970 — `resolveFieldRefValue(m_buffer_type_maps, buffer_profile_field_name, ...)` 失敗 → `task_need_retry`
  - `bufferorch.cpp` L976–985 — profile 未変更かつ `m_partiallyAppliedQueues` 未登録 → SAI 呼び出しスキップ（冪等）
  - `bufferorch.cpp` L992 — `setObjectReference(m_buffer_type_maps, APP_BUFFER_QUEUE_TABLE_NAME, key, ...)` で参照追跡
- **意味**: BUFFER_PROFILE が未存在なら `task_need_retry`。ingress 方向のプロファイルを BUFFER_QUEUE に使用すると即 `task_failed`。BUFFER_QUEUE は必ず egress 方向のプロファイルを参照しなければならない。

### 2. BUFFER_POOL egress（プール準備ゲート）

- **参照先テーブル**: `BUFFER_POOL`（egress 方向）
- **参照方向**: 間接参照。`BUFFER_PROFILE` が参照する `BUFFER_POOL` の `direction = BUFFER_EGRESS` 確認
- **条件**: `m_bufferPoolReady` フラグが false の間は BUFFER_PROFILE 書き込み自体がデファーされ、BUFFER_QUEUE の profile 解決も連鎖でブロックされる
- **参照元 (buffermgrdyn)**:
  - `buffermgrdyn.cpp` L818–819 — `m_bufferPoolReady = true` 条件成立まで profile 書き込みを保留
  - `buffermgrdyn.cpp` L892 — `m_bufferObjectsPending = true`（profile 書き込みを pending 状態にセット）
  - `buffermgrdyn.cpp` L2549 — `bufferPool.direction = BUFFER_EGRESS;` で egress pool を識別・格納
- **参照元 (orchagent)**:
  - `bufferorch.cpp` L449 — `SAI_BUFFER_POOL_TYPE_EGRESS` として pool type を SAI に設定（間接確認）
- **意味**: egress BUFFER_POOL が APPL_DB に書き込まれるまで、BUFFER_PROFILE（egress）も確立されず、BUFFER_QUEUE の profile 参照解決は `task_need_retry` を繰り返す。egress pool 欠如は QUEUE 全体の初期化ブロッカーとなる。

### 3. PORT（ポート OID 解決 + admin_status）

- **参照先テーブル**: `PORT`（CONFIG_DB）
- **参照方向**: OID 取得（`gPortsOrch->getPort()`）および admin_status 参照
- **条件**: 常時。PORT が PortsOrch に登録されていない場合 `task_invalid_entry` を返す
- **参照元 (buffermgrdyn)**:
  - `buffermgrdyn.cpp` L449 — `CFG_PORT_TABLE_NAME` を `handlePortTable` にバインド
  - `buffermgrdyn.cpp` L2272 — `m_portInfoLookup[port]` で PORT の admin_status / state を管理
  - `buffermgrdyn.cpp` L3346 — `PORT_ADMIN_DOWN == portInfo.state` の場合 `handleSetSingleBufferObjectOnAdminDownPort()` を呼び出し（SAI 適用を保留）
  - `buffermgrdyn.cpp` L3366 — DEL 時も `PORT_ADMIN_DOWN` で分岐して APPL_DB 書き込みをスキップ
- **参照元 (orchagent)**:
  - `bufferorch.cpp` L1033 — `gPortsOrch->getPort(port_name, port)` 失敗 → `task_invalid_entry`
  - `bufferorch.cpp` L1111 — processQueueBulk でも同様に `getPort()` で OID 取得
- **意味**: PORT が PortsOrch に未登録の場合 `task_invalid_entry`。PORT が admin-down の場合 buffermgrd は APPL_DB 書き込みを保留し、admin-up 遷移後に適用再開。

### 4. SYSTEM_PORT / VOQ（VOQ シャーシモード）

- **参照先テーブル**: `SYSTEM_PORT`（CONFIG_DB）、実体は `gMySwitchType == "voq"` フラグで判定
- **参照方向**: key 形式の切り替えと VOQ OID 取得
- **条件**: `DEVICE_METADATA.switch_type = voq` のとき
- **参照元 (orchagent)**:
  - `bufferorch.cpp` L116–139 — 初期化時に `gMySwitchType == "voq"` を確認し、VOQ 用の `CFG_BUFFER_QUEUE_TABLE_NAME` テーブルを登録
  - `bufferorch.cpp` L916 — processQueue 冒頭で `gMySwitchType == "voq"` をチェックし、key の token 数を 4 (VOQ) / 2 (非 VOQ) で分岐
  - `bufferorch.cpp` L930–940 — VOQ の場合 `tokens[0]|tokens[1]|tokens[2]` を hostname|asic_name|port として解析
  - `bufferorch.cpp` L1049–1058 — `gPortsOrch->getPortVoQIds(port)` で VOQ OID リストを取得し、指定インデックスの VOQ に buffer profile を適用
  - `bufferorch.cpp` L1135–1136 — VOQ の場合 flex counter 追加・削除をスキップ（flexcounterorch が一括登録）
  - `bufferorch.cpp` L1166–1168 — VOQ の場合 `gPortsOrch->increasePortRefCount()` / `decreasePortRefCount()` をスキップ（SYSTEM_PORT は動的削除なし）
- **意味**: VOQ モードでは key が `hostname|asic_name|port|qindex` の 4 トークン形式になり、PORT テーブル代わりに SYSTEM_PORT のポートが参照先となる。非 VOQ とは flex counter 管理・ref count 管理のパスが完全に分岐する。

## まとめ

| 参照先テーブル | YANG leafref | 参照種別 | 非充足時の挙動 |
|---------------|:------------:|---------|--------------|
| `BUFFER_PROFILE` | ✅ (profile フィールド) | 必須: direction チェック + SAI profile OID 解決 | `task_need_retry` / `task_failed`（ingress profile 指定時） |
| `BUFFER_POOL` (egress) | ✗ | 間接ブロッキング: egress pool 未確立で profile もデファー | BUFFER_QUEUE 書き込み全体がデファー |
| `PORT` | ✅ (port key の leafref) | 必須: OID 取得 + admin_status 分岐 | `task_invalid_entry` / admin-down 時は APPL_DB 書き込み保留 |
| `SYSTEM_PORT` / VOQ | ✗ | VOQ モード専用: key 形式と VOQ OID 取得 | token 数不正 → `task_invalid_entry`; VOQ OID 範囲外 → `task_invalid_entry` |
