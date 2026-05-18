# NAT ゾーン (nat_zone フィールド) — 書込み順依存 (Phase B) 調査メモ

調査日: 2026-05-18
対象ソース:
- `sonic-swss/cfgmgr/natmgr.cpp` (HEAD) — doNatZoneIntfTask L7380-7640
- `sonic-swss/orchagent/intfsorch.cpp` (HEAD) — doTask L660-990

---

## 検出した順序依存

### 1. orchagent: allPortsReady() が true になるまで処理しない

- **場所**: `intfsorch.cpp:665-668`
- **内容**: `IntfsOrch::doTask()` の冒頭で `gPortsOrch->allPortsReady()` が false なら即 return。全ポートが初期化される前に `nat_zone` を設定しても、`orchagent` の SAI 書き込みは実行されない。ポート初期化完了後に `doTask()` が自動再実行される。

### 2. natmgrd: ポート state_ok が先行必須 (非 Loopback の zone エントリ)

- **場所**: `natmgr.cpp:7493-7499` (`isPortStateOk()`)
- **内容**: ゾーン単位エントリ (key サイズ 1) の SET 処理時、Loopback 以外のインタフェースは `isPortStateOk(port)` が false なら `it++; continue` でキューに残す。ポートが ready になると自動再試行される。

### 3. natmgrd: インタフェース state_ok が先行必須 (IP プレフィックス付きエントリ)

- **場所**: `natmgr.cpp:7595-7601` (`isIntfStateOk()`)
- **内容**: IP プレフィックス付きエントリ (key サイズ 2) の SET 処理時、`isIntfStateOk(key)` が false なら `it++; continue` で再試行待機。インタフェースが IP 有効化された後に自動再試行。

### 4. ゾーン変更時: 既存 Static / Dynamic NAT ルールが先に削除される (副作用)

- **場所**: `natmgr.cpp:7534-7566`
- **内容**: `nat_zone` 値が既存値と異なる場合、natmgr は先に `removeStaticNatIptables()` / `removeStaticNaptIptables()` / `removeDynamicNatRules()` を呼んでから新しいゾーン値で再構築する。この間 (数 ms〜数百 ms) は NAT ルールが一時消失する。

### 5. Loopback は iptables mangle ルールを設定しない (設計上の先行不要)

- **場所**: `natmgr.cpp:7526-7528` / `natmgr.cpp:7548-7550`
- **内容**: `strncmp(LOOPBACK_PREFIX)` が真の場合、`setMangleIptablesRules()` をスキップして SAI zone_id 設定のみ行う。Loopback の `nat_zone` は iptables mark に影響しないため、Loopback インタフェースの設定順序は non-Loopback とは独立。

### 6. IntfsOrch: SAI 書き込みは gIsNatSupported が前提

- **場所**: `intfsorch.cpp:977-985`
- **内容**: `gIsNatSupported == false` の場合、`setRouterIntfsNatZoneId()` を呼ばずに `SWSS_LOG_NOTICE` のみ出力。プラットフォームの NAT ハードウェアサポートが確認されるまで SAI への zone_id 設定は実行されない。起動時の SAI capability クエリ (`SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY`) の結果に依存。

---

## 順序依存サマリ

| # | 先行必須条件 | 処理系 | 方向 | 緩和策 |
|---|------------|--------|------|--------|
| 1 | `PortsOrch::allPortsReady()` が true | orchagent (IntfsOrch) | 強制先行 | 全ポート初期化完了まで SAI 書き込みを全スキップ、完了後自動再実行 |
| 2 | `isPortStateOk(port)` が true (非 Loopback zone エントリ) | natmgrd | 強制先行 | ポート ready 後に自動再試行 |
| 3 | `isIntfStateOk(key)` が true (IP プレフィックス付きエントリ) | natmgrd | 強制先行 | インタフェース IP 有効化後に自動再試行 |
| 4 | 既存 Static / Dynamic NAT ルール削除が先行 (ゾーン変更時) | natmgrd | 内部順序 (副作用) | ゾーン変更は一時的に NAT ルールを無効化してから再構築 |
| 5 | `gIsNatSupported == true` (SAI capability) | orchagent (IntfsOrch) | 強制先行 | false の場合は SAI 書き込みを silent skip |
