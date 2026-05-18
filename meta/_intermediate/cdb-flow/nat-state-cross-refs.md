# nat-state — Phase C 暗黙参照テーブルスキャンノート

対象ページ: `docs/reference/config-db/nat-state.md`
対象テーブル:
  - `STATE_DB:NAT_RESTORE_TABLE`
  - `COUNTERS_DB:COUNTERS_NAT` / `COUNTERS_NAPT` / `COUNTERS_TWICE_NAT` / `COUNTERS_TWICE_NAPT` / `COUNTERS_GLOBAL_NAT`
Producer: `restore_nat_entries.py` (STATE_DB) / `NatOrch` (COUNTERS_DB)
スキャン範囲: `orchagent/natorch.cpp` NatOrch コンストラクタ / `doTask()` dispatch / `addSnatEntry()` / `addDnatEntry()` / `queryCounters()` / `updateSnatCounters()` / `updateDnatCounters()` / `natsyncd/natsync.cpp` `isNatRestoreDone()` / `scripts/natshow` / `config/nat.py`

---

## 検出した暗黙参照

### 1. `APP_NAT_GLOBAL_TABLE_NAME` (APPL_DB: `NAT_GLOBAL_TABLE`) — admin_mode トリガ

- `NatOrch::doTask()` は `APP_NAT_GLOBAL_TABLE_NAME` を購読し、`admin_mode` フィールド変化で `enableNatFeature()` / `disableNatFeature()` を呼ぶ (`natorch.cpp:3061-3064`)。
- `enableNatFeature()` (`natorch.cpp:2534-2567`) で `m_natQueryTimer` を開始 → 5 秒周期カウンタポーリング開始 → `COUNTERS_NAT*` 更新開始。
- **参照方向**: APPL_DB `NAT_GLOBAL_TABLE.admin_mode` の値が COUNTERS_DB の更新可否を制御する。

### 2. `APP_NAT_TABLE_NAME` / `APP_NAPT_TABLE_NAME` 等 (APPL_DB) — エントリキー転写

- `doNatTableTask()` (`natorch.cpp:2617-`) / 類似関数で APPL_DB の NAT エントリを処理し、SAI に登録する。
- 登録成功直後に `updateNatCounters(ipAddr, 0, 0)` / `updateNaptCounters(...)` を呼び `COUNTERS_NAT|<ip>` / `COUNTERS_NAPT|<proto:ip:port>` に初期値 `"0"` を書き込む (`natorch.cpp:789, 1322`)。
- **参照方向**: APPL_DB NAT エントリのキー（IP / プロトコル:IP:ポート）が `COUNTERS_NAT*` のキーに転写される。

### 3. SAI Switch attribute `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` — MAX_NAT_ENTRIES 決定

- NatOrch コンストラクタで SAI からクエリし、取得値を `maxAllowedSNatEntries` に格納して `COUNTERS_GLOBAL_NAT|Values.MAX_NAT_ENTRIES` に書き込む (`natorch.cpp:108-130`)。
- クエリ失敗時は `maxAllowedSNatEntries=0` → `gIsNatSupported=false` → NAT 機能が無効化される。
- **参照方向**: SAI クエリ結果 → `COUNTERS_GLOBAL_NAT|Values.MAX_NAT_ENTRIES` (1 回限り)。

### 4. `restore_nat_entries.py` (sonic-buildimage) — STATE_DB 書き手

- warm reboot 後に `/var/warmboot/nat/nat_entries.dump` を読み、kernel conntrack に復元し、完了後に `STATE_DB:NAT_RESTORE_TABLE|Flags.restored = "true"` を書く (`restore_nat_entries.py:49-52`)。
- **参照方向**: `restore_nat_entries.py` が唯一の書き手。`natsyncd` は読み手のみ。

### 5. `natsyncd` — STATE_DB 読み手 (warm reboot 時のみ)

- `isNatRestoreDone()` (`natsync.cpp:96-108`) で `STATE_DB:NAT_RESTORE_TABLE|Flags.restored` を確認。
- `"true"` になってから reconciliation を開始する。通常起動では参照されない。

### 6. `natshow` スクリプト / `config/nat.py` — COUNTERS_DB 読み手

- `scripts/natshow` (`natshow:93-95`, `natshow:217-234`) が `COUNTERS_GLOBAL_NAT:Values` / `COUNTERS_NAT:<ip>` を参照し `show nat statistics` / `show nat translations` に表示。
- `config/nat.py` (`nat.py:290-295`, `nat.py:382-387`, `nat.py:475-480`) が `COUNTERS_GLOBAL_NAT:Values.SNAT_ENTRIES` / `MAX_NAT_ENTRIES` を参照し、エントリ上限チェックや統計情報の表示に使用。

---

## ページ反映方針

- `<!-- cross-refs -->` ブロックを `<!-- ordering -->` の直後（`<!-- /ordering -->` の次行）に挿入する。
- 既存の `<!-- defaults -->` / `<!-- ordering -->` / `<!-- cdb-mermaid -->` は変更しない。
- 暗黙参照表と 2 つの note admonition（書き手/読み手の分離、COUNTERS_GLOBAL_NAT の起動時書込み特性）を含める。
