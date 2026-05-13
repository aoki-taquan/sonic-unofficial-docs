# SFLOW 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-swss/cfgmgr/sflowmgr.cpp`
- `sonic-swss/orchagent/sfloworch.cpp`

## 抽出した例外条件

1. **PORT_TABLE consumer 未初期化**: sflowmgr 起動時に `PORT_TABLE` の consumer が見つからない場合 `SWSS_LOG_ERROR("Consumer object for PORT_TABLE not found")` を出す。per-port サンプリングレートの解決ができなくなる。
   - 証拠: sflowmgr.cpp l.34

2. **hsflowd サービス制御失敗**: `service hsflowd restart/stop` が返り値 0 以外の場合 `SWSS_LOG_ERROR("Command '%s' failed with rc %d")` を出す。サービス制御失敗時は CONFIG_DB の状態と実際のサービス状態がずれる。
   - 証拠: sflowmgr.cpp l.70

3. **ポート名が port configuration map に未登録**: per-port のサンプリングレート算出時に PORT_TABLE に存在しないポートを指定すると `SWSS_LOG_ERROR("%s not found in port configuration map")` を出し `ERROR_SPEED` を返す。
   - 証拠: sflowmgr.cpp l.391

4. **SAI sample packet session 作成失敗**: `sai_samplepacket_api->create_samplepacket()` が失敗した場合 `SWSS_LOG_ERROR("Failed to create sample packet session with rate %d")` → sFlow セッションが有効化されない。
   - 証拠: sfloworch.cpp l.33

5. **既存セッションのクリーンアップ失敗**: レート変更時に古い session の destroy に失敗した場合 `SWSS_LOG_ERROR("Failed to destroy sample packet session")` → 複数レートのセッションが ASIC に残留する可能性がある。
   - 証拠: sfloworch.cpp l.52 / l.99

6. **per-port セッション設定失敗**: `sai_samplepacket_api->set_port_attribute()` が失敗した場合 `SWSS_LOG_ERROR("Failed to set session ... on port ...")` → そのポートのみ sFlow が有効にならない。
   - 証拠: sfloworch.cpp l.126 / l.143

7. **グローバル無効 + ローカル有効の組み合わせ**: `isPortEnabled()` は `m_gEnable && (m_intfAllConf || (local_admin && status))` で判定するため、グローバル sflow が無効なら per-port 設定に関わらず全ポートで sFlow は停止する。
