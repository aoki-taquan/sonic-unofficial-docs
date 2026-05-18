# counters-state — Phase C 暗黙参照テーブル 調査メモ

**対象**: `STATE_DB / PORT_COUNTER_CAPABILITIES`, `QUEUE_COUNTER_CAPABILITIES`, `DEBUG_COUNTER_CAPABILITIES`
**調査日**: 2026-05-18  
**調査対象ソース**:
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/debugcounterorch.cpp`
- `sonic-utilities/utilities_common/portstat.py`
- `sonic-utilities/scripts/dropconfig`
- `sonic-swss-common/common/schema.h`

---

## 1. 生成側 (producer) の暗黙依存

### portsorch (PORT_COUNTER_CAPABILITIES / QUEUE_COUNTER_CAPABILITIES)

`initCounterCapabilities()` は以下のリソースに暗黙的に依存する:

- **SAI API** (`sai_query_stats_capability`): SAI_OBJECT_TYPE_QUEUE / SAI_OBJECT_TYPE_PORT に対して能力問い合わせを実行
  - SAI 接続が確立されていない（switchId = SAI_NULL_OBJECT_ID 等）と呼び出し自体が失敗 → 全フィールドが "false" のまま残存
  - portsorch.cpp:1107 でコンストラクタから呼び出される。gSwitchId が確定済みである前提

- **m_state_db** (STATE_DB 接続): `portsorch.cpp:793-794` で `Table` インスタンスを生成
  - STATE_DB 接続失敗時は Table 生成例外 → orchagent クラッシュ

### debugcounterorch (DEBUG_COUNTER_CAPABILITIES)

`publishDropCounterCapabilities()` は以下に依存する:

- **SAI API** (`sai_query_attribute_enum_values_capability`): DROP_REASON リスト、COUNTER_TYPE リストを問い合わせ
  - `getSupportedDropReasons()` が空集合返却 → エントリ書き込みなし（テーブル自体が空）
  - `getSupportedCounterTypes()` が空集合 → 全 counter_type がスキップ
  - debugcounterorch.cpp:315-363

## 2. 消費側 (consumer) の暗黙参照

### portstat.py → PORT_COUNTER_CAPABILITIES

`portstat.py:297-329` で STATE_DB から 4 フィールドを HGET して WRED カウンタのポーリング対象を決定。
- 参照テーブル: `PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_*_DROP_COUNTER`
- フィールド: `isSupported`
- 参照タイミング: ポーリング実行前（毎回）

### dropconfig → DEBUG_COUNTER_CAPABILITIES

`scripts/dropconfig:423-455` が `DEBUG_COUNTER_CAPABILITIES` テーブルを走査してサポートされる drop reason と counter_type を取得。
- `show debug-counter capabilities` コマンドがこの参照に依存
- テーブルが空の場合は出力が空（エラーなし）

## 3. 暗黙参照が YANG に記述されていない問題

これらの STATE_DB テーブルは CONFIG_DB / YANG モデルに leafref として記述されていない。
`sonic-portcounters.yang` / `sonic-flex_counter.yang` には定義なし。
WRED カウンタが N/A になる場合は STATE_DB の内容を直接確認する必要がある。
