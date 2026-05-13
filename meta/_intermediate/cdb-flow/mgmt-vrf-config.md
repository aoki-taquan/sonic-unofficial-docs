# CONFIG_DB 例外条件分析: MGMT_VRF_CONFIG

## Consumer

- `vrfmgr` (`sonic-swss/cfgmgr/vrfmgr.cpp`): `MGMT_VRF_CONFIG` を購読し、管理 VRF (table ID 6000) のカーネル VRF netdev を作成・削除。

## 例外条件

### 1. mgmtVrfEnabled=false または in_band_mgmt_enabled=false → DEL 扱い
- ソース: `vrfmgr.cpp` L257 — SET コマンドでも `mgmtVrfEnabled` が false または `in_band_mgmt_enabled` が false の場合、op を DEL_COMMAND に上書きして削除処理を実行。

### 2. 既に同 VRF が存在する状態で SET → スキップ
- ソース: `vrfmgr.cpp` L263-265 — `m_vrfTableMap` に "mgmt" が既に存在する場合、エントリを消費してスキップ (重複 SET 無効化)。

### 3. 存在しない VRF に DEL → スキップ
- ソース: `vrfmgr.cpp` L263-265 — `m_vrfTableMap` に "mgmt" が存在しない場合の DEL もスキップ。

### 4. VRF netdev 作成失敗 → SWSS_LOG_ERROR
- ソース: `vrfmgr.cpp` L287 — `setLink()` 失敗時に `"Failed to create vrf netdev %s"` をログ。処理は継続されるが netdev が未作成の状態になる。

### 5. VRF VNI マップ設定失敗 → SWSS_LOG_ERROR + エントリ消費して break
- ソース: `vrfmgr.cpp` L295-303 — `doVrfVxlanTableCreateTask()` が false を返した場合、エラーログして `m_toSync` からエントリを消費し次のエントリへ。

### 6. mgmtVrfEnabled のデフォルト値
- ソース: `sonic-mgmt_vrf.yang` — `default false`。エントリが存在しない場合は管理 VRF 無効として扱われる。
- NTP VRF 設定で `vrf = "mgmt"` を指定する場合、`mgmtVrfEnabled = true` が必要 (NTP YANG must 制約)。
