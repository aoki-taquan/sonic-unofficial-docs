# COUNTERS_DB PORT カウンタ — Phase H: プラットフォーム差異

対象: `docs/reference/config-db/counters-port.md`
Consumer: `orchagent/portsorch.cpp`, `orchagent/flexcounterorch.cpp`

スキャン範囲:
- `isMlnxPlatform()` (`portsorch.cpp:689-698`)
- `isPortStatSupported()` (`portsorch.cpp:656-687`)
- `initCounterCapabilities()` (`portsorch.cpp:1842-1969`)
- Lua プラグイン登録コード (`portsorch.cpp:798-864`)
- gearbox 関連 (`portsorch.cpp:822-835`, `9120-9126`)
- DPU/VOQ switch type 分岐 (`portsorch.cpp:987-1056`, `8483-8512`)

---

## 1. WRED drop カウンタの SAI capability ゲート（全プラットフォーム共通処理）

### 1.1 `initCounterCapabilities()` の動作

`portsorch.cpp:1842-1969` — orchagent 起動時に 1 回だけ `sai_query_stats_capability()` を呼び、
`SAI_OBJECT_TYPE_PORT` の統計 capability を調査する。

調査対象の 4 つの WRED drop カウンタ:

| SAI stat | STATE_DB キー |
|----------|--------------|
| `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` | `WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER` |
| `SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS` | `WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER` |
| `SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS` | `WRED_ECN_PORT_WRED_RED_DROP_COUNTER` |
| `SAI_PORT_STAT_WRED_DROPPED_PACKETS` | `WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER` |

- 初期状態: 全て `{isSupported: "false"}` で STATE_DB `PORT_COUNTER_CAPABILITIES` に書き込み
- SAI query 成功かつ capability list に含まれれば `{isSupported: "true"}` に更新
- `sai_query_stats_capability()` が `SAI_STATUS_SUCCESS` / `SAI_STATUS_BUFFER_OVERFLOW` 以外を返した場合は全項目 `false` のまま

`portstat.py:297-329` はこの STATE_DB の値を参照して WRED drop フィールドを `counter_bucket_dict` に含めるか判断するため、**ASIC が WRED drop counter を実装していないプラットフォームでは portstat 表示から WRED フィールドが事前除外される**。

### 1.2 プラットフォーム別 WRED 対応状況（実装例）

| プラットフォーム種別 | WRED drop counter 対応 | 備考 |
|---------------------|----------------------|------|
| Broadcom XGS (BCM) | 実装依存（ASIC 世代によって差） | 対応世代は `true` |
| NVIDIA/Mellanox | true（典型的） | mlnx-sai が WRED drop counter を実装 |
| VS (libsaivs) | false | `sai_query_stats_capability` がスタブ応答 → `false` |
| DPU (`gMySwitchType == "dpu"`) | 実装依存 | DPU 固有のカウンタセットを持つ場合あり |
| VoQ chassis | 実装依存 | system port / fabric port の扱いが異なる |

---

## 2. Nvidia (MLNX) プラットフォーム固有: nvda_port_trim_drop.lua

### 2.1 条件

`portsorch.cpp:858-863`:

```cpp
if (isMlnxPlatform() &&
    isPortStatSupported(SAI_PORT_STAT_TRIM_PACKETS) &&
    isPortStatSupported(SAI_PORT_STAT_TX_TRIM_PACKETS) &&
    !isPortStatSupported(SAI_PORT_STAT_DROPPED_TRIM_PACKETS))
{
    portStatPlugins += "," + nvdaPortTrimSha;
}
```

3 条件がすべて成立した場合のみ `nvda_port_trim_drop.lua` を `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` の `PORT_PLUGIN_FIELD` に追加する。

- `isMlnxPlatform()`: 環境変数 `platform` に `"mellanox"` が含まれる (`portsorch.cpp:689-698`)
- `SAI_PORT_STAT_TRIM_PACKETS` / `SAI_PORT_STAT_TX_TRIM_PACKETS`: SAI capability list に含まれる
- `SAI_PORT_STAT_DROPPED_TRIM_PACKETS`: SAI capability list に**含まれない**（Nvidia 固有の代替計算が必要なケース）

### 2.2 効果

`nvda_port_trim_drop.lua` が有効になると、`SAI_PORT_STAT_DROPPED_TRIM_PACKETS` の代わりに
Lua スクリプトが `TRIM_PACKETS - TX_TRIM_PACKETS` を計算して `COUNTERS_DB` の
`SAI_PORT_STAT_DROPPED_TRIM_PACKETS` フィールドに書き込む（派生カウンタ）。

Nvidia / Mellanox 以外のプラットフォームでは、このプラグインは常にスキップされる。

---

## 3. Gearbox 有効時の GB_COUNTERS_DB

### 3.1 gearbox 判定

`isGearboxEnabled()` (`portsorch.cpp:1709`) が起動時に `_GEARBOX_TABLE` を確認して `m_gearboxEnabled` を設定する。

### 3.2 generatePortCounterMap() での分岐

`portsorch.cpp:9120-9126`:

```cpp
if (it.second.m_system_side_id)
    gb_port_stat_manager.setCounterIdList(it.second.m_system_side_id,
            CounterType::PORT, gbport_counter_stats, it.second.m_switch_id);
if (it.second.m_line_side_id)
    gb_port_stat_manager.setCounterIdList(it.second.m_line_side_id,
            CounterType::PORT, gbport_counter_stats, it.second.m_switch_id);
```

- Gearbox 有効: system-side / line-side の OID に対して `gbport_stat_ids[]` を `GB_COUNTERS_DB` に書き込む
- Gearbox 無効: このブランチはスキップされ、通常の `COUNTERS_DB` のみ更新

### 3.3 Gearbox Lua プラグイン

`portsorch.cpp:822-835`: gearbox 有効時は `port_rates.lua` を `m_gb_counter_db`（GB_COUNTERS_DB）にも別途ロードし、Gearbox ポートのレートカウンタ (`GB_COUNTERS_DB:RATES:<oid>`) を管理する。

| 条件 | 書き込み先 |
|------|----------|
| gearbox 無効 | `COUNTERS_DB` のみ |
| gearbox 有効 | `COUNTERS_DB` + `GB_COUNTERS_DB` |

---

## 4. DPU (`gMySwitchType == "dpu"`) での制限

`portsorch.cpp:987-1056`, `6449-6460`:

DPU モードでは以下がスキップされる:

| 機能 | 条件 | 備考 |
|------|------|------|
| Auto-neg FEC mode override SAI capability query | `if (gMySwitchType != "dpu")` | DPU は FEC capability の問い合わせ不要 |
| System Port の初期化 | `if (gMySwitchType != "dpu")` | DPU は System Port を持たない |
| `postPortInit()` の queue 初期化 | `if (p.m_queue_ids.size() > p.m_host_tx_queue)` | DPU では queue_ids が初期化されないプラットフォームがある |

PORT カウンタの `generatePortCounterMap()` 自体は DPU でも呼ばれるが、`gMySwitchType == "dpu"` の分岐で System Port や LAG が対象外になるため、収集対象は DPU ローカルの PHY ポートのみとなる。

---

## 5. VoQ chassis での PORT カウンタ

### 5.1 PORT カウンタ収集（変化なし）

通常の PHY ポートの PORT カウンタ収集は VoQ でも同一。`generatePortCounterMap()` は `gMySwitchType` に関係なく PHY ポート全体に適用される。

### 5.2 VOQ カウンタは常時有効（FLEX_COUNTER_TABLE に依存しない）

`portsorch.cpp:8483-8512`:

```cpp
/* voq counters are always enabled. There is no mechanism to disable voq
 * counters in a voq system. */
```

- `gMySwitchType == "voq"` の場合、egress queue と VOQ カウンタは `FLEX_COUNTER_TABLE|QUEUE = enable` に関係なく常時 `addQueueFlexCountersPerPortPerQueueIndex()` で登録される。
- この仕様は PORT カウンタ（`FLEX_COUNTER_TABLE|PORT`）には影響しない。PORT カウンタは VoQ でも通常通り enable/disable が可能。

---

## 6. VS (virtual switch) での挙動

| 項目 | VS での挙動 |
|------|------------|
| `initCounterCapabilities()` | `sai_query_stats_capability()` がスタブ → WRED 全フィールド `false` |
| `isPortStatSupported()` | スタブ応答 → `false` → nvda_port_trim_drop.lua は isMlnxPlatform() で除外 |
| PORT カウンタ収集 | SAI dummy 値 (0) を書き込む |
| FEC カウンタ | `SAI_PORT_STAT_IF_IN_FEC_*` はスタブなので値 0 |
| Gearbox | VS では `_GEARBOX_TABLE` が空 → gearbox 無効 |

VS での counterpoll / portstat テストは mock SAI を使うため、値の検証は機能テストでのみ行われる。

---

## プラットフォーム差異サマリ

| 差異 | Broadcom | Mellanox/NVIDIA | VS/VPP | DPU | VoQ chassis |
|------|----------|-----------------|--------|-----|-------------|
| WRED drop counter | ASIC 依存 | 典型的に `true` | `false` | ASIC 依存 | ASIC 依存 |
| nvda_port_trim_drop.lua | 無効 | 条件次第で有効 | 無効 | 無効 | 無効 |
| Gearbox GB_COUNTERS_DB | 環境依存 | 環境依存 | 無効 | 無効 | 環境依存 |
| VOQ カウンタ常時有効 | N/A | N/A | N/A | N/A | Yes |
| PORT カウンタ収集対象 | PHY ポートのみ | PHY ポートのみ | PHY ポートのみ | PHY ポートのみ | PHY ポートのみ |
