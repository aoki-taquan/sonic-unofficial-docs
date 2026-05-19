# fdb-aging Phase H — プラットフォーム差異スキャンノート

Generated: 2026-05-19
Target doc: docs/reference/config-db/fdb-aging.md

対象: APPL_DB `SWITCH_TABLE:switch` の `fdb_aging_time` フィールド
スキャン範囲: `switch.json.j2:35-48`, `switchorch.cpp:49,664-666`, `orchdaemon.cpp:190`

---

## 1. プラットフォーム識別の主体

`SwitchOrch::doAppSwitchTableTask()` (`switchorch.cpp:595-748`) には `isMlnxPlatform()` のようなプラットフォーム識別コードが一切存在しない。`SAI_SWITCH_ATTR_FDB_AGING_TIME` の処理は `to_uint<uint32_t>(value)` でキャストするのみで、プラットフォーム条件分岐はない (`switchorch.cpp:664-666`)。

プラットフォーム差異は SAI レイヤより上位の **`switch.json.j2` テンプレート展開時**にのみ発生する。

---

## 2. switch.json.j2 による注入可否の差異

`switch.json.j2:35` の Jinja2 条件式:

```jinja2
{% if not DEVICE_METADATA.localhost.switch_type or DEVICE_METADATA.localhost.switch_type != "dpu" %}
    "ecmp_hash_seed": "{{ hash_seed_value }}",
    "lag_hash_seed": "{{ hash_seed_value }}",
    "fdb_aging_time": "600",
...
{% endif %}
```

`switch_type == "dpu"` のノード（SmartSwitch DPU スロット）では `fdb_aging_time` フィールドが APPL_DB に**注入されない**。

| `switch_type` 値 | `fdb_aging_time` 注入 | 備考 |
|---|---|---|
| 未設定（通常スイッチ） | される (`"600"`) | ToRRouter / LeafRouter / SpineRouter 等 |
| `"dpu"` | されない | SmartSwitch DPU スロット (DASH ノード) |
| `"chassis-packet"` | される (`"600"`) | `dpu` でないため条件を通過 |
| その他 (任意文字列) | される (`"600"`) | `dpu` 以外は全て注入 |

evidence: `sonic-buildimage/dockers/docker-orchagent/switch.json.j2:35-38`
evidence (DPU 非注入の実証): `sonic-buildimage/src/sonic-config-engine/tests/sample_output/t1-smartswitch-dpu.json` — `SWITCH_TABLE` エントリが存在しない

---

## 3. DPU 環境での SAI 挙動

`switch_type == "dpu"` のノードでは `fdb_aging_time` が APPL_DB に書き込まれないため、SAI `SAI_SWITCH_ATTR_FDB_AGING_TIME` は orchagent 起動時の ASIC ハードウェアデフォルト値のままになる。SONiC は DPU ノードを DASH (Data-plane Acceleration with Disaggregated Hardware) ターゲットとして扱い、従来の Ethernet スイッチング (FDB aging) を必要としない。

---

## 4. ASIC 固有 SAI capability の有無

`switchorch.cpp:683-703` では `SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_OFFSET` および `SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_OFFSET` に対して `querySwitchCapability()` による SAI capability チェックが実施されているが、`SAI_SWITCH_ATTR_FDB_AGING_TIME` (`switchorch.cpp:664-666`) にはこのチェックが存在しない。すべての ASIC において `SAI_SWITCH_ATTR_FDB_AGING_TIME` は capability チェックなしで直接 `set_switch_attribute()` される。

---

## 5. multi-asic 環境

`orchdaemon.cpp:190` で `platform = getenv("platform")` が取得されるが、`SwitchOrch` はこの値を `fdb_aging_time` の処理で使用しない。multi-asic 環境では各 asic namespace ごとに orchagent が起動し、それぞれ独立した `switch.json.j2` 展開により `fdb_aging_time: "600"` が注入される。`switch.json.j2:28-31` の `namespace_id` は `ecmp_hash_seed` / `lag_hash_seed` のオフセット計算にのみ使用され、`fdb_aging_time` には影響しない。

evidence: `switch.json.j2:28-31`, `t2-switch-masic1.json` (全 asic 共通 `"fdb_aging_time": "600"`)

---

## まとめ

| 条件 | `fdb_aging_time` 注入 | SAI 設定値 | 備考 |
|---|---|---|---|
| 通常スイッチ (switch_type 未設定) | あり | `600` 秒 | ToR / Leaf / Spine 等 |
| chassis-packet ノード | あり | `600` 秒 | chassis-packet は `dpu` 条件を通過 |
| SmartSwitch DPU (switch_type=dpu) | なし | ASIC ハードウェアデフォルト | DASH ターゲット; FDB aging 不要 |
| multi-asic 各 namespace | あり | `600` 秒 (全 namespace 共通) | namespace_id は aging time に影響しない |
| 全 ASIC ベンダー共通 | — | SAI capability チェックなし | 直接 set_switch_attribute() |
