# DHCP_RELAY — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/dhcp-relay.md`
調査日: 2026-05-14

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | DHCP_RELAY の SubscriberStateTable consumer 本体 |
| `sonic-dhcp-relay/dhcp6relay/src/main.cpp` | 起動エントリ (`initialize_swss` → `loop_relay`) |
| `sonic-buildimage/dockers/docker-dhcp-relay/docker-dhcp-relay.supervisord.conf.j2` | supervisord 起動順定義 |
| `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv6-relay.agents.j2` | dhcp6relay プロセス条件生成 |
| `sonic-buildimage/dockers/docker-dhcp-relay/wait_for_intf.sh.j2` | インタフェース ready 待機スクリプト |
| `sonic-buildimage/dockers/docker-dhcp-relay/cli/config/plugins/dhcp_relay.py` | CLI add/del ハンドラ、サービス再起動呼び出し |

## 検出した書込み順依存

### 1. VLAN_INTERFACE 先行必須（key 設定前）

`processRelayNotification` (config_interface.cpp:130-143) は、DHCP_RELAY エントリを受け取ったとき、まず `VLAN_INTERFACE|<vlan>|*` キーを CONFIG_DB に問い合わせる。
- キーが存在しない → `LOG_WARNING: "%s doesn't exist in VLAN_INTERFACE table, skip it"` してスキップ
- IPv6 アドレスを持つキーがない → `LOG_WARNING: "%s doesn't have IPv6 address configured, skip it"` してスキップ

**順序制約**: `VLAN` → `VLAN_INTERFACE`（IPv6 アドレス付き）→ `DHCP_RELAY` の順で書き込む必要がある。逆順だと SET が無視される（再起動または再 SET が必要）。

### 2. サービス再起動が必要（ランタイム変更不可）

`get_dhcp` (config_interface.cpp:73-79) は `dynamic=true` 時に設定変更を**無視**してログだけ出す:
```
syslog(LOG_WARNING, "relay config changed, need restart container to take effect");
```
初期化時のみ `dynamic=false` でハンドラが呼ばれる。`initialize_swss` から `get_dhcp(..., false, ...)` が呼ばれ、これが唯一の設定取り込みパス。

**順序制約**: DHCP_RELAY に SET/DEL した後、`systemctl stop/start dhcp_relay` が必要。CLI (`dhcp_relay.py:restart_dhcp_relay_service`) はこれを自動実行する。

### 3. dhcpv6_servers の ordered-by user 挿入順

`processRelayNotification` (config_interface.cpp:160-165) で `dhcpv6_servers` フィールドをカンマ区切りで `getline` し `intf.servers.push_back` でリストに積む。

YANG 定義 (`sonic-dhcpv6-relay.yang`) が `ordered-by user` のため、CONFIG_DB はリスト挿入順を保持する。`dhcp6relay` はこの順序で upstream サーバをスキャンする。

**順序制約**: サーバ追加順がリレー転送の試行順序になる。後から add したサーバは末尾に追加される（`dhcp_relay.py:dhcp_servers.append`）。

### 4. `rfc6939_support` / `interface_id` フィールドのデフォルト確定タイミング

`processRelayNotification` (config_interface.cpp:117-121):
```cpp
bool option_79_default = true;   // rfc6939_support default
bool interface_id_default = false;
if (dual_tor_sock) {
    interface_id_default = true;  // DualToR では true
}
```
フィールドが未設定の場合はこのデフォルト値が使われる。`dual_tor_sock` は `main.cpp` の起動引数 `-u` で決まり、**起動時に確定**する。

- `rfc6939_support="false"` は config_interface.cpp:169 で明示的に `false` にされる（SET では `"true"` の明示が不要 = デフォルト on）
- `interface_id="true"` は config_interface.cpp:172-173 で明示的に `true` にされる（非 DualToR ではデフォルト off）

**順序制約**: これらのフィールドはエントリ書込み後の **再起動時点** のデフォルト値で評価される。起動後に `dual_tor_sock` は変わらないため、DualToR 判定はサービス起動引数に依存（supervisord テンプレートで `DEVICE_METADATA.subtype` から決定）。

### 5. ブート時の supervisord 起動順

`docker-dhcp-relay.supervisord.conf.j2` での priority:
1. `rsyslogd` (priority=1)
2. `start` = `start.sh` / `wait_for_intf.sh.j2` (priority=2) → STATE_DB で `INTERFACE_TABLE|<vlan>|<prefix>|state==ok` をポーリング
3. `dhcp6relay` / `dhcprelayd` (priority=3, `dependent_startup_wait_for=start:exited`)

`wait_for_intf.sh.j2`:
- `VLAN_INTERFACE` に IPv4 prefix がある VLAN を全てポーリング
- `DHCP_RELAY` に該当 VLAN が存在し IPv6 prefix がある場合も同様にポーリング
- 全インタフェース ready 後、さらに **sleep 10 秒** 待機してから dhcp6relay 起動

**順序制約**: STATE_DB の `INTERFACE_TABLE|<vlan>|<prefix>|state` が `ok` になるまで dhcp6relay は起動しない。つまり CONFIG_DB の VLAN_INTERFACE 設定 → カーネル/netns でのインタフェース up → STATE_DB 更新 → dhcp6relay 起動、という順序依存がある。

### 6. DEL/SET 順序の副作用

`del_dhcp_relay` (dhcp_relay.py:155-162):
- `dhcpv6_servers` が空になると `del table[dhcpv6_servers]` → `set_entry(table_name, vlan_name, table)` でフィールドだけ削除
- テーブル全体が空になると `set_entry(table_name, vlan_name, None)` でエントリ削除（DEL 操作が SubscriberStateTable へ伝搬）

DEL 操作が SubscriberStateTable に到達しても `processRelayNotification` は DEL op を `skip it` ログなしで受け取るが、`vlans` マップへの削除ロジックがない。つまり、DEL 後に config を消しても **`vlans` マップはメモリ上に残る**。サービス再起動でのみ状態がリセットされる。

**順序制約**: サーバ全削除 → 再起動しないと、メモリ上は古い設定で動き続ける（dhcp6relay が再起動されるまで DEL は未反映）。

## 結論まとめ

| 依存 | トリガ | 影響フィールド | 修正方法 |
|------|--------|---------------|---------|
| VLAN_INTERFACE 先行必須 | DHCP_RELAY SET | key (vlan name), dhcpv6_servers | VLAN/VLAN_INTERFACE を先に作成 |
| サービス再起動必須 | DHCP_RELAY SET/DEL | 全フィールド | systemctl restart dhcp_relay (CLI が自動実行) |
| dhcpv6_servers 挿入順 | SET | dhcpv6_servers | 追加順がスキャン優先順に直結 |
| DualToR 起動引数 | 起動時 | interface_id default | DEVICE_METADATA.subtype で決定 |
| STATE_DB インタフェース up 待機 | boot/restart | 全体 | wait_for_intf.sh が STATE_DB ポーリング |
| DEL 後メモリ残留 | DEL op | dhcpv6_servers | 再起動でのみ vlans マップリセット |
