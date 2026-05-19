# CONFIG_DB プラットフォーム差異分析: HEARTBEAT (Phase H)

## 概要

`HEARTBEAT` テーブルは SAI / ASIC 経由の設定ではなく、ホストサービス (`supervisor-proc-exit-listener`) の watchdog 設定を管理する。そのため ASIC Capability 依存・ベンダー固有分岐は存在しない。

## 調査結果

### 1. supervisor-proc-exit-listener — プラットフォーム分岐なし

`sonic-buildimage/src/sonic-supervisord-utilities/scripts/supervisor-proc-exit-listener` を全文走査したところ:
- `platform` / `asic_type` / `switch_type` 参照ゼロ件
- `mellanox` / `broadcom` 等のベンダー文字列判定ゼロ件
- `voq` / `multi-asic` 分岐ゼロ件

Rust 版 (`proc_exit_listener.rs`) も同様にプラットフォーム依存コードなし。

### 2. orchagent.sh — heartbeat_interval は全プラットフォーム共通

`orchagent.sh:126-130` でプラットフォーム (broadcom / mellanox 等) の分岐と独立した後に `HEARTBEAT|orchagent.heartbeat_interval` を読む。
`-I <interval>` フラグは全プラットフォームで同一処理。

```bash
HEARTBEAT_INTERVAL=`sonic-db-cli CONFIG_DB hget  "HEARTBEAT|orchagent" "heartbeat_interval"`
if [ ! -z "$HEARTBEAT_INTERVAL" ] && [ $HEARTBEAT_INTERVAL != "null" ]; then
    ORCHAGENT_ARGS+=" -I $HEARTBEAT_INTERVAL"
fi
```

orchagent 側 (`main.cpp:75`) のデフォルト値 `HEART_BEAT_INTERVAL_MSECS_DEFAULT = 10000 ms` はプラットフォーム非依存。

### 3. multi-ASIC 環境での挙動

multi-ASIC ではコンテナ名前空間 (NAMESPACE_ID) ごとに独立した orchagent インスタンスが起動する。各インスタンスが同一 CONFIG_DB の `HEARTBEAT|orchagent` を読むため、ASIC 数に関係なく同一値が使われる。ただし CONFIG_DB 自体が名前空間ごとに分かれる場合は各 DB インスタンスで個別設定が必要。

### 4. vs (virtual switch) での挙動

`supervisor-proc-exit-listener` は vs でも同一コードで動作する。vs 環境では SAI 非経由のため、heartbeat 監視が動作することに差異はない。

## 結論

HEARTBEAT テーブルの全消費者はホストサービス層に閉じており、ASIC 種別・ベンダー・switch_type・voq による挙動差異は存在しない。
