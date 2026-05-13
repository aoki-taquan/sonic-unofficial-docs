# LOOPBACK_INTERFACE 値依存挙動分析

## enum フィールド

### admin_status
- `up` (デフォルト): Linux dummy デバイスを UP 状態にする
- `down`: Linux dummy デバイスを DOWN 状態にする
- 設定失敗時: SWSS_LOG_WARN → warn のみで継続

### scope
- `global`: グローバルスコープアドレス
- `local`: ローカルスコープアドレス

### family
- `IPv4`: IPv4 アドレス
- `IPv6`: IPv6 アドレス。ip-prefix の `:` と整合する `must` でチェック

### vrf_name
- 設定: 指定 VRF にバインド
- 未設定: デフォルト VRF に属する

## 数値フィールド

### nat_zone (uint8 0..3)
- 0 (デフォルト): NAT zone 0
- 1〜3: NAT zone 設定。natmgrd が参照

## 結論
enum 有り: admin_status (up/down)、scope (global/local)、family (IPv4/IPv6)。
特殊値: L3 enable 行なしで IP 行のみ投入は失敗（MTU=65536 で dummy デバイス作成が前提）。
