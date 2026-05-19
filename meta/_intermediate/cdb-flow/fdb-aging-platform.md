# fdb-aging Phase H: プラットフォーム / SAI Capability 差異

## 調査対象

- `sonic-swss/orchagent/switchorch.cpp`
- `sonic-buildimage/dockers/docker-orchagent/switch.json.j2`

## 主要知見

### 1. DPU プラットフォーム: fdb_aging_time 注入なし

`switch.json.j2:35` の条件分岐:

```jinja2
{% if not DEVICE_METADATA.localhost.switch_type or DEVICE_METADATA.localhost.switch_type != "dpu" %}
    "ecmp_hash_seed": "{{ hash_seed_value }}",
    "lag_hash_seed": "{{ hash_seed_value }}",
    "fdb_aging_time": "600",
```

`switch_type == "dpu"` のノードでは `fdb_aging_time` を含む SWITCH_TABLE:switch 全体のフィールドセットが生成されない。
結果として SAI `SAI_SWITCH_ATTR_FDB_AGING_TIME` はハードウェアリセット時の初期値のまま。

### 2. chassis-packet プラットフォーム: fdb_aging_time は注入される

```jinja2
{% if not DEVICE_METADATA.localhost.switch_type or DEVICE_METADATA.localhost.switch_type != "chassis-packet" %}
    "ecmp_hash_offset": "{{ ecmp_hash_offset_value }}",
    "lag_hash_offset": "{{ lag_hash_offset_value }}",
{% endif %}
```

`chassis-packet` は `dpu` ブロックの内側にはない（`switch_type != "dpu"` 条件を満たす）ため `fdb_aging_time: 600` は注入される。
`ecmp_hash_offset` / `lag_hash_offset` のみスキップされる。

### 3. SAI Capability クエリなし

`switchorch.cpp` を全体精読した結果、`SAI_SWITCH_ATTR_FDB_AGING_TIME` に対して `querySwitchCapability()` / `sai_query_attribute_capability()` を呼び出す箇所は存在しない（grep "querySwitchCapability.*FDB_AGING" で 0 件）。

他の属性（ECMP hash offset, LAG hash offset, ASIC SDK health event, PFC DLR 等）は capability クエリが実装されているが、FDB aging time は非対応 ASIC での `SAI_STATUS_NOT_SUPPORTED` 返却を直接 `handleSaiSetStatus()` に委ねる設計。

### 4. VS (仮想スイッチ) での挙動

`sonic-sairedis` の vslib warm.bin ファイルで確認:
- `bcm56850.warm.bin:4480`: `SAI_OBJECT_TYPE_SWITCH oid:0x2100000000 SAI_SWITCH_ATTR_FDB_AGING_TIME 0`
- `mlnx2700.warm.bin:3808`: `SAI_OBJECT_TYPE_SWITCH oid:0x2100000000 SAI_SWITCH_ATTR_FDB_AGING_TIME 0`

VS プラットフォームの warm reboot ダンプでは aging time が `0`（無効）として記録されている。
これは warm-reboot 時の意図的な `setAgingFDB(0)` が適用された状態のスナップショット。

### 5. サマリ

| プラットフォーム種別 | fdb_aging_time 注入 | 初期値 | SAI Capability クエリ |
|---|---|---|---|
| 標準スイッチ (`switch_type` 未設定) | あり (600 秒) | 600 秒 | なし (直接 SET) |
| `chassis-packet` | あり (600 秒) | 600 秒 | なし (直接 SET) |
| `dpu` | なし | ASIC ハードウェアデフォルト | 該当なし (書き込み自体が発生しない) |
| VS (テスト) | あり (600 秒) → warm 後 0 | warm 後 0 | なし |
