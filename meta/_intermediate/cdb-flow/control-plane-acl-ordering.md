# control-plane-acl ordering 調査メモ

## 調査対象

- `sonic-host-services/scripts/caclmgrd` (全行読了)
- `sonic-swss/orchagent/aclorch.cpp` (CTRLPLANE 関連箇所)
- `sonic-host-services/data/debian/sonic-host-services-data.caclmgrd.service`

## iptables ルール生成順序 (caclmgrd)

`get_acl_rules_and_translate_to_iptables_commands()` が生成する iptables コマンドの順序は以下の通り:

1. デフォルトポリシーを ACCEPT に設定 (`INPUT/FORWARD/OUTPUT`)
2. 既存チェーンをフラッシュ・削除 (DHCP チェーンは DualToR 時のみ保持)
3. ループバック (127.0.0.1/::1) を ACCEPT
4. BFD セッションが存在する場合: UDP 3784,4784 を INSERT INPUT 2 で ACCEPT (`get_bfd_iptable_commands`)
5. VxLAN が有効な場合: UDP 4789 を INSERT INPUT 2 で ACCEPT (`get_vxlan_port_iptable_commands`)
6. DASH-HA が有効な場合: swbus_port を INSERT INPUT 2 で ACCEPT (`make_dash_ha_rules`)
7. 内部 Docker IP トラフィックを ACCEPT (`generate_allow_internal_docker_ip_traffic_commands`)
8. Chassis midplane トラフィックを ACCEPT (`generate_allow_internal_chasis_midplane_traffic`)
9. ESTABLISHED/RELATED 接続を ACCEPT (conntrack)
10. ICMPv4 (echo-request/reply/destination-unreachable/time-exceeded) を ACCEPT
11. ICMPv6 (同上 + NDP NS/NA/RS/RA) を ACCEPT
12. DualToR 時: UDP 67 を DHCP チェーンへジャンプ
13. DHCP UDP 67:68 および 546:547 を ACCEPT
14. BGP TCP 179 を ACCEPT (管理ポート eth0 除く)
15. ICMPv6 の conntrack 無効化 (ip6tables -t raw NOTRACK)
16. CONFIG_DB の `ACL_TABLE` / `ACL_RULE` を読み込み、CTRLPLANE テーブルのルールを PRIORITY 降順でソートして iptables -A INPUT に追加
17. ip2me トラフィックを DROP (各インターフェース IP)
18. TTL < 2 の ICMP/UDP/TCP (traceroute 対応) を ACCEPT
19. ルールが 1 件以上存在する場合: INPUT へ DROP を追加 (デフォルト deny)

## ACL_RULE の優先度処理

```python
# caclmgrd L774-825
acl_rules[rule_props["PRIORITY"]] = rule_props
...
for priority in sorted(iter(acl_rules.keys()), reverse=True):
```

`ACL_RULE` の `PRIORITY` フィールドを dict のキーとして収集し、**降順ソート** (`reverse=True`) で iptables に `-A INPUT` する。
高 PRIORITY 値 = 先に `-A` される = iptables チェーン上の優先マッチ。

## caclmgrd の起動・再適用タイミング

- 起動時: `run()` 内の初期ループで `update_control_plane_acls()` を全 namespace に対して即時呼び出す
- Config DB 変更通知 (`ACL_TABLE` / `ACL_RULE` の SubscriberStateTable): `check_and_update_control_plane_acls()` をスレッド生成。`UPDATE_DELAY_SECS = 0.5` 秒のデバウンス後に再適用
- BFD セッション SET: `allow_bfd_protocol()` が BFD ルールを即時追加 (全 namespace フラッシュなし、追加のみ)
- VxLAN TUNNEL SET/DEL: `allow_vxlan_port()` / `block_vxlan_port()` が VxLAN ルールを追加/削除
- DPU SET/DEL (DASH-HA): `update_dash_ha_rules()` が swbus_port ルールを追加/削除
- DualToR MUX_CABLE STATE_DB 変更: `update_dhcp_acl()` が DHCP チェーンを更新

## warm-reboot 挙動

caclmgrd スクリプトに warm-reboot / reconcile ロジックは存在しない。systemd サービスファイルも `Restart=always` のみで warm-boot 固有の処理なし。

warm-reboot 中は caclmgrd が systemd によって再起動される。再起動後に `update_control_plane_acls()` が全 namespace に対して全ルールを再インストールする（フルリプログラム）。

**影響**: warm-reboot 中の CPU 宛パケット (SSH/SNMP/BGP) は iptables ルールが空になる期間が発生しうる。ただし iptables のデフォルトポリシーはフラッシュ直前に ACCEPT に設定されるため (`iptables -P INPUT ACCEPT`)、ルール空の期間はすべてのトラフィックが通過する。

## orchagent (AclOrch) での CTRLPLANE 順序依存

CTRLPLANE テーブルは orchagent 側では `m_ctrlAclTables` に記録されるのみ。aclorch.cpp の `doAclTableTask()` が CTRLPLANE テーブルを先に処理しなくても、`doAclRuleTask()` は `m_ctrlAclTables` でキーを発見した場合に即 erase (スキップ) するため、ACL_RULE の書き込み順序は不問。

ただし caclmgrd は Config DB から `ACL_TABLE` および `ACL_RULE` をまとめて読み込むため、caclmgrd 自身の ordering は以下:

1. `get_table(ACL_TABLE)` → `get_table(ACL_RULE)` の順で読み込む (L729-730)
2. ACL_TABLE のうち `type=CTRLPLANE` のみフィルタ
3. 各テーブルの ACL_RULE を `rule_table_name == table_name` でフィルタ
4. PRIORITY 降順でソートして iptables コマンドリストに追加

## サービス依存 (systemd)

```
caclmgrd.service:
  Requires=config-setup.service
  After=config-setup.service
  BindsTo=sonic.target
  After=sonic.target
```

CONFIG_DB は `config-setup.service` が起動した後に利用可能になる。caclmgrd は config-setup.service 完了後に起動するため、初回 `update_control_plane_acls()` は CONFIG_DB が ready な状態で呼ばれる。

## 証跡

- `caclmgrd L625-901`: `get_acl_rules_and_translate_to_iptables_commands()` 全行読了
- `caclmgrd L1112-1304`: `run()` メインループ全行読了
- `caclmgrd L943-994`: `check_and_update_control_plane_acls()` スレッド読了
- `aclorch.cpp:5556-5560`: `doAclRuleTask()` CTRLPLANE erase ロジック確認
- `sonic-host-services-data.caclmgrd.service`: systemd 依存確認
