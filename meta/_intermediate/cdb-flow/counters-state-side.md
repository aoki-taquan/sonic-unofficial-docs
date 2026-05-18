# STATE_DB カウンタ能力テーブル — Phase F 副作用スキャンノート

対象ページ: `docs/reference/config-db/counters-state.md`
対象テーブル: `STATE_DB / PORT_COUNTER_CAPABILITIES`, `STATE_DB / QUEUE_COUNTER_CAPABILITIES`, `STATE_DB / DEBUG_COUNTER_CAPABILITIES`
スキャン範囲: portsorch.cpp / debugcounterorch.cpp / flexcounterorch.cpp / utilities_common/portstat.py 全行精読

---

## 副作用の分類

これらのテーブルはユーザー操作（CONFIG_DB SET/DEL）に連動して書かれるのではなく、orchagent コンストラクタが SAI 問い合わせ結果を 1 回限りで書き込む。したがって「SET 時副作用」「DEL 時副作用」という通常の分類ではなく、「テーブル書き込み時副作用（起動直後）」と「consumer 参照時副作用（実行時）」に分ける。

---

## 1. COUNTERS_DB ポーリング対象の決定（portstat.py / queuestat）

`PORT_COUNTER_CAPABILITIES` / `QUEUE_COUNTER_CAPABILITIES` の各フィールドは **portstat.py が COUNTERS_DB をポーリングする際に参照**し、ポーリング対象の SAI カウンタ一覧を動的に決定する。

| STATE_DB の値 | portstat.py の挙動 | COUNTERS_DB への影響 |
|------------|----------------|------------------|
| `isSupported = "true"` | 対応 SAI カウンタを `counter_bucket_dict` に保持 → COUNTERS_DB ポーリング実行 | WRED カウンタ値が COUNTERS_DB に存在し表示可能 |
| `isSupported = "false"` | `counter_bucket_dict` から SAI カウンタを削除 → ポーリング対象外 | WRED カウンタは COUNTERS_DB に蓄積されず `N/A` 表示 |
| キー不存在 | 同上（`"false"` 扱い） | 同上 |

evidence: `portstat.py:295-331`

### 副作用の連鎖

```
portsorch コンストラクタ
  → PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_* / isSupported に "true"/"false" 書き込み
  → portstat 実行時に STATE_DB を参照して counter_bucket_dict を更新
  → COUNTERS_DB からの読み取り対象が変化（WRED SAI カウンタの含有/除外）
  → portstat CLI 出力の WRED カラムが値/N/A に分岐
```

---

## 2. DEBUG_COUNTER_CAPABILITIES → show debug-counter capabilities 出力

`DEBUG_COUNTER_CAPABILITIES` テーブルの有無・内容が `dropconfig` (`scripts/dropconfig`) の `show debug-counter capabilities` コマンド出力を決定する。

| 状態 | show debug-counter capabilities 出力 | 操作可能な後続コマンド |
|------|-----------------------------------|--------------------|
| テーブルにエントリあり | counter_type ごとの count / reasons 一覧が表示される | `config debug-counter install <type>` が実行可能 |
| テーブルが空（プラットフォーム非サポート） | 出力が空 | `config debug-counter install` は SAI が失敗する可能性が高い |

evidence: `dropconfig:423-455`（推定）, `debugcounterorch.cpp:315-363`

---

## 3. SAI WRED カウンタポーリングへの間接影響

`FlexCounterOrch` が `FLEX_COUNTER_TABLE|WRED_ECN_PORT` / `WRED_ECN_QUEUE` の `STATUS=enable` を受信すると `gPortsOrch->generateWredPortCounterMap()` を呼ぶ（flexcounterorch.cpp:273）。この関数は `wred_port_stat_ids` ベクタ（SAI カウンタ固定リスト）を `wred_port_stat_manager.setCounterIdList()` で `FLEX_COUNTER_DB` に登録する（portsorch.cpp:9491）。

- `PORT_COUNTER_CAPABILITIES` は `generateWredPortCounterMap()` から**参照されない**（直接依存なし）。
- ただし `portstat.py` が `isSupported` を読んで WRED カウンタを表示対象に含めるかどうかを決定するため、**SAI が実際にカウンタを収集していても `isSupported="false"` なら portstat は N/A を表示する**という非直感的な挙動が生じる。

evidence: `flexcounterorch.cpp:271-279`, `portsorch.cpp:9476-9494`

---

## 4. 副作用サマリ

| 副作用 | 対象 | トリガー | 範囲 |
|--------|------|---------|------|
| COUNTERS_DB WRED ポーリング有効/無効 | portstat.py / queuestat | orchagent 起動時（一回限り STATE_DB 書込み） | 書込み後すべての portstat 実行に影響 |
| show debug-counter capabilities 出力 | dropconfig CLI | 同上 | 書込み後すべての show 実行に影響 |
| portstat 表示が N/A になる | portstat CLI | `isSupported="false"` または キー不存在 | WRED 対応プラットフォームでのみ "true" |
| generateWredPortCounterMap への影響なし | FLEX_COUNTER_DB | なし（間接参照のみ） | ポーリング自体は SAI から独立して動作 |
