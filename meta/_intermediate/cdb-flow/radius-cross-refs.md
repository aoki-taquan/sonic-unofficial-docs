# RADIUS — Phase C cross-refs 調査メモ

## 調査対象

`docs/reference/config-db/radius.md` への Phase C (cross-refs) ブロック追加。

## ソース

- `sonic-net/sonic-host-services/scripts/hostcfgd`

## 発見された暗黙参照

### modify_conf_file() 内で常時結合されるテーブル

1. `RADIUS_SERVER` — サーバ毎の auth_port / passkey / retransmit / timeout / src_intf を global dict とマージ (hostcfgd:681-695)
2. `AAA` — authentication.login に radius が含まれる場合のみ PAM に反映 (hostcfgd:752-780)

### 動的 IP / hostname 解決

- `MGMT_INTERFACE`: nas_ip 未指定時に eth0 の IPv4 を自動注入 (hostcfgd:671-674)
- `DEVICE_METADATA` hostname: nas_id 未指定時にホスト名を自動注入 (hostcfgd:675-678)
- `INTERFACE` / `VLAN_INTERFACE` / `VLAN_SUB_INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE`: src_intf 指定時に IP 解決 (hostcfgd:582-614)

### 逆方向 subscribe (RADIUS conf を再トリガ)

- `MGMT_INTERFACE` → handle_radius_source_intf_ip_chg() + handle_radius_nas_ip_chg() (hostcfgd:2348-2349, 2485)
- `INTERFACE` → handle_radius_source_intf_ip_chg() (hostcfgd:2365, 2489)
- `VLAN_INTERFACE` → handle_radius_source_intf_ip_chg() (hostcfgd:2369, 2486)
- `PORTCHANNEL_INTERFACE` → handle_radius_source_intf_ip_chg() (hostcfgd:2377, 2488)
- `DEVICE_METADATA` → hostname_update() → nas_id 再生成 (hostcfgd:2280, 2492)
