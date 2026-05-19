# SWITCH_TABLE.fdb_aging_time — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/fdb-aging.md`
解析日: 2026-05-19
根拠ソース: `sonic-buildimage/dockers/docker-orchagent/switch.json.j2` / `sonic-swss/orchagent/switchorch.cpp` / `sonic-swss/orchagent/orchdaemon.cpp`

---

## 目的

`SWITCH_TABLE:switch` の `fdb_aging_time` フィールドが注入される過程で、`switch.json.j2` テンプレートが
**暗黙的に参照する** CONFIG_DB テーブル/フィールドを網羅する。
YANG に leafref 定義がないため、依存はコードのみで表現される。

---

## 1. DEVICE_METADATA|localhost.switch_type (注入条件分岐)

### 参照箇所

`switch.json.j2:35`

```jinja2
{% if not DEVICE_METADATA.localhost.switch_type or DEVICE_METADATA.localhost.switch_type != "dpu" %}
    "ecmp_hash_seed": "{{ hash_seed_value }}",
    "lag_hash_seed": "{{ hash_seed_value }}",
    "fdb_aging_time": "600",
```

### 依存内容

| 参照元 | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| `switch.json.j2` (注入条件) | `DEVICE_METADATA` | `localhost.switch_type` | orchagent コンテナ起動時 (Jinja2 展開) |

### 特記事項

- `switch_type` が未設定または `"dpu"` 以外の場合、`fdb_aging_time: "600"` が APPL_DB `SWITCH_TABLE:switch` に注入される。
- `switch_type = "dpu"` のノードは `fdb_aging_time` が注入されないため、SAI へは設定されない。
- 欠如は注入スキップではなく「条件が true になる」ため、むしろ未設定の方が注入される（Jinja2 の `not` 評価）。

---

## 2. DEVICE_METADATA|localhost.namespace_id (hash_seed 算出の副次参照)

### 参照箇所

`switch.json.j2:28-31`

```jinja2
{% if DEVICE_METADATA.localhost.namespace_id %}
{% set hash_seed_offset = DEVICE_METADATA.localhost.namespace_id | int %}
{% endif %}
{% set hash_seed_value = hash_seed_offset + hash_seed %}
```

### 依存内容

| 参照元 | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| `switch.json.j2` (hash_seed 算出) | `DEVICE_METADATA` | `localhost.namespace_id` | orchagent コンテナ起動時 (Jinja2 展開) |

### 特記事項

- `fdb_aging_time` フィールド自体への直接影響はないが、同一 `switch.json.j2` テンプレート内で
  `ecmp_hash_seed` / `lag_hash_seed` の算出に使われる。
- `namespace_id` 未設定の場合は `hash_seed_offset = 0` となり、デフォルト hash_seed が使用される。
- multi-asic 構成では各 ASIC の namespace_id が異なるため hash_seed が分散する。

---

## 3. FdbOrch / orchdaemon の内部参照 (間接)

### 参照箇所

`orchdaemon.cpp:1065-1068`

```cpp
if (!gSwitchOrch->checkRestartNoFreeze())
{
    // Disable FDB aging
    gSwitchOrch->setAgingFDB(0);
```

`switchorch.cpp:1671-1688` (`setAgingFDB`)

```cpp
bool SwitchOrch::setAgingFDB(uint32_t sec)
{
    sai_attribute_t attr;
    attr.id = SAI_SWITCH_ATTR_FDB_AGING_TIME;
    attr.value.u32 = sec;
    auto status = sai_switch_api->set_switch_attribute(gSwitchId, &attr);
    ...
}
```

### 依存内容

`setAgingFDB(0)` は APPL_DB `SWITCH_TABLE` を経由せず直接 SAI API を呼ぶため、cross-refs（他テーブルへの leafref 依存）ではない。
warm-reboot 時の一時無効化として Phase B 順序依存に記載済み。

---

## 4. cross-refs ブロック (最終形)

以下を `<!-- glossary-links-injected: fdb-aging -->` 直前に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`fdb_aging_time` フィールドはコードの直接 leafref 参照を持たないが、値の**注入元テンプレート**
`switch.json.j2` が CONFIG_DB `DEVICE_METADATA` を暗黙的に参照して注入条件を決定する。

### switch.json.j2 → DEVICE_METADATA 参照一覧

| 参照元 (テンプレート) | 参照先テーブル | 参照先フィールド | 参照タイミング | 効果 |
|---|---|---|---|---|
| `switch.json.j2:35` | `DEVICE_METADATA` | `localhost.switch_type` | orchagent コンテナ起動時 | `"dpu"` のとき `fdb_aging_time` 注入をスキップ |
| `switch.json.j2:28-31` | `DEVICE_METADATA` | `localhost.namespace_id` | orchagent コンテナ起動時 | multi-asic 時の `ecmp_hash_seed` / `lag_hash_seed` オフセット計算（`fdb_aging_time` 自体には影響なし） |

### 注入スキップ条件

`DEVICE_METADATA|localhost` の `switch_type` が `"dpu"` に設定されている場合、`switch.json.j2` は
`fdb_aging_time` フィールドを生成しない。この場合 APPL_DB `SWITCH_TABLE:switch` に当フィールドが書き込まれず、
SAI `SAI_SWITCH_ATTR_FDB_AGING_TIME` は orchagent 初期化時のハードウェアデフォルト値のままになる。

### 直接 APPL_DB 参照なし

`SwitchOrch::doAppSwitchTableTask()` は `fdb_aging_time` 値を処理するにあたり、他の CONFIG_DB / APPL_DB
テーブルを参照しない（値をそのまま `uint32_t` にキャストして SAI に渡す）。
`orchdaemon.cpp` の warm-reboot パスが呼ぶ `setAgingFDB(0)` も APPL_DB を経由せず直接 SAI API を呼ぶため、
cross-refs としての依存テーブルはない（Phase B 順序依存として記載済み）。
<!-- /cross-refs -->
```
