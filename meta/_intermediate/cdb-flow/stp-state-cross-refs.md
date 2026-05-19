# stp-state cross-refs (Phase C) — 調査メモ

## 対象ページ
`docs/reference/config-db/stp-state.md`

## 要約
STATE_DB `STP_TABLE|GLOBAL` は `orchagent` の `StpOrch` が SAI クエリ結果をそのまま書き込む単方向の状態テーブル。
書き込み時に CONFIG_DB テーブルを参照することはない。読み側の `stpmgrd` は `STP_TABLE|GLOBAL` を読み取った後、
`APPL_DB PORT_TABLE|PortInitDone`（ポート初期化完了ガード）および `CONFIG_DB DEVICE_METADATA|localhost`（MAC アドレス取得）も
並行して参照するが、これらは `STP_TABLE` の書き込みとは独立した処理である。

## 根拠コード

### 書き込み側 — stporch.cpp（暗黙参照なし）

`StpOrch::updateMaxStpInstance()` (`stporch.cpp:603-617`) は SAI 属性値から計算した `max_stp_inst` を
`m_stpTable->set("GLOBAL", ...)` で STATE_DB に書き込む。この関数は他の DB テーブルを読み取らない。

```cpp
// stporch.cpp:603-617
bool StpOrch::updateMaxStpInstance(uint32_t max_stp_instances)
{
    m_maxStpInstance = (sai_uint16_t)max_stp_instances - 1;
    vector<FieldValueTuple> tuples;
    FieldValueTuple tuple("max_stp_inst", to_string(m_maxStpInstance));
    tuples.push_back(tuple);
    m_stpTable->set("GLOBAL", tuples);
    return true;
}
```

唯一の入力は SAI switch attribute `SAI_SWITCH_ATTR_MAX_STP_INSTANCE`（`stporch.cpp:30-41`）。

### 読み取り側 — stpmgrd.cpp（間接参照テーブル）

`stpmgrd` (`stpmgrd.cpp:68-88`) は起動時に以下の順序でリソースを参照する:

1. `stpmgr.isPortInitDone(&app_db)` — `APPL_DB PORT_TABLE|PortInitDone` が存在するまでポーリング (`stpmgr.cpp:1263`)
2. `stpmgr.getStpMaxInstances()` — `STATE_DB STP_TABLE|GLOBAL` を最大 60 秒ポーリング (`stpmgr.cpp:1381-1413`)
3. `table.get("localhost", ovalues)` — `CONFIG_DB DEVICE_METADATA|localhost` から `mac` フィールド取得 (`stpmgrd.cpp:81-88`)

ポート初期化完了 (`PortInitDone`) が確認された後に `STP_TABLE` が参照される。`STP_TABLE` の内容自体は `DEVICE_METADATA` や `PORT_TABLE` に依存しないが、読み取りの実行順序として `PORT_TABLE|PortInitDone` が前提となる。

```cpp
// stpmgrd.cpp:72-78
stpmgr.ipcInitStpd();
stpmgr.isPortInitDone(&app_db);          // APPL_DB PORT_TABLE|PortInitDone 待機
STP_INIT_READY_MSG msg;
msg.max_stp_instances = stpmgr.getStpMaxInstances();  // STATE_DB STP_TABLE|GLOBAL 読み取り
```

## 暗黙参照まとめ

| テーブル | DB | 参照タイミング | 依存方向 | evidence |
|---|---|---|---|---|
| `PORT_TABLE|PortInitDone` | APPL_DB | stpmgrd 起動時、STP_TABLE 読み取り前 | 読み側ガード（stpmgrd が STP_TABLE を参照する前提条件） | `stpmgr.cpp:1257-1273`, `stpmgrd.cpp:72` |
| `DEVICE_METADATA|localhost` | CONFIG_DB | stpmgrd 起動時、STP_TABLE 読み取り直後 | 読み側の後続処理（MAC アドレス取得）、STP_TABLE 内容に影響なし | `stpmgrd.cpp:81-88` |
| SAI `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` | SAI | orchagent 起動時 1 回 | 書き側の入力（STP_TABLE の値ソース） | `stporch.cpp:30-41`, `stporch.cpp:609` |

## 結論
`STP_TABLE|GLOBAL` 自体は他の DB テーブルを leafref / 暗黙参照しない。
書き込み側（orchagent）は SAI のみを入力とし、読み取り側（stpmgrd）は `PORT_TABLE|PortInitDone` を先行参照してから `STP_TABLE` を読む。
この「ポート初期化完了ガード」が実質的な唯一の暗黙順序依存である。
