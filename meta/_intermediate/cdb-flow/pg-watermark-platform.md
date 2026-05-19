# FLEX_COUNTER_TABLE|PG_WATERMARK — Phase H プラットフォーム差スキャンノート

対象エントリ: `CONFIG_DB FLEX_COUNTER_TABLE|PG_WATERMARK`
スキャン範囲:
- `sonic-swss/orchagent/main.cpp:874,997`
- `sonic-swss/orchagent/orchdaemon.cpp:232,609,625`
- `sonic-swss/orchagent/flexcounterorch.cpp:145-175,265-270`
- `sonic-swss/orchagent/portsorch.cpp:8889-8960`
- `sonic-swss/orchagent/watermarkorch.cpp:23-50`

---

## getenv("platform") 分岐の有無

`flexcounterorch.cpp`, `portsorch.cpp`, `watermarkorch.cpp` のいずれにも `getenv("platform")` による ASIC 種別分岐は存在しない。PG_WATERMARK FlexCounter の制御ロジック自体はプラットフォーム非依存。

---

## 構成・スイッチタイプ起因のプラットフォーム差

### fabric スイッチタイプ — PortsOrch が存在しない

`main.cpp:997` の分岐:

```cpp
else if (gMySwitchType != "fabric")
{
    orchDaemon = make_shared<OrchDaemon>(...);
    ...
}
```

`gMySwitchType == "fabric"` の場合、`OrchDaemon` が生成されない（`FabricOrchDaemon` が代わりに起動）。`orchdaemon.cpp:232` の `gPortsOrch = new PortsOrch(...)` は `OrchDaemon::init()` 内にあるため、fabric スイッチでは `gPortsOrch == nullptr` のまま。

`FlexCounterOrch::doTask()` の冒頭チェック (`flexcounterorch.cpp:164`):

```cpp
if (gPortsOrch && !gPortsOrch->allPortsReady())
{
    return;
}
```

`gPortsOrch == nullptr` の場合はチェックをスキップするが、PG_WATERMARK ハンドラ自体 (`flexcounterorch.cpp:265-270`) が `gPortsOrch->generatePriorityGroupMap()` / `gPortsOrch->addPriorityGroupWatermarkFlexCounters()` を呼ぶため、fabric スイッチでは `gPortsOrch` が null で **クラッシュするか、そもそも FlexCounterOrch が fabric 向けには生成されない**。

実際には `FlexCounterOrch` は `orchdaemon.cpp:625` で生成されるため、`OrchDaemon` が生成されない fabric スイッチでは FlexCounterOrch 自体が存在しない。

| 構成 | FlexCounterOrch | gPortsOrch | PG_WATERMARK 処理 |
|------|----------------|------------|-----------------|
| 通常スイッチ / voq / chassis-packet | 存在 | 存在 | 正常に enable/disable 反映 |
| fabric スイッチ (`gMySwitchType == "fabric"`) | **存在しない** | **存在しない** | **CONFIG_DB エントリを書き込んでも無効** |

### VOQ シャーシ — PG_WATERMARK の挙動は通常スイッチと同一

VOQ シャーシ (`gMySwitchType == "voq"`) では `OrchDaemon` が生成され `gPortsOrch` も存在する。`flexcounterorch.cpp:544-558` の VOQ 専用コードパスは QUEUE グループ向けで PG_WATERMARK には関係しない。PG_WATERMARK の動作は通常スイッチと同一。

### FabricPortsOrch ブロック — fabric ポートが全部 ready になるまで doTask がブロック

`flexcounterorch.cpp:169-172`:

```cpp
if (gFabricPortsOrch && !gFabricPortsOrch->allPortsReady())
{
    return;
}
```

`gFabricPortsOrch` が存在する構成（ファブリックポートを持つラインカード等）では、ファブリックポートが全部 ready になるまで `FLEX_COUNTER_TABLE|PG_WATERMARK` の処理もブロックされる。

### SAI カウンタ サポート — ASIC 依存

`portsorch.cpp:9051` で `pg_watermark_manager.setCounterIdList()` が呼ばれると、syncd は `sai_get_ingress_priority_group_stats()` で `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES` / `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES` を取得しようとする。ASIC がこれらのカウンタをサポートしない場合、SAI は `SAI_STATUS_NOT_SUPPORTED` を返す。CONFIG_DB / FLEX_COUNTER_DB の書き込み自体は行われるが COUNTERS_DB には値が現れない。

---

## プラットフォーム差サマリ

| 差異点 | 条件 | PG_WATERMARK への影響 |
|--------|------|----------------------|
| FlexCounterOrch/PortsOrch 非存在 | fabric スイッチ (`gMySwitchType == "fabric"`) | CONFIG_DB に書き込んでも PG watermark カウンタは無効 |
| doTask ブロック | FabricPortsOrch 存在 + ファブリックポート未 ready | enable 受信が遅延 |
| SAI カウンタ非サポート | ASIC 依存 | FLEX_COUNTER_DB 登録は行われるが COUNTERS_DB に値が出ない |
| Gearbox / DASH / MACsec | 各オプション | PG_WATERMARK には無関係 |
