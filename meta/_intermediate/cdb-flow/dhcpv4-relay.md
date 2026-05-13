# DHCPV4_RELAY — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| sonic-utilities / config/vlan.py | VLAN 削除時の依存チェック | sonic-utilities/config/vlan.py:242-243 |
| sonic-utilities / config/main.py | VRF 削除時の依存チェック | sonic-utilities/config/main.py:1699-1706 |
| sonic-utilities / db_migrator.py | DHCP_RELAY → DHCPV4_RELAY スキーマ移行 | sonic-utilities/scripts/db_migrator.py:917-933 |
| docker-dhcp-relay / dhcp_relay.py | サーバ IP の追加・削除 | sonic-buildimage/dockers/docker-dhcp-relay/cli/config/plugins/dhcp_relay.py:98,147 |

## 例外条件

### db_migrator: 旧 DHCP_RELAY → DHCPV4_RELAY 移行時の重複スキップ
- db_migrator.py:928 — DHCPV4_RELAY に既に `dhcpv4_servers` が存在する場合、`log.log_notice("Skipping migration for {vlan_key}: dhcpv4_servers already present in DHCPV4_RELAY")` を出力してスキップ（べき等性）。

### config vlan: DHCPV4_RELAY 参照中の VLAN 削除拒否
- config/vlan.py:242-243 — DHCPV4_RELAY テーブルに参照が存在する VLAN を削除しようとすると `ctx.fail("{vlan} cannot be removed as it is being used in DHCPV4_RELAY table.")` でエラー終了。

### config main: VRF 削除時の依存チェック
- config/main.py:1699-1706 — VRF 削除時に DHCPV4_RELAY テーブルで当該 VRF が参照されていないか確認。参照がある場合は削除を拒否する。

### dhcp_relay CLI: 重複サーバ IP の扱い
- dhcp_relay.py では既存エントリを get_entry で取得してからマージして set_entry するため、同一 IP を複数回追加しても重複エントリは発生しない（リスト重複除去）。
