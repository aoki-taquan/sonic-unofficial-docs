# counter-buffer Phase H — プラットフォーム差 (platform)

Generated: 2026-05-17  
Target doc: docs/reference/config-db/counter-buffer.md

## スキャン対象

- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss/orchagent/watermarkorch.cpp`

---

## 1. VoQ (Virtual Output Queue) 環境固有の挙動

### 1-1. voq_stat_ids — VoQ 専用カウンタ

`portsorch.cpp:399-402` で `voq_stat_ids` が定義されている:

```cpp
static const vector<sai_queue_stat_t> voq_stat_ids =
{
    SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS
};
```

`addQueueFlexCountersPerPortPerQueueIndex()` (portsorch.cpp:8592-8614) で VoQ フラグが真の場合、`queue_stat_ids` に加えて `voq_stat_ids` が counter_stats に追加され syncd へ投入される。  
**非 VoQ 環境ではこのフィールドは一切登録されない**。

### 1-2. VoQ カウンタは常時有効 — counterpoll 無効化不可

`generateQueueMapPerPort()` (portsorch.cpp:8483-8499) のコメントに明記されている:

```
/* voq counters are always enabled. There is no mechanism to disable voq
 * counters in a voq system. */
```

- VoQ システムでは `FlexCounterQueueStates` による queue index の enable/disable フィルタが**バイパス**される (`gMySwitchType != "voq"` のガードが外れる)
- egress queue も同様に常時有効: `// In voq systems, always install a flex counter for this egress queue`

### 1-3. VoQ システムの BUFFER_QUEUE 設定キー形式

VoQ システムでは `bufferorch.cpp:916` の processQueue() が `gMySwitchType == "voq"` を確認し、キー形式を `<switch>:<asic>:<port>:<queue_index>` (4 トークン) として parse する。非 VoQ 環境では `<port>:<queue_index>` (2 トークン)。

### 1-4. VoQ システムの `m_ready_list` 初期化源

- 通常起動: `initVoqBufferReadyList(queue_table, true)` — CONFIG_DB の `BUFFER_QUEUE` テーブルから読み込む (`bufferorch.cpp:132-140`)
- Warm Reboot: `initVoqBufferReadyList(queue_table, false)` — APPL_DB から読み込む (`bufferorch.cpp:116-124`)

通常環境ではそれぞれ `initBufferReadyList(queue_table, true/false)` が呼ばれる。

### 1-5. VoQ システムの ref counter 省略

Queue プロファイル適用時の `gPortsOrch->increasePortRefCount()` 呼び出しは `gMySwitchType != "voq"` のガードで skip される (`bufferorch.cpp:1168`)。  
理由: "for voq switches the buffer configuration is applied on the VOQ which is applicable on the system ports. System ports are not dynamically created/deleted so no need to maintain ref counter"

### 1-6. `getQueueConfigurations()` の VoQ 特別扱い

`flexcounterorch.cpp:544-550`:

```cpp
if ((!isCreateOnlyConfigDbBuffers()) || (gMySwitchType == "voq"))
{
    FlexCounterQueueStates flexCounterQueueState(0);
    queuesStateVector.insert(make_pair(createAllAvailableBuffersStr, flexCounterQueueState));
    return queuesStateVector;
}
```

VoQ システムでは `create_only_config_db_buffers` が true であっても **全 Queue を対象にする** `createAllAvailableBuffersStr` が無条件で返される。非 VoQ + `create_only_config_db_buffers=true` の場合のみ BUFFER_QUEUE に記載された Queue のみが対象になる。

### 1-7. COUNTERS_VOQ_NAME_MAP

VoQ システムでは VoQ OID → 名前マップが `COUNTERS_DB / COUNTERS_VOQ_NAME_MAP` (portsorch.cpp:779) に書き込まれる。非 VoQ 環境には存在しない。

---

## 2. bufferorch.doTask() の ready 判定差

`bufferorch.cpp:2075-2092`:

```cpp
if (gMySwitchType == "voq")
{
    if(!gPortsOrch->isInitDone())
        return;  // PortInitDone 待ち
}
else if (!gPortsOrch->isConfigDone())
{
    return;  // PortConfigDone 待ち (PortInitDone より先に解除される)
}
```

| 環境 | 待機条件 | 条件が解除されるタイミング |
|------|---------|--------------------------|
| VoQ | `isInitDone()` = true | `PortInitDone` ノーティフィケーション受信後 |
| 非 VoQ | `isConfigDone()` = true | 全物理ポートの SAI create_port が pipeline に投入された後 |

VoQ では `isConfigDone()` より遅い `isInitDone()` を待つため、bufferorch の処理開始がわずかに遅れる。

---

## 3. DPU (Data Processing Unit) 環境固有の挙動

`bufferorch.cpp:64-67`:

```cpp
if (gMySwitchType != "dpu")
{
    initBufferConstants();
}
```

DPU 環境では `initBufferConstants()` (xoff 等のバッファ定数計算) がスキップされる。結果として `BUFFER_POOL` の xoff 関連フィールドが未設定のまま SAI へ投入されることがなく、DPU に不要な shared headroom 計算が行われない。

`portsorch.cpp:987,1043,1056` にも `gMySwitchType != "dpu"` ガードが複数あり、DPU では port の一部初期化フローが異なる (ポートの up/down 通知連鎖等が省略される)。

---

## 4. Fabric ポート環境の影響

`flexcounterorch.cpp:169-172`:

```cpp
if (gFabricPortsOrch && !gFabricPortsOrch->allPortsReady())
{
    return;
}
```

Fabric ポートが存在するシャーシ環境では、`FabricPortsOrch` が全 Fabric ポートの ready を確認するまで `FlexCounterOrch::doTask()` が全グループについてブロックされる。  
バッファカウンタグループ (QUEUE_WATERMARK / PG_WATERMARK / BUFFER_POOL_WATERMARK / PORT_BUFFER_DROP 等) の有効化はすべて `FlexCounterOrch::doTask()` 内で行われるため、Fabric ポートの準備遅延がバッファカウンタ全体の有効化を遅延させる。

---

## 5. create_only_config_db_buffers (dynamic buffer model)

`DEVICE_METADATA|localhost` の `create_only_config_db_buffers` フィールドが `"true"` の場合 (mlnx 等の dynamic buffer model 環境):

- Queue カウンタ: BUFFER_QUEUE テーブルに記載された (port, queue index) のみ登録される (`getQueueConfigurations()`)
- PG カウンタ: BUFFER_PG テーブルに記載された (port, pg index) のみ登録される (`getPgConfigurations()`)
- false または VoQ システムの場合は全 Queue / 全 PG が対象

この設定は runtime に `DEVICE_METADATA` テーブルの変更で更新されるが (`flexcounterorch.cpp:508-520`)、既登録のカウンタ ID リストは自動的には再構成されない (再起動が必要)。

---

## 6. WRED カウンタの ASIC 能力依存

WRED 統計 (`SAI_QUEUE_STAT_WRED_*` / `SAI_PORT_STAT_*_WRED_*`) は `sai_query_stats_capability()` で ASIC が対応しているかを確認してから登録される (`portsorch.cpp:1882-1909`)。Broadcom XGS 等 WRED 対応 ASIC と Mellanox Spectrum 等では対応フィールドが異なる。

---

## 検出されたポイント

1. **VoQ システムでは `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` が追加登録される**: 非 VoQ 環境にはないフィールド。Credit Watchdog が機能するシャーシ VoQ 環境専用。
2. **VoQ カウンタは counterpoll で無効化できない**: `gMySwitchType == "voq"` 判定で `FlexCounterQueueStates` フィルタをバイパスするため、`counterpoll queue disable` を実行しても VoQ キューのカウンタは停止しない。
3. **DPU 環境では bufferorch の定数計算が省略される**: xoff / shared headroom 計算が不要なため、`initBufferConstants()` が skip される。
4. **Fabric ポートの ready がバッファカウンタ有効化をブロックする**: Fabric ポート初期化遅延はバッファカウンタ全体の遅延につながる可能性がある。
5. **`create_only_config_db_buffers=true` で対象 Queue/PG が限定される**: Dynamic buffer model (mlnx 等) では BUFFER_QUEUE/BUFFER_PG 未登録の Queue/PG にはカウンタが付与されない。
