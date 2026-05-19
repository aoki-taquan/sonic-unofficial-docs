# HEARTBEAT — プラットフォーム差調査

Task F Phase H: `HEARTBEAT` テーブル適用時のプラットフォーム/構成差を `sonic-buildimage` の関連アセットから精読した結果。

## 結論

**プラットフォーム差はほぼなし**。ただし `HEARTBEAT|orchagent` エントリのみ、`orchagent.sh` がプラットフォームに依存する形で heartbeat interval を orchagent プロセスへ引き渡す。multi-asic 環境では名前空間ごとに独立した orchagent インスタンスが存在し、各インスタンスが自身の namespace の CONFIG_DB から `HEARTBEAT|orchagent` を読む。Virtual Switch (vs) プラットフォームでは orchagent.sh が同一経路で動作するため差異なし。

## 根拠

### 1. YANG モジュールは host スコープのみ

`sonic-heartbeat.yang` は `container sonic-heartbeat → container HEARTBEAT → list HEARTBEAT_LIST` の 3 層構造であり、namespace や asic 分岐を持たない。YANG に `when` 条件や `if-feature` はなく、すべてのプラットフォームで同一スキーマが適用される。

### 2. 主消費者 `supervisor-proc-exit-listener` はプラットフォーム非依存

Python 版 (`sonic-supervisord-utilities/scripts/supervisor-proc-exit-listener:124-135`) および Rust 版 (`sonic-supervisord-utilities-rs/src/proc_exit_listener.rs:212-233`) はともに `get_table("HEARTBEAT")` で全エントリを一括読み込みするのみで、`platform` / `asic_type` / `is_multi_npu()` の参照はゼロ。コンテナ名 (`-c <container_name>`) を引数として受け取るが、`HEARTBEAT` 読み込みロジックには影響しない。

### 3. `orchagent.sh` に唯一のプラットフォーム関連エントリ読み込み

`dockers/docker-orchagent/orchagent.sh:127-130`:

```sh
HEARTBEAT_INTERVAL=`sonic-db-cli CONFIG_DB hget "HEARTBEAT|orchagent" "heartbeat_interval"`
if [ ! -z "$HEARTBEAT_INTERVAL" ] && [ $HEARTBEAT_INTERVAL != "null" ]; then
    ORCHAGENT_ARGS+=" -I $HEARTBEAT_INTERVAL"
fi
```

`HEARTBEAT|orchagent` の `heartbeat_interval` のみを読み、orchagent プロセスに `-I <ms>` 引数として渡す。`orchagent.sh` 中の他の `platform` 分岐（ASIC 種別ごとの MAC アドレス処理 L72-103、SmartSwitch ZMQ アドレス L105-118）は HEARTBEAT エントリ読み込みパスとは独立しており、heartbeat_interval の取得に ASIC 種別は影響しない。

### 4. multi-asic 環境での挙動

multi-asic 環境では各 `asic<N>` namespace ごとに orchagent インスタンスが起動し、それぞれが `$NAMESPACE_ID` で参照する namespace の CONFIG_DB に接続する (`orchagent.sh` ではなく namespace 起動スクリプト経由)。`HEARTBEAT|orchagent` エントリが host CONFIG_DB のみに存在する場合、asic namespace CONFIG_DB には反映されないため各 asic のデーモンはデフォルト動作になる。ただしこれは multi-asic 対応設計上の問題であり、community master ではマルチ ASIC ごとに個別の HEARTBEAT エントリを設けることは現状サポートされていない。

### 5. Virtual Switch (vs) 環境

`orchagent.sh:80-81` は `platform == "vs"` の場合でも HEARTBEAT 読み込みパスは同一。`HEARTBEAT|orchagent` エントリが存在しない場合は `-I` 引数なしで orchagent が起動し、orchagent のデフォルト heartbeat 動作が使われる。

## まとめ

HEARTBEAT テーブルの大半のプロセス（supervisor-proc-exit-listener）はプラットフォーム差ゼロ。orchagent のみ、ASIC 種別に依らず `orchagent.sh` の統一経路で `HEARTBEAT|orchagent.heartbeat_interval` を読む。multi-asic 環境では host CONFIG_DB の `HEARTBEAT|orchagent` が各 asic namespace の orchagent に反映されない点が唯一の構成差。
