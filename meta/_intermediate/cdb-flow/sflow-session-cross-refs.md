# sflow-session — Phase C 暗黙参照（テーブル間依存）調査証跡

調査日: 2026-05-17  
調査対象: `sonic-swss/cfgmgr/sflowmgr.cpp`, `cfgmgr/sflowmgrd.cpp`, `orchagent/sfloworch.cpp`

## 調査結果

### 1. PORT テーブル（必須参照）

`sflowmgrd.cpp:31` および `sflowmgr.cpp:80-165`:  
sflowmgrd は起動時に `CFG_PORT_TABLE_NAME` を `TableConnector` に登録し、`sflowUpdatePortInfo()` でポート SET/DEL イベントを処理して `m_sflowPortConfMap` を初期化する。per-port `SFLOW_SESSION|<port>` の SET イベントは `m_sflowPortConfMap` にキーが存在する場合のみ処理される（`sflowmgr.cpp:522-528`）。ポートが未登録だと `it++; continue` で永続スキップ。

### 2. STATE_PORT テーブル (STATE_DB) （推奨参照）

`sflowmgrd.cpp:32` および `sflowmgr.cpp:167-218`:  
sflowmgrd は `STATE_PORT_TABLE_NAME` (STATE_DB) の `speed` フィールド変化を購読。`sample_rate` 未指定ポートに対して `oper_speed` 確定時に `APP_SFLOW_SESSION_TABLE` を自動更新する (`sflowProcessOperSpeed()`)。SFLOW_SESSION テーブル自体にこのテーブルへの直接参照はないが、`sample_rate` の自動導出でデータを読む。

### 3. SFLOW テーブル（実効化の前提依存）

`sflowmgr.cpp:456-471` (CFG_SFLOW_TABLE_NAME SET ハンドラ):  
`m_gEnable = false`（グローバル sFlow 無効）の場合、per-port SESSION SET を受けても `APP_SFLOW_SESSION_TABLE` に書かれない (`sflowmgr.cpp:531-534`)。また `sflowHandleService(enable)` により `service hsflowd restart/stop` が呼ばれる。SFLOW テーブルへの明示的 YANG 参照はないが、実効化の必須前提。

### 4. SFLOW_SESSION|all（グローバルデフォルト — 暗黙継承）

`sflowmgr.cpp:374-382`:  
per-port SESSION に `sample_direction` が未指定の場合、`m_intfAllDir`（SFLOW_SESSION|all の方向）をフォールバックとして採用。`m_gDirection` は SFLOW テーブルのグローバル方向。`SFLOW_SESSION|all` の admin_state が `m_intfAllConf` に格納され、per-port 有効化判定 (`isPortEnabled`) で参照される。

### 5. APP_SFLOW_TABLE（SflowOrch 段の前提依存）

`sfloworch.cpp:365-368` および `sfloworch.cpp:388-392`:  
SflowOrch は `APP_SFLOW_TABLE_NAME` の SET を受けて `m_sflowStatus = true` にする (`sflowStatusSet()`)。`m_sflowStatus = false` の間は `APP_SFLOW_SESSION_TABLE` の全 SET を `return` でスキップ。SFLOW_SESSION の APP_DB 反映が SflowOrch に届いても、APP_SFLOW_TABLE が先行していないと無効化される。

### 6. gPortsOrch（SflowOrch 段の必須依存）

`sfloworch.cpp:370-373`:  
`gPortsOrch->allPortsReady()` が false の間は SESSION テーブル処理全体をスキップ。PortsOrch が全ポート初期化を完了するまで SflowOrch の SESSION 処理は開始されない。

## 参照表（まとめ）

| 参照先 | 参照種別 | 条件 | コード箇所 |
|--------|---------|------|-----------|
| `PORT\|<port>` | 必須参照（m_sflowPortConfMap 登録） | per-port SESSION 処理の前提 | `sflowmgr.cpp:522-528` |
| `STATE_DB PORT\|<port>` (speed) | 自動導出参照 | `sample_rate` 未指定時の oper_speed 参照 | `sflowmgr.cpp:385-401` |
| `SFLOW\|global` | 実効化前提（m_gEnable） | グローバル admin_state=up が APP_DB 書込みの必須前提 | `sflowmgr.cpp:531-534` |
| `SFLOW_SESSION\|all` | 暗黙継承（方向・admin デフォルト） | per-port direction/admin 未指定時 | `sflowmgr.cpp:374-382` |
| `APP_SFLOW_TABLE` | SflowOrch 段の前提依存 | m_sflowStatus=false の間 SESSION をスキップ | `sfloworch.cpp:388-392` |
| `gPortsOrch` | PortsOrch 初期化完了待ち | allPortsReady()=false の間 SESSION 処理なし | `sfloworch.cpp:370-373` |
