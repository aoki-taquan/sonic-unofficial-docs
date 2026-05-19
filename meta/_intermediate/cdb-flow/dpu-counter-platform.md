# dpu-counter Phase H — プラットフォーム差分調査

調査日: 2026-05-19
対象: `FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER` に関わるプラットフォーム差分

## 調査対象ファイル

- `sonic-swss/orchagent/main.cpp` (gMySwitchType 分岐, DpuOrchDaemon 選択)
- `sonic-swss/orchagent/orchdaemon.cpp` (DpuOrchDaemon::init, FlexCounterOrch 登録)
- `sonic-swss/orchagent/flexcounterorch.cpp` (gMySwitchType VOQ 分岐, FlexCounterOrch 全体)
- `sonic-swss/orchagent/dash/dashcounter.cpp` (fetchStats — queryAvailableCounterStats)
- `sonic-swss/orchagent/dash/dashcounter.h` (DashCounter テンプレート)
- `sonic-swss/orchagent/dash/dashorch.cpp` (DashOrch コンストラクタ, addEniEntry)
- `sonic-buildimage/dockers/docker-orchagent/enable_counters.py` (switch_type=dpu 分岐)
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` (platform, subtype 分岐)

---

## 1. switch_type=dpu のみで ENI / DASH_METER カウンタが有効化される

`enable_counters.py:43-44` の `switch_type == 'dpu'` ガードにより、
ENI / DASH_METER カウンタの自動有効化は DPU ノード専用の動作である。

| switch_type 値 | enable_counters.py の ENI/DASH_METER 処理 |
|--------------|----------------------------------------|
| `dpu` | `FLEX_COUNTER_STATUS=enable` を書き込む |
| `switch` (標準 NPU) | スキップ。CONFIG_DB に何も書かない |
| `voq` (VOQ chassis) | スキップ。ENI/DASH_METER は不要 |
| `fabric` | スキップ。Fabric スイッチには DASH 機能なし |
| `chassis-packet` | スキップ |

DPU 以外の switch_type で手動 enable した場合、`FlexCounterOrch` は受け付けるが
`DashOrch` が存在しない (`gDirectory.get<DashOrch*>()` が nullptr) ため、
`handleFCStatusUpdate` / `handleMeterFCStatusUpdate` が呼ばれず実質的に no-op。

---

## 2. DpuOrchDaemon 専用 — DashOrch は DPU のみ存在

`main.cpp:990-994`:
```cpp
if (gMySwitchType == "dpu")
{
    orchDaemon = make_shared<DpuOrchDaemon>(...);
}
```

`DpuOrchDaemon::init()` (`orchdaemon.cpp:1322-1419`) のみが `DashOrch` を
`gDirectory` に登録する。`switch_type != "dpu"` の場合、`DashOrch` は存在しないため
`FlexCounterOrch` が `gDirectory.get<DashOrch*>()` で `nullptr` を返し、
ENI / DASH_METER キーへの `handleFCStatusUpdate` 委譲が発生しない。

---

## 3. FlexCounterOrch 自体の platform 分岐 — ENI/DASH_METER には影響なし

`flexcounterorch.cpp:546` の `gMySwitchType == "voq"` 分岐はキューカウンタ
(VOQ キュー) の追加処理であり、ENI / DASH_METER カウンタグループには無関係。

`OrchDaemon::init()` での Mellanox (`MLNX_PLATFORM_SUBSTRING`) /
Broadcom (`BRCM_PLATFORM_SUBSTRING`) / Marvell 等のプラットフォーム分岐
(`orchdaemon.cpp:635,674,733`) は PFC-WD ・Buffer 等に関するものであり、
`FlexCounterOrch` の ENI / DASH_METER 処理パスには影響しない。

---

## 4. SAI Capability — fetchStats は sai_metadata から動的取得

`dashcounter.cpp:12-16`:
```cpp
auto stat_enum_list = queryAvailableCounterStats((sai_object_type_t)SAI_OBJECT_TYPE_ENI);
for (auto &stat_enum: stat_enum_list)
{
    auto counter_id = static_cast<sai_eni_stat_t>(stat_enum);
    counter_stats.insert(sai_serialize_eni_stat(counter_id));
}
```

`queryAvailableCounterStats` (`saihelper.cpp:1099-1123`) は SAI メタデータ
(`sai_metadata_get_object_type_info`) から静的な statenum リストを取得する。
したがって**実際にポーリングされる統計 ID の種類は SAI メタデータ定義に依存**し、
ベンダー SAI ライブラリ（NVIDIA BlueField / Pensando 等）が提供する
`SAI_OBJECT_TYPE_ENI` および `SAI_OBJECT_TYPE_METER_BUCKET_ENTRY` の統計 ID 定義によって異なりうる。
orchagent コード側に ASIC 種別ごとのハードコード差分はない。

---

## 5. platform (asic_type) による MAC アドレス取得の差 — カウンタには無関係

`orchagent.sh` の `platform` 分岐 (`nvidia-bluefield`, `pensando`) は
orchagent の `-m <MAC>` 引数のみに影響し、FlexCounter / ENI カウンタの動作には無関係。

---

## 6. VS (Virtual Switch) — switch_type=dpu で完全動作可

`platform/vs/docker-sonic-vs/platform-dpu-2p.json` が存在し、VS 上で `switch_type=dpu`
を設定した場合も `DpuOrchDaemon` → `DashOrch` → `DashCounter` の経路が成立する。
VS の SAI 実装 (`libsaivs`) が ENI SAI オブジェクトをサポートしている範囲でカウンタ動作する。

---

## 結論

| 観点 | 結果 | 根拠 |
|------|------|------|
| switch_type=dpu 専用 | ENI / DASH_METER カウンタは DPU ノード固有。他 switch_type では enable_counters.py がスキップし、DashOrch も存在しないため実質無効 | `enable_counters.py:43`, `main.cpp:990` |
| ASIC 種別 (NVIDIA BF / Pensando / Marvell 等) | orchagent コード側の差分なし。SAI ENI 統計 ID の種類はベンダー SAI メタデータ定義に依存 | `dashcounter.cpp:12-16`, `saihelper.cpp:1099-1123` |
| VOQ chassis | FlexCounterOrch の VOQ 分岐はキューカウンタ専用。ENI / DASH_METER には影響なし | `flexcounterorch.cpp:546` |
| multi-asic | ENI / DASH_METER は DPU ノード固有 (single-ASIC 前提の DASH パイプライン) | `orchdaemon.cpp:1350` |
| VS (Virtual Switch) | switch_type=dpu 設定で DpuOrchDaemon が起動し ENI カウンタ経路が成立 | `platform/vs/docker-sonic-vs/platform-dpu-2p.json` |
| SmartSwitch NPU 側 (subtype=SmartSwitch) | switch_type=switch のため enable_counters.py が ENI/DASH_METER をスキップ。NPU 側では DashOrch 非起動 | `enable_counters.py:43`, `orchdaemon.cpp:613` |
