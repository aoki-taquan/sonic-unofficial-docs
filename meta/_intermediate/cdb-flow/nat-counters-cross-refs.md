# nat-counters-cross-refs.md — Phase C 中間ファイル

対象: `docs/reference/config-db/nat-counters.md`
調査日: 2026-05-18

## 調査ファイル

- `sonic-swss/orchagent/natorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-swss/cfgmgr/natmgrd.cpp`

## 概要

`COUNTERS_DB` NAT カウンタテーブル群（`COUNTERS_NAT` / `COUNTERS_NAPT` / `COUNTERS_TWICE_NAT` / `COUNTERS_TWICE_NAPT` / `COUNTERS_GLOBAL_NAT`）は `NatOrch` が書き手専用として管理する。カウンタエントリの生成・更新・削除は以下のテーブル・リソースへの暗黙依存によって制御される。

## 検出した暗黙参照

### 1. NAT_GLOBAL_TABLE.admin_mode (APPL_DB) — 最重要ガード

- **場所**: `natorch.cpp:2534-2582` (`enableNatFeature`), `natorch.cpp:2617-2680` (`doNatGlobalTableTask`)
- **方向**: APPL_DB `APP_NAT_GLOBAL_TABLE_NAME|Values` → COUNTERS_NAT* エントリ存在可否を制御
- **内容**: `admin_mode="enabled"` で `enableNatFeature()` が呼ばれ、SAI NAT エントリ一括登録 + カウンタ初期化が実行される。`admin_mode="disabled"` の間は `addNatEntry()` が `isNatEnabled()==false` のため早期 return し、SAI 登録もカウンタも書かれない。結果として `COUNTERS_NAT*` エントリは admin_mode が enabled になるまで COUNTERS_DB に存在しない。

### 2. APP_NAT_TABLE / APP_NAPT_TABLE (APPL_DB) — NAT エントリのキー転写

- **場所**: `natorch.cpp:789` (`addSnatEntry` 内 `updateNatCounters`), `natorch.cpp:873` (`addNaptEntry` 内 `updateNaptCounters`)
- **方向**: APPL_DB SET → SAI 登録成功 → COUNTERS_DB エントリ初期化
- **内容**: `APP_NAT_TABLE|<global_ip>` が APPL_DB に SET されると `doNatTableTask()` → `addNatEntry()` → `addHwSnatEntry()` / `addHwDnatEntry()` の順で処理。SAI 登録成功後に `updateNatCounters(ip, 0, 0)` が呼ばれ `COUNTERS_NAT|<ip>` に `NAT_TRANSLATIONS_PKTS="0"` / `NAT_TRANSLATIONS_BYTES="0"` が書き込まれる。SAI 失敗時はカウンタエントリ不在。

### 3. APP_NAT_TWICE_TABLE / APP_NAPT_TWICE_TABLE (APPL_DB) — Twice NAT エントリ

- **場所**: `natorch.cpp:1343-1430` (`addHwTwiceNatEntry`), `natorch.cpp:4108-4135` (`updateTwiceNatCounters`)
- **方向**: APPL_DB SET → SAI 登録成功 → `COUNTERS_TWICE_NAT*` エントリ初期化
- **内容**: Twice NAT / Twice NAPT エントリも同様のパターン。`addHwTwiceNatEntry()` 成功後に `updateTwiceNatCounters(key, 0, 0)` が呼ばれる。

### 4. FLUSHNATSTATISTICS 通知 (APPL_DB) — カウンタリセット

- **場所**: `natorch.cpp:3271-3303` (`clearCounters`), コンストラクタ `m_flushNotificationsConsumer = new NotificationConsumer(appDb, "FLUSHNATSTATISTICS")`
- **方向**: APPL_DB 通知 → SAI reset → カウンタ 0 リセット
- **内容**: `sonic-clear nat statistics` が `FLUSHNATSTATISTICS` 通知を APPL_DB に送信すると `clearCounters()` が呼ばれ、各 NAT エントリに対して SAI `reset_nat_entry_attribute` を実行後 `updateNatCounters(…,0,0)` でカウンタを `"0"` にリセットする。次の 5 秒タイマ周期まで COUNTERS_DB は `"0"` のまま。

### 5. SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY — MAX_NAT_ENTRIES の決定

- **場所**: `natorch.cpp:115-130` (NatOrch コンストラクタ)
- **方向**: SAI クエリ → `COUNTERS_GLOBAL_NAT|Values.MAX_NAT_ENTRIES` 書込み
- **内容**: NatOrch 起動時に `sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr)` で `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を取得し、`COUNTERS_GLOBAL_NAT|Values` の `MAX_NAT_ENTRIES` フィールドに書き込む。SAI クエリ失敗時は `"0"` → `gIsNatSupported=false` → NAT 機能全体が無効化される（`enableNatFeature()` で即 return）。

### 6. SAI NAT カウンタ API — 5 秒周期ポーリング

- **場所**: `natorch.cpp:3118-3177` (`queryCounters`), `natorch.cpp:3095-3117` (`doTask(SelectableTimer)`)
- **方向**: SAI `get_nat_entry_attribute` → COUNTERS_NAT* フィールド更新
- **内容**: `NAT_HITBIT_N_CNTRS_QUERY_PERIOD=5` 秒のタイマ割り込みで `queryCounters()` が呼ばれ、全 NAT エントリの `SAI_NAT_ENTRY_ATTR_PACKET_COUNT` / `SAI_NAT_ENTRY_ATTR_BYTE_COUNT` を取得して COUNTERS_DB を更新する。タイマは `enableNatFeature()` で start、`disableNatFeature()` で stop される。

### 7. RouteOrch / NeighOrch (DNAT NH 解決) — 間接依存

- **場所**: `natorch.cpp:155-202` (`update`), `natorch.cpp:390-432` (`addDnatToNhCache`)
- **方向**: NH 解決通知 → `addHwDnatEntry()` 呼び出し → カウンタ初期化
- **内容**: DNAT エントリは宛先 IP への next-hop が解決されるまで SAI 登録されない。`m_routeOrch->attach(this, translatedIp)` で RouteOrch のオブザーバとして登録し、NH 解決コールバック (`update(SubjectType::SUBJECT_TYPE_NEXTHOP_CHANGE, ...)`) 受信後に `addHwDnatEntry()` が実行されてカウンタが初期化される。NH 未解決の間は `COUNTERS_NAT|<ip>` エントリは COUNTERS_DB に存在しない。

## 参照タイプ別サマリ

| 参照先テーブル / リソース | DB | 方向 | 契機 | 備考 |
|--------------------------|-----|------|------|------|
| `NAT_GLOBAL_TABLE\|Values.admin_mode` | APPL_DB | READ (トリガ) | admin_mode 変更 | `"enabled"` でカウンタ一括初期化、`"disabled"` で一括削除 |
| `APP_NAT_TABLE\|<ip>` | APPL_DB | SET (トリガ) | NAT エントリ追加 | SAI 登録成功後に COUNTERS_NAT エントリ生成 |
| `APP_NAPT_TABLE\|<proto>:<ip>:<port>` | APPL_DB | SET (トリガ) | NAPT エントリ追加 | SAI 登録成功後に COUNTERS_NAPT エントリ生成 |
| `APP_NAT_TWICE_TABLE\|<src>:<dst>` | APPL_DB | SET (トリガ) | Twice NAT エントリ追加 | SAI 登録成功後に COUNTERS_TWICE_NAT エントリ生成 |
| `FLUSHNATSTATISTICS` | APPL_DB | 通知 | `sonic-clear nat statistics` | 全カウンタを SAI reset + `"0"` 書込み |
| `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` | SAI | クエリ | NatOrch 起動時 1 回 | `MAX_NAT_ENTRIES` 決定。0 なら NAT 機能無効 |
| SAI NAT カウンタ API | SAI | 5 秒周期クエリ | タイマ割り込み | `NAT_TRANSLATIONS_PKTS/BYTES` 実値更新 |
| `RouteOrch` NH 解決通知 | orchagent 内部 | コールバック | DNAT NH 解決時 | NH 未解決時は DNAT カウンタエントリ不在 |
