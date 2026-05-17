# COUNTERS_DB RIF カウンタ — Phase G 通信メカニズムスキャンノート

対象テーブル: `COUNTERS_DB / COUNTERS_RIF_NAME_MAP`, `COUNTERS_RIF_TYPE_MAP`, `COUNTERS:<oid>`, `RATES:<oid>`
調査対象: `sonic-swss/orchagent/flexcounterorch.cpp`, `sonic-swss/orchagent/intfsorch.cpp`, `sonic-swss/orchagent/orchdaemon.cpp`, `sonic-utilities/scripts/intfstat`
スキャン範囲: flexcounterorch.cpp doTask 全行, intfsorch.cpp 全行, intfstat 全行

---

## Producer/Consumer ペア

RIF カウンタの制御経路は **CONFIG_DB → FlexCounterOrch → IntfsOrch → syncd** という 4 段構成をとる。APPL_DB 中継なし。

| 区間 | 方式 | 詳細 |
|------|------|------|
| CONFIG_DB → FlexCounterOrch | `SubscriberStateTable` | `FLEX_COUNTER_TABLE|RIF` を購読。keyspace notification で変化を検出 |
| FlexCounterOrch → IntfsOrch | 直接関数呼び出し | `gIntfsOrch->generateInterfaceMap()` → `m_updateMapsTimer->start()` |
| IntfsOrch タイマー起動後 | `SelectableTimer` 駆動 | `doTask(SelectableTimer&)` で `m_rifsToAdd` リストを処理 |
| IntfsOrch → COUNTERS_DB | 直接書き込み | `m_rifNameTable->set()` / `m_rifTypeTable->set()` |
| IntfsOrch → FLEX_COUNTER_DB | `startFlexCounterPolling()` | `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>:COUNTER_ID_LIST` を書き込む |
| syncd → ASIC | SAI flex counter ポーリング | `RIF_FLEX_STAT_COUNTER_POLL_MSECS = 1000 ms` 間隔で SAI stat API をポーリング |
| syncd → COUNTERS_DB | 直接書き込み | `COUNTERS:<oid>` Hash に各 SAI フィールドの値をアトミック更新 |
| syncd + rif_rates.lua | Lua プラグイン実行 | ポーリング毎に `RATES:<oid>` の RX_BPS/TX_BPS/RX_PPS/TX_PPS を指数平滑化計算 |
| COUNTERS_DB → intfstat | `Table::get()` 直接読み出し | `COUNTERS_RIF_NAME_MAP` で名前→OID 解決後、`COUNTERS:<oid>` を読む（pull 型） |

### flexcounterorch.cpp における RIF 経路の詳細

`FlexCounterOrch::doTask()` の `FLEX_COUNTER_STATUS_FIELD == "enable"` ブランチ (flexcounterorch.cpp:283-286):

```cpp
if(gIntfsOrch && (key == RIF_KEY) && (value == "enable"))
{
    gIntfsOrch->generateInterfaceMap();
}
```

`generateInterfaceMap()` は `m_updateMapsTimer->start()` を呼ぶだけで、実際の OID 登録は `doTask(SelectableTimer&)` (intfsorch.cpp:1598-1637) で非同期処理される。

---

## warm-start 遅延タイマー

`FlexCounterOrch` は cold-start では即座に処理を開始するが、warm-start では **60 秒** のタイマー (`FLEX_COUNTER_DELAY_SEC = 60`) が期限切れになるまで `doTask()` 全体をブロックする (flexcounterorch.cpp:127-137, 156-158)。

```
cold-start: m_delayTimerExpired = true → 即処理可能
warm-start: SelectableTimer(60s) 起動 → 60s 間 doTask ブロック
```

---

## gTraditionalFlexCounter モードの非同期待機

`gTraditionalFlexCounter == true` の場合（ASIC_DB が VIDTORID テーブルを持つ従来モード）、IntfsOrch は `m_rifsToAdd` に RIF を一旦キューイングし、`doTask(SelectableTimer&)` のたびに ASIC_DB `VIDTORID` テーブルに OID が現れるまで待機する (intfsorch.cpp:1627-1636):

```cpp
if (!gTraditionalFlexCounter || m_vidToRidTable->hget("", id, value))
{
    addRifToFlexCounter(id, it->m_alias, type);
    it = m_rifsToAdd.erase(it);
}
```

`gTraditionalFlexCounter == false`（新モード）の場合は VIDTORID 未到達でも即時 `addRifToFlexCounter()` が呼ばれる。

---

## intfstat の読み出しパス（pull 型）

`intfstat` スクリプト (`sonic-utilities/scripts/intfstat`) は COUNTERS_DB を **直接読み取る**（pull 型）。pub/sub 購読は行わず、コマンド実行時点の最新値を取得する。

```python
# intfstat:81-82
self.db = SonicV2Connector(use_unix_socket_path=False)
self.db.connect(self.db.COUNTERS_DB)

# intfstat:123
counter_rif_name_map = self.db.get_all(self.db.COUNTERS_DB, COUNTERS_RIF_NAME_MAP)
# → {"Ethernet0": "oid:0x6000000000001", ...}

# intfstat:96
counter_data = self.db.get(self.db.COUNTERS_DB, full_table_id, counter_name)
# → "12345678"  (uint64 文字列)

# intfstat:109
counter_data = self.db.get(self.db.COUNTERS_DB, rates_table_id, name)
# → "1234.56"   (float 文字列、RATES テーブル)
```

`SubscriberStateTable` / `ConsumerStateTable` / Redis `PSUBSCRIBE` は使用しない。

---

## COUNTERS_DB と FLEX_COUNTER_DB の書き込みキー

| DB | キー | 書き手 | 内容 |
|----|------|--------|------|
| COUNTERS_DB | `COUNTERS_RIF_NAME_MAP` | IntfsOrch | `<rif_name>` → `<SAI OID>` マッピング |
| COUNTERS_DB | `COUNTERS_RIF_TYPE_MAP` | IntfsOrch | `<SAI OID>` → `<type string>` マッピング |
| COUNTERS_DB | `COUNTERS:<oid>` | syncd FlexCounter | RIF 統計カウンタ (SAI_ROUTER_INTERFACE_STAT_*) |
| COUNTERS_DB | `RATES:<oid>` | syncd + rif_rates.lua | RX_BPS / TX_BPS / RX_PPS / TX_PPS |
| FLEX_COUNTER_DB | `RIF_STAT_COUNTER:<oid>:COUNTER_ID_LIST` | IntfsOrch | ポーリング対象 SAI カウンタ ID のカンマ区切りリスト |
| FLEX_COUNTER_DB | `FLEX_COUNTER_GROUP_TABLE:RIF_STAT_COUNTER` | IntfsOrch コンストラクタ | `POLL_INTERVAL`, `FLEX_COUNTER_STATUS`, Lua プラグイン SHA |

---

## データフロー図（テキスト形式）

```text
CONFIG_DB[FLEX_COUNTER_TABLE|RIF]
  ↓ SubscriberStateTable (keyspace notification)
orchdaemon select() loop (SELECT_TIMEOUT=1000ms)
  ↓ FlexCounterOrch::doTask() [delayTimerExpired チェック] [allPortsReady チェック]
      gIntfsOrch->generateInterfaceMap()
  ↓ m_updateMapsTimer->start()
IntfsOrch::doTask(SelectableTimer&) → addRifToFlexCounter()
  → COUNTERS_DB[COUNTERS_RIF_NAME_MAP] / [COUNTERS_RIF_TYPE_MAP]
  → FLEX_COUNTER_DB[RIF_STAT_COUNTER:<oid>:COUNTER_ID_LIST]
  ↓ syncd FlexCounter スレッド (1000ms ポーリング)
      sai_router_intfs_api->get_router_interface_stats()
  → COUNTERS_DB[COUNTERS:<oid>] ← SAI 統計値 (uint64 文字列)
  → rif_rates.lua 実行 → COUNTERS_DB[RATES:<oid>] ← 指数平滑 BPS/PPS
  ↓ intfstat (pull 型 direct read)

NotificationConsumer: なし（カウンタ配信に使用せず）
APPL_DB 書き込み: なし
STATE_DB 書き込み: なし
```

---

## evidence

- `sonic-swss/orchagent/flexcounterorch.cpp:283-286` — RIF enable ブランチ
- `sonic-swss/orchagent/intfsorch.cpp:1576-1578` — `generateInterfaceMap()` 実装
- `sonic-swss/orchagent/intfsorch.cpp:1598-1637` — `doTask(SelectableTimer&)` / `addRifToFlexCounter()` 呼び出し
- `sonic-swss/orchagent/intfsorch.cpp:1527-1553` — `addRifToFlexCounter()` 実装
- `sonic-swss/orchagent/intfsorch.cpp:1556-1568` — `removeRifFromFlexCounter()` 実装
- `sonic-swss/orchagent/flexcounterorch.cpp:127-136,156-158` — warm-start delay timer
- `sonic-swss/orchagent/flexcounterorch.cpp:164-167` — allPortsReady ガード
- `sonic-utilities/scripts/intfstat:81-82,96,109,123` — pull 型 COUNTERS_DB 直接読み出し
- `sonic-swss/orchagent/rif_rates.lua` — RATES テーブル書き込みロジック
