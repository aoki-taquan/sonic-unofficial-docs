# PORT_STORM_CONTROL テーブル — Phase H プラットフォーム差スキャンノート

対象テーブル: `CONFIG_DB PORT_STORM_CONTROL`
Consumer: `PolicerOrch::handlePortStormControlTable()` (`sonic-swss/orchagent/policerorch.cpp`)
CLI: `config/main.py:is_storm_control_supported()` (`sonic-net/sonic-utilities`)
スキャン範囲: `policerorch.cpp` 全行、`orchdaemon.cpp:395-402`、`config/main.py:806-830`

---

## 検出したプラットフォーム依存

### 1. orchagent 内の ASIC 種別分岐: なし

`policerorch.cpp` 全行に `platform` 文字列比較・`BRCM_PLATFORM_SUBSTRING` / `MLNX_PLATFORM_SUBSTRING` 等の定数参照は存在しない。
ASIC 種別による orchagent 内の動作分岐は一切ない。

### 2. SAI 属性の ASIC 依存性

orchagent が固定値で設定する SAI 属性はすべて ASIC SAI 実装に委ねられる:
- `SAI_POLICER_ATTR_METER_TYPE = BYTES`
- `SAI_POLICER_ATTR_MODE = STORM_CONTROL`
- `SAI_POLICER_ATTR_RED_PACKET_ACTION = DROP`
- CBS / Green / Yellow / Color source: 未設定

ASIC が BYTES + STORM_CONTROL の組み合わせを SAI でサポートしない場合、`create_policer` が SAI エラーを返す。
orchagent は `handleSaiCreateStatus()` で `task_need_retry` を返し、無限再試行となる可能性がある。

### 3. BUM_STORM_CAPABILITY の dead connector

`orchdaemon.cpp:401`:
```cpp
TableConnector stateDbStorm(m_stateDb, "BUM_STORM_CAPABILITY");
gPolicerOrch = new PolicerOrch(policer_tables, gPortsOrch);
```

`stateDbStorm` は `PolicerOrch` コンストラクタに渡されない。`policer_tables` は `CFG_POLICER_TABLE_NAME` と `CFG_PORT_STORM_CONTROL_TABLE_NAME` の 2 コネクタのみ。
→ `BUM_STORM_CAPABILITY` は `PolicerOrch` が直接 subscribe しない。dead code 的な残骸。

### 4. BUM_STORM_CAPABILITY の書き込み主体

コミュニティ master ソースで確認した限り、`BUM_STORM_CAPABILITY` を STATE_DB に書き込むコードは以下のリポジトリに存在しない:
- `sonic-swss/orchagent/` — 書き込みなし
- `sonic-buildimage/` — 書き込みなし
- `sonic-platform-daemons/` — 書き込みなし

おそらくベンダー固有のプラットフォームプラグイン（`sonic_platform` package 等）が書き込む設計と推定されるが、コミュニティ版では書き込み主体が不明確。

### 5. CLI の capability チェック

`config/main.py:806-814`:
```python
def is_storm_control_supported(storm_type, namespace):
    asic_id = multi_asic.get_asic_index_from_namespace(namespace)
    state_db = SonicV2Connector(host='127.0.0.1')
    state_db.connect(state_db.STATE_DB, False)
    entry_name="BUM_STORM_CAPABILITY|"+storm_type
    supported = state_db.get(state_db.STATE_DB, entry_name,"supported")
    return supported
```

`get()` が `None` を返す（エントリ不在）場合、caller (`storm_control_set_entry()`:L822) で `== 0` 比較が `False` となり設定スキップとはならない点に注意。
実際の guard は L822: `if is_storm_control_supported(storm_type, namespace) == 0:` — `None == 0` は `False` なので、エントリ不在でも CLI は設定を試みる。

### 6. multi-asic

`is_storm_control_supported()` が `get_asic_index_from_namespace(namespace)` を使って asic 単位で STATE_DB を参照する設計になっているが、実際の DB 接続は `SonicV2Connector(host='127.0.0.1')` のデフォルト接続のため、multi-asic 環境での正確な namespace 分離が機能するかは実装依存。
