# buffer-profile — Task F Phase B 書込順依存スキャンノート

中間ファイル。詳細は `docs/reference/config-db/buffer-profile.md` の `<!-- ordering -->` ブロックを参照。

## 検出した順序依存

### 1. BUFFER_POOL 先行必須（buffermgrdyn.cpp — 動的バッファモデル）

`updateBufferProfileToDb()` の冒頭（L892-896）で `m_bufferPoolReady` フラグを確認する。
`m_bufferPoolReady == false` の場合、APPL_DB への書き込みを行わず `m_bufferObjectsPending = true` をセットして即座にリターンする。

```
// buffermgrdyn.cpp:892-896
if (!m_bufferPoolReady)
{
    SWSS_LOG_NOTICE("Buffer pools are not ready when configuring buffer profile %s, pending", name.c_str());
    m_bufferObjectsPending = true;
    return;
}
```

- evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:892-896`

### 2. BUFFER_POOL 内部 lookup 先行必須（buffermgrdyn.cpp — handleBufferProfileTable）

`handleBufferProfileTable()` は `m_bufferPoolLookup` でプール名を解決する（L2705-2715）。
プールが未登録の場合、`task_need_retry` を返してエントリ処理を延期する。

```
// buffermgrdyn.cpp:2705-2715
auto poolRef = m_bufferPoolLookup.find(poolName);
if (poolRef == m_bufferPoolLookup.end())
{
    SWSS_LOG_INFO("Pool %s hasn't been configured yet, need retry", poolName.c_str());
    ...
    return task_process_status::task_need_retry;
}
```

- evidence: `sonic-swss/cfgmgr/buffermgrdyn.cpp:2705-2715`

### 3. BUFFER_POOL 先行必須（orchagent bufferorch.cpp — processBufferProfile）

`processBufferProfile()` は `resolveFieldRefValue()` で `pool` フィールドの参照を解決する（L641-651）。
プールが APPL_DB に未登録の場合、`ref_resolve_status::not_resolved` → `task_need_retry` を返す。

```
// bufferorch.cpp:641-651
ref_resolve_status resolve_result = resolveFieldRefValue(m_buffer_type_maps, buffer_pool_field_name, ...);
if (ref_resolve_status::success != resolve_result)
{
    if(ref_resolve_status::not_resolved == resolve_result)
    {
        SWSS_LOG_INFO("Missing or invalid pool reference specified");
        return task_process_status::task_need_retry;
    }
    ...
}
```

- evidence: `sonic-swss/orchagent/bufferorch.cpp:641-651`

### 4. SAI create-only 制約 — pool と threshold_mode は変更不可

一度 SAI buffer profile を生成した後、`pool`（`SAI_BUFFER_PROFILE_ATTR_POOL_ID`）および
`threshold_mode`（`SAI_BUFFER_POOL_THRESHOLD_MODE_DYNAMIC`/`_STATIC`）は SAI create-only 属性のため変更不可。
`processBufferProfile()` は既存オブジェクトに対するこれらの SET をサイレントにスキップする。

- `pool` のスキップ: `bufferorch.cpp:654-659`
- `threshold_mode` のスキップ: `bufferorch.cpp:692-706` (dynamic_th), `710-724` (static_th)

操作上の意味: BUFFER_POOL への変更（pool 差し替え）は SAI レベルでは反映されない。
既存プロファイルを削除して再作成する必要がある。

### 5. Lua plugin 実行順序（動的バッファモデルのみ）

Lua plugin は 3 種類あり、実行順序に依存関係がある。

1. `buffer_pool_<vendor>.lua` — BUFFER_POOL のサイズを計算して APPL_DB に書き込む。
   実行後 `m_bufferPoolReady = true` がセットされる。
   MMU サイズ（`STATE_DB.BUFFER_MAX_PARAM_TABLE.global.mmu_size`）未到着時は暫定値 0 を返す。
   - evidence: `buffermgrdyn.cpp:667-819`

2. `buffer_headroom_<vendor>.lua` — BUFFER_PROFILE の `size`, `xon`, `xoff`, `xon_offset` を
   ポート速度・ケーブル長・MTU・レーン数から計算する。`m_bufferPoolReady == true` 後に実行。
   - evidence: `buffermgrdyn.cpp:605-625, 989-1001`

3. `buffer_check_headroom_<vendor>.lua` — per-port 累積 headroom の上限チェック。
   headroom 超過時は `task_failed` + `releaseProfile()` でロールバック。
   - evidence: `buffermgrdyn.cpp:1541-1546`

### 6. handlePendingBufferObjects — 一括適用フロー

`m_bufferPoolReady == true` になった時点で `handlePendingBufferObjects()` が呼び出され、
pending 状態のすべての BUFFER_PROFILE / PG / Queue / profile list を APPL_DB に一括適用する。

```
// buffermgrdyn.cpp:3644-3661 (概略)
void BufferMgrDynamic::handlePendingBufferObjects()
{
    if (m_bufferPoolReady && !m_defaultThreshold.empty())
    {
        if (m_bufferObjectsPending)
        {
            for (auto &profile : m_bufferProfileLookup)
                updateBufferProfileToDb(profile.first, profile.second);
            // ... PG / Queue / profile list も一括適用
            m_bufferObjectsPending = false;
        }
    }
}
```

- evidence: `buffermgrdyn.cpp:3613-3690`

### 7. zero profile 適用順序

zero buffer pool と zero buffer profile はポートの admin-down 時に未使用バッファを回収するために使用される。
JSON ファイル（per-platform）内の順序通りに APPL_DB へ書き込まれる。

依存関係:
- zero pool が先に APPL_DB に存在しないと、zero profile の SAI 生成が失敗する（pool 参照解決失敗）
- ベンダーの責任として JSON ファイル内の順序が依存関係を反映していることを保証する

削除時の逆順:
- zero profile を先に APPL_DB から削除（`m_applBufferProfileTable.del()`）
- その後 zero pool を削除（`m_applBufferPoolTable.del()`）

タイミング:
- cold/fast reboot: `m_bufferPoolReady` 後に 30 秒デファー（`m_waitApplyAdditionalZeroProfiles = 3`、ポーリング単位 10 秒）
- warm reboot: 即時適用（`m_waitApplyAdditionalZeroProfiles = 0`）

- evidence: `buffermgrdyn.cpp:236-239, 156-169, 408-431, 2444-2447`

## 順序依存サマリ

```
BUFFER_POOL（APPL_DB 登録完了）
  ↓ m_bufferPoolReady = true
buffer_pool_<vendor>.lua 実行
  ↓ pool サイズ確定
BUFFER_PROFILE（APPL_DB 転送解禁）
  ↓ handlePendingBufferObjects()
buffer_headroom_<vendor>.lua 実行
  ↓ size/xon/xoff 確定
BUFFER_PG / BUFFER_QUEUE / profile list（APPL_DB 転送）
  ↓ orchagent processBufferProfile()
SAI sai_create_buffer_profile()
  ↓ SAI オブジェクト生成（pool/threshold_mode は create-only で変更不可）
SAI sai_create_ingress_priority_group_attribute() / sai_set_queue_attribute()
```

## SAI call

- `sai_buffer_api->create_buffer_profile(&sai_object, ...)` — 初回作成
- `sai_buffer_api->set_buffer_profile_attribute(...)` — 更新（pool/threshold_mode はスキップ）
- `sai_buffer_api->remove_buffer_profile(...)` — 削除（参照中は `m_pendingRemove` で保留）

evidence: `sonic-swss/orchagent/bufferorch.cpp:802, 767-791, 862`
