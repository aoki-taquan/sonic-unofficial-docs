# Phase A — BUFFER_PORT_EGRESS_PROFILE_LIST 暗黙デフォルト調査

生成日: 2026-05-14  
対象ページ: `docs/reference/config-db/buffer-port-egress-profile-list.md`

## フィールド列挙

YANG (`sonic-buffer-port-egress-profile-list.yang`) が定義するフィールド:

| フィールド | YANG 型 | YANG default |
|-----------|---------|-------------|
| `port` (key) | leafref → PORT.name | なし |
| `profile_list` | leaf-list of leafref → BUFFER_PROFILE.name (ordered-by user) | なし (YANG default 無し) |

## 暗黙デフォルト・挙動詳細

### 1. `profile_list` — YANG default なし、実装上の fallback なし

- YANG に `default` 文なし。
- `buffermgrdyn.cpp` の `handleSingleBufferPortProfileListEntry` は `profile_list` フィールドが存在しない場合、何も `profileListLookup[port]` に書かず APPL_DB への書き込みも行わない（フィールドが来ない限り何もしない）。
- 空リストの送付: DEL 操作時に `orchagent` が `attr.value.objlist.count = 0` を SAI に送る（空リストが実行時 fallback）。
- **evidence**: `bufferorch.cpp:1939-1940`

### 2. admin-down ポートへの implicit zero-profile 差し替え（書き込み経路依存乖離）

- Dynamic buffer model のみの挙動。
- SET コマンドを受けた時点でポートが `PORT_ADMIN_DOWN` 状態の場合、`buffermgrdyn.cpp` は実際の `profile_list` 値を APPL_DB に書かず、代わりにゼロプロファイルリスト（`constructZeroProfileListFromNormalProfileList` が生成）を書き込む。
- つまり CONFIG_DB に書いた値と APPL_DB に実際に流れる値が乖離する。
- ポートが admin-up に戻ると `updateBufferObjectListToDb` で本来の profile_list が再適用される。
- **evidence**: `buffermgrdyn.cpp:3418-3438`

### 3. buffer pool 未準備時の pending (silent fallback)

- Dynamic buffer model で `m_bufferPoolReady == false` の時、SET コマンドを受けても `m_bufferObjectsPending = true` を立てて APPL_DB には何も書かない。`task_success` を返すためリトライキューにも入らず、pool ready 後の一括処理に委ねられる。
- **evidence**: `buffermgrdyn.cpp:3408-3415`

### 4. direction mismatch → task_failed (書き込み経路: dynamic model のみ)

- Dynamic buffer model の `buffermgrdyn.cpp:checkBufferProfileDirection` が `profile_list` 内の各プロファイルの `direction` を検証する。ingress 方向のプロファイルを egress profile list に指定すると `SWSS_LOG_ERROR("Profile %s's direction is %s but %s is expected")` → `task_failed`。
- 静的 buffer model (`buffermgr.cpp`) にはこの検証がなく、CONFIG_DB 値をそのまま APPL_DB にコピーする。
- **書き込み経路依存乖離**: Static model は direction 検証なし、Dynamic model は検証あり。
- **evidence**: `buffermgrdyn.cpp:3275-3299`

### 5. profile 未登録時の挙動差（dynamic vs static）

- Dynamic model (`buffermgrdyn.cpp`): `m_bufferProfileLookup` に未登録 → `task_need_retry`（プロファイル到着後に再処理）。
- Static model (`buffermgr.cpp`): 検証なし。CONFIG_DB 値をそのまま APPL_DB にコピー。APPL_DB→SAI 処理は `orchagent` 側で `ref_resolve_status::not_resolved` → `task_need_retry`。
- **書き込み経路依存乖離**: Dynamic model は mgr 段で retry、Static model は orch 段で retry。

### 6. 不明フィールドの silent drop

- `buffermgrdyn.cpp:handleSingleBufferPortProfileListEntry` で `fvField(i) != buffer_profile_list_field_name` の場合 `SWSS_LOG_ERROR("Unknown field %s in %s")` を出力して `continue`（silent drop）。
- 単一の認識フィールドは `profile_list` のみ。それ以外のフィールドを CONFIG_DB に書いても無視される。
- **evidence**: `buffermgrdyn.cpp:3401-3405`

### 7. trimming-eligible プロファイルの egress 禁止（orchagent 段 task_failed）

- `bufferorch.cpp:processEgressBufferProfileList` が `profCfg.isTrimmingEligible == true` を検出した場合 `task_failed` を返す。
- 対応する ingress (`processIngressBufferProfileList`) にも同様の禁止があるが、egress 専用チェック。
- **dead field**: このテーブル自体に enum フィールドはなく、チェック対象は参照する BUFFER_PROFILE の `packet_discard_action`。
- **evidence**: `bufferorch.cpp:1907-1921`

### 8. 複数ポートキー → 個別処理分割（複合制約）

- CONFIG_DB のキーにカンマ区切りポートリスト（例 `Ethernet0,Ethernet4`）が指定された場合、`handleBufferObjectTables` がポートごとに分解して `handleSingleBufferPortEgressProfileListEntry` を呼び出す。
- `keyWithIds=false`（BUFFER_PG/BUFFER_QUEUE と異なりインデックス部分がない）。
- 途中でどれかが `task_need_retry` を返すと即時 return し、残りポートは未処理になる（partial failure）。
- **evidence**: `buffermgrdyn.cpp:3532-3548`

### 9. Static model での DEL: エントリを APPL_DB から削除

- Static model (`buffermgr.cpp:doBufferTableTask`): DEL コマンドで即座に `applTable.del(key)`。
- Dynamic model (`buffermgrdyn.cpp:handleSingleBufferPortProfileListEntry`): DEL で `profileListLookup.erase(port)` + `appTable.del(key)`。コードコメントに "Not supported on Mellanox platform for now." とある（プラットフォーム依存の制約示唆）。
- **evidence**: `buffermgrdyn.cpp:3441-3446`

### 10. Static model での dynamic_buffer_model guard

- `buffermgr.cpp:doTask` が `dynamic_buffer_model == true` の場合は全テーブル処理をスキップし `SWSS_LOG_DEBUG("Dynamic buffer model enabled. Skipping further processing")` を出力する。
- つまり `DEVICE_METADATA.buffer_model == "dynamic"` の環境では `buffermgr` は BUFFER_PORT_EGRESS_PROFILE_LIST を一切処理しない（BufferMgrDynamic が担当）。
- **evidence**: `buffermgr.cpp:476-480`

### 11. Bulk SAI 呼び出し（orchagent 段）

- `bufferorch.cpp:processEgressBufferProfileListBulk` が bulk SET/DEL を一括で `sai_port_api->set_ports_attribute(SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR, ...)` に送る。
- `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` モードのため、一部ポートの SAI 失敗が他ポートをブロックしない。失敗した場合は `processEgressBufferProfileListPost` でポートごとにエラーログ + SAI ステータスハンドリング。
- **evidence**: `bufferorch.cpp:2009-2014`

## YANG vs 実装 discrepancy

| 項目 | YANG | 実装 |
|------|------|------|
| `profile_list` ordered-by | `ordered-by user` | SAI には `objlist` として順序付きで渡される。順序保持は実装側で保証 |
| direction 制約 | YANG に記述なし | dynamic model 実装で profile direction が egress でないと `task_failed` |
| trimming 制約 | YANG に記述なし | orchagent 実装で trimming-eligible profile を egress list に設定すると `task_failed` |

## まとめ（検出した暗黙挙動）

1. **admin-down silent substitution**: ポートが admin-down の場合、CONFIG_DB 値でなくゼロプロファイルリストが APPL_DB に書き込まれる（dynamic model のみ）
2. **buffer pool 未準備 pending**: pool ready 前の SET は APPL_DB に反映されず pending 状態になる（silent fallback）
3. **direction mismatch task_failed**: ingress profile を egress list に指定すると失敗（dynamic model のみ）
4. **unknown field silent drop**: `profile_list` 以外のフィールドは SWSS_LOG_ERROR + continue で無視
5. **trimming-eligible task_failed**: trim profile を egress list に指定すると orchagent が task_failed
6. **複数ポートキー partial failure**: カンマ区切りポートリスト中で retry が発生すると残ポート未処理
7. **Mellanox DEL 制約**: DEL は "Not supported on Mellanox platform for now" コメントあり
8. **Bulk SAI IGNORE_ERROR**: 複数ポート処理で一部失敗が他をブロックしない
