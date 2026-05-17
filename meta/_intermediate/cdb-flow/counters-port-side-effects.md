# COUNTERS_DB PORT カウンタ — Phase F 副作用スキャンノート

対象: `FLEX_COUNTER_TABLE|PORT` / `PORT_BUFFER_DROP` / `WRED_ECN_PORT` の enable/disable 時に  
orchagent / syncd が COUNTERS_DB 以外のどのテーブル・状態を書き換えるかを追跡する。  
スキャン範囲: `portsorch.cpp` (コンストラクタ, generatePortCounterMap, generatePortBufferDropCounterMap,  
generateWredPortCounterMap, ctor Lua 登録ブロック), `flexcounterorch.cpp` (doTask)  
コミット: `4305596156d7`

---

## 検出した副作用

### 1. FLEX_COUNTER_DB への COUNTER_ID_LIST 書き込み（enable 時）

`FLEX_COUNTER_TABLE|PORT FLEX_COUNTER_STATUS=enable` を受信すると `flexcounterorch.cpp:239` で  
`gPortsOrch->generatePortCounterMap()` が呼ばれる。この関数は各 PHY ポートに対して  
`port_stat_manager.setCounterIdList()` を実行し、以下の FLEX_COUNTER_DB エントリを書く:

```
FLEX_COUNTER_DB:PORT_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>:COUNTER_ID_LIST
  = "SAI_PORT_STAT_IF_IN_OCTETS,SAI_PORT_STAT_IF_IN_UCAST_PKTS,..."
```

これは COUNTERS_DB ではなく **FLEX_COUNTER_DB**（Redis DB index 5）への書き込み。  
syncd が FLEX_COUNTER_DB を監視し、COUNTER_ID_LIST を受け取ってポーリングを開始する。  
evidence: `portsorch.cpp:9118-9119`, `flexcounterorch.cpp:239-241`

### 2. FLEX_COUNTER_DB の COUNTER_ID_LIST クリア（disable / ポート削除時）

`FLEX_COUNTER_TABLE|PORT FLEX_COUNTER_STATUS=disable` または物理ポート削除時に  
`port_stat_manager.clearCounterIdList(port.m_port_id)` が呼ばれ、  
FLEX_COUNTER_DB の当該エントリが削除される。syncd はポーリングを停止する。  
**COUNTERS_DB の値は削除されず残留する**（最後のポーリング値が stale として残る）。  
evidence: `portsorch.cpp:3954-3955`, `portsorch.cpp:4280-4289`

### 3. orch 起動時の STATE_DB:PORT_COUNTER_CAPABILITIES 書き込み（WRED 能力）

`PortsOrch` コンストラクタで `initCounterCapabilities()` が呼ばれ、ASIC の SAI ケイパビリティを  
問い合わせた結果を STATE_DB に書き込む。PORT カウンタ enable/disable とは独立して、  
**orchagent 起動時に 1 回だけ**発生する副作用:

```
STATE_DB:PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER   {isSupported: "false"|"true"}
STATE_DB:PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER  {isSupported: "false"|"true"}
STATE_DB:PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_RED_DROP_COUNTER     {isSupported: "false"|"true"}
STATE_DB:PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER   {isSupported: "false"|"true"}
```

`portstat.py` はこのテーブルを参照して、WRED drop カウンタフィールドを  
`counter_bucket_dict` に含めるかどうかを決定する (`portstat.py:297-329`)。  
evidence: `portsorch.cpp:1842-1980`

### 4. port_rates.lua / port_flr.lua による COUNTERS_DB:RATES:<oid> 書き込み

`PortsOrch` コンストラクタで `port_rates.lua` と `port_flr.lua` を Redis にロードし、  
`PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` に Lua プラグインとして登録する  
（`setFlexCounterGroupParameter(..., PORT_PLUGIN_FIELD, portStatPlugins)`、`portsorch.cpp:879-882`）。

syncd が 1 s ごとのポーリングサイクルで Lua スクリプトを実行し、収集した SAI 生カウンタから  
レートを計算して **COUNTERS_DB:RATES:<oid>** に書き込む（`port_rates.lua` が RX_BPS/TX_BPS/  
RX_PPS/TX_PPS/RX_UTIL/TX_UTIL/FEC_PRE_BER/FEC_POST_BER/FEC_FLR 等を書く）。  
この書き込みは `FLEX_COUNTER_TABLE|PORT=enable` 後、syncd がポーリングを開始してから発生する。  
disable 時は Lua 実行が停止し、RATES:<oid> の値が stale のまま残る。  
evidence: `portsorch.cpp:801-882`

### 5. Nvidia プラットフォーム固有: nvda_port_trim_drop.lua の登録

`isMlnxPlatform()` かつ `SAI_PORT_STAT_TRIM_PACKETS` がサポートされ  
`SAI_PORT_STAT_DROPPED_TRIM_PACKETS` が非サポートの場合、  
`nvda_port_trim_drop.lua` が `portStatPlugins` に追加される（`portsorch.cpp:862-870`）。  
このプラグインは Trimming カウンタの派生値を計算して COUNTERS_DB に書き込む。  
非 Nvidia プラットフォームではこの副作用は発生しない。

### 6. GB_COUNTERS_DB への Gearbox カウンタ書き込み（Gearbox 有効時のみ）

`m_gearboxEnabled` が true の場合、コンストラクタで `GB_COUNTERS_DB` に接続し  
`COUNTERS_PORT_NAME_MAP` を `GB_COUNTERS_DB` にも書き込む（`portsorch.cpp:10392-10393`）。  
`generatePortCounterMap()` が `gb_port_stat_manager.setCounterIdList()` を呼び、  
FLEX_COUNTER_DB の Gearbox グループに system-side / line-side の COUNTER_ID_LIST を書く。  
通常の COUNTERS_DB とは独立した DB インデックスを使用。  
evidence: `portsorch.cpp:9121-9126`

---

## 副作用サマリ

| トリガー | 副作用 DB/テーブル | 内容 | 持続性 |
|---|---|---|---|
| `FLEX_COUNTER_TABLE\|PORT = enable` | FLEX_COUNTER_DB | `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>:COUNTER_ID_LIST` 書き込み | syncd ポーリング開始まで持続 |
| `FLEX_COUNTER_TABLE\|PORT = disable` / ポート削除 | FLEX_COUNTER_DB | COUNTER_ID_LIST 削除（ポーリング停止）| 即時 |
| orchagent 起動時（PORT enable と独立） | STATE_DB | `PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_*` ASIC ケイパビリティ書き込み | orchagent 生存中永続 |
| syncd ポーリングサイクル（PORT enable 後） | COUNTERS_DB | `RATES:<oid>` にレート・BER・FLR 値書き込み（port_rates.lua / port_flr.lua） | disable 後も stale 残留 |
| Nvidia + Trim サポートあり + PORT enable 後 | COUNTERS_DB | nvda_port_trim_drop.lua による派生 Trim カウンタ書き込み | Nvidia プラットフォーム固有 |
| Gearbox 有効 + PORT enable | FLEX_COUNTER_DB / GB_COUNTERS_DB | Gearbox system/line-side COUNTER_ID_LIST + COUNTERS_PORT_NAME_MAP 書き込み | Gearbox 固有 |
