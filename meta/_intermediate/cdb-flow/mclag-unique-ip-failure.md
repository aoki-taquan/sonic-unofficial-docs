# MCLAG_UNIQUE_IP 失敗挙動調査ノート (Phase D)

調査日: 2026-05-19

## 対象ソースコード

- `sonic-swss/mclagsyncd/mclaglink.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/mclagsyncd/mclaglink.h` (同リポ)
- `sonic-swss/mclagsyncd/mclag.h` (同リポ)
- `sonic-utilities/config/mclag.py` (ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9)

## 調査結果

### mclagsyncdSendMclagUniqueIpCfg の失敗パス

`mclaglink.cpp:1087-1180` の `mclagsyncdSendMclagUniqueIpCfg()` を精読。

**パス1: 空 ifname**
```cpp
// mclaglink.cpp:1119-1122
unique_ip_ifnames = key.substr(delimiter_pos+1);
if (unique_ip_ifnames.empty())
{
    SWSS_LOG_ERROR("Invalid Key %s Format. No unique ip ifname specified", key.c_str());
    continue;
}
```
`continue` でスキップ。リトライなし。

**パス2: バッファフラッシュ失敗**
```cpp
// mclaglink.cpp:1138-1155
if (MCLAG_MAX_SEND_MSG_LEN - infor_len < (sizeof(struct mclag_unique_ip_cfg_info)) )
{
    // ...flush attempt...
    write = ::write(getConnSocket(), infor_start, cfg_msg_hdr->msg_len);
    if (write <= 0)
    {
        SWSS_LOG_ERROR("mclagsycnd to ICCPD, mclag unique ip cfg send, buffer full; write to m_connection_socket failed");
    }
    infor_len = sizeof(mclag_msg_hdr_t);
}
```
`MCLAG_MAX_SEND_MSG_LEN = 4096` (mclag.h:62)。バッファ超過時に強制フラッシュするが失敗してもループ継続。

**パス3: 最終 write 失敗**
```cpp
// mclaglink.cpp:1173-1177
write = ::write(getConnSocket(), infor_start, cfg_msg_hdr->msg_len);
if (write <= 0)
{
    SWSS_LOG_ERROR("mclagsycnd to ICCPD, mclag unique ip cfg send; write to m_connection_socket failed");
}
```
エラーログのみ。リトライなし。メッセージ消失。

### mclag_unique_ip_cfg_info 構造体

```cpp
// mclaglink.h:94-99
struct mclag_unique_ip_cfg_info
{
    int op_type;/*add/del mclag unique ip iface */
    char mclag_unique_ip_ifname[MAX_L_PORT_NAME];
};
```

SET → `op_type = MCLAG_CFG_OPER_ADD`、DEL → `op_type = MCLAG_CFG_OPER_DEL`。

### CLI バリデーション (config/mclag.py:327-378)

```python
# L328-330: DOMAIN チェック
if len(db.get_table('MCLAG_DOMAIN')) == 0:
    ctx.fail("MCLAG not configured.")

# L335-336: Vlan プレフィックスチェック
if not interface_name.startswith("Vlan"):
    ctx.fail("MCLAG unique ip interface %s is not a VLAN interface" % interface_name)

# L338-344: IP アドレス存在チェック
vlan_intf_table = db.get_table('VLAN_INTERFACE')
if (interface_name, '') in vlan_intf_table:
    ctx.fail("MCLAG unique ip not supported when ip address is already configured on interface %s" % interface_name)

# L346-347: VRF バインドチェック  
if interface_name in vlan_intf_table and 'vrf_name' in vlan_intf_table[interface_name]:
    ctx.fail("MCLAG unique ip not supported when VRF is already configured on interface %s" % interface_name)
```

### iccpd 接続断時の挙動

`MclagLink::accept()` (mclaglink.cpp:1851-1861) で新規ソケットを受け入れ後、
`addDomainCfgDependentSelectables()` (mclaglink.cpp:910-921) が `MCLAG_UNIQUE_IP` 購読を再登録する。
しかしその時点での CONFIG_DB 全スナップショット再送機能はない。
SubscriberStateTable は Redis keyspace notification を利用するため、接続断の間に届いた変更は再送されない。

## 結論

mclagsyncd の MCLAG_UNIQUE_IP 失敗は全て syslog のみで STATE_DB/ERROR_TABLE への記録なし。
iccpd 断後の再接続時に CONFIG_DB との同期が取れない可能性あり（既知の制限）。
