# TAM テーブル — Phase H プラットフォーム差 調査証跡

調査日: 2026-05-19

## 調査対象ソース

- `sonic-net/sonic-swss/orchagent/portsorch.cpp`（`isPathTracingSupported`, `checkPathTracingCapability`）
- `sonic-net/sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp`（`isSupportedHFTel`）
- `sonic-net/sonic-swss/orchagent/switchorch.h`（`SWITCH_CAPABILITY_TABLE_PATH_TRACING_CAPABLE`）
- `sonic-net/sonic-swss-common/common/schema.h`（`STATE_SWITCH_CAPABILITY_TABLE_NAME`）

## 結論サマリ

TAM 4 テーブル（`TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` / `TAM_INT_IFA_FLOW_TABLE`）の処理において、プラットフォーム固有のコード分岐（`getenv("platform")` や `ASIC_VENDOR` 環境変数による条件分岐）は **存在しない**。

ただし TAM に関わる 2 つの主要処理経路（Path Tracing TAM / High Frequency Telemetry TAM）は、ともに **SAI capability query** の結果によってランタイムで有効/無効が決まるため、プラットフォーム（ベンダー SAI 実装）によって動作差が生じる。

## 1. Path Tracing TAM（portsorch.cpp）

`isPathTracingSupported()`（portsorch.cpp:576-631）は以下の 4 条件をすべて SAI capability query で確認する:

1. `SAI_SWITCH_ATTR_SUPPORTED_OBJECT_TYPE_LIST` に `SAI_OBJECT_TYPE_TAM` が含まれる
2. `SAI_OBJECT_TYPE_PORT` が `SAI_PORT_ATTR_PATH_TRACING_INTF` をサポートする
3. `SAI_OBJECT_TYPE_PORT` が `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` をサポートする
4. `SAI_OBJECT_TYPE_PORT` が `SAI_PORT_ATTR_TAM_OBJECT` をサポートする

上記 capability query は `getenv("platform")` による vendor 識別を行わない。判定結果は `STATE_SWITCH_CAPABILITY_TABLE_NAME = "SWITCH_CAPABILITY"` テーブルの `PATH_TRACING_CAPABLE` フィールドに `"true"` / `"false"` で書き込まれる（portsorch.cpp:641, 648）。

- **SAI がこれらの capability を返さないプラットフォーム**（多くのソフトウェアスイッチ、仮想スイッチ等）では Path Tracing TAM 機能全体が無効化される
- **SAI がサポートを報告するプラットフォーム**（一部ハードウェア ASIC）では `createPtTam()` を通じて SAI TAM オブジェクトが作成される

## 2. High Frequency Telemetry TAM（hftelorch.cpp）

`isSupportedHFTel()`（hftelorch.cpp:168-260）は以下の SAI capability query を実施する:

- `sai_query_stats_st_capability`（`SAI_OBJECT_TYPE_PORT`）: `SUCCESS` または `BUFFER_OVERFLOW` 以外なら HFTel 無効
- `SAI_OBJECT_TYPE_TAM_COLLECTOR` の各属性（`SRC_IP`, `DST_IP`, `TRANSPORT`, `LOCALHOST`, `HOSTIF_TRAP`, `DSCP_VALUE`）の create 能力
- `SAI_SWITCH_ATTR_TAM_TEL_TYPE_CONFIG_CHANGE_NOTIFY` および `SAI_SWITCH_ATTR_TAM_OBJECT_ID` の set 能力
- `SAI_TAM_TRANSPORT_TYPE_NONE` および `SAI_TAM_BIND_POINT_TYPE_SWITCH` の enum 値サポート

いずれかが未サポートの場合は `NOTICE "HFTel disabled"` ログを出して HFTel 機能を完全に無効化する。

## 3. CONFIG_DB TAM 4 テーブルとプラットフォームの無関係性

コミュニティ版 orchagent は `TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` / `TAM_INT_IFA_FLOW_TABLE` を CONFIG_DB から購読しない。これらテーブルは GNMI/REST 経由の CVL バリデーションにのみ使用される。CVL はプラットフォーム非依存の YANG スキーマ処理を行う。

## 証拠リンク

- `portsorch.cpp:576`: `isPathTracingSupported()` 開始
- `portsorch.cpp:634`: `checkPathTracingCapability()` — STATE_DB 書込
- `portsorch.cpp:641,648`: `PATH_TRACING_CAPABLE` への `"true"` / `"false"` 書込
- `hftelorch.cpp:168`: `isSupportedHFTel()` 開始
- `hftelorch.cpp:175-180`: `sai_query_stats_st_capability` チェック
- `switchorch.h:21`: `SWITCH_CAPABILITY_TABLE_PATH_TRACING_CAPABLE = "PATH_TRACING_CAPABLE"` 定義
- `schema.h:417`: `STATE_SWITCH_CAPABILITY_TABLE_NAME = "SWITCH_CAPABILITY"` 定義
