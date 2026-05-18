# nat-counters — Phase B ordering 調査メモ

## 調査対象
- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 検出された順序依存

### 1. Constructor → COUNTERS_GLOBAL_NAT 初期化 (強制先行)
`NatOrch::NatOrch()` コンストラクタ末尾で SAI クエリ後に
`m_countersGlobalNatTable.set("Values", values)` を一度だけ呼ぶ。
`enableNatFeature()` / エントリ追加よりも必ず先行する。
evidence: `natorch.cpp:127-134`

### 2. `gIsNatSupported=false` → カウンタ更新タイマー不起動
`enableNatFeature()` 冒頭で `gIsNatSupported==false` なら即 return。
`m_natQueryTimer->start()` に到達しない → `queryCounters()` は呼ばれない →
`COUNTERS_NAT*` テーブルはエントリ追加時の初期化 (0) から変化しない。
evidence: `natorch.cpp:2541-2565`

### 3. NAT_GLOBAL admin_mode=enabled → タイマー起動 → 周期更新
`doTask(Consumer)` が `APP_NAT_GLOBAL_TABLE_NAME` を処理し mode=="enabled" のとき
`enableNatFeature()` → `m_natQueryTimer->start()`。
以降 5 秒ごとに `doTask(SelectableTimer)` → `queryCounters()` が各エントリをポーリングし
`update*Counters()` で COUNTERS_DB を更新する。
evidence: `natorch.cpp:2943,2565,3099-3122`

### 4. SAI エントリ作成 → カウンタ 0 初期化 → 最初の更新は 5s 後
`addNatEntry()` が SAI `create_nat_entry` 成功後に `updateNatCounters(ip, 0, 0)` を呼ぶ。
カウンタが 0 以外の値になるのは次の `queryCounters()` 呼び出し後 (最大 5 秒後)。
evidence: `natorch.cpp:789` (NAT), `873` (NAPT), `1322` (SNAT), `1404,1495,1591` (Twice*)

### 5. エントリ削除 → カウンタキー削除 (即時)
`deleteNatCounters()` は SAI DEL 後即座に COUNTERS_DB から対応キーを del() する。
evidence: `natorch.cpp:943,1131,1645,1734`

### orchdaemon 優先度
NatOrch テーブル優先度 (orchdaemon.cpp:457-462):
- APP_NAT_DNAT_POOL_TABLE_NAME: 55
- APP_NAT_TABLE_NAME: 54
- APP_NAPT_TABLE_NAME: 53
- APP_NAT_TWICE_TABLE_NAME: 52
- APP_NAPT_TWICE_TABLE_NAME: 51
- APP_NAT_GLOBAL_TABLE_NAME: 50 (最低 → admin_mode 変更は他テーブルより後処理)
