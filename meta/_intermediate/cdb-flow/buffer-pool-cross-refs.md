# BUFFER_POOL — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/buffer-pool.md` Phase C 追加分。
YANG leafref は `BUFFER_PROFILE.pool → BUFFER_POOL.name` の被参照のみで、
BUFFER_POOL 自身からの leafref はない。実装上の全外部テーブル参照が「暗黙参照」に相当する。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/cfgmgr/buffermgrdyn.cpp` | `BufferMgrDynamic` — dynamic buffer model のメインハンドラ |
| `sonic-swss/cfgmgr/buffermgr.cpp` | `BufferMgr` — static buffer model のメインハンドラ |
| `sonic-swss/cfgmgr/buffermgrd.cpp` | エントリポイント — 購読テーブルリスト定義 |
| `sonic-swss/cfgmgr/buffer_headroom_mellanox.lua` | Mellanox headroom 計算 Lua plugin |
| `sonic-swss/cfgmgr/buffer_pool_mellanox.lua` | Mellanox pool size 計算 Lua plugin |
| `sonic-swss/cfgmgr/buffer_headroom_barefoot.lua` | Barefoot headroom 計算 Lua plugin |
| `sonic-swss/cfgmgr/buffer_pool_barefoot.lua` | Barefoot pool size 計算 Lua plugin |
| `sonic-swss/orchagent/bufferorch.cpp` | `BufferOrch` — APPL_DB → SAI 変換（外部テーブル参照なし） |

## YANG leafref

BUFFER_POOL 自身が他テーブルを leafref で参照する定義はない。
（被参照: `BUFFER_PROFILE.pool` が `BUFFER_POOL.name` を leafref する）

## 暗黙参照 (実装レベル)

### 1. DEFAULT_LOSSLESS_BUFFER_PARAMETER (CONFIG_DB)

- **参照先テーブル**: `DEFAULT_LOSSLESS_BUFFER_PARAMETER`
- **参照方向**: 購読 + 読み取り
- **条件**: dynamic buffer model (`buffermgrdyn`) 起動時のみ
- **参照元**:
  - `buffermgrdyn.cpp:40` — `m_cfgDefaultLosslessBufferParam(cfgDb, CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER)` メンバ初期化
  - `buffermgrdyn.cpp:442` — `handleDefaultLossLessBufferParam` ハンドラを `m_bufferTableHandlerMap` に登録
  - `buffermgrdyn.cpp:150-153` — 起動時に `getKeys()` + `hget()` で `default_dynamic_th` 初期値を読み取り
  - `buffermgrdyn.cpp:1978-2040` — `handleDefaultLossLessBufferParam()` 実装
  - `buffer_headroom_mellanox.lua:105-109` — `KEYS('DEFAULT_LOSSLESS_BUFFER_PARAMETER*')` で `over_subscribe_ratio` を取得
  - `buffer_pool_mellanox.lua:261-268` — 同上
- **読み取りフィールド**: `default_dynamic_th`、`over_subscribe_ratio`
- **意味**:
  - `over_subscribe_ratio` が非ゼロになると SHP (Shared Headroom Pool) が有効化され、`ingress_lossless_pool` の xoff が計算・設定される。
  - ゼロに戻ると SHP が無効化され全プロファイルの headroom が再計算される。
  - `default_dynamic_th` は `BUFFER_PROFILE` に `dynamic_th` 未指定の場合のフォールバック値。
  - `ingress_lossless_pool` が未設定の状態での SET は `task_need_retry` (`buffermgrdyn.cpp:1987-1992`)。

### 2. ASIC_TABLE (STATE_DB)

- **参照先テーブル**: `ASIC_TABLE` (STATE_DB — 通常の CONFIG_DB ではない)
- **参照方向**: 読み取り（Lua plugin 経由、C++ から直接参照なし）
- **条件**: dynamic buffer model の headroom / pool size Lua 計算時のみ（Mellanox・Barefoot のみ）
- **参照元**:
  - `buffer_headroom_mellanox.lua:62-88` — `KEYS('ASIC_TABLE*')` + `HGETALL`
  - `buffer_pool_mellanox.lua:289-310` — 同上
  - `buffer_headroom_barefoot.lua:57-75` — `KEYS('ASIC_TABLE*')` + `HGETALL`
  - `buffer_pool_barefoot.lua:9-20` — 同上
- **読み取りフィールド**: `cell_size`、`pipeline_latency`、`mac_phy_delay`、`peer_response_time`
- **意味**:
  - ASIC の物理パラメータ（セルサイズ、パイプライン遅延等）を headroom 計算式の定数として使用する。
  - `cell_size` はバイト→セル変換に使用。`pipeline_latency` と `mac_phy_delay` はトラフィックがパイプラインを通過する間に到着するデータ量の推定に使用。
  - `ASIC_TABLE` 未設定時は Lua 算術エラーで headroom 計算失敗 → `buffermgrdyn.cpp:648` WARN ログ。
  - `bufferorch.cpp` は `ASIC_TABLE` を参照しない（Lua plugin 専用）。

### 3. LOSSLESS_TRAFFIC_PATTERN (CONFIG_DB)

- **参照先テーブル**: `LOSSLESS_TRAFFIC_PATTERN`
- **参照方向**: 読み取り（Lua plugin 経由、C++ から直接参照なし）
- **条件**: dynamic buffer model の headroom 計算時（Mellanox・Barefoot のみ）
- **参照元**:
  - `buffer_headroom_mellanox.lua:91-103` — `KEYS('LOSSLESS_TRAFFIC_PATTERN*')` + `HGETALL`
  - `buffer_headroom_barefoot.lua:80-93` — 同上
- **読み取りフィールド**: `mtu`、`small_packet_percentage`
- **意味**:
  - `mtu` はロスレスパケットの最大サイズ。headroom 計算の上限バウンド。
  - `small_packet_percentage` はワーストケースのセル利用率補正係数（%）。値が高いほど headroom が増加し `ingress_lossless_pool.xoff`（SHP サイズ）が拡大方向に動く。
  - 未設定時は Lua の変数が nil となり headroom 計算失敗。

### 4. PORT_QOS_MAP (CONFIG_DB)

- **参照先テーブル**: `PORT_QOS_MAP`
- **参照方向**: 購読 + 読み取り
- **条件**: static buffer model (`buffermgr`) 起動時のみ（dynamic model では不使用）
- **参照元**:
  - `buffermgrd.cpp:201` — 購読テーブルリストに `CFG_PORT_QOS_MAP_TABLE_NAME` を追加（static model 分岐）
  - `buffermgr.cpp:517-519` — `doTask()` 内で `doPortQosTableTask()` にルーティング
  - `buffermgr.cpp:416-462` — `doPortQosTableTask()` 実装
  - `buffermgr.cpp:167-176` — PORT_QOS_MAP 未到着時の BUFFER_PG 通知クリア処理
- **読み取りフィールド**: `pfc_enable`
- **意味**:
  - `pfc_enable` の変化（PFC 有効キューの追加/削除）を検知すると `doSpeedUpdateTask()` を呼び出し、当該ポートの headroom プロファイルを再計算して APPL_DB へ書き込む。
  - PFC 有効キューが増えると lossless PG が増え `ingress_lossless_pool` の実効消費が増加するため、BUFFER_POOL の使用量に間接影響する。
  - `PORT_QOS_MAP` が未到達の状態で `BUFFER_PG` 通知が来た場合、通知をクリアして `pfc_enable` 到着後に再処理 (`buffermgr.cpp:175`)。

## 参照関係サマリ

```
BUFFER_POOL
  ├─ [暗黙/dynamic-only] CONFIG_DB.DEFAULT_LOSSLESS_BUFFER_PARAMETER
  │     over_subscribe_ratio → SHP 有効/無効 切替
  │     default_dynamic_th  → フォールバック alpha 閾値
  ├─ [暗黙/lua-only]     STATE_DB.ASIC_TABLE
  │     cell_size / pipeline_latency / mac_phy_delay / peer_response_time
  │     → headroom 計算定数（Mellanox/Barefoot Lua plugin）
  ├─ [暗黙/lua-only]     CONFIG_DB.LOSSLESS_TRAFFIC_PATTERN
  │     mtu / small_packet_percentage
  │     → headroom 計算パラメータ（Mellanox/Barefoot Lua plugin）
  └─ [暗黙/static-only]  CONFIG_DB.PORT_QOS_MAP
        pfc_enable → headroom 再計算トリガ（buffermgr static model）
```

## evidence

- `buffermgrdyn.cpp`: L40 (メンバ初期化), L150-153 (起動時読み取り), L442 (ハンドラ登録), L605-815 (Lua 計算呼び出し・結果処理), L1978-2040 (`handleDefaultLossLessBufferParam()`)
- `buffermgr.cpp`: L167-176 (PORT_QOS_MAP 未到着ガード), L413-462 (`doPortQosTableTask()`), L517-519 (ルーティング)
- `buffermgrd.cpp`: L183-201 (購読テーブルリスト)
- `buffer_headroom_mellanox.lua`: L9-16 (コメント定義), L62-88 (ASIC_TABLE 読み取り), L91-103 (LOSSLESS_TRAFFIC_PATTERN 読み取り), L105-109 (DEFAULT_LOSSLESS_BUFFER_PARAMETER 読み取り)
- `buffer_pool_mellanox.lua`: L261-268 (DEFAULT_LOSSLESS_BUFFER_PARAMETER), L289-310 (ASIC_TABLE)
- `buffer_headroom_barefoot.lua`: L8-11 (コメント), L57-75 (ASIC_TABLE), L80-93 (LOSSLESS_TRAFFIC_PATTERN)
- `buffer_pool_barefoot.lua`: L9-20 (ASIC_TABLE)
