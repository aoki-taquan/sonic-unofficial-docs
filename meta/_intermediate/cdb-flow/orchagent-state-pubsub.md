# orchagent STATE_DB — Phase G PUBSUB / Keyspace 通知スキャンノート

対象ページ: `docs/reference/config-db/orchagent-state.md`
対象テーブル: `STATE_DB`
  - `WARM_RESTART_TABLE`
  - `PORT_TABLE`
  - `FDB_TABLE`
  - `VRF_OBJECT_TABLE`
  - `FIPS_MACSEC_POST_TABLE`

Producer: 各テーブルの書込み主体
  - `WarmStart` (`sonic-swss-common/common/warm_restart.cpp`)
  - `PortsOrch` (`sonic-swss/orchagent/portsorch.cpp`)
  - `FdbOrch` (`sonic-swss/orchagent/fdborch.cpp`)
  - `VrfOrch` (`sonic-swss/orchagent/vrforch.cpp`)
  - `MaCSECPost` (`sonic-swss/orchagent/macsecpost.cpp`)

スキャン範囲: 各 producer の Table 型宣言・set/hset/del 呼び出し・PUBLISH 系 API の有無を精読

---

## 検出結果

### 書込み API: 全テーブルで `swss::Table` (Pub/Sub 非対応)

本ページが扱う 5 テーブルはすべて `swss::Table` (raw Redis HSET / HDEL / DEL) で書き込まれる。
`ProducerStateTable` や `NotificationProducer` は一切使用されない。

#### WARM_RESTART_TABLE

`warm_restart.cpp:55-56`:
```cpp
warmStart.m_stateWarmRestartTable =
    std::unique_ptr<Table>(new Table(warmStart.m_stateDb.get(), STATE_WARM_RESTART_TABLE_NAME));
```
書込みは `hset()` のみ (`warm_restart.cpp:113, 125, 133, 227, 247`)。PUBLISH なし。

#### PORT_TABLE (STATE_DB)

`portsorch.h:320`:
```cpp
Table m_portStateTable;
```
初期化: `portsorch.cpp:725-726`
```cpp
m_portStateTable(stateDb, STATE_PORT_TABLE_NAME),
```
書込みは `set()` / `hset()` / `hdel()` のみ (`portsorch.cpp:3172, 3320, 4862, 4907, 5200, 9857, 9870, 11338, 11380`)。PUBLISH なし。

#### FDB_TABLE

`fdborch.h:114`:
```cpp
Table m_fdbStateTable;
```
書込みは `set()` / `del()` のみ (`fdborch.cpp:135, 170, 1582, 1592, 1725`)。PUBLISH なし。

#### VRF_OBJECT_TABLE

`vrforch.cpp:120, 150` で `m_stateVrfObjectTable.set(...)` / `del()` を直接呼び出す。型は `swss::Table`。PUBLISH なし。

#### FIPS_MACSEC_POST_TABLE

`macsecpost.cpp:9-24` で `m_macsecPostTable.set(...)` を呼ぶ。型は `swss::Table`。PUBLISH なし。

---

## 通知チャンネル状況

| テーブル | Producer API | PUBLISH 発行 | keyspace 通知 |
|---------|-------------|-------------|--------------|
| `WARM_RESTART_TABLE` | `swss::Table::hset` | なし | Redis `notify-keyspace-events` 設定次第 |
| `PORT_TABLE` | `swss::Table::set/hset/hdel` | なし | 同上 |
| `FDB_TABLE` | `swss::Table::set/del` | なし | 同上 |
| `VRF_OBJECT_TABLE` | `swss::Table::set/del` | なし | 同上 |
| `FIPS_MACSEC_POST_TABLE` | `swss::Table::set` | なし | 同上 |

---

## Consumer 側 — すべて on-demand polling

- `show warm_restart` (`sonic-utilities/show/warm_restart.py:48-62`): `db.keys(STATE_DB, 'WARM_RESTART_TABLE|*')` + `db.get_all()` — CLI 起動毎 1 回の polling
- `show interfaces status` (`sonic-utilities/show/interfaces/__init__.py`): APPL_DB `PORT_TABLE` を主に参照。STATE_DB `PORT_TABLE` は `sonic-db-cli` 等で直接確認
- `show mac` (`sonic-utilities/show/main.py`): APPL_DB の MAC テーブルを参照。STATE_DB `FDB_TABLE` は内部同期用
- `vrfmgrd` (`sonic-swss/cfgmgr/vrfmgrd.cpp`): VRF 削除時に `VRF_OBJECT_TABLE` を `get()` でポーリング確認して同期制御
- keyspace 通知を **購読している正規 consumer は存在しない**

---

## event_publish (sonic-events フレームワーク)

`portsorch` はポート UP/DOWN 変化時に `event_publish(g_events_handle, "if-state", &params)` を呼ぶ (`portsorch.cpp:3798, 7101`)。
これは Redis DB への直接書込みではなく `sonic-events` フレームワーク経由のイベント送出であり、STATE_DB `PORT_TABLE` の更新とは独立した経路。

---

## ページ反映方針

- `<!-- pubsub -->` ブロックを `<!-- /side-effects -->` の直後、引用元セクションの直前に挿入する。
- 全 5 テーブルが `swss::Table` (PUBLISH 非発行) で書かれること、consumer 側はすべて polling であることを主軸に記述する。
- `event_publish` 経路は補足として言及する。
