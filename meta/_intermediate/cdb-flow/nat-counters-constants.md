# COUNTERS_DB NAT カウンタテーブル群 — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/natorch.h`
- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/schema.h`
- `sonic-swss/orchagent/orch.h`

---

## カウンタ更新タイマー周期定数 (natorch.h)

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `NAT_HITBIT_N_CNTRS_QUERY_PERIOD` | `5` 秒 | COUNTERS_NAT* の更新周期 (`natorch.h:37`) |
| `NAT_CONNTRACK_TIMEOUT_PERIOD` | `86400` 秒 | conntrack 老化チェック周期 (カウンタ非関与) (`natorch.h:38`) |
| `NAT_HITBIT_QUERY_MULTIPLE` | `6` | ヒットビット周期倍率 → 30 秒周期 (`natorch.h:39`) |

## COUNTERS_GLOBAL_NAT 初期値ハードコード (natorch.cpp コンストラクタ)

| フィールド | 値 | ソース |
|-----------|-----|--------|
| `TIMEOUT` | `600` | `natorch.cpp:67` |
| `TCP_TIMEOUT` | `86400` | `natorch.cpp:70` |
| `UDP_TIMEOUT` | `300` | `natorch.cpp:73` |

## テーブル名定数 (schema.h:260-264)

- `COUNTERS_NAT_TABLE` = `"COUNTERS_NAT"`
- `COUNTERS_NAPT_TABLE` = `"COUNTERS_NAPT"`
- `COUNTERS_TWICE_NAT_TABLE` = `"COUNTERS_TWICE_NAT"`
- `COUNTERS_TWICE_NAPT_TABLE` = `"COUNTERS_TWICE_NAPT"`
- `COUNTERS_GLOBAL_NAT_TABLE` = `"COUNTERS_GLOBAL_NAT"`

## APPL_DB 優先度定数 (orchdaemon.cpp:454-462)

`natorch_base_pri = 50`。`APP_NAT_GLOBAL_TABLE_NAME` が最低優先度 50 のため `admin_mode` 処理が最後になる。

## プラットフォーム定数

- `BRCM_PLATFORM_SUBSTRING` = `"broadcom"` (`orch.h:43`)
- Broadcom のみ `gNhTrackingSupported = true` → DNAT NH tracking 有効 (`natorch.cpp:145-148`)
