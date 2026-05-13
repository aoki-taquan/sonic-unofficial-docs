# LLDP 値依存挙動分析

## enum フィールド

### mode (enum RECEIVE / TRANSMIT) - sonic-lldp.yang L34-35
- `RECEIVE`: RX のみ。送信しないため自ノードが対向スイッチのトポロジーに映らない
- `TRANSMIT`: TX のみ。受信しないため対向情報を学習しない
- 未設定: lldpd デフォルト（双方向 tx_and_rx）
- 不正値: lldpcli がエラー → lldpd に反映されない

### enabled (boolean)
- `true` (デフォルト): LLDP 有効
- `false`: LLDP 無効

## 数値フィールド

### hello_time (uint8 5..254)
- 5〜254 秒: hold time = hello_time × multiplier
- 0 または負: lldpd がデフォルト 30 秒で動作。YANG バリデーション有効時は reject

### multiplier (uint8 1..10)
- 1〜10: ネイバー保持時間 = hello_time × multiplier

## boolean フィールド

### supp_mgmt_address_tlv
- `false` (デフォルト): Management Address TLV 送信
- `true`: Management Address TLV 送信抑制

### supp_system_capabilities_tlv
- `false` (デフォルト): System Capabilities TLV 送信
- `true`: System Capabilities TLV 送信抑制

## 結論
enum 有り: mode (RECEIVE / TRANSMIT)。boolean: enabled, supp_*_tlv。数値: hello_time, multiplier。
