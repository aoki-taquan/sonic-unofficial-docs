# buffer-queue — Phase B 書込順依存スキャンノート

中間ファイル。詳細は `docs/reference/config-db/buffer-queue.md` の `<!-- ordering -->` ブロックを参照。

## 検出した順序依存

### 1. BUFFER_POOL 先行必須（buffermgrdyn.cpp — 動的バッファモード）

`updateBufferObjectToDb()` の冒頭で `m_bufferPoolReady` フラグを確認する。
`m_bufferPoolReady` が `false` の場合は APPL_DB への書き込みを行わず `m_bufferObjectsPending = true` にして返す。
BUFFER_POOL が登録されるまで BUFFER_QUEUE も APPL_DB に転送されない。

- evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:933-936`

### 2. BUFFER_PROFILE 先行必須（buffermgrdyn.cpp — 動的バッファモード）

`handleSingleBufferQueueEntry()` は `checkBufferProfileDirection()` を呼び出す。
`checkBufferProfileDirection()` は `m_bufferProfileLookup` でプロファイルを検索し、
未登録の場合 `task_need_retry` を返してエントリの処理を延期する。
BUFFER_PROFILE が buffermgrd の内部キャッシュに登録されるまで BUFFER_QUEUE は書き込まれない。

- evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:3282-3286` (`checkBufferProfileDirection`)

### 3. PORT 先行必須（buffermgrdyn.cpp — 動的バッファモード）

`handleSingleBufferQueueEntry()` は `m_portInfoLookup[port]` でポート情報を参照する。
ポートが `PORT_ADMIN_DOWN` 状態の場合は `handleSetSingleBufferObjectOnAdminDownPort()` に委譲し、
admin-up 後に改めて APPL_DB へ書き込む。ポートが `m_portInfoLookup` 未登録の場合は
STATE_DB の `max_queues` 通知（`handleBufferMaxParam`）が到着するまで
`reclaimReservedBufferForPort()` / `refreshQueuesForPort()` は起動しない。

- evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:3344-3350` (`handleSingleBufferQueueEntry`)

### 4. BUFFER_PROFILE 先行必須（BufferOrch — orchagent 側）

`BufferOrch::doBufferQueueTask()` は APPL_DB 上のプロファイル参照を
`resolveFieldRefValue()` で解決する。プロファイルが APPL_DB に未登録の場合
`ref_resolve_status::not_resolved` となり `task_need_retry` を返す。

- evidence: `sonic-swss/orchagent/bufferorch.cpp:961-970`

### 5. PORT 先行必須（BufferOrch — orchagent 側）

`doBufferQueueTask()` は `gPortsOrch->getPort(port_name, port)` で PORT を取得する。
ポートが未登録の場合 `task_invalid_entry` を返す（non-VOQ）。
VOQ モードでは `gPortsOrch->getPortVoQIds(port)` で VOQ ID リストを取得し、
範囲外インデックスは `task_invalid_entry`。

- evidence: `sonic-swss/orchagent/bufferorch.cpp:1033-1038` (non-VOQ), `1051-1058` (VOQ)

### 6. VOQ シャーシ特別扱い（BufferOrch）

`gMySwitchType == "voq"` の場合、key は 4 トークン形式
`<hostname>|<asic_name>|<port>|<qindex>` を要求し、
`tokens[0] == gMyHostName && tokens[1] == gMyAsicName` に一致する場合のみ
local port として処理する。一致しない場合は SAI 書き込みが行われない
（`local_port == false` のまま `need_update_sai` が false になる）。
key 形式が 4 トークンでない場合は即 `task_invalid_entry`。

- evidence: `sonic-swss/orchagent/bufferorch.cpp:918-940`

## SAI call

- `sai_buffer_api->set_queue_attribute()` (queue 単位)
  `SAI_QUEUE_ATTR_BUFFER_PROFILE_ID` を設定
- evidence: `sonic-swss/orchagent/bufferorch.cpp` (doBufferQueueTask post-processing)
