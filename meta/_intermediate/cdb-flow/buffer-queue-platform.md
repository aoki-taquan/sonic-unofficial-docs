# BUFFER_QUEUE — Phase H プラットフォーム差異 中間調査ファイル

生成日: 2026-05-16  
対象ページ: `docs/reference/config-db/buffer-queue.md`  
調査ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`

---

## 1. Dynamic / Static バッファモデル — BUFFER_QUEUE への影響

`buffermgrdyn.cpp` (Dynamic モード専用デーモン) は `BUFFER_QUEUE` テーブルをハンドルするが、
BUFFER_PG と異なり egress キューのヘッドルーム自動計算は行わない。
キューのプロファイル割り当て自体はビルド時テンプレートで決定済みであり、
`buffermgrdyn` は受け取った `profile` フィールドをそのまま APPL_DB に転送する。

### Dynamic モード固有処理 — zero profile (buffermgrdyn.cpp:285-289)

```cpp
else if (fvField(fv) == "queues_to_apply_zero_profile")
{
    m_bufferObjectIdsToZero[BUFFER_QUEUE] = fvValue(fv);
}
else if (fvField(fv) == "egress_zero_profile")
{
    m_bufferZeroProfileName[BUFFER_QUEUE] = fvValue(fv);
}
```

- ベンダー提供の JSON (per-platform zero profiles info) に `queues_to_apply_zero_profile` が定義されている場合のみ有効
- Admin-down ポートまたはバッファ回収時に、指定された queue インデックスに zero profile を適用する
- Static モードデーモン (`buffermgr`) はこの処理を持たない

---

## 2. ASIC ベンダー差異 — `ASIC_VENDOR` 環境変数

### buffermgrdyn.cpp (L68-102)

```cpp
string platform = getenv("ASIC_VENDOR") ? getenv("ASIC_VENDOR") : "";
m_platform = platform;  // e.g. "mellanox", "broadcom", ""

if (m_platform == "mellanox") {
    m_cfgDeviceMetaDataTable.hget("localhost", "platform", m_specific_platform);
    // "sn" 位置でモデル番号 4 桁を抽出
    m_model_number = atoi(model_number.c_str());  // e.g. 4600, 5600
}
```

`BUFFER_QUEUE` のプロファイル名はビルド時テンプレートで決定されるため、
`buffermgrdyn` ランタイムでの ASIC vendor 依存処理は BUFFER_QUEUE に直接影響しない。
(BUFFER_PG のヘッドルーム計算で使われる `_8lane` サフィックス等は BUFFER_QUEUE には適用されない。)

### Lua プラグイン (ベンダー別)

`buffer_headroom_<vendor>.lua` / `buffer_pool_<vendor>.lua` はベンダー別に提供されるが、
これらは BUFFER_PG / BUFFER_POOL の計算専用であり BUFFER_QUEUE の値には影響しない。

---

## 3. VOQ Chassis 専用処理

### 3-1. 初期化ゲート — `isInitDone` vs `isConfigDone` (bufferorch.cpp:2079-2090)

```cpp
if (gMySwitchType == "voq")
{
    // VOQ: PortsOrch の初期化完了 (isInitDone) を待つ
    if(!gPortsOrch->isInitDone()) return;
}
else
{
    // 通常: config 完了 (isConfigDone) を待つ
    if (!gPortsOrch->isConfigDone()) return;
}
```

VOQ シャーシは通常の `isConfigDone` ではなく `isInitDone` を待機ゲートとして使用する。

### 3-2. Warm Reboot Ready List 分岐 (bufferorch.cpp:116-136)

```cpp
if (gMySwitchType == "voq")
{
    initVoqBufferReadyList(queue_table, false);  // VOQ 専用 ready list
}
else
{
    initBufferReadyList(queue_table, false);     // 通常 ready list
}
```

VOQ は `initVoqBufferReadyList()` を使用。通常の `initBufferReadyList()` とは異なるロジックで
queue buffer の ready 状態を管理する。

### 3-3. Key パース — 4 トークン vs 2 トークン (bufferorch.cpp:916-956)

```cpp
if (gMySwitchType == "voq")
{
    if (tokens.size() != 4)  // hostname|asic_name|port|qindex
    {
        return task_process_status::task_invalid_entry;
    }
    // tokens[0]=hostname, tokens[1]=asic_name, tokens[2]=port, tokens[3]=qindex
    // gMyHostName + gMyAsicName と比較してローカルポート判定
    local_port = (tokens[0] == gMyHostName) && (tmp_token_1 == tmp_gMyAsicName);
    local_port_name = tokens[2];
}
else
{
    if (tokens.size() != 2)  // port|qindex
    {
        return task_process_status::task_invalid_entry;
    }
}
```

VOQ では key に `<hostname>|<asic_name>` が付加されるため 4 トークン必須。
`gMyHostName` / `gMyAsicName` との照合によりリモートシャーシ上のポートかローカルかを判定する。

### 3-4. Queue ID 取得 — VOQ ID vs 通常 Queue ID (bufferorch.cpp:1049-1075)

```cpp
if (gMySwitchType == "voq")
{
    // getPortVoQIds() で VOQ 専用の queue_id を取得
    std::vector<sai_object_id_t> queue_ids = gPortsOrch->getPortVoQIds(port);
    if (queue_ids.size() <= ind)
    {
        SWSS_LOG_ERROR("Invalid voq index specified:%zd", ind);
        return task_process_status::task_invalid_entry;
    }
    queue_id = queue_ids[ind];
}
else
{
    // 通常ポートの m_queue_ids から取得
    if (port.m_queue_ids.size() <= ind)
    {
        return task_process_status::task_invalid_entry;
    }
    if (port.m_queue_lock[ind])
    {
        // ロック中は retry + partiallyApplied
        m_partiallyAppliedQueues.insert(key);
        return task_process_status::task_need_retry;
    }
    queue_id = port.m_queue_ids[ind];
}
```

VOQ では `getPortVoQIds()` で Virtual Output Queue の SAI object ID を取得。
通常モードの queue lock チェック (`port.m_queue_lock[ind]`) は VOQ では不要なためスキップ。

### 3-5. Flex Counter 管理 — VOQ 専用スキップ (bufferorch.cpp:1134-1136)

```cpp
// For VOQ chassis, flexcounterorch adds the Queue Counters for all egress and VOQ queues
// of all front panel and system ports to the FLEX_COUNTER_DB irrespective of BUFFER_QUEUE
// configuration. So Port Queue counter needs to be updated only for non VOQ switch.
else if (gMySwitchType != "voq")
{
    // flex counter の追加/削除処理
}
```

VOQ では `flexcounterorch` がシステムポートの全 VOQ を一括登録するため、
`BufferOrch` 内での per-queue flex counter 管理は不要。

### 3-6. ポート参照カウント — VOQ スキップ (bufferorch.cpp:1166-1168)

```cpp
// for voq switches the buffer configuration is applied on the VOQ which is applicable
// on the system ports. System ports are not dynamically created/deleted so no need
// to maintain ref counter.
if (gMySwitchType != "voq")
{
    if (op == SET_COMMAND)   { gPortsOrch->increasePortRefCount(port_name); }
    else if (op == DEL_COMMAND) { gPortsOrch->decreasePortRefCount(port_name); }
}
```

VOQ シャーシのシステムポートは動的に生成・削除されないため、参照カウント管理が不要。

---

## 4. ASIC queue 数差異

YANG の qindex 正規表現は 0〜15 を許容するが、実際の上限は ASIC が SAI 初期化時に通知する queue 数次第。

- 非 VOQ: `port.m_queue_ids.size() <= ind` → `task_invalid_entry` (`bufferorch.cpp:1061-1064`)
- VOQ: `getPortVoQIds(port).size() <= ind` → `task_invalid_entry` (`bufferorch.cpp:1052-1055`)

プラットフォームごとに 8 / 16 / それ以外の queue 数がありうる。YANG 上の 0-15 制約はソフトウェア側の上限であり、ASIC ベンダーごとに実際の上限が異なる。

---

## 5. Flex Counter — `isCreateOnlyConfigDbBuffers()` 条件 (非 VOQ のみ)

`bufferorch.cpp:1139-1152`:

```cpp
// non-VOQ のみ
auto flexCounterOrch = gDirectory.get<FlexCounterOrch*>();
if (flexCounterOrch->isCreateOnlyConfigDbBuffers())
{
    if (!queueContext.counter_was_added && queueContext.counter_needs_to_add && ...)
        gPortsOrch->createPortBufferQueueCounters(port, queues);
    else if (queueContext.counter_was_added && !queueContext.counter_needs_to_add && ...)
        gPortsOrch->removePortBufferQueueCounters(port, queues);
}
```

- `isCreateOnlyConfigDbBuffers() == true`: CONFIG_DB ベースのバッファ設定があるときのみ FlexCounter counter を作成するモード。`BufferOrch` が per-queue に counter を追加・削除する。
- `isCreateOnlyConfigDbBuffers() == false`: 従来モード（`FlexCounterOrch` が一括管理）。`BufferOrch` からは操作しない。
- VOQ シャーシではこのブロック全体をスキップ（`flexcounterorch` が system port 全体の VOQ counter を管理）。

---

## 6. VOQ — ローカルポート判定とリモートエントリスキップ

`bufferorch.cpp:916-940`:

```cpp
if (gMySwitchType == "voq")
{
    // tokens[0]=hostname, tokens[1]=asic_name, tokens[2]=port, tokens[3]=qindex
    local_port = (tokens[0] == gMyHostName) && (tmp_token_1 == tmp_gMyAsicName);
    // local_port == false のとき SAI 書き込みをスキップ（リモートシャーシのエントリ）
}
```

VOQ シャーシでは複数ラインカードの BUFFER_QUEUE エントリが CONFIG_DB に混在する。
自ノードの `gMyHostName` と `gMyAsicName` が一致しないエントリは SAI に書き込まず `task_success` を返す。

---

## スキャン証跡

| ファイル | 行 | 確認内容 |
|---------|-----|---------|
| `buffermgrdyn.cpp` | L68-102 | `ASIC_VENDOR` 取得、Mellanox モデル番号抽出 |
| `buffermgrdyn.cpp` | L285-289 | BUFFER_QUEUE 用 zero profile 設定読み取り |
| `buffermgrdyn.cpp` | L1286-1381 | `reclaimReservedBufferForPort` — admin-down 時 zero profile 2 モード |
| `buffermgrdyn.cpp` | L3784-3786 | port 削除時 zero profile cleanup |
| `bufferorch.cpp` | L116-136 | VOQ warm reboot — `initVoqBufferReadyList` 分岐 |
| `bufferorch.cpp` | L916-940 | VOQ key 4-トークンパース、ローカルポート判定・リモートスキップ |
| `bufferorch.cpp` | L1049-1075 | VOQ `getPortVoQIds()` vs 通常 `m_queue_ids`、lock チェックスキップ |
| `bufferorch.cpp` | L1052-1064 | ASIC queue 数チェック（VOQ/非 VOQ）|
| `bufferorch.cpp` | L1134-1136 | VOQ flex counter 管理スキップ |
| `bufferorch.cpp` | L1139-1152 | 非 VOQ: `isCreateOnlyConfigDbBuffers()` 条件付き counter 追加・削除 |
| `bufferorch.cpp` | L1166-1168 | VOQ 参照カウントスキップ |
| `bufferorch.cpp` | L2079-2090 | VOQ `isInitDone()` ゲート |
