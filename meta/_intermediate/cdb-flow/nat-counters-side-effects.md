# COUNTERS_DB NAT カウンタテーブル群 — Phase F 副作用スキャンノート

対象テーブル: `COUNTERS_DB:COUNTERS_NAT / COUNTERS_NAPT / COUNTERS_TWICE_NAT / COUNTERS_TWICE_NAPT / COUNTERS_GLOBAL_NAT`
Consumer/Producer: `NatOrch` (`sonic-swss/orchagent/natorch.cpp`)
スキャン範囲: L3095–3117 (doTask/SelectableTimer), L3118–3177 (queryCounters), L3304–3441 (queryHitBits), L3443–3505 (updateAllConntrackEntries), L4450–4479 (doTask/NotificationConsumer), L4481–4589 (updateStatic/DynamicCounters)

---

## 検出した副作用

### 1. カウンタポーリングが動的 NAT エントリのエージアウトを駆動 (queryHitBits → SETTIMEOUTNAT)

- `doTask(SelectableTimer)` L3101–3104: 5 秒タイマーが起動するたびに `natTimerTickCntr++ % NAT_HITBIT_QUERY_MULTIPLE (6)` を評価し、30 秒に 1 度 `queryHitBits()` を呼ぶ。
- `queryHitBits()` L3304–3441: SNAT / NAPT / Twice NAT / Twice NAPT の全動的エントリについて SAI `get_nat_entry_attribute(HIT_BIT, HIT_BIT_COR)` を呼び、ヒットビットを取得しつつクリアする。
- ヒットビット = 0 かつ `activeTime` からの経過秒数がタイムアウト超過 → `setTimeoutNotifier->send("AGEOUT-SINGLE-NAT", key, ...)` を APPL_DB の `SETTIMEOUTNAT` チャンネルに送信。natsyncd がこれを受信して APPL_DB からエントリを削除し、最終的に `removeNatEntry()` → `deleteNatCounters()` で COUNTERS_DB からカウンタエントリが削除される。
- **副作用**: カウンタポーリング自体がエージアウト通知のトリガになる。カウンタを読むと同時にエントリが削除される可能性がある。
- evidence: `natorch.cpp:3101-3104` (タイマー多重化), `natorch.cpp:3316-3338` (AGEOUT通知送信), `natorch.cpp:4063-4075` (deleteNatCounters)

### 2. ヒットビット取得時の HIT_BIT_COR による SAI 内部状態変更

- `checkIfNatEntryIsActive()` L4166–4171: SAI 属性 `SAI_NAT_ENTRY_ATTR_HIT_BIT` とともに `SAI_NAT_ENTRY_ATTR_HIT_BIT_COR=1` を同時に取得する。これはヒットビットの読み取りと同時にクリアを行う "read-and-clear" 操作。
- **副作用**: COUNTERS_DB の値を読み取るだけでなく、SAI 内部のヒットビットを消費する。外部ツールが SAI を直接参照した場合、NatOrch のポーリング後はヒットビットがゼロになっている。
- evidence: `natorch.cpp:4166-4170` (HIT_BIT + HIT_BIT_COR=1)

### 3. 1 日周期タイマーが conntrack エントリの timeout 延長通知を送信 (updateAllConntrackEntries)

- `doTask(SelectableTimer)` L3107–3111: `m_natTimeoutTimer` (1 日周期) が起動すると `updateAllConntrackEntries()` を呼ぶ。
- `updateAllConntrackEntries()` L3443–3505: HW に追加済みの全動的 SNAT / NAPT / Twice NAT / Twice NAPT エントリに対して `setTimeoutNotifier->send("SET-SINGLE-NAT" / "SET-SINGLE-NAPT" / ...)` を送信。natsyncd がこれを受けてカーネル conntrack エントリのタイムアウトをリセットする。
- **副作用**: COUNTERS_DB への書き込みは行わないが、このタイマー動作は COUNTERS_DB のカウンタ更新タイマーと同じ SelectableTimer dispatch から派生しており、タイマー間の干渉が発生した場合（m_natQueryTimer と m_natTimeoutTimer が同時に FD を返すなど）に予期しない動作が起きうる。
- evidence: `natorch.cpp:3107-3111` (タイマー分岐), `natorch.cpp:3443-3505` (updateAllConntrackEntries)

### 4. SNAT_ENTRIES / DNAT_ENTRIES カウンタ更新の副作用 (NAT 動作全体の観測窓)

- `addHwSnatEntry()` 末尾: `totalSnatEntries++; updateSnatCounters(totalSnatEntries)` を呼び、COUNTERS_GLOBAL_NAT|Values の `SNAT_ENTRIES` を更新 (`natorch.cpp:1903-1905`)。
- `removeHwSnatEntry()` 末尾: `totalSnatEntries--; updateSnatCounters(totalSnatEntries)` (`natorch.cpp:1663-1670`)。
- **副作用**: `COUNTERS_GLOBAL_NAT|Values.SNAT_ENTRIES` は NAT エントリの SAI 操作が成功するたびに逐次更新される「実態カウンタ」として機能する。`show nat statistics` の表示外でも直接 COUNTERS_DB を参照することで NAT エントリ数の増減をリアルタイム監視できる。
- evidence: `natorch.cpp:4569-4578` (updateSnatCounters), `natorch.cpp:1903-1905` (addHwSnatEntry), `natorch.cpp:4580-4589` (updateDnatCounters)

### 5. NAT_DB_CLEANUP_NOTIFICATION 受信時の APPL_DB 一括削除副作用

- `doTask(NotificationConsumer)` L4474–4478: `NAT_DB_CLEANUP_NOTIFICATION` 受信時に `cleanupAppDbEntries()` を呼ぶ。
- `cleanupAppDbEntries()` L2457–2532: 全 NAT / NAPT / Twice NAT エントリを `m_natQueryTable.del()` で APPL_DB から削除し、`removeNatEntry()` → `deleteNatCounters()` で COUNTERS_DB のカウンタエントリも削除する。
- **副作用**: natorch docker 停止時にトリガされるこの通知により、COUNTERS_DB の `COUNTERS_NAT*` 全エントリが消滅する。docker が再起動した後、次の `NAT_GLOBAL.admin_mode=enabled` 処理と `addAllNatEntries()` が完了するまで COUNTERS_DB にカウンタエントリが存在しない。
- evidence: `natorch.cpp:4474-4478` (クリーンアップ通知受信), `natorch.cpp:2457-2532` (cleanupAppDbEntries)

---

## 副作用サマリ

| # | 副作用 | トリガ | 対象 DB / システム | 可逆性 |
|---|--------|--------|-------------------|--------|
| 1 | 動的 NAT エントリのエージアウト → COUNTERS_NAT* キー削除 | 5×6=30 秒ポーリング + ヒットビット=0 + タイムアウト超過 | APPL_DB (SETTIMEOUTNAT), COUNTERS_DB | 再フロー時に新エントリ追加で復元 |
| 2 | SAI ヒットビットのクリア (read-and-clear) | 30 秒ごとの `checkIfNatEntryIsActive()` 呼び出し | SAI 内部状態 | 次のフロー通過で SAI がビットをセット |
| 3 | conntrack タイムアウトリセット通知 | 1 日周期タイマー | カーネル conntrack テーブル | — (周期的動作) |
| 4 | SNAT_ENTRIES / DNAT_ENTRIES のリアルタイム更新 | SAI エントリ追加/削除成功 | COUNTERS_GLOBAL_NAT\|Values | — (状態反映) |
| 5 | COUNTERS_NAT* 全エントリ一括削除 | natorch docker 停止 (NAT_DB_CLEANUP_NOTIFICATION) | COUNTERS_DB | docker 再起動 + admin_mode=enabled で復元 |
