# DHCP_RELAY — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/dhcp-relay.md`
調査日: 2026-05-16

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | DHCP_RELAY の SubscriberStateTable consumer 本体 (dhcp6relay) |
| `sonic-dhcp-relay/dhcp6relay/src/main.cpp` | dhcp6relay 起動エントリ (`initialize_swss` → `loop_relay`) |
| `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py` | dhcprelayd Python デーモン (VLAN/DHCP_SERVER_IPV4 監視・dhcrelay 管理) |
| `sonic-buildimage/dockers/docker-dhcp-relay/docker-dhcp-relay.supervisord.conf.j2` | supervisord 起動順定義 (priority=1/2/3/4) |
| `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv4-relay.agents.j2` | isc-dhcpv4-relay-<vlan> プロセス生成条件 |
| `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv6-relay.agents.j2` | dhcp6relay プロセス条件生成 |
| `sonic-buildimage/dockers/docker-dhcp-relay/dhcp-relay.monitors.j2` | dhcpmon プロセス生成・依存関係 |
| `sonic-buildimage/dockers/docker-dhcp-relay/wait_for_intf.sh.j2` | インタフェース ready 待機スクリプト |
| `sonic-buildimage/dockers/docker-dhcp-relay/cli/config/plugins/dhcp_relay.py` | CLI add/del ハンドラ、サービス再起動呼び出し |

## 検出した書込み順依存

### A. dhcp6relay (DHCPv6) — 起動時一度読み込み設計

`processRelayNotification` (config_interface.cpp:130-143) は、DHCP_RELAY エントリを受け取ったとき、まず `VLAN_INTERFACE|<vlan>|*` キーを CONFIG_DB に問い合わせる。
- キーが存在しない → `LOG_WARNING: "%s doesn't exist in VLAN_INTERFACE table, skip it"` してスキップ
- IPv6 アドレスを持つキーがない → `LOG_WARNING: "%s doesn't have IPv6 address configured, skip it"` してスキップ

**順序制約**: `VLAN` → `VLAN_INTERFACE`（IPv6 アドレス付き）→ `DHCP_RELAY` の順で書き込む必要がある。逆順だと SET が無視される（再起動または再 SET が必要）。

`get_dhcp` (config_interface.cpp:73-79) は `dynamic=true` 時に設定変更を**無視**してログだけ出す:
```
syslog(LOG_WARNING, "relay config changed, need restart container to take effect");
```
初期化時のみ `dynamic=false` でハンドラが呼ばれる。**順序制約**: DHCP_RELAY に SET/DEL した後、`systemctl stop/start dhcp_relay` が必要。

`dhcpv6_servers` は `ordered-by user` で YANG が設定順を保持。`push_back` (cpp:160-165) により追加順がスキャン優先順に直結。

### B. isc-dhcp-relay (`dhcrelay`) — VLAN.dhcp_servers 依存

`dhcpv4-relay.agents.j2` (行2) の起動条件:
```jinja2
{% if VLAN and vlan_name in VLAN and 'dhcp_servers' in VLAN[vlan_name] and VLAN[vlan_name]['dhcp_servers']|length > 0 %}
```
コンテナ起動時に `VLAN[<vlan>].dhcp_servers` が 1 件以上でないと `isc-dhcpv4-relay-<vlan>` が supervisord に登録されない。

upstream インタフェースは `VLAN_INTERFACE|pfx_filter` (行18-19)、`INTERFACE|pfx_filter` (行21-22)、`PORTCHANNEL_INTERFACE|pfx_filter` (行24-25) から `-iu <name>` として列挙。これらのテーブルが存在しない場合 `-iu` なしで起動する。

**PORT 監視 (dhcpmon) の順序依存**:
`dhcp-relay.monitors.j2` (行52-56):
```jinja2
{% if 'has_sonic_dhcpv4_relay' ... == 'True' %}
dependent_startup_wait_for=dhcp4relay:running
{% else %}
dependent_startup_wait_for=isc-dhcpv4-relay-{{ vlan_name }}:running
{% endif %}
```
`dhcpmon-<vlan>` (priority=4) は `isc-dhcpv4-relay-<vlan>:running` または `dhcp4relay:running` を待つ。isc-dhcpv4-relay が起動しない場合 dhcpmon も起動しない。

### C. dhcprelayd — VLAN/VLAN_INTERFACE/DHCP_SERVER_IPV4 動的監視

`dhcprelayd.py` が購読するテーブルと順序依存:

| チェッカー | 購読テーブル | トリガ | 動作 |
|----------|-----------|-------|------|
| `VlanTableEventChecker` | VLAN | VLAN 追加/削除 | `refresh_dhcrelay(force_kill=False)` |
| `VlanIntfTableEventChecker` | VLAN_INTERFACE | VLAN_INTERFACE 変更 | `refresh_dhcrelay(force_kill=True)` (強制再起動) |
| `DhcpServerTableIntfEnablementEventChecker` | DHCP_SERVER_IPV4 | state 変更 | `refresh_dhcrelay(force_kill=False)` |
| `DhcpServerFeatureStateChecker` | FEATURE | dhcp_server.state 変更 | supervisord stop/start + checker 有効/無効切替 |

`refresh_dhcrelay()` (dhcprelayd.py:81-116) での VLAN チェック:
```python
if dhcp_interface not in vlan_table and dhcp_interface != mid_plane_bridge_name:
    dhcp_interfaces.discard(dhcp_interface)  # VLAN 未存在は除外
    continue
```

**順序制約**: `DHCP_SERVER_IPV4[<vlan>].state = "enabled"` を設定する前に `VLAN[<vlan>]` が存在していないと、dhcprelayd が `dhcp_interfaces` からそのインタフェースを除外し dhcrelay が起動しない。VLAN 追加後に dhcprelayd が VlanTableEventChecker 経由で `refresh_dhcrelay` を呼ぶことで自動修正される。

`dhcprelayd.start()` (dhcprelayd.py:67) は `time.sleep(5)` で supervisord が isc-dhcpv4-relay を起動するのを待つ。この 5 秒以内に VLAN/DHCP_SERVER_IPV4 の書き込みが完了している必要がある（ただし start 後にも dhcprelayd がポーリングするため致命的ではない）。

### D. ブート時の完全起動順序

```
1. rsyslogd (priority=1)
2. start.sh / wait_for_intf.sh (priority=2)
   - VLAN_INTERFACE (IPv4) / DHCP_RELAY (IPv6 prefix) の全 VLAN を
     STATE_DB INTERFACE_TABLE|<vlan>|<prefix>|state == "ok" までポーリング
   - 全 ready 後 sleep 10 秒
3. dhcp6relay          (priority=3, wait_for=start:exited) ← DHCP_RELAY を読む
   isc-dhcpv4-relay-*  (priority=3, wait_for=start:exited) ← VLAN.dhcp_servers を読む
   dhcprelayd          (priority=3, wait_for=start:exited) ← DHCP_SERVER_IPV4 監視
4. dhcpmon-*           (priority=4, wait_for=isc-dhcpv4-relay-*:running)
```

VLAN/VLAN_INTERFACE が CONFIG_DB に存在しない場合:
- `wait_for_intf.sh` がポーリング対象を持たず即 exited → dhcp6relay/isc-dhcpv4-relay が設定なしで起動
- j2 テンプレートが VLAN エントリなしで生成された場合、isc-dhcpv4-relay エントリが supervisord.conf に存在しない → dhcpmon も起動しない

## 結論まとめ

| 依存 | Consumer | トリガ | 影響フィールド | 修正方法 |
|------|---------|--------|---------------|---------|
| VLAN_INTERFACE (IPv6) 先行必須 | dhcp6relay | DHCP_RELAY SET | key, dhcpv6_servers | VLAN → VLAN_INTERFACE(IPv6) を先に作成 |
| サービス再起動必須 | dhcp6relay | DHCP_RELAY SET/DEL | 全フィールド | systemctl restart dhcp_relay |
| dhcpv6_servers 挿入順 | dhcp6relay | SET | dhcpv6_servers | 追加順がスキャン優先順 |
| VLAN.dhcp_servers 存在 | isc-dhcp-relay | コンテナ起動時 | supervisord エントリ生成 | VLAN + dhcp_servers 設定 → コンテナ再起動 |
| VLAN_INTERFACE (IPv4) upstream | isc-dhcp-relay | コンテナ起動時 | -iu オプション | VLAN_INTERFACE (IPv4) 設定 → コンテナ再起動 |
| PORT 監視 (dhcpmon) 順序 | dhcpmon | 起動時 | isc-dhcpv4-relay running 状態 | isc-dhcpv4-relay が先に起動している必要 |
| VLAN 存在チェック | dhcprelayd | DHCP_SERVER_IPV4 enabled | dhcp_interfaces セット | VLAN → DHCP_SERVER_IPV4 の順 |
| VLAN_INTERFACE 変更 → force kill | dhcprelayd | VLAN_INTERFACE 変更 | dhcrelay 全インタフェース | dhcprelayd が自動 force kill + 再起動 |
