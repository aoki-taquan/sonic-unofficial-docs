# dpu-counter Phase C — 暗黙参照テーブル調査メモ

調査日: 2026-05-19  
対象ページ: `docs/reference/config-db/dpu-counter.md`  
対象テーブル: `FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER`

## 調査ソース

| ファイル | リポジトリ | SHA |
|---------|----------|-----|
| `orchagent/flexcounterorch.cpp` | sonic-net/sonic-swss | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `orchagent/dash/dashorch.cpp` | sonic-net/sonic-swss | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `orchagent/dash/dashorch.h` | sonic-net/sonic-swss | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `orchagent/dash/dashcounter.h` | sonic-net/sonic-swss | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `dockers/docker-orchagent/enable_counters.py` | sonic-net/sonic-buildimage | 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd |
| `src/sonic-py-common/sonic_py_common/device_info.py` | sonic-net/sonic-buildimage | 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd |
| `common/schema.h` | sonic-net/sonic-swss-common | (HEAD) |

## 検出された暗黙参照

### 1. DEVICE_METADATA|localhost (CONFIG_DB)

**参照元**: `enable_counters.py:42-45` / `device_info.py:563-566`

```python
# enable_counters.py:37-45
def enable_counters():
    db = swsscommon.ConfigDBConnector()
    db.connect()
    dpu_counters = ["ENI","DASH_METER"]
    platform_info = device_info.get_platform_info(db)
    if platform_info.get('switch_type') == 'dpu':
        for key in dpu_counters:
            enable_counter_group(db, key)
```

```python
# device_info.py:563-566
metadata = config_db.get_table('DEVICE_METADATA')["localhost"]
switch_type = metadata.get('switch_type')
if switch_type:
    hw_info_dict['switch_type'] = switch_type
```

`enable_counters.py` は `DEVICE_METADATA|localhost` の `switch_type` フィールドを読み取り、
`dpu` の場合のみ `FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER` に
`FLEX_COUNTER_STATUS=enable` を書き込む。YANG leafref なし。

- `switch_type` が `dpu` でない場合: ENI / DASH_METER への書き込みをスキップ → カウンタは `disable` のまま
- `switch_type` が欠如している場合: `platform_info.get('switch_type')` が `None` → 書き込みスキップ

### 2. PORT (gPortsOrch::allPortsReady) — FlexCounterOrch 起動順序ガード

**参照元**: `flexcounterorch.cpp:164-166`

```cpp
if (gPortsOrch && !gPortsOrch->allPortsReady())
{
    return;
}
```

`FlexCounterOrch::doTask()` は `gPortsOrch->allPortsReady()` が `false` の間、
`FLEX_COUNTER_TABLE|ENI` / `|DASH_METER` の SET メッセージを処理しない。
`allPortsReady()` が `true` になるまで `m_toSync` に残留する。

DPU ノードでは物理 PORT が存在しない場合もあるが、
`gPortsOrch` が `nullptr` でない限りこのガードが適用される。

### 3. DashOrch eni_entries_ (内部マップ) — APPL_DB APP_DASH_ENI_TABLE 由来

**参照元**: `dashorch.cpp:1350-1352`, `dashorch.h:128-129`

`DashCounter::refreshStats()` が走査する `eni_entries_` は、
`DashOrch` が APPL_DB の `APP_DASH_ENI_TABLE_NAME` から ENI エントリを追加するたびに
`addEniEntry()` で更新される。

```cpp
// dashorch.cpp:69
dash_eni_result_table_ = make_unique<Table>(app_state_db, APP_DASH_ENI_TABLE_NAME);
```

`FLEX_COUNTER_TABLE|ENI` の `FLEX_COUNTER_STATUS=enable` が処理された時点で
`eni_entries_` が空の場合、FLEX_COUNTER_DB への ENI カウンタ ID 書込みは発生しない。
後から ENI が追加された時点で `EniCounter.addToFC()` が個別登録する。

YANG leafref なし。`APP_DASH_ENI_TABLE_NAME` は APPL_DB 側の運用経路。

### 4. COUNTERS_DB|COUNTERS_ENI_NAME_MAP — DashOrch が書き込む名前マップ

**参照元**: `dashorch.cpp:67-68`, `schema.h:249`

```cpp
m_counter_db = std::shared_ptr<DBConnector>(new DBConnector("COUNTERS_DB", 0));
m_eni_name_table = make_unique<Table>(m_counter_db.get(), COUNTERS_ENI_NAME_MAP);
```

`DashOrch` は ENI 追加/削除のたびに `COUNTERS_DB|COUNTERS_ENI_NAME_MAP` に
ENI 名 → OID のマッピングを書き込む (`dashorch.cpp:1382, 1395`)。
`counterpoll` や `show dash counters eni` はこのマップを経由してカウンタ値を参照する。

FLEX_COUNTER_TABLE|ENI が `enable` になる前提として、
`COUNTERS_ENI_NAME_MAP` に ENI エントリが存在することが実用上求められる。

### 5. create_only_config_db_buffers (DEVICE_METADATA) — FlexCounterOrch 初期化

**参照元**: `flexcounterorch.cpp:106`, `114`

```cpp
m_deviceMetadataConfigTable(db, CFG_DEVICE_METADATA_TABLE_NAME)
...
m_deviceMetadataConfigTable.hget("localhost", "create_only_config_db_buffers", ...)
```

`FlexCounterOrch` コンストラクタは `DEVICE_METADATA|localhost` の
`create_only_config_db_buffers` フィールドを初期化時に読む。
ENI / DASH_METER の処理パスには直接影響しないが、
`FlexCounterOrch` が参照する副次的な `DEVICE_METADATA` 依存として記録する。

## YANG leafref の有無

`sonic-flex_counter.yang` ENI / DASH_METER コンテナには leafref 定義なし。
すべての暗黙参照は実装ロジックのみで成立し、YANG スキーマによる強制はない。

## まとめ

| # | 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 |
|---|--------|-----|---------|-------------|--------------|
| 1 | `DEVICE_METADATA\|localhost.switch_type` | CONFIG_DB | 読み取り | なし | DPU 自動有効化に必須 |
| 2 | `PORT` (allPortsReady) | — (PortsOrch 内部) | 状態確認 | なし | FlexCounterOrch 処理開始の前提 |
| 3 | `APP_DASH_ENI_TABLE` → `eni_entries_` | APPL_DB | 間接 (DashOrch 内部マップ) | なし | カウンタ ID 投入に実質必須 |
| 4 | `COUNTERS_ENI_NAME_MAP` | COUNTERS_DB | 書き込み (DashOrch が生産) | なし | counterpoll / show の参照先 |
| 5 | `DEVICE_METADATA\|localhost.create_only_config_db_buffers` | CONFIG_DB | 読み取り (初期化のみ) | なし | ENI/DASH_METER 処理パスに非直接 |
