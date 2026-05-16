# buffer-pg — Phase B 書込順依存スキャンノート

中間ファイル。詳細は `docs/reference/config-db/buffer-pg.md` の `<!-- ordering -->` ブロックを参照。

## 検出した順序依存

### 1. BUFFER_POOL 先行必須（buffermgrdyn.cpp）

`updateBufferObjectToDb()` の冒頭で `m_bufferPoolReady` を確認する。
プールが未登録の場合は APPL_DB への書き込みを行わず `m_bufferObjectsPending = true` にして返す。

- evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:935`

### 2. BUFFER_PROFILE 先行必須（buffermgrdyn.cpp）

`updateBufferProfileToDb()` の冒頭で同様に `m_bufferPoolReady` を確認する。
プロファイルも pool が ready になるまで APPL_DB への書き込みをデファーする。

- evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:894`

### 3. PORT 先行必須（buffermgrdyn.cpp）

`refreshPgsForPort()` 内で `portInfo.state != PORT_READY` の場合は
`"Nothing to be done for %s since port is not ready"` を LOG_INFO して処理をスキップ。
PORT テーブルの speed / cable_length が揃うまで PG は書き込まれない。

- evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:1485-1487`

### 4. PORT 先行必須（buffermgr.cpp 静的モード）

`doSpeedUpdateTask()` は cable length が未設定の場合 `task_need_retry` を返す。
さらに PORT admin_status が未取得の場合も `task_need_retry` を返す。
PORT_QOS_MAP の `pfc_enable` が未設定の場合は BUFFER_PG の書き込みをスキップして `task_success` 返却。

- evidence: `sonic-swss/cfgmgr/buffermgr.cpp:155`, `L167`, `L175-179`

### 5. profile 解決（BufferOrch）

`BufferOrch::processPriorityGroup()` は APPL_DB 上のプロファイル参照を `resolveFieldRefValue()` で解決する。
プロファイルが APPL_DB に存在しない場合 `task_need_retry` を返し、orchagent が再試行する。

- evidence: `sonic-swss/orchagent/bufferorch.cpp:1345-1348`

### 6. SAI 順序制約（BufferOrch）

`processPriorityGroupPost()` において、PG が `m_ready_list` に存在しない（起動後の実行時追加）場合、
対象ポートが admin up であれば `SWSS_LOG_WARN("PG profile '%s' applied after port %s is up")` を発行する。
SAI 上の適用順序は「PORT up 前に BUFFER_PG を設定する」ことが要求される。

- evidence: `sonic-swss/orchagent/bufferorch.cpp:1576-1589`

## SAI call

- `sai_buffer_api->set_ingress_priority_groups_attribute()` (bulk)
  `SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE` を一括設定
- evidence: `sonic-swss/orchagent/bufferorch.cpp:1621`
