# 値依存挙動分析: NTP (global)

## Phase 1: YANG フィールド全列挙

- `src_intf` (leaf-list union): PORT.name / PORTCHANNEL.name / LOOPBACK_INTERFACE.name / MGMT_PORT.name / "eth0"
- `vrf` (string): pattern `mgmt|default`
- `authentication` (admin_mode): default `disabled`
- `dhcp` (admin_mode): default `enabled`
- `server_role` (admin_mode): default `enabled`
- `admin_state` (admin_mode): default `enabled`

## Phase 2: per-value explicit grep

- `hostcfgd`: `ntp_global_update()` — 変更があれば `systemctl restart chrony` 実行
- `hostcfgd`: `old_vrf` vs `new_vrf` 比較 → chrony restart
- `hostcfgd`: `old_dhcp` vs `new_dhcp` 比較 → chrony restart
- `sonic-ntp.yang`: `vrf=mgmt` must → `mgmtVrfEnabled='true'` が必要

## Phase 3: 専用ファイル確認

- `sonic-host-services/scripts/hostcfgd`: 全グローバル変更 → `systemctl restart chrony`
- chrony の ExecStartPre が CONFIG_DB の NTP/NTP_SERVER/NTP_KEY を読み込んで設定生成

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `vrf` | `default` | NTP パケットをデータプレーン default VRF 経由で送受信 |
| `vrf` | `mgmt` | NTP パケットを mgmt VRF (eth0) 経由で送受信。`mgmtVrfEnabled=true` が必要 |
| `vrf` | 未設定 | VRF 指定なし。OS デフォルトルーティングに従う |
| `authentication` | `disabled` (default) | NTP 認証なし。NTP_KEY テーブルが存在しても使用しない |
| `authentication` | `enabled` | NTP 認証を有効化。NTP_SERVER.key と NTP_KEY で鍵検証 |
| `dhcp` | `enabled` (default) | DHCP 配布の NTP サーバ情報を優先使用 |
| `dhcp` | `disabled` | DHCP NTP を無視。NTP_SERVER テーブルの設定のみ使用 |
| `server_role` | `enabled` (default) | 本機を NTP server として他ホストに応答 |
| `server_role` | `disabled` | NTP クライアント専用。問い合わせに応答しない |
| `admin_state` | `enabled` (default) | NTP 機能有効 |
| `admin_state` | `disabled` | NTP 機能無効化 |
| `src_intf` 変更 | 任意 IF | `chrony restart` トリガー + 新 src_intf の IP で NTP パケット送信 |

enum: `authentication`/`dhcp`/`server_role`/`admin_state` = enabled/disabled。全変更で `systemctl restart chrony` 実行。
