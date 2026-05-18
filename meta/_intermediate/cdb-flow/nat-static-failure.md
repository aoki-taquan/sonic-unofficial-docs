# STATIC_NAT 失敗挙動調査メモ (Phase D)

調査日: 2026-05-18
対象テーブル: CONFIG_DB `STATIC_NAT`

## 調査対象ファイル

- `sonic-swss/cfgmgr/natmgr.cpp` (`doStaticNatTask` L5813-6136, `addStaticNatEntry` L1548-1590, `addStaticSingleNatEntry` L1992-2064)
- `sonic-swss/orchagent/natorch.cpp` (`doNatTableTask` L2617-2681, `addNatEntry` L1866-1937, `addHwDnatEntry` L738-800, `addHwSnatEntry` L1271-1330)

---

## 段階 1: CONFIG_DB → natmgrd 失敗パターン

### 即時 DROP (m_toSync.erase) パターン

- `local_ip` 欠落: `natmgr.cpp:5902-5907` — `SWSS_LOG_ERROR + erase`
- `nat_type` が `snat`/`dnat` 以外: `natmgr.cpp:5954-5958` — ERROR + erase
- `global_ip` 特殊アドレス (Zero/BC/Loop/MC/Reserved): `natmgr.cpp:5855-5861` — ERROR + erase
- `local_ip` 特殊アドレス: `natmgr.cpp:5944-5950` — ERROR + erase
- `global_ip` と STATIC_NAPT 重複: `natmgr.cpp:6007-6011` — ERROR + erase
- `global_ip` と NAT_POOL IP 範囲重複: `natmgr.cpp:6052-6056` — ERROR + erase
- 重複エントリ (key + local_ip 一致): `natmgr.cpp:6067` — ERROR + erase
- 未知フィールド (nonValueFound=true): `natmgr.cpp:5897-5933` — ERROR + erase

### キャッシュ保持 → 自動回復パターン

- `NAT_GLOBAL.admin_mode != enabled`: `natmgr.cpp:1557-1560` — `addStaticNatEntry()` が即 return。
  エントリは `m_staticNatEntry` に格納済み。admin_mode が enabled になると `addStaticNatEntries()` で再処理 (`natmgr.cpp:3040`)。
- DNAT でインタフェース IP 未設定: `natmgr.cpp:1564-1568` — `getIpEnabledIntf()` が false → return。
  インタフェース ready 時に `doNatIpInterfaceTask()` が `addStaticNatEntries()` を呼び再処理 (`natmgr.cpp:7640`)。

### iptables 失敗パターン

`addStaticSingleNatEntry()` 末尾の `setStaticNatIptablesRules()` 失敗:
- APPL_DB への `m_appNatTableProducer.set()` は既に完了している
- `SWSS_LOG_ERROR("Failed to add Static NAT iptables rules for %s")` のみ
- APPL_DB は書かれたまま、iptables は未設定 → **不整合状態が残る**

---

## 段階 2: APPL_DB → NatOrch → SAI 失敗パターン

### 即時 DROP パターン

- APPL_DB `NAT_TABLE` キーサイズ != 1: `natorch.cpp:2636-2640` — ERROR + erase
- 不明 op type: `natorch.cpp:2672-2675` — ERROR + erase

### 暗黙成功 (エラーなし) パターン

- 重複エントリ (`m_natEntries` に既存): `natorch.cpp:1873-1880` — INFO + `return true`
- dynamic SNAT で上限到達: `natorch.cpp:1886-1892` — `setTimeoutNotifier->send("AGEOUT-SINGLE-NAT")` + `return true`
- `isNatEnabled() == false`: `natorch.cpp:1910-1915` — WARN + `return true`（キャッシュに保持）

### SAI 失敗 → 無限 retry パターン

`addHwDnatEntry()` (`natorch.cpp:774-786`) / `addHwSnatEntry()` (`natorch.cpp:1307-1319`):
- `sai_nat_api->create_nat_entry()` が `SAI_STATUS_SUCCESS` 以外
- `handleSaiCreateStatus(SAI_API_NAT, status)` → `parseHandleSaiStatusFailure()` → `return false`
- `doNatTableTask()` で `it++` (保留) → 次 tick で再試行 (`natorch.cpp:2661-2663`)

---

## STATE_DB / エラー通知

NAT パスには STATE_DB へのステータス書き込みなし。`ERROR_TABLE` への書き込みもなし。
失敗は `SWSS_LOG_ERROR` / `SWSS_LOG_WARN` (syslog) のみ。
