# SWITCH_TRIMMING — Phase G Redis 通知メカニズム 調査証跡

生成日: 2026-05-19  
対象ページ: `docs/reference/config-db/switch-trimming.md`  
調査コミット: sonic-swss `orchagent/switchorch.cpp`, `orchdaemon.cpp`

---

## 1. 購読方式

`SwitchOrch` は `orchdaemon.cpp` の初期化コードで `SWITCH_TRIMMING` テーブルを登録し、`SubscriberStateTable` を通じて CONFIG_DB からの keyspace notification を受信する。

`SubscriberStateTable` は内部で `__keyspace@4__:SWITCH_TRIMMING|*` に対する Redis `PSUBSCRIBE` を発行する。CONFIG_DB の DB インデックスは 4。

---

## 2. 主ループと select タイムアウト

`orchdaemon.cpp` の主ループは `SELECT_TIMEOUT = 1000` ms でポーリングする:

```cpp
// orchdaemon.cpp:23
#define SELECT_TIMEOUT 1000
// orchdaemon.cpp:959
while (true) {
    s.select(&temps, SELECT_TIMEOUT);
    // ...各 Orch の doTask() を呼び出す
}
```

`SWITCH_TRIMMING` エントリが CONFIG_DB に書き込まれると最大 1000 ms 以内に `SwitchOrch::doCfgSwitchTrimmingTableTask()` が起動される。

---

## 3. APPL_DB 中継なし

`doCfgSwitchTrimmingTableTask()` は `ProducerStateTable` への書き込みを行わず、CONFIG_DB → SAI の直接パスを使う。下流の Orch が APPL_DB チャネルを購読するようなパブリッシュは発生しない。

---

## 4. STATE_DB capability 書き込み（起動時のみ）

`SwitchTrimmingCapabilities::writeCapabilitiesToDb()` は orchagent 起動時に一度だけ `STATE_DB:SWITCH_CAPABILITY|switch` に書き込む。これは CONFIG_DB の `SET` 操作に起因する通常の pubsub パスではなく、初期化シーケンスの一部である。

---

## 5. evidence

- `sonic-swss/orchdaemon.cpp:23,500,959`: SELECT_TIMEOUT 定数、SwitchOrch 登録、主ループ
- `sonic-swss/orchagent/switchorch.cpp:1320-1371`: `doCfgSwitchTrimmingTableTask()` — ProducerStateTable 呼び出しなし
- `sonic-swss/orchagent/switch/trimming/capabilities.cpp:142-146,724`: `writeCapabilitiesToDb()` — コンストラクタから起動時一回のみ実行
