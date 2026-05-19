# ERROR_DB プラットフォーム差調査メモ

調査日: 2026-05-19
対象テーブル: ERROR_DB `ERROR_ROUTE_TABLE` / `ERROR_NEIGH_TABLE`

## 調査対象ファイル

- `SONiC/doc/error-handling/error_handling_design_spec.md` (HLD Rev 0.1, 2019-05-06)
- `sonic-swss-common/common/status_code_util.h` (SWSS_RC enum 定義、実装済み)
- `SONiC/doc/bgp_error_handling/BGP_Route_Error_Handling_Arlo.md` (BGP ユースケース HLD)

---

## 調査結果: プラットフォーム差の有無

### 結論

**ERROR_DB フレームワーク自体にプラットフォーム依存は存在しない。**

HLD Section 3.1–3.4 にはプラットフォーム固有の分岐・条件分け・定数が一切記載されていない。
`sonic-swss-common/common/status_code_util.h` の `StatusCode` enum および `statusCodeMapping` はプラットフォームに依存しない静的マッピングである。

---

## プラットフォーム依存が存在するか否かの検証

### 1. status_code_util.h — プラットフォーム非依存

`statusCodeMapping` はコンパイル時静的な `std::map<StatusCode, std::string>` であり、
プリプロセッサ条件（`#ifdef PLATFORM_BRCM` 等）は一切使用していない。

```cpp
// sonic-swss-common/common/status_code_util.h
static const std::map<StatusCode, std::string> statusCodeMapping = {
    {StatusCode::SWSS_RC_SUCCESS, "SWSS_RC_SUCCESS"},
    {StatusCode::SWSS_RC_FULL, "SWSS_RC_FULL"},
    // ... 15 コード、すべてプラットフォーム非依存
};
```

### 2. SAI → SWSS_RC 変換テーブル — HLD 設計上は固定マッピング

HLD Section 3.2 に SAI ステータス → SWSS_RC のマッピング表が定義されている。
プラットフォーム名による分岐は記載されていない。

| SWSS_RC コード | SAI ステータス | プラットフォーム制限 |
|--------------|---------------|------------------|
| SWSS_RC_SUCCESS | SAI_STATUS_SUCCESS | なし |
| SWSS_RC_FULL | SAI_STATUS_TABLE_FULL | なし |
| SWSS_RC_NO_MEMORY | SAI_STATUS_NO_MEMORY | なし |
| SWSS_RC_UNAVAIL | SAI_STATUS_NOT_SUPPORTED | なし |
| （他 11 コード） | — | なし |

### 3. SAI 実装の差異がある場合の挙動

プラットフォーム固有 SAI が `SAI_STATUS_TABLE_FULL` 以外の実装依存エラーコードを返す場合でも、
OrchAgent が `SWSS_RC_*` に変換する際に `SWSS_RC_UNKNOWN` にマップされる（`strToStatusCode()` フォールバック）。

つまり「プラットフォームが返す SAI エラーコードの種類の差」は ERROR_DB の `rc` フィールドに
`SWSS_RC_UNKNOWN` として抽象化される。プラットフォーム固有の値は ERROR_DB には書かれない。

### 4. `bgp_error_handling` 有効化条件 — プラットフォーム非依存

`BGP_GLOBALS|default` の `bgp_error_handling` フィールドは CONFIG_DB のグローバル設定であり、
プラットフォームに依存しない（BGP HLD Section 3.7.1）。

### 5. `database_config.json` の ERROR_DB エントリ — 未登録、プラットフォーム差なし

現行の `database_config.json` に ERROR_DB は未登録（実装未マージのため）。
実装時に追加される DB ID はプラットフォーム固有ではなく、全環境共通 ID が割り当てられる設計。

---

## 間接的プラットフォーム影響：SAI エラー発生頻度

プラットフォームによって特定の SAI エラーの**発生しやすさ**は異なる。

| SAI エラー | 発生しやすい条件 | ERROR_DB に現れる SWSS_RC |
|----------|--------------|------------------------|
| `SAI_STATUS_TABLE_FULL` | テーブルサイズが小さい ASIC（一部 OF-DPA / barefoot など） | `SWSS_RC_FULL` |
| `SAI_STATUS_NO_MEMORY` | メモリ制限の厳しいプラットフォーム | `SWSS_RC_NO_MEMORY` |
| `SAI_STATUS_NOT_SUPPORTED` | 機能非対応 ASIC（例：L3V4V6 ACL 非対応） | `SWSS_RC_UNAVAIL` |
| 実装依存エラーコード | ベンダー固有 SAI 拡張エラー | `SWSS_RC_UNKNOWN`（フォールバック） |

この差は「ERROR_DB 自体の動作差」ではなく「エラーがいつ発生するか」の差であり、
フレームワーク仕様としてのプラットフォーム差ではない。

---

## 要約

| 観点 | プラットフォーム差 | 根拠 |
|------|-----------------|------|
| SWSS_RC_* enum 定義 | **なし** | `status_code_util.h` — 静的マッピング |
| SAI → SWSS_RC 変換 | **なし** | HLD Section 3.2 — 固定マッピング表、分岐なし |
| ERROR_DB スキーマ（フィールド名・型） | **なし** | HLD Section 3.4.3 — 全 ASIC 共通 |
| pub/sub 通知方式 | **なし** | Redis PUBLISH/SUBSCRIBE — 実装非依存 |
| SAI エラー発生頻度 | **間接的にあり** | ASIC テーブルサイズ・機能対応状況に依存 |
| `bgp_error_handling` 有効化条件 | **なし** | CONFIG_DB グローバル設定 |

---

## 証拠リンク

- `SONiC/doc/error-handling/error_handling_design_spec.md` Section 3.2 — SAI → SWSS_RC マッピング表（プラットフォーム分岐なし）
- `sonic-swss-common/common/status_code_util.h` — `StatusCode` enum・`statusCodeMapping`・`strToStatusCode()` フォールバック
- `SONiC/doc/bgp_error_handling/BGP_Route_Error_Handling_Arlo.md` Section 3.7.1 — `bgp_error_handling` はプラットフォーム非依存の CONFIG_DB 設定
