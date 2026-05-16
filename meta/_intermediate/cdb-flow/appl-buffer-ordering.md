# APPL_DB BUFFER_* — Phase B 書込み順依存スキャンノート

対象テーブル: `BUFFER_POOL_TABLE` / `BUFFER_PROFILE_TABLE` / `BUFFER_PG_TABLE` / `BUFFER_QUEUE_TABLE` / `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE` / `BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE`
Consumer: `BufferOrch::doTask()` / `BufferOrch::doTask(Consumer&)` (`sonic-swss/orchagent/bufferorch.cpp`)
スキャン範囲: L33-260, L391-1500, L2040-2138 精読
ref: `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 検出した順序依存・タイミング依存

### 1. PortsOrch readiness ガード（ポート初期化先行必須）

- `doTask(Consumer&)` L2079-2091: 全 BUFFER_* テーブルの処理が PortsOrch の初期化フラグに対するガードで一括ブロックされる。
  - VOQ 経路 (`gMySwitchType == "voq"`, L2079): `gPortsOrch->isInitDone()` が false なら return。
  - non-VOQ 経路 (L2087): `gPortsOrch->isConfigDone()` が false なら return。
- 違いは VOQ chassis で `system port` が PortsOrch の`init`フェーズに揃う設計に合わせるため。`isConfigDone()` は PORT_CONFIG_DONE 受信後、`isInitDone()` はさらに後段の PORT_INIT_DONE 相当。
- ガード中、`consumer.m_toSync` は erase されず次回 doTask まで保留される（無限再ディスパッチ）。
- 順序依存: **PortsOrch の `isConfigDone()` (VOQ では `isInitDone()`) 完了が BUFFER_* 全テーブルより先**。
- evidence: `bufferorch.cpp:2079-2091`

### 2. BUFFER_POOL → BUFFER_PROFILE → (BUFFER_PG / BUFFER_QUEUE / PORT_*_PROFILE_LIST) の階層依存

`doTask()` (no-arg, L2040-2073) は次の固定順で consumer を `drain()` する:

1. `APP_BUFFER_POOL_TABLE_NAME` の consumer を `drain()` (L2057-2058)
2. `APP_BUFFER_PROFILE_TABLE_NAME` の consumer を `drain()` (L2060-2061)
3. 残り全 consumer (`BUFFER_QUEUE_TABLE` / `BUFFER_PG_TABLE` / `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE` / `BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE`) を順不同で `drain()` (L2063-2071)

この順序は SAI の隠れた依存ツリー（L2042-2053 コメント引用）:

```
buffer pool
└── buffer profile
    ├── buffer port ingress profile list
    ├── buffer port egress profile list
    ├── buffer queue
    └── buffer pq table
```

に対応する。順序を破ると下記の retry が走る（task は erase されず保留される）:

- `processBufferProfile()` (L602-888): `pool` 参照が `not_resolved` → `task_need_retry`（pool 未登録のため）
- `processQueue()` / `processPriorityGroup()`: `profile` 参照 `not_resolved` → `task_need_retry`
- `processIngressBufferProfileList()` / `processEgressBufferProfileList()`: list 内のいずれかの profile が `not_resolved` → `task_need_retry`

順序依存: **Pool → Profile → (PG / Queue / ProfileList) の orchagent 内処理順**は `doTask()` で保証されるが、外部から WRITE する順序が逆でも最終的には `task_need_retry` でループ収束する（書込側の順序契約ではなく、収束保証）。
evidence: `bufferorch.cpp:2040-2073`, retry 条件は `bufferorch.cpp:391-888`, `914-1495`

### 3. DEL の逆順依存（参照されている pool / profile は消せない）

- `processBufferPool()` DEL (L562-585): 当該 pool が profile から参照中なら `task_need_retry`（`object_reference_map` の参照カウントで判定）。
- `processBufferProfile()` DEL (L860-878): 当該 profile が PG / Queue / ProfileList から参照中なら `task_need_retry`。
- 順序依存: **削除は SET の逆順** — まず PG/Queue/ProfileList を消し、次に profile、最後に pool。逆順違反は `task_need_retry` で永遠に保留される（消費側が消えるまでループ）。
- evidence: `bufferorch.cpp:562-585, 860-878`

### 4. m_ready_list（ポートごとの buffer readiness）

- ctor (`bufferorch.cpp:86-143`, `initBufferReadyLists`) で CONFIG_DB（cold/fast start）または APPL_DB（warm reboot）の `BUFFER_PG` / `BUFFER_QUEUE` キーを走査し、ポート毎に `m_port_ready_list_ref[port_name]` に未処理 PG/Queue を登録し `m_ready_list[appldb_key] = false` で初期化。
- `processPriorityGroup()` / `processQueue()` の SAI bind 成功後、`m_ready_list[appldb_key] = true` に更新（同時に PortsOrch にも buffer-ready を通知）。
- `isPortReady(port_name)` (L254-275): 当該ポートの全 PG/Queue がいずれも true になった時点で `true` を返す。
- PortsOrch は `isPortReady()` を見て後段のポート初期化（`SAI_PORT_ATTR_ADMIN_STATE` 等）を進める。
- 順序依存: **BUFFER_PG / BUFFER_QUEUE の SAI bind 完了が、後段のポート初期化トリガ**。dynamic buffer model の admin down ポートは buffermgr からの明示削除通知で `m_ready_list` 経由で ready 扱いになる（L97-98 コメント）。
- evidence: `bufferorch.cpp:86-208, 254-275`

### 5. warm reboot の初期 ready 充填

- `WarmStart::isWarmStart()` (L111) が true のとき、`initBufferReadyList(applDb, …)` で APPL_DB 側のキーから初期化する（admin down ポートぶんは APPL_DB に書かれていない前提で ready 扱いにできる、L100-107 コメント）。
- 非 warm 起動時は CONFIG_DB 側を見て、admin down ポートぶんも `m_port_ready_list_ref` に積まれる。
- 順序依存: warm reboot 後の orchagent 起動時、buffermgrd は orchagent より**後**に起動するため、admin down ポート向けの削除通知は不要（既に APPL_DB スナップショットが完成している）。
- evidence: `bufferorch.cpp:100-107, 111-126`

### 6. flex counter group 初期化のタイミング

- ctor (`BufferOrch::BufferOrch`, L33-83) で:
  - `initFlexCounterGroupTable()` (L232-252) → FLEX_COUNTER_DB に group / Lua sha 登録（起動時 1 回）
  - `initBufferConstants()` (L210-230) → STATE_DB に MMU 総量公開（起動時 1 回、`gMySwitchType == "dpu"` ではスキップ L64）
- `generateBufferPoolWatermarkCounterIdList()` (L286-362) は FlexCounterOrch が `FLEX_COUNTER_STATUS=enable` を受信したときに呼ばれる遅延初期化。`m_isBufferPoolWatermarkCounterIdListGenerated` フラグで多重実行をガード。
- 順序依存: **BUFFER_POOL の SAI create が `generateBufferPoolWatermarkCounterIdList()` より先**であれば watermark counter は登録される。逆（pool 未登録で flex counter enable）でも、後続の `processBufferPool()` SET 経路では個別の `startFlexCounterPolling()` は呼ばれない（生成は `generateBufferPoolWatermarkCounterIdList()` の一括処理に閉じる）→ flex counter group enable 後に pool を作った場合の watermark 登録は再度 enable イベントが必要。
- evidence: `bufferorch.cpp:33-83, 232-252, 286-362`

### 7. processBufferProfile の 2 段 retry（同一 doTask 内）

- L778-797: `sai_set_buffer_profile_attribute()` 初回失敗時、bufferorch が同一 doTask 内で**もう一度同じ SAI 呼出を即時 retry**。これは `task_need_retry`（次回 doTask 待ち）とは別経路。
- 順序依存ではないが、SAI ベンダ実装の transient エラー（DMA タイミング等）を吸収するための即時 retry である点に注意。`processBufferPool()` 側にはこの即時 retry はない。
- evidence: `bufferorch.cpp:778-797`

### 8. profile_list bulk flush の発火順

- `BufferOrch::doTask(Consumer&)` 末尾 L2132-2135: `m_bufferFlushHandlerMap` 登録テーブル（`BUFFER_PORT_INGRESS_PROFILE_LIST` / `BUFFER_PORT_EGRESS_PROFILE_LIST` / `BUFFER_PG` / `BUFFER_QUEUE`）は per-entry 処理後にまとめて bulk flush handler を呼ぶ。
- bulk handler 内で `sai_port_api->set_ports_attribute()` を bulk 一発で叩く (L1956-2014)。retry は post 処理で `consumer.m_toSync.emplace()` し直す（L2027-2034）。
- 順序依存: per-entry 処理（参照解決）完了後に bulk flush。Profile 未登録の entry は bulk に積まれず保留される。
- evidence: `bufferorch.cpp:2132-2135, 1956-2034`

---

## まとめ: 外部書込側が守るべき順序

| 順序 | 操作 | 違反時 |
|---|---|---|
| 1 | PortsOrch `isConfigDone()` (VOQ では `isInitDone()`) 完了を待つ | `doTask` 全体が return、`m_toSync` に保留され続ける |
| 2 | `BUFFER_POOL_TABLE` SET → `BUFFER_PROFILE_TABLE` SET → `BUFFER_PG`/`BUFFER_QUEUE`/`PROFILE_LIST` SET | 個別 handler が `task_need_retry`、最終的には収束するが retry log が出る |
| 3 | DEL は SET の逆順: PG/Queue/ProfileList → Profile → Pool | 参照中の pool/profile は `task_need_retry` で永続保留 |

orchagent 内では `BufferOrch::doTask()`（no-arg）が pool → profile → 残り の順で `drain()` するため、同一イベントループ内なら順序は自動矯正される。

## grep カバレッジ

- `gPortsOrch->isConfigDone` / `isInitDone` / `flushCounters`: 各 1 hit / 1 hit / 2 hit (L2072, L2087, L2081)
- `m_ready_list` / `m_port_ready_list_ref`: 16 hit / 7 hit （全て精読済み）
- `task_need_retry`: 12 hit （ordering 起因のものは pool/profile/PG/Queue/profile-list 全 handler で確認）
- `drain()` (consumer): 3 hit (L2058, L2061, L2070) — doTask() の固定順
- `WarmStart::isWarmStart`: 1 hit (L111)
- `m_isBufferPoolWatermarkCounterIdListGenerated`: 3 hit (L279, L294, L361)
