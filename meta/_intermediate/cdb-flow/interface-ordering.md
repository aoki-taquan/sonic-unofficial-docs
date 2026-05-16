# INTERFACE テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-16 (VLAN/LAG 先行・kernel netlink 発行順序を追記)
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

---

## 1. 他テーブル先行必須

### PORT / LAG / VLAN が STATE_DB で ready になること

`intfmgrd` は `doIntfGeneralTask()` 冒頭で `isIntfStateOk(alias)` を呼ぶ。
`isIntfStateOk()` はインタフェース名プレフィクスで確認先テーブルを切り替える（`intfmgr.cpp` L649–710）:

| プレフィクス | 確認先 STATE_DB | 行 |
|------------|----------------|-----|
| `Vlan` | `STATE_VLAN_TABLE` | L653 |
| `PortChannel` (LAG) | `STATE_LAG_TABLE` | L661 |
| `Vnet` | `STATE_VRF_TABLE` | L669 |
| `Vrf` / `mgmt` | `STATE_VRF_TABLE` | L677 |
| `Ethernet` (PORT) | `STATE_PORT_TABLE` | L686 |
| `Loopback` | 常に true | L696 |

```cpp
// intfmgr.cpp:831-837
if (op == SET_COMMAND)
{
    if (!isIntfStateOk(parentAlias.empty() ? alias : parentAlias))
    {
        SWSS_LOG_DEBUG("Interface is not ready, skipping %s", alias.c_str());
        return false;
    }
```

- **PORT テーブル書込み前に INTERFACE を書いても適用されない**。portmgrd が STATE_DB に `state=ok` を書くまで retry。
- **PORTCHANNEL (LAG) が STATE_LAG_TABLE に登録される前に LAG_INTERFACE を書いても適用されない**。lagmgrd が STATE_DB に書くまで retry。
- **VLAN が STATE_VLAN_TABLE に登録される前に VLAN_INTERFACE を書いても適用されない**。vlanmgrd が STATE_DB に書くまで retry。

### VRF が STATE_DB で ready になること

`vrf_name` が指定された場合、同じく `isIntfStateOk(vrf_name)` で VRF の STATE_DB エントリを確認する。

```cpp
// intfmgr.cpp:839-842
if (!vrf_name.empty() && !isIntfStateOk(vrf_name))
{
    SWSS_LOG_DEBUG("VRF is not ready, skipping %s", vrf_name.c_str());
    return false;
}
```

**VRF テーブル書込み前に `INTERFACE|<port>` に `vrf_name` をセットしても適用されない。**

### orchagent 側の VRF 確認

`intfsorch.cpp` の `doTask()` でも `m_vrfOrch->isVRFexists(vrf_name)` を確認し、存在しなければキューに戻す（L826-830）。CONFIG_DB → APP_DB を超えた二段階の依存がある。

### IP プレフィクスロウは L3 enable 行が先

`doIntfAddrTask()` で `isIntfCreated(alias)` を確認する。`isIntfCreated()` は STATE_DB `STATE_INTERFACE_TABLE` に alias エントリが存在するかで判断する。

```cpp
// intfmgr.cpp:1115
if (!isIntfStateOk(alias) || !isIntfCreated(alias))
{
    SWSS_LOG_DEBUG("Interface is not ready, skipping %s", alias.c_str());
    return false;
}
```

**`INTERFACE|<port>` (L3 enable 行) を先に SET し、intfmgrd が STATE_INTERFACE_TABLE に書いた後でなければ、`INTERFACE|<port>|<ip_prefix>` は適用されない。**

---

## 2. SET 後 DEL 順依存

### L3 enable 行の DEL はすべての IP プレフィクスロウ削除が先

```cpp
// intfmgr.cpp:1058-1063
/* make sure all ip addresses associated with interface are removed */
if (getIntfIpCount(alias))
{
    return false;
}
```

IP カウントが 0 でなければ DEL を受け付けない → retry。
**手順: すべての `INTERFACE|<port>|<ip_prefix>` を DEL してから `INTERFACE|<port>` を DEL。**

### VRF 変更は 2 ステップ必須

同じ VRF 名が設定済みの場合に別 VRF へ直接変更しようとすると `isIntfChangeVrf()` が `true` を返し、エラーログを出してスキップされる（return true = エントリは erase されるが SAI に反映しない）。

```cpp
// intfmgr.cpp:846-849
if (isIntfChangeVrf(alias, vrf_name))
{
    SWSS_LOG_ERROR("%s can not change to %s directly, skipping", alias.c_str(), vrf_name.c_str());
    return true;
}
```

**手順: `vrf_name` を空に SET（unbind）→ 新 VRF を SET（rebind）の 2 ステップ。**

---

## 3. Notification（通知）順

### STATE_PORT_TABLE Notification トリガ

`intfmgrd` コンストラクタで `SubscriberStateTable(stateDb, STATE_PORT_TABLE_NAME)` と `SubscriberStateTable(stateDb, STATE_LAG_TABLE_NAME)` を購読している（intfmgr.cpp L45-52）。

portmgrd が PORT `state=ok` を STATE_DB に書くと、intfmgrd の `doPortTableTask` がトリガされ、ペンディング中の INTERFACE エントリが retry される。
LAG も同様（`STATE_LAG_TABLE_NAME`、delay=200 ms）。

### APP_INTF_TABLE への通知順序

intfmgrd は L3 enable 行の処理完了後に `m_appIntfTableProducer.set(alias, data)` を呼ぶ（L1053）。
IP プレフィクスロウは L3 enable 行の APP_DB 書込み後に自動 retry される流れだが、コード上は独立した doTask ループで処理されるため、**CONFIG_DB への書込み順序は L3 enable 行 → IP プレフィクスロウの順が推奨**（逆順でも retry で最終収束するが収束が遅れる）。

---

## 4. warm-reboot 影響

### `buildIntfReplayList()` と `m_pendingReplayIntfList`

warm-start 時、intfmgrd は初期化時に `buildIntfReplayList()` を呼び、CONFIG_DB の `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` のキーを `m_pendingReplayIntfList` に積む（intfmgr.cpp L274-283）。

リストが空になった時点で `setWarmReplayDoneState()` を呼び、`WarmStart::REPLAYED` → `WarmStart::RECONCILED` と即遷移する（L289-292）。**reconciliation ロジックはなく、カーネルへの再 replay で完了とみなされる。**

### `ipv6_use_link_local_only` はメモリ状態がリセットされる

`m_ipv6LinkLocalModeList` は in-memory の `std::set`。warm-reboot 後は空に戻るため、CONFIG_DB の `ipv6_use_link_local_only: enable` エントリが replay されて再 SET されない限り、link-local モードは失われる。warm-reboot 後の replay で CONFIG_DB 内容が再処理されれば収束するが、**replay 完了前に IP プレフィクスロウを処理しようとすると `isIntfCreated()` 失敗で retry に入ることがある。**

### cold restart（通常再起動）

cold restart では `flushLoopbackIntfs()` を呼び、Loopback インタフェースをすべてカーネルから削除してから再作成する（L57）。INTERFACE エントリは再処理されるため、PORT STATE_DB ready の通知を待ってから処理が進む（通常と同じ順序依存）。

---

## 5. kernel netlink コマンド発行順序

`doIntfGeneralTask()` SET パス内（`intfmgr.cpp` L831–1054）での実際の発行順:

```
Step  コマンド / 操作                                        条件
1     isIntfStateOk(port/LAG/VLAN)                         always — 未 ready なら return false
2     isIntfStateOk(vrf_name)                              vrf_name 指定時のみ
3     isIntfChangeVrf() 確認                               always — VRF 直接変更をブロック
4     ip link add <alias> link <parent> type vlan id <id>  サブインタフェース新規作成時
5     ip link set <alias> mtu <mtu>                        サブ IF かつ mtu 指定時
      (min(parent_mtu, config_mtu) を適用)
6     ip link set <alias> master <vrf>                     vrf_name 指定時
      または ip link set <alias> nomaster                  VRF 除去時 (vrf_name 空)
7     ip link set <alias> address <mac>                    mac_addr 指定時
8     sysctl net.mpls.conf.<alias>.input=1/0               mpls=enable/disable 時
9     echo N > /proc/sys/net/ipv4/conf/<alias>/proxy_arp   proxy_arp 指定時
10    echo N > /proc/sys/net/ipv4/conf/<alias>/arp_accept  grat_arp 指定時
11    m_appIntfTableProducer.set(alias, data)               always — APP_DB INTF_TABLE
12    m_stateIntfTable.hset(alias, "vrf", vrf_name)         always — STATE_DB 更新
```

`doIntfAddrTask()` SET パス（`intfmgr.cpp` L1099–1170）:

```
Step  コマンド / 操作                                        条件
1     isIntfStateOk(alias) && isIntfCreated()              always — 属性ロウ完了確認
2a    ip address add <ip/plen> [broadcast <bcast>] dev <alias>
                                                           IPv4 (/31 未満は broadcast 付き)
2b    ip -6 address add <ip/plen> [broadcast <bcast>] dev <alias> [metric 256]
                                                           IPv6 (VoQ 時は metric 256 付与)
3     enableIpv6Flag() + retry                             IPv6 add 失敗時のみ
4     m_appIntfTableProducer.set(appKey, {scope, family})  always — APP_DB
5     m_stateIntfTable.hset("<alias>|<ip>", "state", "ok") always — STATE_DB
```

**VRF binding (Step 6) は IP 付与 (doIntfAddrTask Step 2) より必ず先に完了する。**
属性ロウ処理が STATE_DB に完了を書いた後でなければ `isIntfCreated()` を通過しない。

---

## 6. まとめ（書込み順依存一覧）

| 依存カテゴリ | 必須順序 | ソース |
|------------|---------|-------|
| PORT → INTERFACE | `PORT` エントリ + portmgrd の STATE_DB `STATE_PORT_TABLE` が先 | `intfmgr.cpp:686-695` |
| PORTCHANNEL → LAG_INTERFACE | `PORTCHANNEL` + lagmgrd の STATE_DB `STATE_LAG_TABLE` が先 | `intfmgr.cpp:661-667` |
| VLAN → VLAN_INTERFACE | `VLAN` + vlanmgrd の STATE_DB `STATE_VLAN_TABLE` が先 | `intfmgr.cpp:653-660` |
| VRF → INTERFACE | `VRF` エントリ + vrfmgrd の STATE_DB ready が先 | `intfmgr.cpp:839-842` |
| VRF binding → IP 付与 | ip link set master → ip address add の順 | doIntfGeneralTask L1007→ doIntfAddrTask L1121 |
| L3 enable → IP prefix | `INTERFACE|<port>` SET → STATE_DB 反映後に `INTERFACE|<port>|<ip>` SET | `intfmgr.cpp:1115` |
| IP prefix DEL → L3 enable DEL | すべての IP prefix ロウを DEL してから L3 enable 行を DEL | `intfmgr.cpp:1060-1063` |
| VRF 変更 2 ステップ | unbind (`ip link set nomaster`) → rebind (`ip link set master`) | `intfmgr.cpp:846-849` |
| warm-reboot replay | PORT/LAG/VLAN STATE_DB ready 後に INTERFACE replay 収束 | `intfmgr.cpp:286-292` |
