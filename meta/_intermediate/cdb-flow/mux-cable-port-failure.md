# mux-cable-port — Phase D 失敗挙動メモ

ソース: `sonic-swss/orchagent/muxorch.cpp`, `sonic-linkmgrd/src/DbInterface.cpp`

## 1. handleMuxCfg — SET 操作の失敗パターン

`MuxOrch::handleMuxCfg()` (`muxorch.cpp:2202`) は `MuxOrch::addOperation()` (`muxorch.cpp:2394`) から呼び出される。
`addOperation()` の catch ブロック (`muxorch.cpp:2409`) は `std::runtime_error` のみを捕捉し `return true`（エントリを消費、retry なし）する。

### server_ipv4 / server_ipv6 欠落
- `handleMuxCfg()` の冒頭 (`muxorch.cpp:2206-2207`) で `request.getAttrIpPrefix("server_ipv4")` と `request.getAttrIpPrefix("server_ipv6")` を**無条件**で呼び出す。
- フィールドが欠落していると `std::out_of_range` 例外が発生。
- `addOperation()` の `catch(std::runtime_error&)` はこれを捕捉しない（`out_of_range` は `logic_error` 派生）ため、例外は上位の `Orch2::doTask()` まで伝播する。
- 結果: エントリが erase され **retry なし**。orchagent は次のイベントループに進む。
- **対策**: `server_ipv4` と `server_ipv6` は SET コマンドに必ず含める。

### neighbor_mode 変更の禁止
- 既存 mux ポートに対して `neighbor_mode` を変更しようとすると (`muxorch.cpp:2258-2266`):
  - `SWSS_LOG_ERROR("Neighbor mode change is not allowed for existing mux port '%s'")` を出力
  - `return false` でエントリをリトライキューへ保留
- `PEER_SWITCH` が存在する限り同一エントリが永続的に `return false` を返し続ける → **永続 retry ループ**
- **対策**: ポートを DEL してから再 SET する。

### PEER_SWITCH 未設定
- `mux_peer_switch_.isZero()` が true の場合 (`muxorch.cpp:2271-2274`):
  - `SWSS_LOG_INFO("Mux Peer switch addr not yet configured")` を出力
  - `return false` でリトライキューへ保留
- `PEER_SWITCH` エントリが SET された後の次イベントループで自動処理される → **自動回復あり**

### isMuxExists — 重複エントリ
- ポートがすでに登録済みの場合 (`muxorch.cpp:2254-2257`):
  - `SWSS_LOG_INFO("Mux for port '%s' already exists")` → `return true`（消費、no-op）
  - STATE_DB 更新なし。APPL_DB / SAI も変更なし。

## 2. DEL 操作

`MuxOrch::handleMuxDel()` の失敗は `mux_cable_tb_` に存在しないキーを DEL した場合:
- `SWSS_LOG_NOTICE("Mux cable port not found in table, skip DEL")` を出力 → `return true`（no-op）

## 3. linkmgrd — state フィールド欠落

`DbInterface.cpp:996`:
- `getMuxModeConfig()` が `MUX_CABLE` テーブルから `state` フィールドを読み取れない場合:
  - `MUXLOGERROR("port: %s, mode mux is not found in %s table")` を出力
  - 返り値マップに当該ポートは含まれず、ポートの初期化がスキップされる。
  - **自動回復なし**（SubscriberStateTable ループで再通知されるまで未初期化のまま）

## 4. ycabled — state / soc_ipv4 欠落

`y_cable_helper.py:295-320, 660-718`:
- `check_mux_cable_port_type()`: `"state" in mux_table_dict` チェックが False → `(False, None)` を返す → gRPC セットアップ未実施
- gRPC チャネル設定関数: `"state" in dict and "soc_ipv4" in dict` が False → チャネルセットアップをスキップ
- いずれも例外なし。警告・エラーログも出力されず、**silent skip**。

## 5. ERROR_TABLE 書き込み

MUX_CABLE 処理に関して STATE_DB/ERROR_TABLE への書き込みは行われない。
エラーは `SWSS_LOG_ERROR` / `SWSS_LOG_INFO` で orchagent ログ（`/var/log/swss/orchagent.log`）にのみ出力される。
