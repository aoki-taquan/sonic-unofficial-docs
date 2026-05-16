# BUFFER_PORT_INGRESS_PROFILE_LIST — Phase B 書込み順依存スキャンノート

対象テーブル: `BUFFER_PORT_INGRESS_PROFILE_LIST`
Consumer: `buffermgrd` (`BufferMgrDynamic`) / `orchagent` (`BufferOrch`)
スキャン範囲: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `sonic-swss/orchagent/bufferorch.cpp` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. BUFFER_PROFILE 先行必須（`task_need_retry` 依存）

- `BufferMgrDynamic::checkBufferProfileDirection()` (buffermgrdyn.cpp:3282-3285) は `profile_list` に指定された各プロファイル名を `m_bufferProfileLookup` で検索する。
- プロファイルが未ロードの場合、`SWSS_LOG_INFO("Profile %s doesn't exist, need retry")` を出力して `task_need_retry` を返す。
- `orchagent::processIngressBufferProfileList()` (bufferorch.cpp:1680-1688) も `resolveFieldRefArray()` でプロファイル OID を解決できない場合に `task_need_retry` を返す（`ref_resolve_status::not_resolved`）。
- **順序依存**: `BUFFER_PORT_INGRESS_PROFILE_LIST` エントリを書き込む前に、参照する `BUFFER_PROFILE` エントリが CONFIG_DB / APPL_DB に存在し、orchagent に認識されている（SAI OID 取得済み）こと。未先行の場合はキューに再投入されて silent retry になるが、ログに `need_retry` が残る。
- evidence: `buffermgrdyn.cpp:3282-3285`, `bufferorch.cpp:1683-1688`

### 2. BUFFER_POOL 先行必須（`m_bufferPoolReady` ゲート）

- `BufferMgrDynamic::handleSingleBufferPortProfileListEntry()` (buffermgrdyn.cpp:3408-3414) は `m_bufferPoolReady` が `false` の場合、APPL_DB 書き込みをスキップして `m_bufferObjectsPending = true` に設定し `task_success` を返す（silent pending）。
- `m_bufferPoolReady` は `BUFFER_POOL` テーブルの初期ロード完了時に `true` になる (buffermgrdyn.cpp:690, 818)。
- **順序依存**: `BUFFER_POOL` エントリが CONFIG_DB に存在し `buffermgrd` に認識されていない状態では、`BUFFER_PORT_INGRESS_PROFILE_LIST` の書き込みは APPL_DB に到達しない（pending 状態）。BUFFER_POOL 完了後に pending エントリが自動再処理される。
- evidence: `buffermgrdyn.cpp:3408-3414`

### 3. PORT 先行必須（ポート不在で `task_invalid_entry`）

- `orchagent::processIngressBufferProfileList()` (bufferorch.cpp:1762-1765) は `gPortsOrch->getPort(port_name, port)` でポートを検索し、存在しない場合 `task_invalid_entry` を返してエントリを消去する。
- **順序依存**: `BUFFER_PORT_INGRESS_PROFILE_LIST|<port>` を書き込む前に、対象ポートが `PORT` テーブルに存在し orchagent（PortsOrch）に認識済みであること。ポート未存在の場合は retry ではなくエントリ消去（永続エラー）になる。
- evidence: `bufferorch.cpp:1762-1765`

### 4. `packet_discard_action=trim` プロファイルの ingress 適用禁止（SAI 方向制約）

- `orchagent::processIngressBufferProfileList()` (bufferorch.cpp:1725-1731) は参照プロファイルの `isTrimmingEligible` が `true` の場合、`task_failed` を返す。
- SAI 仕様上、ingress side でのパケットトリミング (`packet_discard_action=trim`) は禁止されており、このチェックはハードコードされている。
- **制約**: `packet_discard_action=trim` を持つ `BUFFER_PROFILE` は `BUFFER_PORT_INGRESS_PROFILE_LIST` には設定不可。`BUFFER_PORT_EGRESS_PROFILE_LIST` にのみ使用可。
- evidence: `bufferorch.cpp:1725-1731`

### 5. SAI 方向制約（egress プロファイルを ingress list に混在禁止）

- `BufferMgrDynamic::checkBufferProfileDirection()` (buffermgrdyn.cpp:3289-3296) は各プロファイルの `direction` フィールドと期待方向 (`BUFFER_INGRESS`) を比較する。
- 不一致の場合、`SWSS_LOG_ERROR("Profile direction mismatch")` を出力して `task_failed` を返す。
- **制約**: `direction=egress` の `BUFFER_PROFILE` を `profile_list` に指定すると即座に `task_failed` となりエントリが消去される。
- evidence: `buffermgrdyn.cpp:3289-3296`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 違反時の挙動 |
|---|----------|------|------------|
| 1 | `BUFFER_PROFILE` エントリが先行 | 先行必須 | `task_need_retry`（silent retry、ログに残る） |
| 2 | `BUFFER_POOL` エントリが先行 | 先行必須 | APPL_DB 書き込み pending（silent）、BUFFER_POOL 完了後自動再処理 |
| 3 | `PORT` エントリが先行 | 先行必須 | `task_invalid_entry`（エントリ消去、永続エラー） |
| 4 | `packet_discard_action=trim` プロファイル禁止 | ハードコード禁止 | `task_failed`（エントリ消去） |
| 5 | egress 方向プロファイルを ingress list に設定禁止 | ハードコード禁止 | `task_failed`（エントリ消去） |
