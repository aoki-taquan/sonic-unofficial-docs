# LOSSLESS_TRAFFIC_PATTERN — Phase D 失敗・リトライ挙動 調査ノート

## 調査対象

- `sonic-swss/cfgmgr/buffermgrdyn.cpp` — `calculateHeadroom()`, `recalculateSharedBufferPool()`
- `sonic-swss/cfgmgr/buffer_headroom_mellanox.lua` — L88-100
- `sonic-swss/cfgmgr/buffer_headroom_barefoot.lua` — L80-92

## 失敗パターン

### 1. Lua エラー（エントリなし）

`buffer_headroom_<vendor>.lua` は `KEYS 'LOSSLESS_TRAFFIC_PATTERN*'` でキー一覧を取得し
`lossless_traffic_keys[1]` を `HGETALL` する。エントリが 0 件の場合 `lossless_traffic_keys[1]` は
`nil` → Lua エラー。

C++ 側では `calculateHeadroom()` が `runRedisScript()` を try/catch で囲んでいる。
例外が発生すると `SWSS_LOG_WARN("Lua scripts for headroom calculation were not executed successfully")` を
記録して return する。headroom 計算が失敗した場合、対応する BUFFER_PROFILE は APPL_DB に転送されない。

evidence: `buffer_headroom_mellanox.lua:91-94`, `buffer_headroom_barefoot.lua:80-83`, `buffermgrdyn.cpp:645-648`

### 2. フィールド欠損 → tonumber(nil) → 計算失敗

`mtu` または `small_packet_percentage` フィールドが DB に存在しない場合、
Lua の `tonumber(nil)` は `nil` を返す。Lua の算術演算は `nil` と数値の演算でエラーになるため、
ヘッドルーム計算式が失敗する。

YANG では両フィールドが `mandatory true` のため、CLI 経由では発生しないが、
手動 redis-cli 書き込みやバグのある producer がフィールドを省略した場合に起きる。

### 3. 計算結果が空 → ret.empty() → WARN

Lua が正常に返ってきたが `xon`/`xoff`/`size` フィールドが一切含まれない空リストを返した場合、
C++ 側の `calculateHeadroom()` は `SWSS_LOG_WARN("Failed to calculate headroom for %s")` を
記録して return する。

evidence: `buffermgrdyn.cpp:621-623`

### 4. static buffer モードではエラーなし（silent skip）

`buffermgr.cpp`（static buffer モード）は `LOSSLESS_TRAFFIC_PATTERN` テーブルを一切参照しない。
static モードで値を変更しても計算は行われず、エラーも発生しない（silent skip）。

### 5. DEL 操作の非サポート

`buffermgrdyn` は `LOSSLESS_TRAFFIC_PATTERN` テーブルを C++ コードで明示的に購読していない。
テーブルの DEL は Lua プラグインが次回実行時に `KEYS` で取得した際に 0 件となり、
上記 1 のエラーが発生する。DEL 後は全 lossless ポートのヘッドルーム再計算が失敗状態に入る。

## 復旧方法

失敗後に正しい値で `LOSSLESS_TRAFFIC_PATTERN|AZURE` を SET すると、
次回 buffermgrdyn が当テーブルへの変更（または関連テーブル変更）でトリガされた際に
ヘッドルーム計算が再実行される。
