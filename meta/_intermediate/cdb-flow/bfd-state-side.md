# bfd-state — Phase F (副次 DB 書込) 検出メモ

対象ページ: `docs/reference/config-db/bfd-state.md`
対象テーブル: `STATE_DB::BFD_SESSION_TABLE`
ソース: `sonic-swss/orchagent/bfdorch.cpp` (HEAD, ~841 行) + `bfdorch.h`

## 結論

**STATE_DB 以外への副次書込は 0 件**。COUNTERS_DB / APPL_STATE_DB / FLEX_COUNTER_DB / CONFIG_DB への書込は `bfdorch` には実装されていない。

## 検出手順

### 1. DBConnector 生成箇所の網羅

```
grep -nE "DBConnector\(" bfdorch.cpp
```

- L63: `new DBConnector("ASIC_DB", 0)` — NotificationConsumer 用 (subscribe 専用)
- L67: `make_unique<DBConnector>("STATE_DB", 0)` — m_stateSoftBfdSessionTable 用

それ以外の DB ("COUNTERS_DB", "APPL_STATE_DB", "FLEX_COUNTER_DB", "CONFIG_DB", "ASIC_STATE_DB") の DBConnector 生成は **0 件**。

### 2. Table オブジェクトの網羅

`bfdorch.h` メンバ:

- `m_stateBfdSessionTable` (swss::Table, STATE_DB)
- `m_stateSoftBfdSessionTable` (unique_ptr<swss::Table>, STATE_DB)
- `m_bfdStateNotificationConsumer` (NotificationConsumer, ASIC_DB の "NOTIFICATIONS" channel)

それ以外の `Table` メンバは無い。

### 3. 書込 API 呼出箇所の確認

```
grep -nE "->set\(|\.set\(|->hset\(|\.hset\(|->del\(|\.del\(" bfdorch.cpp
```

すべて以下 2 ハンドルのいずれかに対する呼出:

| 行 | ハンドル | 操作 | DB |
|---|---|---|---|
| L78 | `m_stateBfdSessionTable.del` | クリーンアップ削除 | STATE_DB |
| L84 | `m_stateSoftBfdSessionTable->del` | クリーンアップ削除 | STATE_DB |
| L136 | `m_stateSoftBfdSessionTable->set` | software 経路書込 | STATE_DB |
| L185 | `m_stateSoftBfdSessionTable->del` | software 経路削除 | STATE_DB |
| L252 | `m_stateBfdSessionTable.hset` | SAI 通知 state 更新 | STATE_DB |
| L565 | `m_stateBfdSessionTable.set` | create 直後の構成書込 | STATE_DB |
| L629 | `m_stateBfdSessionTable.del` | remove 時削除 | STATE_DB |
| L708 | `m_stateSoftBfdSessionTable->set` | software 経路 (createSoftwareBfdSession) | STATE_DB |
| L714 | `m_stateSoftBfdSessionTable->del` | software 経路 (removeSoftwareBfdSession) | STATE_DB |

→ **すべて STATE_DB**。

### 4. publish / Notifier の確認

- L64-65: NotificationConsumer (ASIC_DB → 受信)
- `notify_session_state_down()` (L683-704) は内部関数で SAI 削除前に `state="Down"` を STATE_DB に hset するだけ。NotificationProducer / publish API の呼出は無い。

### 5. grep 結果サマリ

```
grep -cE "COUNTERS_DB|APPL_STATE_DB|FLEX_COUNTER" bfdorch.cpp bfdorch.h
# → bfdorch.cpp:0  bfdorch.h:0
```

## 含意

1. **BFD セッション統計が COUNTERS_DB に出ない** — sonic-utilities `show bfd peers details` も STATE_DB のみ参照。SAI API を直接叩かないと pkt 数等は取れない。
2. **APPL_STATE_DB ack なし** — `producerstatetable` の two-phase delete pattern (portsorch 等) は BFD には未適用。削除は同期完結。
3. **flex counter 化は未実装** — 将来拡張する場合は別 Orch (BfdCounterOrch 等) の新設が必要。

## 引用元

- `sonic-swss/orchagent/bfdorch.cpp` (HEAD)
- `sonic-swss/orchagent/bfdorch.h` (HEAD)
- <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/bfdorch.cpp>
