# portchannel 例外条件エビデンス

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/cfgmgr/teammgr.cpp`

## 例外条件まとめ

### スキーマ検証 (YANG)
- `name` pattern: `PortChannel[0-9]{1,4}` — 名前形式不正は reject。
- `admin_status` は mandatory。
- `min_links` range: 1..1024。
- `mtu` range: 1..9216。
- `lacp_key`: `auto` または uint16 (1..65535)。
- `tpid`: `stypes:tpid_type` (0x8100 / 0x9100 / 0x9200 / 0x88a8 / 0x88A8)。

### consumer (portsorch / teammgr) 例外動作
- LAG ID 払い出し失敗: `Failed to allocate unique LAG id for local lag %s rv:%d` → SWSS_LOG_ERROR (portsorch.cpp:7981)
- SAI LAG create 失敗: `Failed to create LAG %s lid:` → SWSS_LOG_ERROR (portsorch.cpp:7998)
- 非空 LAG の DEL: `Failed to remove non-empty LAG %s` → SWSS_LOG_ERROR (portsorch.cpp:8060)
- VLAN 所属 LAG の DEL: `Failed to remove LAG %s, it is still in VLAN` → SWSS_LOG_ERROR (portsorch.cpp:8065)
- SAI LAG remove 失敗: `Failed to remove LAG %s lid:` → SWSS_LOG_ERROR (portsorch.cpp:8077)
- LAG TPID 設定失敗: `Failed to set TPID 0x%x to LAG pid:` → SWSS_LOG_ERROR (portsorch.cpp:8280)
- LAG collection/distribution 設定失敗: SWSS_LOG_ERROR (portsorch.cpp:8310,8341)
- SIGTERM 送信失敗 (teamd): `Failed to send SIGTERM to port channel %s pid %d` → SWSS_LOG_ERROR (teammgr.cpp:209,674)
- `ref_count` > 0 の LAG DEL: `Failed to remove ref count %d LAG %s` → SWSS_LOG_ERROR (portsorch.cpp:8051)
