# NTP_GLOBAL — 暗黙参照テーブル (Phase C) 調査メモ

## 調査対象

- `sonic-host-services/scripts/hostcfgd` (NtpCfg クラス, HostConfigDaemon.setup())
- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang`

## hostcfgd の暗黙参照

### NTP_SERVER (CFG_NTP_SERVER_TABLE_NAME)

`ntp_srv_key_handler()` (hostcfgd:2387-2391) が NTP_SERVER / NTP_KEY イベントを受け取ると、
`ntp_srv_key_update()` を `config_db.get_table(CFG_NTP_SERVER_TABLE_NAME)` で全テーブルを引数に呼ぶ。
つまり NTP_GLOBAL の変更ではなく NTP_SERVER の変更時も全 NTP_SERVER が読まれる。

初期化時 (HostConfigDaemon.load, hostcfgd:2255-2272) も `init_data.get(CFG_NTP_SERVER_TABLE_NAME)` で読む。

### NTP_KEY (CFG_NTP_KEY_TABLE_NAME)

NTP_SERVER と同様。`ntp_srv_key_update()` に `get_table(CFG_NTP_KEY_TABLE_NAME)` で渡す。
authentication=enabled 時のみ chrony.conf.j2 の keyfile / key ディレクティブが有効化される。

### MGMT_VRF_CONFIG (CFG_MGMT_VRF_CONFIG_TABLE_NAME)

hostcfgd:2249 の init 時に `init_data.get(CFG_MGMT_VRF_CONFIG_TABLE_NAME)` で読む。
ただし NtpCfg 自体は MGMT_VRF_CONFIG を直接読まない。YANG must 制約が `vrf=mgmt` → `mgmtVrfEnabled=true` を保証する。
CLI 経由なら YANG バリデーション時点で mgmtVrfEnabled が確認される (sonic-ntp.yang must 制約)。

### LOOPBACK_INTERFACE

- hostcfgd:2483 で subscribe して `lpbk_handler` に接続。
- `lpbk_handler` は `NtpCfg.handle_ntp_source_intf_chg(intf_name)` を呼ぶ (hostcfgd:598 経由)。
- `handle_ntp_source_intf_chg` は NTP_SERVER が空なら early return (hostcfgd:1315)。
  src_intf にその loopback 名が含まれるときのみ chrony restart。

## chrony.conf.j2 の暗黙参照

### NTP_SERVER (j2:20-55)

テンプレートのメインループ。`NTP_SERVER` の全エントリを `admin_state != 'disabled'` フィルタで読み出し、
server / pool / peer ディレクティブを生成。association_type / resolve_as / key / iburst / version を参照。

### DEVICE_METADATA (j2:16)

`DEVICE_METADATA.localhost.subtype` が `'SmartSwitch'` かつ `type != 'SmartSwitchDPU'` のときのみ
`allow` / `binddevice bridge-midplane` を出力 (j2:58-64)。NTP サーバ機能（server_role / dhcp）はこの条件下でのみ有効。

### MGMT_INTERFACE (j2:91-92)

`src_intf == "eth0"` のとき `get_ip_on_interface(eth0, MGMT_INTERFACE, ...)` で IPv4/IPv6 アドレスを取得し
`bindacqaddress` に使用。`MGMT_INTERFACE` から `(eth0, prefix)` のペアを走査。

### VLAN_INTERFACE (j2:94-95)

`src_intf.startswith('Vlan')` のとき `VLAN_INTERFACE` からアドレス取得。

### INTERFACE (j2:97-98)

`src_intf.startswith('Ethernet')` のとき `INTERFACE` からアドレス取得。

### PORTCHANNEL_INTERFACE (j2:100-101)

`src_intf.startswith('PortChannel')` のとき `PORTCHANNEL_INTERFACE` からアドレス取得。

### LOOPBACK_INTERFACE (j2:103-104)

`src_intf.startswith('Loopback')` のとき `LOOPBACK_INTERFACE` からアドレス取得。
これは hostcfgd の subscribe とは独立したテンプレート側の参照。

## vrf=mgmt 時の特殊挙動

j2:109 `{% if not ((NTP) and NTP['global']['vrf'] == 'mgmt') %}` — mgmt VRF 時は bindacqaddress を出力しない。
カーネルの mgmt VRF routing に委ねる設計。
