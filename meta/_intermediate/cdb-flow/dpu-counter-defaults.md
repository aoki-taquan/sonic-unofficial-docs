# DPU カウンタ フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER`

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashorch.h` — ENI / METER ポーリング定数
- `sonic-swss/orchagent/dash/dashorch.cpp` — EniCounter / MeterCounter 初期化
- `sonic-swss/orchagent/dash/dashcounter.h` — DashCounter テンプレート (fc_status 初期値)
- `sonic-swss/orchagent/flex_counter/flex_counter_manager.cpp` — ENI_COUNTER_ID_LIST / DASH_METER_COUNTER_ID_LIST マッピング
- `sonic-swss/orchagent/flexcounterorch.cpp` — グループ名マッピング
- `sonic-buildimage/dockers/docker-orchagent/enable_counters.py` — DPU 専用ランタイム自動有効化
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-flex_counter.yang` — ENI / DASH_METER コンテナ定義

---

## フィールド別 暗黙デフォルト

### `FLEX_COUNTER_STATUS` (ENI / DASH_METER 共通)

**コード由来デフォルト**: `disable` (コード起動時フォールバック)

```cpp
// dashcounter.h:15
bool fc_status = false;

// dashorch.cpp:62-63
EniCounter(ENI_STAT_COUNTER_FLEX_COUNTER_GROUP, StatsMode::READ,
           ENI_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS, false),   // enabled=false
MeterCounter(METER_STAT_COUNTER_FLEX_COUNTER_GROUP, StatsMode::READ,
             METER_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS, false) // enabled=false
```

`FlexCounterManager` の第 4 引数 `enabled=false` が orchagent 起動時の初期状態。
`FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER` エントリが CONFIG_DB に存在しない場合、polling は開始されない。

**ランタイム上書き (DPU 専用)**:

```python
# enable_counters.py:40-44
dpu_counters = ["ENI","DASH_METER"]
if platform_info.get('switch_type') == 'dpu':
    for key in dpu_counters:
        enable_counter_group(db, key)
```

`switch_type == 'dpu'` のノードでのみ、起動後 3 分 (uptime < 5 分) または 60 秒 (uptime >= 5 分) 待機後に `FLEX_COUNTER_STATUS: enable` を CONFIG_DB に書き込む。非 DPU (ToR / Spine 等) では書き込まれない。

---

### `POLL_INTERVAL` (ENI)

**コード由来デフォルト**: `10000` ms

```cpp
// dashorch.h:30
#define ENI_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS 10000
```

`FlexCounterManager::applyGroupConfiguration()` が orchagent 起動時に `POLL_INTERVAL = 10000` をセットする。CONFIG_DB に `POLL_INTERVAL` が書き込まれていない場合は、orchagent の内部状態 (10000 ms) が使われるが、`FLEX_COUNTER_TABLE|ENI` が存在しない間は FlexCounterGroup への書き込みも行われない。

`enable_counters.py` の `enable_counter_group()` は `FLEX_COUNTER_STATUS: enable` のみを書き込み、`POLL_INTERVAL` は書き込まない (デフォルト 10000 ms が継続有効)。

---

### `POLL_INTERVAL` (DASH_METER)

**コード由来デフォルト**: `10000` ms

```cpp
// dashorch.h:33
#define METER_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS 10000
```

ENI と同様、10000 ms が orchagent ハードコード値。

---

### `FLEX_COUNTER_DELAY_STATUS`

**コード由来デフォルト**: YANG 定義では `stypes:boolean_type` (true/false の文字列)。
初期値を明示する orchagent コードは存在しない。エントリ未設定時は delay 処理が走らない (= delay なし)。

---

## カウンタ ID リスト (counter_id_field_lookup)

```cpp
// flex_counter_manager.cpp:54-55
{ CounterType::ENI,        ENI_COUNTER_ID_LIST },
{ CounterType::DASH_METER, DASH_METER_COUNTER_ID_LIST },
```

`schema.h` では:
- `ENI_COUNTER_ID_LIST` (schema.h:293)
- `DASH_METER_COUNTER_ID_LIST` (schema.h:295)

実際のカウンタ ID 一覧は SAI の `sai_eni_stat_t` / `sai_meter_stat_t` に依存するため、ここでは列挙しない。

---

## グループ名マッピング

```cpp
// flexcounterorch.cpp:92-93
{"ENI",        ENI_STAT_COUNTER_FLEX_COUNTER_GROUP},   // "ENI_STAT_COUNTER"
{"DASH_METER", METER_STAT_COUNTER_FLEX_COUNTER_GROUP}, // "METER_STAT_COUNTER"
```

FLEX_COUNTER_DB のグループキー名と CONFIG_DB のテーブルキー名の対応:

| CONFIG_DB key | FlexCounter グループ名 |
|--------------|----------------------|
| `ENI` | `ENI_STAT_COUNTER` |
| `DASH_METER` | `METER_STAT_COUNTER` |

---

## 要約表

| フィールド | グループ | コード由来デフォルト | 設定源 |
|-----------|---------|-------------------|-------|
| `FLEX_COUNTER_STATUS` | ENI | `disable` (false) | dashorch.cpp:62 `enabled=false` |
| `FLEX_COUNTER_STATUS` | DASH_METER | `disable` (false) | dashorch.cpp:63 `enabled=false` |
| `POLL_INTERVAL` | ENI | `10000` ms | dashorch.h:30 `ENI_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` |
| `POLL_INTERVAL` | DASH_METER | `10000` ms | dashorch.h:33 `METER_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` |
| `FLEX_COUNTER_DELAY_STATUS` | ENI | 未設定/delay なし | orchagent 初期化コードなし |
| `FLEX_COUNTER_DELAY_STATUS` | DASH_METER | 未設定/delay なし | orchagent 初期化コードなし |

---

## 重要な特記事項

1. **DPU 専用の自動有効化**: `enable_counters.py` が `switch_type == 'dpu'` のみ `FLEX_COUNTER_STATUS: enable` を書き込む。init_cfg.json.j2 には ENI / DASH_METER の記載なし。

2. **init_cfg.json.j2 に未掲載**: 通常の ToR/Spine では ENI / DASH_METER カウンタは起動時デフォルトで無効。

3. **遅延起動**: enable_counters.py は uptime < 300s の場合 180s、それ以外は 60s 待機後に有効化。orchagent が完全起動してから CONFIG_DB に書き込む設計。

---

## 証拠リンク

- `sonic-swss/orchagent/dash/dashorch.h:29-33` — グループ名定数 / polling interval 定数
- `sonic-swss/orchagent/dash/dashorch.cpp:62-63` — EniCounter / MeterCounter 初期化 (enabled=false)
- `sonic-swss/orchagent/dash/dashcounter.h:15` — fc_status = false
- `sonic-swss/orchagent/flex_counter/flex_counter_manager.cpp:54-55` — counter_id_field_lookup ENI / DASH_METER
- `sonic-swss/orchagent/flexcounterorch.cpp:92-93` — flexCounterGroupMap ENI / DASH_METER
- `sonic-buildimage/dockers/docker-orchagent/enable_counters.py:40-44` — DPU 専用自動有効化
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-flex_counter.yang:93-125` — ENI / DASH_METER コンテナ
