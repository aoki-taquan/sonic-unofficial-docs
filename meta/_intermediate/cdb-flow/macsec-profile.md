# CONFIG_DB 例外条件分析: MACSEC_PROFILE

## Consumer

- `macsecmgr` (`sonic-swss/cfgmgr/macsecmgr.cpp`): `MACSEC_PROFILE` テーブルを subscribe し、`wpa_supplicant` を起動して MKA セッションを確立する。

## 例外条件

### 1. policy 不正値 → std::invalid_argument + WARN + task_invalid_entry
- ソース: `macsecmgr.cpp` L65, L428-447
- `policy` フィールドが `integrity_only` / `security` 以外の値を受けると `throw std::invalid_argument("Invalid policy : " + policy_str)` → `catch(const std::invalid_argument & e)` で `SWSS_LOG_WARN` → `return task_invalid_entry`（Consumer キューには戻らず破棄）。

### 2. cipher_suite 不正値 → invalid_argument + WARN + task_invalid_entry
- ソース: `macsecmgr.cpp` L91, L125, L131
- `cipher_suite` が `GCM-AES-128` / `GCM-AES-256` / `GCM-AES-XPN-128` / `GCM-AES-XPN-256` 以外、または CAK 文字列長が不正（16B / 32B 以外）の場合 `throw std::invalid_argument("Invalid length for cipher_string : " + cipher_str)` → task_invalid_entry。

### 3. primary_cak のみで fallback_ckn なし → warn + skip
- ソース: `macsecmgr.cpp` L361
- `fallback_cak` が存在するが `fallback_ckn` が未設定の場合 `GetValue(ta, fallback_ckn)` が false → フォールバックキーの設定がスキップされる。MKA フォールバック機能が動作しない。

### 4. wpa_supplicant 起動失敗 → WARN（MACsec 有効化失敗）
- ソース: `macsecmgr.cpp` L546-554
- `wpa_supplicant` の起動コマンドが失敗した場合 `SWSS_LOG_WARN("Cannot start the wpa_supplicant of the port '%s' : %s", ...)` → MACsec は有効化されずポートは非暗号化のまま。

### 5. フィールド値変換失敗 → エラーログ
- ソース: `macsecmgr.cpp` L170
- `GetValue()` で期待型に変換できない値（例: priority に非整数）が来ると `SWSS_LOG_ERROR("Cannot convert value(%s) in field(%s)", ...)` → そのフィールドはデフォルト値または前回値が使われる。

### 6. MACsec 有効化失敗 → WARN（ポート処理継続）
- ソース: `macsecmgr.cpp` L838
- `wpa_supplicant` 接続失敗等で MACsec 有効化が例外を投げた場合 `SWSS_LOG_WARN("Enable MACsec fail : %s", e.what())` → ポートは引き続き動作するが暗号化されない。

### 7. MACsec 無効化失敗 → WARN
- ソース: `macsecmgr.cpp` L918
- 無効化処理が失敗した場合 `SWSS_LOG_WARN("Disable MACsec fail : %s", error_message.c_str())` → wpa_supplicant プロセスが残留する可能性がある。
