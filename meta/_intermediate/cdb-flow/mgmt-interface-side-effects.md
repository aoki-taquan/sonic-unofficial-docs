# MGMT_INTERFACE — Phase F 副次 DB 書込み調査ノート

調査日: 2026-05-18  
調査対象: `sonic-host-services/scripts/hostcfgd`、`sonic-buildimage/files/image_config/interfaces/interfaces-config.sh`

## 調査結果サマリ

`MGMT_INTERFACE` エントリの SET/DEL が CONFIG_DB に書き込まれると、`hostcfgd` の `mgmt_intf_handler` が以下の 3 系統の副次処理を連鎖させる。APPL_DB / STATE_DB / ASIC_DB への直接書き込みは一切発生しない（eth0 は intfmgrd 非対象）。

## 1. RADIUS PAM 設定ファイル再生成

`hostcfgd L2345-2350`:
```python
def mgmt_intf_handler(self, key, op, data):
    key = ConfigDBConnector.deserialize_key(key)
    mgmt_intf_name = self.__get_intf_name(key)
    self.aaacfg.handle_radius_source_intf_ip_chg(mgmt_intf_name)  # L2348
    self.aaacfg.handle_radius_nas_ip_chg(mgmt_intf_name)          # L2349
    self.mgmtifacecfg.update_mgmt_iface(mgmt_intf_name, key, data)
```

### handle_radius_source_intf_ip_chg (L495-510)

`RADIUS_GLOBAL.src_intf` または `RADIUS_SERVER.<addr>.src_intf` が変更されたインターフェースを参照していた場合、`AaaCfg.modify_conf_file()` が呼ばれて `/etc/pam_radius_auth.d/<server>` 設定ファイルが再生成される。

条件: `radius_global['src_intf'] == key[0]` または `radius_servers[addr]['src_intf'] == key[0]`

### handle_radius_nas_ip_chg (L512-525)

NAS IP が `radius_global` / `radius_servers` のいずれにも明示設定されていない場合（= mgmt IP を NAS IP として暗黙使用するケース）、IP 変化時に `modify_conf_file()` で `/etc/pam_radius_auth.d/` 全体を再生成する。

条件: `'nas_ip' not in radius_global` かつ `'nas_ip' not in radius_servers[addr]`（いずれかの server で成立）

## 2. /etc/network/interfaces 再生成 + カーネル netlink 適用

`MgmtIfaceCfg.update_mgmt_iface(L1626-1643)`:
```python
run_cmd(['sudo', 'systemctl', 'restart', 'interfaces-config'], True, True)
```

`interfaces-config.sh` は:
1. `sonic-cfggen -d ... -t interfaces.j2,/etc/network/interfaces` → `/etc/network/interfaces` を再生成
2. `systemctl restart networking` → `ifupdown2` が eth0 の IP アドレス・ルートを netlink で再適用

これはファイルシステム (`/etc/network/interfaces`) の変更であり DB への書き込みではない。

## 3. カーネル routing table / アドレステーブルへの反映

`ifupdown2` が `/etc/network/interfaces` を解釈し、以下の netlink メッセージをカーネルへ発行する。

| netlink メッセージ型 | 対応 ip コマンド | 条件 |
|---|---|---|
| `RTM_NEWADDR` | `ip addr add <ip_prefix> dev eth0` | 常時 |
| `RTM_DELADDR` | `ip addr del <old_prefix> dev eth0` | IP 変更・削除時 |
| `RTM_NEWROUTE` (metric 201) | `ip route add default via <gw> dev eth0 metric 201` | `gwaddr` が有効な場合 |
| `RTM_NEWROUTE table mgmt` | `ip route add ... table 6000` | `mgmtVrfEnabled=true` の場合 |
| `RTM_NEWROUTE` (forced routes) | `ip route add <prefix> dev eth0 table <mgmt|default>` | `forced_mgmt_routes` 非空 |

DB への書き戻しなし。

## DB 書き込みサマリ

| 副次書込先 | テーブル | 書込者 | 条件 |
|---|---|---|---|
| ファイルシステム | `/etc/network/interfaces` | `sonic-cfggen` (interfaces-config.sh) | 設定変化時 |
| カーネル netlink | routing table / addr table | `ifupdown2` | 常時 |
| APPL_DB | なし | — | eth0 は intfmgrd 非対象 |
| STATE_DB | なし | — | eth0 は intfmgrd 非対象 |
| ASIC_DB | なし | — | SAI 非経由 |
| COUNTERS_DB | なし | — | — |
| FLEX_COUNTER_DB | なし | — | — |
| `/etc/pam_radius_auth.d/` | RADIUS PAM conf | `AaaCfg.modify_conf_file()` | RADIUS src_intf または NAS IP 変化時のみ |

## SSH 切断リスク

eth0 の IP アドレスが変更される場合、`interfaces-config` サービスの再起動中に eth0 の IP が一時的に解除される。SSH セッションが eth0 経由であれば接続が切断される。

## grep スキャン証跡

- `hostcfgd:2345-2350` — mgmt_intf_handler
- `hostcfgd:495-525` — handle_radius_source_intf_ip_chg / handle_radius_nas_ip_chg
- `hostcfgd:1626-1643` — update_mgmt_iface
- `sonic-buildimage/files/image_config/interfaces/interfaces-config.sh` — interfaces-config 全体
- `intfmgrd.cpp:28-35` — MGMT_INTERFACE を購読しないことを確認
