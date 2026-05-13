# MACSEC_PROFILE 値依存挙動分析

## enum フィールド

### policy (macsecmgr.cpp L51-65)
- `integrity_only`: 認証のみ（暗号化なし）。MKA SAは設立するが実データは平文
- `security` (デフォルト): 認証 + 暗号化
- その他: throw std::invalid_argument → SWSS_LOG_WARN → task_invalid_entry（破棄）

### cipher_suite (macsecmgr.cpp L69-91)
- `GCM-AES-128` (デフォルト): 128-bit AES。CAK 長 = 66 hex 文字
- `GCM-AES-256`: 256-bit AES。CAK 長 = 130 hex 文字
- `GCM-AES-XPN-128`: Extended Packet Numbering 128-bit。CAK 長 = 66 hex 文字
- `GCM-AES-XPN-256`: Extended Packet Numbering 256-bit。CAK 長 = 130 hex 文字
- その他: throw std::invalid_argument → task_invalid_entry

### primary_cak / fallback_cak の長さ検証 (macsecmgr.cpp L121-131)
- 128/XPN-128 cipher: 66 hex 文字（33 バイト = 16B CAK + 1B KCK 風）
- 256/XPN-256 cipher: 130 hex 文字（65 バイト）
- 長さ不一致: throw std::invalid_argument → task_invalid_entry

## boolean フィールド

### send_sci (macsecmgr.cpp L373-375)
- `true` (デフォルト): 送信フレームに SCI (Secure Channel Identifier) を含める
- `false`: SCI を含めない（相互接続に影響する場合あり）

### enable_replay_protect (macsecmgr.cpp L365-367)
- `false` (デフォルト): リプレイ保護なし
- `true`: replay_window の値を wpa_supplicant に渡す（macsec_replay_protect=1, macsec_replay_window=N）

## 数値フィールド

### rekey_period (macsecmgr.cpp L377-379, L788-795)
- `0` (デフォルト): 能動的 SAK 再生成なし
- 正値: 指定秒数ごとに SAK を再生成（mka_rekey_period として wpa_supplicant に設定）

### priority (uint8)
- `255` (デフォルト): MKA アクター優先度最低（key server になりにくい）
- 小さい値（例: 0）: key server になりやすい

## 結論
enum 有り: policy (integrity_only/security)、cipher_suite (4 値)。
CAK 長は cipher_suite に依存する重要な制約。rekey_period=0 と正値で挙動が分岐。
