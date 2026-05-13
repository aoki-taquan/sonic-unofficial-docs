# 値依存挙動分析: MGMT_INTERFACE

## Phase 1: YANG フィールド全列挙

- `name` (leafref → MGMT_PORT.name, key)
- `ip_prefix` (sonic-ip-prefix, key): IPv4/IPv6 プレフィクス
- `gwaddr` (ip-address): デフォルト GW
- `forced_mgmt_routes` (leaf-list): 強制ルート一覧

## Phase 2: per-value explicit grep

- `sonic-mgmt_interface.yang`: must — `ip_prefix` と `gwaddr` は同じ IP family であること
- `interfaces.j2`: `forced_mgmt_routes` を mgmt VRF または default VRF に追加
- `config/main.py`: `reset_mgmt_interface_if_usb_not_running()` — USB NW 未稼働時にエントリ削除

## Phase 3: 専用ファイル確認

- `sonic-host-services/scripts/hostcfgd`: MGMT_INTERFACE 変更 → `/etc/network/interfaces` 再生成
- `mgmt_vrf_enabled` フラグで forced_mgmt_routes の投入先 VRF が分岐

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `gwaddr` | 有効 IP (同 family) | mgmt VRF または default VRF にデフォルト GW 設定 |
| `gwaddr` | 異なる IP family | YANG must 制約違反 → バリデーション拒否 |
| `gwaddr` | 未設定 | GW なし。mgmt VRF 内に default route なくリモート接続不能の恐れ |
| `forced_mgmt_routes` | prefix/address 列挙 | mgmtVrfEnabled=true → mgmt VRF ルートテーブルへ追加。false → default VRF |
| `forced_mgmt_routes` | 未設定 | 強制ルートなし。通常のルーティングに従う |

enum なし。
