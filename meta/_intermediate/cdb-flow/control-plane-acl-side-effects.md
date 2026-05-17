# control-plane-acl — Phase F: 副作用カタログ (中間トレース)

調査日: 2026-05-17
対象ファイル:
- sonic-host-services/scripts/caclmgrd (全行読了)
- sonic-swss/orchagent/aclorch.cpp (関連箇所読了)
- sonic-swss/orchagent/aclorch.h (関連箇所読了)

## 1. orchagent (AclOrch) 側の副作用

### STATE_DB への書き込み

`doAclTableTask()` は `addAclTable()` 成功後に必ず `setAclTableStatus(table_id, AclObjectStatus::ACTIVE)` を呼ぶ。
これは CTRLPLANE テーブルも例外ではない。

- `addAclTable()` 内で CTRLPLANE 判定 → `m_ctrlAclTables.emplace()` + `return true`
- 呼び出し元 `doAclTableTask()` L5474-5477 が `true` を受取り `setAclTableStatus(ACTIVE)` を実行
- 書き込み先: `STATE_DB / ACL_TABLE_TABLE` (テーブル名 `STATE_ACL_TABLE_TABLE_NAME`)
- フィールド: `status = "active"`

evidence: `aclorch.cpp:4680-4684` (addAclTable CTRLPLANE早期 return), `aclorch.cpp:5474-5477` (呼び元 ACTIVE 書き込み), `aclorch.cpp:6088-6093` (setAclTableStatus 実装)

**注意**: ACL_RULE については CTRLPLANE テーブルの場合は erase するため、`setAclRuleStatus()` は呼ばれない。

### SAI への副作用

なし。CTRLPLANE ACL は `m_ctrlAclTables` に登録されるのみ。

### APPL_DB への副作用

なし。AclOrch は APPL_DB に書き込まない。

---

## 2. caclmgrd 側の副作用

### 2-1. iptables / ip6tables INPUT チェーン (全プラットフォーム共通)

ACL_TABLE/ACL_RULE の SET/DEL イベント受信時、caclmgrd は全ルールをフラッシュして再インストールする。

**フラッシュ対象** (`update_control_plane_acls()` → `get_acl_rules_and_translate_to_iptables_commands()`):
- `iptables -P INPUT/FORWARD/OUTPUT ACCEPT` (デフォルトポリシーを一時 ACCEPT)
- `iptables -F <chain>` (全チェーンのルールをフラッシュ)
- `iptables -X <non-default chain>` (デフォルト以外のチェーンを削除、DualToR 時 DHCP チェーンを除く)
- `ip6tables -F / -X / -t raw -F` (ip6tables も同様)

**新規インストール対象** (上から順):
1. loopback 127.0.0.1 / ::1 ACCEPT (INPUT)
2. BFD UDP 3784,4784 ACCEPT (条件付き: `bfdAllowed==True`)
3. VxLAN UDP 4789 ACCEPT (条件付き: `VxlanAllowed==True`)
4. DASH-HA swbus_port ACCEPT (条件付き: `dash-ha` feature が存在)
5. 内部 Docker IP ACCEPT (multi-ASIC 時のみ実質追加)
6. chassis midplane ACCEPT (chassis/SmartSwitch 時のみ)
7. ESTABLISHED/RELATED ACCEPT (conntrack)
8. ICMPv4/ICMPv6 各種 ACCEPT
9. DualToR: UDP 67 → DHCP チェーン ACCEPT (DualToR のみ)
10. DHCP UDP 67:68 / 546:547 ACCEPT
11. BGP TCP 179 ACCEPT (eth0 除外)
12. ip6tables raw PREROUTING/OUTPUT ICMPv6 NOTRACK
13. CONFIG_DB ACL_RULE → `iptables -A INPUT` (PRIORITY 降順)
14. ip2me DROP (LOOPBACK/VLAN/PORTCHANNEL/INTERFACE の各 IP)
15. TTL<2 traceroute ACCEPT
16. デフォルト DROP (ACL ルール 1 件以上の場合のみ)

evidence: `caclmgrd:625-901` (get_acl_rules_and_translate_to_iptables_commands 全体)

### 2-2. iptables nat テーブル (multi-ASIC 専用)

`update_control_plane_nat_acls()` → `generate_fwd_traffic_from_namespace_to_host_commands()` が
名前空間ごとに nat テーブルを書き換える。

- `iptables -t nat -X` / `-F` (nat チェーン全削除・フラッシュ)
- `iptables -t nat -A PREROUTING -p <proto> -s <src_ip> --dport <port> -j DNAT --to-destination <host_mgmt_ip>`
- `iptables -t nat -A POSTROUTING -p <proto> -s <src_ip> --dport <port> -j SNAT --to-source <ns_docker_mgmt_ip>`

対象サービス: `multi_asic_ns_to_host_fwd=True` の `SNMP` (tcp/udp:161) と `SSH` (tcp:22) のみ。

evidence: `caclmgrd:476-516` (generate_fwd_traffic_from_namespace_to_host_commands)

### 2-3. iptables nat テーブル (DualToR 専用)

`generate_fwd_traffic_from_host_to_soc()`:
- `iptables -t nat --flush POSTROUTING` (POSTROUTING フラッシュ)
- `iptables -t nat -A POSTROUTING --destination <soc_ip> --source <vlan_addr> -j SNAT --to-source <loopback3>`

`generate_block_bgp_loopback1()`:
- `iptables -I INPUT 1 -d <loopback1_addr> -p tcp --dport 179 -j DROP`

evidence: `caclmgrd:429-427,401-427` (generate_fwd_traffic_from_host_to_soc, generate_block_bgp_loopback1)

### 2-4. スレッド生成 (ACL 更新時)

CONFIG_DB の ACL_TABLE/ACL_RULE 変更通知を受信すると、caclmgrd は `check_and_update_control_plane_acls()` を別スレッドとして起動する。

- スレッド名: Python の `threading.Thread`
- スレッドは `UPDATE_DELAY_SECS=0.5` 秒のデバウンス後に `update_control_plane_acls()` を実行
- スレッド完了後 `update_thread[namespace] = None` でクリア

evidence: `caclmgrd:1299-1303`

### 2-5. caclmgrd 起動時の副作用

`run()` 開始時、全名前空間に対して無条件で `update_control_plane_acls()` を実行する。
これにより既存の iptables ルールが一度フラッシュ・再インストールされる。

evidence: `caclmgrd:1169-1171`

---

## 3. 副作用サマリ

| 副作用 | 担い手 | 書き込み先 | 条件 |
|-------|-------|-----------|------|
| STATE_DB ACL_TABLE_TABLE に `status=active` 書き込み | AclOrch | STATE_DB | CTRLPLANE テーブル SET 成功時 |
| iptables/ip6tables INPUT チェーン フラッシュ＆再インストール | caclmgrd | カーネル iptables | ACL_TABLE/ACL_RULE 変更時、起動時 |
| ip6tables raw テーブル ICMPv6 NOTRACK | caclmgrd | カーネル ip6tables | 常時 |
| iptables nat PREROUTING/POSTROUTING DNAT/SNAT | caclmgrd | カーネル iptables (名前空間ごと) | multi-ASIC のみ |
| iptables nat POSTROUTING SNAT (SOC 向け) | caclmgrd | カーネル iptables | DualToR のみ |
| iptables INPUT DROP BGP Loopback1 | caclmgrd | カーネル iptables | DualToR のみ |
| update thread 生成 | caclmgrd | Python threading | ACL_TABLE/ACL_RULE 変更時 |
