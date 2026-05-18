# SRv6 カウンタ状態 — Phase C テーブル間クロスリファレンス スキャンノート

対象テーブル: `COUNTERS_SRV6_NAME_MAP` / `COUNTERS:<oid>` (COUNTERS_DB)
Consumer: `Srv6Orch` (`srv6orch.cpp`), `srv6stat.py` (`sonic-utilities`)
スキャン範囲: `addMySidCounter()`, `removeMySidCounter()`, `setCountersState()`, `initializeCounters()`, `getMySidCounterKey()`, `srv6stat.py` 全行精読

---

## 検出したクロスリファレンス

### 1. COUNTERS_SRV6_NAME_MAP ← SRV6_MY_SIDS (CONFIG_DB) 経由

`Srv6Orch::createUpdateMysidEntry()` が APPL_DB `SRV6_MY_SID_TABLE` イベントを処理して SAI に MySID を作成した後、
`addMySidCounter()` が `COUNTERS_SRV6_NAME_MAP` にエントリを書き込む。
`COUNTERS_SRV6_NAME_MAP` のキー（`<mysid_prefix>`）は `getMySidCounterKey()` が生成し、
生成ロジックに `SRV6_MY_LOCATORS` の `block_len + node_len + func_len` を使用する（`srv6orch.cpp:177-182`）。

**参照関係**: `COUNTERS_SRV6_NAME_MAP` キーの プレフィックス長は CONFIG_DB `SRV6_MY_LOCATORS` のビット長フィールドに依存する。ロケータ設定が変わるとカウンタキーが変わり、旧キーの `show srv6 stats` エントリが孤立する可能性がある。

evidence: `srv6orch.cpp:177-199`, `srv6orch.cpp:1591-1601`

### 2. COUNTERS:<oid> ← FLEX_COUNTER_DB (SRV6_COUNTER_ID_LIST)

`addMySidCounter()` は `COUNTERS_SRV6_NAME_MAP` に OID を書いた後、1 秒タイマー経過後に
`m_counter_manager.setCounterIdList()` で `FLEX_COUNTER_DB` の `SRV6_COUNTER_ID_LIST` に登録する。
`syncd` の FlexCounter が `SRV6_STAT_COUNTER` グループを 10 秒周期でポーリングして
`COUNTERS_DB` の `COUNTERS|<oid>` に `SAI_COUNTER_STAT_PACKETS` / `SAI_COUNTER_STAT_BYTES` を書き込む。

**参照関係**: `COUNTERS:<oid>` は `FLEX_COUNTER_DB|SRV6_COUNTER_ID_LIST` の間接的な書き込みトリガーを経由する。

evidence: `srv6orch.cpp:26-27`, `srv6orch.cpp:184-210`, `schema.h:257,313`

### 3. COUNTERS_SRV6_NAME_MAP ← FLEX_COUNTER_TABLE|SRV6 enable トリガー

`setCountersState(true)` (`srv6orch.cpp:261-283`) は `FLEX_COUNTER_TABLE|SRV6` が enable になったとき
既存の全 MySID エントリを走査して `addMySidCounter()` を呼ぶ。
`setCountersState(false)` は逆に全 MySID の `removeMySidCounter()` を呼ぶ。

**参照関係**: `COUNTERS_SRV6_NAME_MAP` は `FLEX_COUNTER_TABLE|SRV6` の enable/disable 状態と連動して一括作成・削除される。

evidence: `srv6orch.cpp:261-283`

### 4. srv6stat.py ← COUNTERS_SRV6_NAME_MAP + COUNTERS:<oid>

`srv6stat.py` の `SRv6Stat.show()` は以下の 2 テーブルを参照する:
- `COUNTERS_DB|COUNTERS_SRV6_NAME_MAP` — MySID prefix → OID マッピング（`srv6stat.py:get_all()`）
- `COUNTERS_DB|COUNTERS|<oid>` — パケット・バイトカウンタ値（`srv6stat.py:get_counter_value()`）

**参照関係**: CLI `show srv6 stats` は COUNTERS_DB の 2 テーブルにのみ依存し、CONFIG_DB を直接読まない。

evidence: `srv6stat.py` 全行

---

## クロスリファレンスサマリ

| 参照元 | 参照先 | 種別 | 必須条件 |
|--------|--------|------|----------|
| `COUNTERS_SRV6_NAME_MAP` キー | `SRV6_MY_LOCATORS.block_len/node_len/func_len` | ビット長計算 (直接 GET) | ロケータが CONFIG_DB に存在すること（欠落でキー計算失敗） |
| `COUNTERS:<oid>` | `FLEX_COUNTER_DB SRV6_COUNTER_ID_LIST` | 間接トリガー | SAI 対応プラットフォームであること |
| `COUNTERS_SRV6_NAME_MAP` (一括) | `FLEX_COUNTER_TABLE\|SRV6` | enable/disable 連動 | setCountersState() 呼び出し |
| `show srv6 stats` (CLI) | `COUNTERS_DB COUNTERS_SRV6_NAME_MAP`, `COUNTERS:<oid>` | 直接読取 | カウンタ初期化後 最大 11 秒待ち |
