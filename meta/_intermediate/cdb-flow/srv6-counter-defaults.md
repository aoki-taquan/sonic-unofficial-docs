# srv6-counter — Phase A: コード由来デフォルト調査メモ

対象ページ: `docs/reference/config-db/srv6-counter.md`
調査日: 2026-05-15

---

## 対象テーブル

`FLEX_COUNTER_TABLE|SRV6` — SRv6 MySID エントリのパケット/バイトカウンタ収集設定。

---

## フィールド一覧と型

YANG (`sonic-flex_counter.yang` container SRV6):
- `FLEX_COUNTER_STATUS`: enum `enable` / `disable`
- `FLEX_COUNTER_DELAY_STATUS`: `boolean_type`
- `POLL_INTERVAL`: uint32 (range 100..4294967295) [ms]

`BULK_CHUNK_SIZE` / `BULK_CHUNK_SIZE_PER_PREFIX` は YANG にも orchagent にも SRV6 グループ向けに定義なし。

---

## コード由来デフォルト

### FLEX_COUNTER_STATUS

- YANG に `default` 宣言なし。
- FlexCounterManager コンストラクタ: `m_counter_manager(..., false)` → enabled=false でインスタンス化。
  - ソース: `sonic-swss/orchagent/srv6orch.cpp:108`
- `counterpoll show` の表示デフォルト: `srv6_info.get("FLEX_COUNTER_STATUS", DISABLE)` — 未設定時 `disable` 表示。
  - ソース: `sonic-utilities/counterpoll/main.py:841`
- init_cfg.json.j2 に SRV6 エントリなし → ビルド時デフォルト書き込みなし。
- **暗黙デフォルト: `disable`**

### FLEX_COUNTER_DELAY_STATUS

- YANG に `default` なし。
- SRv6 orch コードに `FLEX_COUNTER_DELAY_STATUS` を参照するコードなし → 未設定のまま運用可。
- **暗黙デフォルト: 未設定（delay なし・即時）**

### POLL_INTERVAL

- ハードコード: `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS = 10000` (ms) — srv6orch.cpp:27
  - FlexCounterManager 初期化時に syncd へ送信される初期 polling interval。
- counterpoll CLI: `click.IntRange(1000, 30000)` — 入力可能範囲 1000〜30000 ms。
  - 表示ソフトデフォルト: `DEFLT_10_SEC = "default (10000)"` — counterpoll main.py:19
- YANG range: 100..4294967295 (CLI は上限を 30000 ms に制限)。
- **ハードコードデフォルト: 10000 ms**

---

## SRV6_COUNTER_ID_LIST — FLEX_COUNTER_DB フィールド

- syncd での counter type: `COUNTER_TYPE_SRV6 = "SRv6 Counter"` (FlexCounter.cpp:44)
- SAI object type: `SAI_OBJECT_TYPE_COUNTER`
- stat type: `sai_counter_stat_t`
- schema.h: `SRV6_COUNTER_ID_LIST` (line 313)
- flex_counter_manager.cpp:56: `{ CounterType::SRV6, SRV6_COUNTER_ID_LIST }`
- 収集 stat: `SAI_COUNTER_STAT_PACKETS`, `SAI_COUNTER_STAT_BYTES` (flow_counter_handler.cpp:12-13)
  - これら 2 stat のみ — `FlowCounterHandler::getGenericCounterStatIdList()` が返すリスト。
- COUNTERS_DB での名前マップ: `COUNTERS_SRV6_NAME_MAP` (schema.h:257)

---

## プラットフォーム能力チェック

`Srv6Orch::queryMySidCountersCapability()` が起動時に `sai_query_attribute_capability(SAI_OBJECT_TYPE_MY_SID_ENTRY, SAI_MY_SID_ENTRY_ATTR_COUNTER_ID)` を呼び出す。
- 失敗 or capability なし → `m_mysid_counters_supported = false` → `FLEX_COUNTER_STATUS = enable` を書き込んでも SAI 設定ゼロ、ログ: `"SRv6 counters are not supported on this platform"`。
- ソース: srv6orch.cpp:122-125, 147-155

---

## counter 更新タイマー

`SRV6_FLEX_COUNTER_UPDATE_TIMER = 1` 秒。`m_pending_counters` に溜まった counter OID を 1 秒ごとに syncd へ登録する遅延登録メカニズム。
ソース: srv6orch.cpp:26, 138-139

---

## エビデンスファイル一覧

| ファイル | 参照箇所 |
|---------|---------|
| `sonic-swss/orchagent/srv6orch.cpp` | :27 (polling interval), :108 (constructor enabled=false), :122-125 (capability), :138 (update timer) |
| `sonic-swss/orchagent/srv6orch.h` | :30 (SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP), :267 (m_mysid_counters_enabled=false) |
| `sonic-swss/orchagent/flex_counter/flow_counter_handler.cpp` | :12-13 (stat IDs) |
| `sonic-swss/orchagent/flex_counter/flex_counter_manager.cpp` | :56 (SRV6 counter type) |
| `sonic-swss/orchagent/flexcounterorch.cpp` | :64 (SRV6_KEY), :96, :337 (setCountersState call) |
| `sonic-sairedis/syncd/FlexCounter.cpp` | :44 (COUNTER_TYPE_SRV6), :97, :3431 (SAI_OBJECT_TYPE_COUNTER) |
| `sonic-swss-common/common/schema.h` | :257 (COUNTERS_SRV6_NAME_MAP), :313 (SRV6_COUNTER_ID_LIST) |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-flex_counter.yang` | :465-479 (SRV6 container) |
| `sonic-utilities/counterpoll/main.py` | :682-716 (srv6 commands), :840-841 (show defaults) |
| `sonic-utilities/utilities_common/srv6stat.py` | 全体 (COUNTER_PACKETS/BYTES stat names) |
