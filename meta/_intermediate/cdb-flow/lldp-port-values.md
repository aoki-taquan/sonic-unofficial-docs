# LLDP_PORT 値依存挙動分析

## enum フィールド

### enabled (boolean)
- `true` (デフォルト): LLDP フレームの送受信を有効化
- `false`: LLDP 送受信停止 → DEVICE_NEIGHBOR 自動学習なし → minigraph との乖離リスク

### mode (enum RECEIVE / TRANSMIT)
- `RECEIVE`: RX のみ（送信しない。自ノードが対向スイッチのトポロジーに映らない）
- `TRANSMIT`: TX のみ（受信しない。対向情報を学習しない）
- 未設定: lldpd デフォルト（双方向）
- 不正値: lldpcli がエラー。CONFIG_DB には書けるが lldpd に反映されない

## 結論
enum 有り: mode (RECEIVE / TRANSMIT)。enabled は boolean。
mode 未指定が双方向の正しい表現（BOTH 等の値は存在しない）。
