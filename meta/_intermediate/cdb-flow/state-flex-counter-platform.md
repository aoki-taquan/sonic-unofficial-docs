# state-flex-counter / プラットフォーム差異 (Phase H 中間メモ)

対象: `docs/reference/config-db/state-flex-counter.md`
（`FLEX_COUNTER_DB` — FlexCounter グループ制御 + per-OID カウンタ ID リスト）

スコープ: `flexcounterorch.cpp` / `FlexCounter.cpp` / `FlexCounterManager.cpp` / `portsorch.cpp` の master HEAD から
プラットフォーム / switch_type / SAI capability による差異を抜き出す。

---

## 1. Gearbox (PHY) 有効時の追加グループ

`flexcounterorch.cpp:204` で `gPortsOrch->isGearboxEnabled()` を確認し、
Gearbox（外付け PHY チップ）が有効な場合のみ追加 FLEX_COUNTER_DB 書き込みが発生する。

```cpp
// flexcounterorch.cpp:204-212, 382-390
if (gPortsOrch && gPortsOrch->isGearboxEnabled())
{
    if (key == PORT_KEY || key.rfind("MACSEC", 0) == 0)
    {
        setFlexCounterGroupPollInterval(flexCounterGroupMap[key], value, true);
        // ...
        setFlexCounterGroupOperation(flexCounterGroupMap[key], value, true);
    }
}
```

`setFlexCounterGroupPollInterval / setFlexCounterGroupOperation` の第 3 引数 `true` は Gearbox 用 `FlexCounterManager`
インスタンスへの書き込みを意味する。`PORT` グループと `MACSEC_*` グループのポーリング間隔・enable/disable が
**Gearbox 専用の FLEX_COUNTER_DB エントリにも同時に書き込まれる**。

Gearbox が無効な場合（`isGearboxEnabled() == false`）、このコードパスは実行されず、
Gearbox 用エントリは FLEX_COUNTER_DB に生成されない。

**対応 ASIC プラットフォーム**: community master では Gearbox (Inphi AN-series 等) を搭載する
一部 T1/T2 スイッチ。Gearbox なしの通常ポート構成ではこの分岐は到達されない。

---

## 2. MACsec カウンタグループ

`flexcounterorch.cpp:89-91` で `MACSEC_SA`, `MACSEC_SA_ATTR`, `MACSEC_FLOW` の 3 グループが
`flexCounterGroupMap` に定義される。

```cpp
{"MACSEC_SA", COUNTERS_MACSEC_SA_GROUP},
{"MACSEC_SA_ATTR", COUNTERS_MACSEC_SA_ATTR_GROUP},
{"MACSEC_FLOW", COUNTERS_MACSEC_FLOW_GROUP},
```

MACsec ハードウェアオフロードが有効なプラットフォーム（`macsecorch` が初期化されるケース）では、
`FLEX_COUNTER_GROUP_TABLE|MACSEC_*` エントリが FLEX_COUNTER_DB に生成される。
MACsec 非搭載のプラットフォームでは `macsecorch` が存在せず、これらのグループは書き込まれない。

Gearbox 有効時、`MACSEC` で始まるキー (`key.rfind("MACSEC", 0) == 0`) に対しても
Gearbox 用ポーリング制御が適用される（`flexcounterorch.cpp:206, 384`）。

---

## 3. VOQ chassis — Queue カウンタ生成の特例

`flexcounterorch.cpp:544-558`:

```cpp
// For VOQ chassis, flexcounterorch adds the Queue Counters for all egress and VOQ queues
// of all front panel and system ports to the FLEX_COUNTER_DB irrespective of BUFFER_QUEUE configuration.
if ((!isCreateOnlyConfigDbBuffers()) || (gMySwitchType == "voq"))
{
    FlexCounterQueueStates flexCounterQueueState(0);
    queuesStateVector.insert(make_pair(createAllAvailableBuffersStr, flexCounterQueueState));
    return queuesStateVector;
}
```

VOQ シャーシ (`gMySwitchType == "voq"`) では、BUFFER_QUEUE CONFIG_DB 設定に関わらず
**全フロントパネルポートおよびシステムポートの全 egress queue と VoQ** に対して
`FLEX_COUNTER_TABLE|QUEUE|<oid>` が FLEX_COUNTER_DB に書き込まれる。

非 VOQ 環境では `BUFFER_QUEUE` テーブルのプロファイル設定を持つキューのみが対象になる
(`getBufferObjectsWithNonZeroProfile()` 経由)。

---

## 4. FabricPortsOrch — ファブリックポートの Queue カウンタ

`flexcounterorch.cpp:291-294`:

```cpp
if (gFabricPortsOrch)
{
    gFabricPortsOrch->generateQueueStats();
}
```

`FLEX_COUNTER_STATUS = enable` を受信した場合、`gFabricPortsOrch` が存在する構成（ファブリックスイッチ
または BOX スイッチのファブリックポートを持つ構成）では、追加で `gFabricPortsOrch->generateQueueStats()` が
呼ばれる。通常の BOX スイッチ (`switch_type=none`) や `FabricPortsOrch` が初期化されない構成では
このコードパスはスキップされる。

また `flexcounterorch.cpp:169` での `allPortsReady()` チェックも `gFabricPortsOrch` 起動待ちに使われるため、
ファブリックスイッチではファブリックポートが全部 ready になるまで CONFIG_DB 変更が処理されない。

---

## 5. DASH / ENI / SmartSwitch プラットフォーム

```cpp
// flexcounterorch.cpp:299-314
if (dash_orch && (key == ENI_KEY))
    dash_orch->handleFCStatusUpdate((value == "enable"));
if (dash_orch && (key == DASH_METER_KEY))
    dash_orch->handleMeterFCStatusUpdate((value == "enable"));
if (dash_ha_orch && (key == HA_SET_KEY))
    dash_ha_orch->handleHaSetFCStatusUpdate((value == "enable"));
```

DASH/SmartSwitch (`DashOrch` / `DashHaOrch` が初期化される構成) では `ENI` / `DASH_METER` / `HA_SET`
カウンタグループが FLEX_COUNTER_DB に書き込まれる。標準 BOX スイッチでは `dash_orch` / `dash_ha_orch` が
`nullptr` となり、これらのコードパスは到達されない。

`flexCounterGroupMap` に `{"ENI", ENI_STAT_COUNTER_FLEX_COUNTER_GROUP}` および
`{"DASH_METER", METER_STAT_COUNTER_FLEX_COUNTER_GROUP}` が定義されている（`flexcounterorch.cpp:92-93`）。

---

## 6. SRv6 Orch プラットフォーム

```cpp
// flexcounterorch.cpp:337-340
if (gSrv6Orch)
    gSrv6Orch->setCountersState((value == "enable"));
```

`gSrv6Orch` が存在する構成（SRv6 が有効な場合）のみ、SRv6 カウンタグループへの
ポーリング制御が連動する。SRv6 無効環境では `gSrv6Orch == nullptr` でスキップ。

---

## 7. SwitchOrch — Switch カウンタ

```cpp
// flexcounterorch.cpp:370-378
if (gSwitchOrch && (key == SWITCH_KEY) && (value == "enable"))
{
    gSwitchOrch->generateSwitchCounterMap();
}
```

`SWITCH` グループは全プラットフォームで `gSwitchOrch` が存在するが、
`generateSwitchCounterMap()` の内部で SAI `sai_switch_api->get_switch_stats_ext`
が対応しない ASIC では個別カウンタが 0 を返すか SAI エラーでスキップされる。

---

## 8. FLEX_COUNTER_DB 自体のプラットフォーム共通性

FLEX_COUNTER_DB（DB 5）の DB 番号・テーブル名・チャネル名（`schema.h`）はプラットフォーム非依存。
`FlexCounter::setStatus` / `setStatsMode` / `setPollInterval` の処理ロジックも共通。
各カウンタグループの SAI 統計収集（`sai_*_stats` API 呼び出し）は ASIC SDK 実装に依存するが、
それは FLEX_COUNTER_DB のフィールド設計上は透過的（FLEX_COUNTER_DB には raw oid と stat id 列を書くのみ）。

---

## 9. ドキュメント反映方針

`docs/reference/config-db/state-flex-counter.md` の `<!-- /pubsub -->` 直後に `<!-- platform -->` ブロックを挿入。
以下の見出しで簡潔にまとめる:

1. Gearbox 有効時: PORT / MACSEC グループへの追加 Gearbox 用エントリ書き込み
2. MACsec オフロード: MACSEC_SA / MACSEC_FLOW グループは MACsec 有効プラットフォームのみ
3. VOQ chassis: QUEUE グループが全ポートの全キューに一括展開
4. FabricPortsOrch: ファブリックポート Queue カウンタの追加生成
5. DASH / ENI / SmartSwitch: ENI / DASH_METER / HA_SET グループの追加
6. FLEX_COUNTER_DB 制御フィールド自体はプラットフォーム共通

Evidence: `flexcounterorch.cpp:89-93, 169, 204-212, 291-294, 299-314, 337-340, 370-378, 382-390, 544-558`
