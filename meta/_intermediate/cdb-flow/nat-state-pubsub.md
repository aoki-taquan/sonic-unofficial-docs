# nat-state — Phase G 通信メカニズム調査メモ

対象ページ: `docs/reference/config-db/nat-state.md`
対象テーブル:
  - `STATE_DB:NAT_RESTORE_TABLE|Flags`
  - `COUNTERS_DB:COUNTERS_NAT*`（全 5 テーブル + COUNTERS_GLOBAL_NAT）

## 書き手と読み手のまとめ

| テーブル | 書き手 | 読み手 | 通信手段 |
|---------|--------|--------|---------|
| `STATE_DB:NAT_RESTORE_TABLE\|Flags` | `restore_nat_entries.py` | `natsyncd` | 直接 `hget` ポーリング (pub/sub なし) |
| `COUNTERS_DB:COUNTERS_NAT*` 各エントリ | `NatOrch` (orchagent) | `show nat statistics` | 直接 `hgetall` (pub/sub なし) |
| `COUNTERS_DB:COUNTERS_GLOBAL_NAT\|Values` | `NatOrch` (orchagent) | `show nat statistics` | 直接 `hgetall` (pub/sub なし) |

## NAT_RESTORE_TABLE の通信経路

`STATE_DB:NAT_RESTORE_TABLE|Flags` はポーリング（busy-wait）モデルで使用される。Redis pub/sub や keyspace 通知は使用しない。

```
restore_nat_entries.py
  → conntrack 復元完了後
  → stateDb.Table("NAT_RESTORE_TABLE").set("Flags", [("restored","true")])
    (restore_nat_entries.py:49-52)

natsyncd main loop (natsyncd.cpp:48-62)
  while (!sync.isNatRestoreDone()):   // 1 秒間隔 sleep ループ
    → NatSync::isNatRestoreDone()
    → m_stateNatRestoreTable.hget("Flags", "restored", value)  // 直接 hget
    → value == "true" → return true → ループ脱出 → reconciliation 開始
```

タイムアウト: `RESTORE_NAT_WAIT_TIME_OUT` 秒 (定数。`natsyncd.cpp:56` の `pasttime > RESTORE_NAT_WAIT_TIME_OUT` で exit)。

## COUNTERS_NAT* の通信経路

`COUNTERS_DB:COUNTERS_NAT*` テーブルは Redis pub/sub ではなく `SelectableTimer` (fd ポーリング) で更新される。

```
orchagent メインループ (Select::select)
  → m_natQueryTimer の fd が ready (5 秒周期)
  → NatOrch::doTask(SelectableTimer&)  (natorch.cpp:3095-3117)
  → queryHitBits()   [30 秒ごと — hit bit リセット + エージアウト判定]
  → queryCounters()  [5 秒ごと — パケット/バイト数取得]
    → getNatCounters() / getNaptCounters() / getTwiceNatCounters() / getTwiceNaptCounters()
    → SAI: sai_nat_api->get_nat_entry_attribute(SAI_NAT_ENTRY_ATTR_BYTE_COUNT / PACKET_COUNT)
    → updateNatCounters(ip, pkts, bytes)
    → m_countersNatTable.set(key, {NAT_TRANSLATIONS_PKTS, NAT_TRANSLATIONS_BYTES})
```

読み取り側（`show nat statistics`）は `sonic-db-cli COUNTERS_DB hgetall 'COUNTERS_NAT|<ip>'` で直接読む。

## 非同期通知チャンネル（COUNTERS_DB への間接影響）

NAT には APPL_DB 経由の 4 本の `NotificationConsumer / NotificationProducer` チャンネルがある。COUNTERS_DB への影響を持つチャンネルは以下:

| チャンネル | DB | 送信者 | 受信者 | COUNTERS_DB への影響 |
|---|---|---|---|---|
| `FLUSHNATSTATISTICS` | APPL_DB | `sonic-clear nat statistics` (CLI) | `NatOrch` (`natorch.cpp:84-86`) | `clearCounters()` → SAI reset → COUNTERS_NAT* フィールドを `"0"` にリセット |
| `NAT_DB_CLEANUP_NOTIFICATION` | APPL_DB | natmgrd 停止時 | `NatOrch` (`natorch.cpp:89-91`) | `cleanupAppDbEntries()` → 全 COUNTERS_NAT* キーを削除 |

`SETTIMEOUTNAT` と `FLUSHNATENTRIES` チャンネルは COUNTERS_DB を直接操作しない。

## キースペース通知の不使用

`NAT_RESTORE_TABLE` の更新を `natsyncd` が検出する際に Redis keyspace 通知 (`CONFIG_SET notify-keyspace-events`) は使用されない。純粋なポーリング実装のため、フラグ書込みから検出まで最大 1 秒の遅延がある。

## Evidence

- `restore_nat_entries.py:49-52` — STATE_DB 書込み
- `natsyncd.cpp:43-62` — warm start ポーリングループ
- `natsync.cpp:96-108` — `isNatRestoreDone()` 実装
- `natorch.cpp:84-91` — NotificationConsumer 登録 (FLUSHNATSTATISTICS / NAT_DB_CLEANUP)
- `natorch.cpp:3095-3117` — SelectableTimer doTask (queryHitBits / queryCounters)
- `natorch.cpp:4049-4135` — updateNatCounters / updateNaptCounters 等
