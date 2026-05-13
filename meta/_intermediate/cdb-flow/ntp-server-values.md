# 値依存挙動分析: NTP_SERVER

## Phase 1: YANG フィールド全列挙

- `server_address` (inet:host, key)
- `association_type` (enum): `server`/`pool`, default `server`
- `iburst` (on-off): default `on`
- `key` (leafref NTP_KEY.id)
- `resolve_as` (inet:host)
- `admin_state` (admin_mode): default `enabled`
- `trusted` (yes-no): default `no`
- `version` (uint8): range 3..4, default 4

## Phase 2: per-value explicit grep

- `sonic-ntp.yang`: max-elements 10 — サーバ上限
- `sonic-ntp.yang`: `version range "3..4"` / `error-message "Failed NTP version"`
- `hostcfgd`: `ntp_srv_key_update()` — server/key 変更で `systemctl restart chrony`

## Phase 3: 専用ファイル確認

- `sonic-host-services/scripts/hostcfgd`: NTP_SERVER 変更 → chrony.conf 再生成 + chrony restart
- chrony.conf の `pool` / `server` ディレクティブで `iburst` / `key` / `prefer` オプションを展開

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `association_type` | `server` (default) | chrony.conf に `server <addr>` として追記 |
| `association_type` | `pool` | chrony.conf に `pool <addr>` として追記。DNS ラウンドロビンで複数 IP を使用 |
| `iburst` | `on` (default) | 起動直後に iburst パケットを送信して高速同期 |
| `iburst` | `off` | 通常ポーリング間隔で同期開始 |
| `admin_state` | `enabled` (default) | サーバを chrony.conf に含める |
| `admin_state` | `disabled` | サーバを chrony.conf から除外 (テンプレートが skip) |
| `trusted` | `no` (default) | chrony で通常の優先度。`prefer` オプションなし |
| `trusted` | `yes` | chrony の `prefer` オプション相当。当該サーバを優先同期先に |
| `version` | `4` (default) | NTPv4 を使用 |
| `version` | `3` | NTPv3 を使用。古い NTP サーバとの互換向け |
| `key` | NTP_KEY.id 参照 | chrony.conf に `key <id>` オプションを付与。NTP.authentication=enabled と組み合わせて認証 |
| エントリ数 | 11件目以上 | YANG max-elements=10 でバリデーション拒否 |

enum: `association_type`=server/pool、`iburst`=on/off、`admin_state`=enabled/disabled、`trusted`=yes/no。
