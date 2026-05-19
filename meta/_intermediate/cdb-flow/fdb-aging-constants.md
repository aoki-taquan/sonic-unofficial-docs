# FDB Aging Time — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/switchorch.cpp` (FDB aging time SAI マッピング・polling interval)
- `sonic-swss/orchagent/orchdaemon.cpp` (warm-reboot 時 aging 無効化の即値 0)
- `sonic-buildimage/dockers/docker-orchagent/switch.json.j2` (デフォルト値 600 秒)
- `sonic-buildimage/dockers/docker-orchagent/swssconfig.sh` (sleep 1 による注入タイミング)

---

## 1. switchorch.cpp のハードコード定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `SWITCH_STAT_COUNTER_POLLING_INTERVAL_MS` | `60000` ms (= 60 秒) | スイッチ統計カウンタのフレックスカウンタ polling 間隔。`fdb_aging_time` 自体ではなく ASIC レベルの統計収集周期であるが、SwitchOrch が管理する唯一の polling 定数 | `switchorch.cpp:32` |
| SAI 属性マッピングキー | `"fdb_aging_time"` | APPL_DB フィールド名 → `SAI_SWITCH_ATTR_FDB_AGING_TIME` へのマッピングキー。`switch_attribute_map` 静的定数で確定 (`extern const`) | `switchorch.cpp:49` |
| warm-reboot 時 aging 無効化値 | `0` (uint32_t) | `setAgingFDB(0)` の即値。0 = aging 無効を SAI 仕様で規定。YANG / CONFIG_DB での管理なし | `orchdaemon.cpp:1068` |

### `SWITCH_STAT_COUNTER_POLLING_INTERVAL_MS = 60000` の詳細

```cpp
// switchorch.cpp:32
#define SWITCH_STAT_COUNTER_POLLING_INTERVAL_MS 60000
```

`SwitchOrch` コンストラクタ (`switchorch.cpp:157`) で `CounterCheckOrch` に渡される:

```cpp
m_counterManager(SWITCH_STAT_COUNTER_FLEX_COUNTER_GROUP, StatsMode::READ,
                 SWITCH_STAT_COUNTER_POLLING_INTERVAL_MS, false)
```

`fdb_aging_time` の SAI 設定には直接関係しないが、SwitchOrch が持つ唯一のハードコード polling 定数であり、aging タイマー分解能に間接的影響を与える可能性がある（aging 期間 < 60 秒の設定では状態反映が遅れ得る）。

---

## 2. switch.json.j2 のハードコード定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `fdb_aging_time` デフォルト | `"600"` (秒) | `switch_type != "dpu"` ノード向けに orchagent コンテナ起動時に自動注入される FDB aging time。YANG / CONFIG_DB に直接エントリがなく、テンプレートハードコードが唯一の注入経路 | `switch.json.j2:38` |

### テンプレート条件分岐

```jinja2
{# switch.json.j2:35-38 #}
{% if not DEVICE_METADATA.localhost.switch_type or DEVICE_METADATA.localhost.switch_type != "dpu" %}
    "fdb_aging_time": "600",
```

`switch_type == "dpu"` の場合 `fdb_aging_time` フィールドは **注入されない**（DPU ノードでは FDB aging は管理対象外）。

---

## 3. swssconfig.sh のハードコード定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| swssconfig 実行後 sleep | `1` 秒 | `swssconfig switch.json` 実行後の待機時間。orchagent Consumer キュー処理を確実に完了させるための時間的バッファ | `swssconfig.sh:100` |

### スクリプト抜粋

```sh
# swssconfig.sh:96-101
SWSSCONFIG_ARGS="ipinip.json ports.json switch.json vxlan.json"
for file in $SWSSCONFIG_ARGS; do
    swssconfig /etc/swss/config.d/$file
    sleep 1
done
```

`sleep 1` は設定ファイルごとに 1 秒待機するため、`switch.json` → `sleep 1` → `vxlan.json` の順序が保証される。

---

## 4. SLEEP_MSECONDS (orchdaemon / orch.cpp)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `SLEEP_MSECONDS` | `500` ms | orchagent メインループ内のリトライ待機時間。warm-reboot 時に SAI 呼び出しをリトライする際のバックオフ間隔 | `orch.h:57` |

これは `fdb_aging_time` SET の直接依存ではないが、warm-reboot 経路での `setAgingFDB(0)` が呼ばれる `checkRestartNoFreeze()` 判定ループで使用される。

---

## まとめ

`fdb_aging_time` に関するハードコード定数は CONFIG_DB / YANG 管理外であり、以下の 3 点が重要:

1. **デフォルト値 `600` 秒** — `switch.json.j2:38` のみで管理。`switch_type != "dpu"` 条件付き注入
2. **warm-reboot 時の即値 `0`** — aging 無効化。`orchdaemon.cpp:1068` にリテラルとして存在
3. **SAI マッピングキー `"fdb_aging_time"`** — `switch_attribute_map` の静的キー。フィールド名変更は後方互換性を破壊する
