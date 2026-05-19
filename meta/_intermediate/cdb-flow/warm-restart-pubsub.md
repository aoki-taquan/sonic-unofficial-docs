# warm-restart — Phase G pubsub 調査証跡

## 対象ファイル

- `sonic-swss-common/common/warm_restart.cpp`
- `sonic-swss-common/common/warm_restart.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/cfgmgr/vlanmgr.cpp`（代表的 mgr）

## 調査結果

### WARM_RESTART テーブルの読み取り方式

`WARM_RESTART` テーブルは `SubscriberStateTable`（keyspace 通知）ではなく **`Table::hget()` による起動時一回の同期読み取り**を使用する。

`WarmStart::initialize()` (warm_restart.cpp:35-62) で `Table` オブジェクトを生成し、
`WarmStart::getWarmStartTimer()` (warm_restart.cpp:149-172) が `hget(docker_name, timer_name, timer_value_str)` を呼ぶ。

この `Table::hget()` は Redis の `HGET` コマンドを同期実行するポーリング型アクセス。
`PSUBSCRIBE` や channel-based PUBLISH/SUBSCRIBE は一切使用しない。

### イベント駆動での変更通知は存在しない

`WARM_RESTART` テーブルが変更されても、実行中のプロセスにはリアルタイム通知が届かない。
各プロセスは次回の起動時にのみ新しい値を参照する。

### STATE_DB への書き込み方式

STATE_DB の `WARM_RESTART_TABLE` / `WARM_RESTART_ENABLE_TABLE` への書き込みは `Table::hset()` を使用。
こちらも channel ベース PUBLISH は発行しない。

## 結論

WARM_RESTART テーブルは pub/sub 機構を使用しない。
Phase G は「pub/sub なし（直接読み取り）」として記載する。
