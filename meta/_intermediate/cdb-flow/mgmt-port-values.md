# 値依存挙動分析: MGMT_PORT

## Phase 1: YANG フィールド全列挙

- `name` (string, key): pattern `eth([1-3][0-9]{3}|[1-9][0-9]{2}|[1-9][0-9]|[0-9])`
- `speed` (uint16): range "10|100|1000" [Mbps]
- `autoneg` (string): pattern "on|off"
- `alias` (string): 別名
- `description` (string): 説明
- `mtu` (uint16): range 1500..9216, default 1500
- `admin_status` (admin_status): default `up`

## Phase 2: per-value explicit grep

- `sonic-mgmt_port.yang`: `default 1500` (mtu), `default up` (admin_status)
- `hostcfgd`: MTU/speed/admin_status を `/etc/network/interfaces` 経由で `ifconfig`/`ethtool` に適用

## Phase 3: 専用ファイル確認

- `sonic-host-services/scripts/hostcfgd`: MGMT_PORT 変更 → Linux netdev 設定更新
- `interfaces.j2`: speed/autoneg → ethtool コマンド生成

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `admin_status` | `up` (default) | eth0 を管理状態 UP に設定 |
| `admin_status` | `down` | eth0 を管理状態 DOWN に設定。OOB 管理が切断される |
| `speed` | `10`/`100`/`1000` | ethtool で該当速度を強制設定 |
| `speed` | 未設定 | ethtool 速度設定なし (autoneg 任せ) |
| `autoneg` | `on` | ethtool でオートネゴ有効化 |
| `autoneg` | `off` | ethtool でオートネゴ無効化。speed 指定必須 |
| `mtu` | 1500 (default) | eth0 MTU を 1500 に設定 |
| `mtu` | 1501..9216 | eth0 MTU を指定値に設定 (Jumbo frame) |

enum: `admin_status` = `up`/`down`。
