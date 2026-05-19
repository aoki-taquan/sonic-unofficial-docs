# nat-state — Phase F 副次 DB 書込みスキャンノート

対象ページ: `docs/reference/config-db/nat-state.md`
対象テーブル:
  - `STATE_DB:NAT_RESTORE_TABLE`
  - `COUNTERS_DB:COUNTERS_NAT` / `COUNTERS_NAPT` / `COUNTERS_TWICE_NAT` / `COUNTERS_TWICE_NAPT` / `COUNTERS_GLOBAL_NAT`
Producer: `restore_nat_entries.py` (STATE_DB) / `NatOrch` (COUNTERS_DB)
スキャン範囲:
  - `sonic-buildimage/dockers/docker-nat/restore_nat_entries.py` — conntrack 復元 + STATE_DB 書込み
  - `sonic-swss/orchagent/natorch.cpp` — NatOrch constructor / enableNatFeature / disableNatFeature / queryCounters / queryHitBits / cleanupAppDbEntries
  - `sonic-swss/natsyncd/natsyncd.cpp` — warm restart loop / isNatRestoreDone polling
  - `sonic-swss/natsyncd/natsync.cpp` — isNatRestoreDone / reconcile

---

## 検出した副次書込み

### 1. `restore_nat_entries.py` → STATE_DB:NAT_RESTORE_TABLE|Flags.restored

- warm reboot 後、`restore_nat_entries.py` が `/var/warmboot/nat/nat_entries.dump` を読んで kernel conntrack に各エントリを復元する。
- 全エントリ復元完了後に `db.hset('NAT_RESTORE_TABLE|Flags', 'restored', 'true')` を STATE_DB に書く (`restore_nat_entries.py:49-52`)。
- **副次書込みの性質**: conntrack カーネル操作（非 Redis）の完了通知として STATE_DB に書く。STATE_DB 以外への書込みはなし。
- **条件**: NAT warm restart が有効な起動のみ。通常起動では `restore_nat_entries.py` 自体が実行されないため STATE_DB への書込みは発生しない。

### 2. NatOrch コンストラクタ → COUNTERS_GLOBAL_NAT|Values（初期化の副次効果）

- `NatOrch::NatOrch()` は起動時に SAI から `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を取得し、`MAX_NAT_ENTRIES` / `TIMEOUT` / `UDP_TIMEOUT` / `TCP_TIMEOUT` を `COUNTERS_GLOBAL_NAT|Values` に一度だけ書き込む (`natorch.cpp:108-138`)。
- **副次書込みの性質**: NatOrch の初期化処理（Config_DB 処理の開始前）として発生するため、これらのフィールドは CONFIG_DB から設定値を読む前に書き込まれる。
- **条件**: orchagent 起動のたびに発生。CONFIG_DB 変更では再書込みされない（起動時 1 回限り）。

### 3. NatOrch `enableNatFeature()` → SAI NAT 有効化 + タイマー起動

- APPL_DB `NAT_GLOBAL_TABLE.admin_mode=enabled` を受信すると `enableNatFeature()` (`natorch.cpp:2534-2580`) が呼ばれる。
- SAI `set_switch_attribute(SAI_SWITCH_ATTR_NAT_ENABLE=true)` を発行し、`m_natQueryTimer->start()` / `m_natTimeoutTimer->start()` を開始する。
- 直後に `addAllDnatPoolEntries()` → `addAllNatEntries()` で既存 APPL_DB エントリを SAI に再登録し、各エントリの COUNTERS_NAT* に初期値 `"0"` を書き込む。
- **副次書込み対象**: SAI (ASIC_DB 経由) + COUNTERS_DB の COUNTERS_NAT* 系テーブル。
- **条件**: `admin_mode` が `disabled` → `enabled` に変化したとき。`gIsNatSupported == false` の場合は即 return。

### 4. NatOrch `disableNatFeature()` → SAI NAT 無効化 + タイマー停止

- `admin_mode=disabled` への変化で `disableNatFeature()` (`natorch.cpp:2583-2627`) が呼ばれる。
- SAI `set_switch_attribute(SAI_SWITCH_ATTR_NAT_ENABLE=false)` を発行し、タイマーを停止する。
- 全 NAT エントリを SAI から削除するが、COUNTERS_DB の COUNTERS_NAT* エントリはそのまま残す（削除しない）。
- **副次書込み対象**: SAI (ASIC_DB 経由)。COUNTERS_DB への削除は行われない（差異に注意）。

### 5. NatOrch `cleanupAppDbEntries()` → COUNTERS_NAT* 全削除

- `NAT_DB_CLEANUP_NOTIFICATION` 通知（natorch docker 停止時に APPL_DB に送信）を受信すると `cleanupAppDbEntries()` (`natorch.cpp:2457-2532`) を呼ぶ。
- 全 NAT エントリを APPL_DB から削除し、対応する COUNTERS_NAT* エントリも `deleteNatCounters()` で削除する。
- **副次書込み対象**: APPL_DB + COUNTERS_DB（全 COUNTERS_NAT* キー削除）。
- **条件**: natorch docker 停止シグナル時のみ。

### 6. STATE_DB への書戻しなし

- `NatOrch` は COUNTERS_DB に書き込むが STATE_DB への書き込みは行わない。
- `natsyncd` は STATE_DB を読むのみで書き込まない。
- FLEX_COUNTER_DB / LOGLEVEL_DB / CONFIG_DB への副次書込みは確認されなかった。

---

## 副次書込みサマリ表

| # | 書込先 | テーブル / キー | 内容 | 発火条件 |
|---|--------|----------------|------|---------|
| 1 | STATE_DB | `NAT_RESTORE_TABLE\|Flags.restored` | `"true"` | warm restart 時、conntrack 復元完了後 (`restore_nat_entries.py:51`) |
| 2 | COUNTERS_DB | `COUNTERS_GLOBAL_NAT\|Values` (4 フィールド) | `MAX_NAT_ENTRIES` / `TIMEOUT` / `UDP_TIMEOUT` / `TCP_TIMEOUT` 初期値 | orchagent 起動時 1 回 (`natorch.cpp:127-138`) |
| 3 | SAI (ASIC_DB) | `SAI_SWITCH_ATTR_NAT_ENABLE` | `true` | `admin_mode=enabled` 受信 (`natorch.cpp:2553-2560`) |
| 4 | COUNTERS_DB | `COUNTERS_NAT*\|<key>` 各エントリ | 初期値 `NAT_TRANSLATIONS_PKTS/BYTES="0"` | enable 後の `addAllNatEntries()` (`natorch.cpp:789, 1322, 873, 1495`) |
| 5 | SAI (ASIC_DB) | `SAI_SWITCH_ATTR_NAT_ENABLE` | `false` | `admin_mode=disabled` 受信 (`natorch.cpp:2589-2596`) |
| 6 | APPL_DB + COUNTERS_DB | `NAT_TABLE*` + `COUNTERS_NAT*` 全削除 | 全エントリ削除 | docker 停止通知 (`natorch.cpp:4474-4478`) |

---

## ページ反映方針

- `<!-- side-effects -->` ブロックを `<!-- /constants -->` の直後、`<!-- defaults -->` の前に挿入する。
- 既存の `<!-- constants -->` / `<!-- defaults -->` / `<!-- ordering -->` / `<!-- cross-refs -->` / `<!-- failure -->` ブロックは変更しない。
- 副次書込みサマリ表（#1〜#6）＋主要副次効果の詳細を含める。
- warm restart 経路 (`restore_nat_entries.py`) と orchagent 経路 (`NatOrch`) の 2 系統を明示する。
