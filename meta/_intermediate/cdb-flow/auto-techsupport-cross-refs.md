# AUTO_TECHSUPPORT / AUTO_TECHSUPPORT_FEATURE — Phase C 暗黙参照抽出

**対象ページ**: `docs/reference/config-db/auto-techsupport.md`, `docs/reference/config-db/auto-techsupport-feature.md`
**ソース**: `sonic-utilities/scripts/coredump_gen_handler.py`, `sonic-utilities/utilities_common/auto_techsupport_helper.py`, `sonic-host-services/scripts/hostcfgd`
**作成日**: 2026-05-16

## 抽出結果 — AUTO_TECHSUPPORT (GLOBAL)

### 1. AUTO_TECHSUPPORT_FEATURE|{container}（暗黙参照）

- **参照種別**: 読み取り（実行時条件）
- **利用箇所**: `CriticalProcCoreDumpHandle.handle_core_dump_creation_event()` 内で `FEATURE.format(self.container)` キーを構築し `cfg_db.get(CFG_DB, FEATURE_KEY, CFG_STATE)` を呼び出す。`AUTO_TECHSUPPORT|GLOBAL.state=enabled` 確認後にのみ到達する。feature エントリの `state != "enabled"` の場合は techsupport 起動をスキップ。
- **evidence**: `sonic-utilities/scripts/coredump_gen_handler.py:54-56`

### 2. STATE_DB AUTO_TECHSUPPORT_DUMP_INFO|{dump_name}（書き込み）

- **参照種別**: 書き込み（副作用）
- **利用箇所**: `invoke_ts_command_rate_limited()` が techsupport 生成成功後に `write_to_state_db()` を呼び出し、`TS_MAP|{dump_name}` キーで `timestamp`, `event_type`, `core_dump`, `container_name` を STATE_DB に格納。次回の rate-limit 判定の基準となる。
- **evidence**: `sonic-utilities/utilities_common/auto_techsupport_helper.py:302-337`

### 3. DEVICE_METADATA|localhost（間接依存、hostcfgd 経由）

- **参照種別**: 読み取り（間接）
- **利用箇所**: `hostcfgd` が起動時に `DEVICE_METADATA` テーブルを `get_table()` / `subscribe()` で取得。`AUTO_TECHSUPPORT` の初期有効化は `init_cfg.json.j2` の `enable_auto_tech_support` ビルドフラグ経由で行われるが、`hostcfgd` がシステム識別情報として `DEVICE_METADATA|localhost` を参照する前提がある。
- **evidence**: `sonic-host-services/scripts/hostcfgd:1422, 2247, 2492`

## 抽出結果 — AUTO_TECHSUPPORT_FEATURE

### 1. AUTO_TECHSUPPORT|GLOBAL.state（先行ガード）

- **参照種別**: 読み取り（先行条件ガード）
- **利用箇所**: `coredump_gen_handler.py` は `handle_core_dump_creation_event()` の冒頭で `db.get(CFG_DB, AUTO_TS, CFG_STATE)` を評価し、`"enabled"` でなければ `AUTO_TECHSUPPORT_FEATURE` を参照せずに即 return する。FEATURE エントリは GLOBAL の `state` が `enabled` のときのみ評価される。
- **evidence**: `sonic-utilities/scripts/coredump_gen_handler.py:47-48`

### 2. AUTO_TECHSUPPORT|GLOBAL.rate_limit_interval（二段階 rate-limit）

- **参照種別**: 読み取り（rate-limit 判定）
- **利用箇所**: `invoke_ts_command_rate_limited()` が `GLOBAL` の `COOLOFF` (`rate_limit_interval`) と `FEATURE|{container}` の `COOLOFF` の両方を取得し、`verify_rate_limit_intervals()` で global・per-container の二段階判定を行う。どちらか一方でも期間内なら techsupport をスキップ。
- **evidence**: `sonic-utilities/utilities_common/auto_techsupport_helper.py:313-333`

### 3. STATE_DB AUTO_TECHSUPPORT_DUMP_INFO|*（読み取り & 書き込み）

- **参照種別**: 読み取り（rate-limit）/ 書き込み（記録）
- **利用箇所**: `verify_rate_limit_intervals()` が STATE_DB の `AUTO_TECHSUPPORT_DUMP_INFO` テーブルを走査し、per-container の前回 dump 時刻を取得して rate-limit を判定する。techsupport 生成後は `write_to_state_db()` でコンテナ名付き新エントリを書き込む。
- **evidence**: `sonic-utilities/utilities_common/auto_techsupport_helper.py:257-338`

## 既存ページとの整合性確認

| 既存記述 | 確認結果 |
|---------|---------|
| `GLOBAL.state=disabled` → FEATURE エントリに関わらず全スキップ | `coredump_gen_handler.py:47` で `AUTO_TS` の `state` を先頭確認 — 整合 |
| `rate_limit_interval` で連続起動を抑制 | GLOBAL・FEATURE 両方の cooloff を二段階で適用 — 整合 |
| STATE_DB への dump 情報記録 | `write_to_state_db()` で `AUTO_TECHSUPPORT_DUMP_INFO` テーブルへ書き込み — 整合 |
| `coredump_gen_handler` が CONFIG_DB を参照 | `SonicV2Connector` で CONFIG_DB/STATE_DB 両方に接続 — 整合 |
