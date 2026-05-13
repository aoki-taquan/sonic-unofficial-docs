# INTERFACE 値依存挙動分析

## enum フィールド

### mpls (intfmgr.cpp L174-178)
- `enable`: Linux MPLS ルーティングを有効化（ip link set mpls on）
- `disable`（または空): MPLS 無効化
- その他: SWSS_LOG_ERROR("MPLS state is invalid") → 設定適用されない

### ipv6_use_link_local_only (intfmgr.cpp L817, L915-920)
- `enable`: IPv6 link-local only モードを有効化。m_ipv6LinkLocalModeList に追加
- `disable`: link-local only モード解除。グローバルアドレス割り当て可能に戻る
- 未設定: デフォルト disable

### admin_status (intfmgr.cpp L867)
- `up`: インタフェース UP
- `down`: インタフェース DOWN
- その他: SWSS_LOG_WARN → `up` にデフォルト

### loopback_action (intfsorch.cpp L1150-1151)
- `drop`: SAI_PACKET_ACTION_DROP（ingress → 同 IF 宛パケットを破棄）
- `forward`: SAI_PACKET_ACTION_FORWARD（通常転送）
- 未設定: SAI デフォルト動作（プラットフォーム依存）

### scope (intfmgr.cpp L1134)
- `global`: グローバルスコープ（intfmgrd が APP_DB に "scope=global" を書く）
- `local`: ローカルスコープ

### family
- `IPv4` / `IPv6`: ip-prefix の形式と must で整合性チェック

## 結論
enum 有り: mpls (enable/disable)、admin_status (up/down)、loopback_action (drop/forward)、
ipv6_use_link_local_only (enable/disable)、scope (global/local)、family (IPv4/IPv6)。
