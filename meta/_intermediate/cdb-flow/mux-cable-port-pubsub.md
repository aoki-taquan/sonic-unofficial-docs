# MUX_CABLE|<ifname> — Redis 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB `MUX_CABLE|<ifname>` エントリ。購読側コンポーネント: `orchagent (MuxOrch)`・`linkmgrd`・`ycabled`。

ソース確認:
- `sonic-swss/orchagent/muxorch.cpp` / `orchdaemon.cpp`
- `sonic-linkmgrd/src/DbInterface.cpp`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_table_helper.py`
- `sonic-swss-common/common/schema.h`

## 1. CONFIG_DB MUX_CABLE の購読方式

### orchagent (MuxOrch): `Orch2` フレームワーク経由 `SubscriberStateTable`

`orchdaemon.cpp:467-471` で CONFIG_DB 接続を `Orch2` フレームワークに渡す:

```cpp
// orchdaemon.cpp:467-471
vector<string> mux_tables = {
    CFG_MUX_CABLE_TABLE_NAME,    // "MUX_CABLE"
    CFG_PEER_SWITCH_TABLE_NAME   // "PEER_SWITCH"
};
gMuxOrch = new MuxOrch(m_configDb, mux_tables, gTunneldecapOrch, gNeighOrch, gFdbOrch);
```

`Orch2` ベースクラスが各テーブルを `ConsumerStateTable` (内部で `SubscriberStateTable`) として wrappし、`orchdaemon.cpp:959` の `m_select->select(&s, SELECT_TIMEOUT=1000ms)` ループで keyspace 通知を受信する。

- PSUBSCRIBE パターン: `__keyspace@4__:MUX_CABLE|*` (CONFIG_DB は DB index 4)
- select タイムアウト: `SELECT_TIMEOUT = 1000` ms (`orchdaemon.cpp:23`)
- dispatch: 通知受信 → `MuxOrch::handleMuxCfg()` (`muxorch.cpp:2189`)

### linkmgrd: 専用 `SubscriberStateTable` + `swss::Select` ループ

`DbInterface.cpp:1824` で専用の `SubscriberStateTable` を CONFIG_DB に対して生成:

```cpp
// DbInterface.cpp:1824
swss::SubscriberStateTable configDbMuxTable(configDbPtr.get(), CFG_MUX_CABLE_TABLE_NAME);
```

`DbInterface.cpp:1862` で `swssSelect.addSelectable(&configDbMuxTable)` としてイベントループに登録し、`DbInterface.cpp:1889-1890` で dispatch:

```cpp
// DbInterface.cpp:1889-1890
} else if (selectable == &configDbMuxTable) {
    handleMuxPortConfigNotifiction(configDbMuxTable);
}
```

- PSUBSCRIBE パターン: `__keyspace@4__:MUX_CABLE|*`
- select タイムアウト: `DEFAULT_TIMEOUT_MSEC = 1000` ms (`DbInterface.cpp:48`)
- dispatch: `handleMuxPortConfigNotifiction()` → `processMuxPortConfigNotifiction()` → `mMuxManagerPtr->updateMuxPortConfig(port, v)` (変更フィールドは `state` と `pck_loss_data_reset` のみ処理; `DbInterface.cpp:1055-1100`)

**注意**: linkmgrd は起動時に `MUX_CABLE` テーブル全体を `swss::Table` で一括読み込みし (`DbInterface.cpp:1846-1849`)、それ以降の変更を `SubscriberStateTable` で差分受信する二段構成。

### ycabled: `swss::Table` 直読み（起動時のみ）

ycabled は CONFIG_DB `MUX_CABLE` を `ProducerStateTable` / `SubscriberStateTable` では購読**しない**。`y_cable_table_helper.py:289` で各 ASIC ごとに素の `swss::Table` として保持する:

```python
# y_cable_table_helper.py:289
self.port_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "MUX_CABLE")
```

これは polling 専用 (HGETALL) で、起動時またはイベント駆動で `check_mux_cable_port_type()` が呼ばれたタイミングで `port_tbl.get(port)` する。

## 2. APPL_DB 側の pub/sub チェーン

`MuxOrch` が `MUX_CABLE` SET 処理完了後に SAI 操作し、結果を APPL_DB へ書き出す経路:

```
orchagent MuxCableOrch → APPL_DB HW_MUX_CABLE_TABLE (ProducerStateTable ではなく直接 Table::set)
  ↓
ycabled SubscriberStateTable (APP_HW_MUX_CABLE_TABLE_NAME, y_cable_table_helper.py:267-268)
  ↓ (SELECT_TIMEOUT = 1000ms, y_cable_helper.py:36,3656)
  STATE_DB HW_MUX_CABLE_TABLE / HW_MUX_CABLE_TABLE_PEER / MUX_CABLE_INFO への書込
```

| consumer | 購読 DB / テーブル | 方式 | SELECT_TIMEOUT | evidence |
|---|---|---|---|---|
| ycabled | APPL_DB `HW_MUX_CABLE_TABLE` | `SubscriberStateTable` | 1000 ms | `y_cable_table_helper.py:267-268` |
| ycabled | APPL_DB `MUX_CABLE_COMMAND_TABLE` | `SubscriberStateTable` | 1000 ms | `y_cable_table_helper.py:269-270` |
| ycabled | APPL_DB `HW_FORWARDING_STATE_PEER` | `SubscriberStateTable` | 1000 ms | `y_cable_table_helper.py:276-277` |
| linkmgrd | APPL_DB `MUX_CABLE_RESPONSE_TABLE` | `SubscriberStateTable` | 1000 ms | `DbInterface.cpp:1829` |
| linkmgrd | STATE_DB `MUX_CABLE_TABLE` | `SubscriberStateTable` | 1000 ms | `DbInterface.cpp:1833` |
| MuxStateOrch | STATE_DB `HW_MUX_CABLE_TABLE` | `Orch2` / ConsumerStateTable | 1000 ms | `orchdaemon.cpp:477` |

## 3. 通知方式サマリ

| 観点 | MuxOrch (CONFIG_DB 購読) | linkmgrd (CONFIG_DB 購読) | ycabled (CONFIG_DB 読み取り) |
|---|---|---|---|
| 購読方式 | `Orch2` / `ConsumerStateTable` | `SubscriberStateTable` + `swss::Select` | `swss::Table` 直読み (polling) |
| channel PUBLISH | orchagent が CONFIG_DB に PUBLISH することはない (消費専用) | 同上 | — |
| keyspace PSUBSCRIBE | `__keyspace@4__:MUX_CABLE\|*` | `__keyspace@4__:MUX_CABLE\|*` | 使わない |
| select タイムアウト | 1000 ms | 1000 ms | — (起動時 1 回) |
| retry interval | なし (イベント駆動、失敗時は `m_toSync` 保留) | なし (イベント駆動) | — |

## 4. `ProducerStateTable` の役割

CONFIG_DB `MUX_CABLE` への書き込みは `minigraph.py` / `config` CLI が `ProducerStateTable` ではなく `sonic-db-cli` (HSET) 経由で直接書き込む。keyspace notification は Redis サーバが自動発行 (`notify-keyspace-events Kx` が有効な場合)。

CONFIG_DB は DB index 4 (`/etc/swss/swssconfig` 等で定義)。

## 5. Evidence

- `sonic-swss/orchagent/orchdaemon.cpp` L467-471 — `mux_tables` + `MuxOrch` 構築
- `sonic-swss/orchagent/orchdaemon.cpp` L23 — `SELECT_TIMEOUT = 1000`
- `sonic-swss/orchagent/orchdaemon.cpp` L959 — `m_select->select(&s, SELECT_TIMEOUT)`
- `sonic-swss/orchagent/muxorch.cpp` L2189 — `handler_map_` に `CFG_MUX_CABLE_TABLE_NAME` → `handleMuxCfg` を登録
- `sonic-linkmgrd/src/DbInterface.cpp` L1824 — `SubscriberStateTable configDbMuxTable(..., CFG_MUX_CABLE_TABLE_NAME)`
- `sonic-linkmgrd/src/DbInterface.cpp` L1862 — `swssSelect.addSelectable(&configDbMuxTable)`
- `sonic-linkmgrd/src/DbInterface.cpp` L1889-1890 — dispatch `handleMuxPortConfigNotifiction()`
- `sonic-linkmgrd/src/DbInterface.cpp` L48 — `DEFAULT_TIMEOUT_MSEC = 1000`
- `sonic-linkmgrd/src/DbInterface.cpp` L1055-1100 — `processMuxPortConfigNotifiction()` (state / pck_loss_data_reset のみ処理)
- `sonic-linkmgrd/src/DbInterface.cpp` L1846-1849 — 起動時一括読み込み (getPortCableType 等)
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_table_helper.py` L267-278 — APPL_DB `SubscriberStateTable` 登録 (HW_MUX_CABLE / COMMAND / PEER)
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_table_helper.py` L289 — `port_tbl[asic_id] = Table(config_db, "MUX_CABLE")` (polling)
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py` L36 — `SELECT_TIMEOUT = 1000`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py` L3656 — `sel.select(SELECT_TIMEOUT)`
- `sonic-swss/orchagent/orchdaemon.cpp` L477 — `MuxStateOrch(m_stateDb, STATE_HW_MUX_CABLE_TABLE_NAME)`
- `sonic-swss-common/common/schema.h` L140-143, L457-465 — テーブル名定数
