# PORTCHANNEL_INTERFACE テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-16
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

---

## 1. 他テーブル先行必須

### PORTCHANNEL が STATE_DB で ready になること

`intfmgrd` の `isIntfStateOk()` は `PortChannel` プレフィクスを検知すると `STATE_LAG_TABLE` を確認する（`intfmgr.cpp:661-667`）。

```cpp
// intfmgr.cpp:661-667
else if (!alias.compare(0, strlen(LAG_PREFIX), LAG_PREFIX))
{
    if (m_stateLagTable.get(alias, temp))
    {
        SWSS_LOG_DEBUG("Lag %s is ready", alias.c_str());
        return true;
    }
}
```

**PORTCHANNEL テーブル書込み + lagmgrd による `STATE_LAG_TABLE` 登録が完了する前に `PORTCHANNEL_INTERFACE` を書いても適用されない。**

### VRF が STATE_DB で ready になること

`vrf_name` 指定時、`isIntfStateOk(vrf_name)` で `STATE_VRF_TABLE` を確認する（`intfmgr.cpp:839-842`）。

### orchagent 側の LAG 確認

`intfsorch.cpp:905-924` で `gPortsOrch->getPort(alias, port)` が false → `m_toSync` 残留・retry。CONFIG_DB → APP_DB を超えた二段階の依存がある。

### IP プレフィクスロウは属性ロウが先

`doIntfAddrTask()` で `isIntfCreated(alias)` を確認する（`intfmgr.cpp:1115`）。`isIntfCreated()` は `STATE_INTERFACE_TABLE` にエントリが存在するかで判断する。

---

## 2. 属性適用順序 (kernel netlink)

`doIntfGeneralTask()` SET パス（`intfmgr.cpp` L831–1054）:

```
Step  コマンド / 操作                                     条件
1     isIntfStateOk("PortChannel*") ガード               STATE_LAG_TABLE 確認
2     isIntfStateOk(vrf_name) ガード                     vrf_name 指定時のみ
3     isIntfChangeVrf() 確認                             直接 VRF 変更をブロック
4     ip link set <alias> master <vrf>                  vrf_name 指定時
      または ip link set <alias> nomaster               VRF 除去時
5     ip link set <alias> address <mac>                 mac_addr 指定時
6     sysctl net.mpls.conf.<alias>.input=1/0            mpls=enable/disable 時
7     m_appIntfTableProducer.set(alias, data)           APP_DB INTF_TABLE SET
8     m_stateIntfTable.hset(alias, "vrf", vrf_name)    STATE_DB 書込み
```

**注意**: PORTCHANNEL_INTERFACE ではサブインタフェース生成（`ip link add ... type vlan`）は発生しない。`mtu` フィールドも読み取られない（PORTCHANNEL テーブル側で管理）。

---

## 3. SET 後 DEL 順依存

```
DEL 順序: PORTCHANNEL_INTERFACE|<name>|<ip_prefix> → PORTCHANNEL_INTERFACE|<name>
```

`intfmgr.cpp:1058-1063`:
```cpp
if (getIntfIpCount(alias))
{
    return false;
}
```

VRF 変更は 2 ステップ必須（`intfmgr.cpp:846-849`）:
1. `vrf_name=""` で unbind (`ip link set nomaster`)
2. 新 VRF で rebind (`ip link set master <vrf>`)

---

## 4. Notification 順序

`intfmgrd` コンストラクタで `SubscriberStateTable(stateDb, STATE_LAG_TABLE_NAME)` を購読（pri=200）。lagmgrd が PORTCHANNEL の `state=ok` を STATE_DB に書くと `doPortTableTask` がトリガされ、ペンディング中の `PORTCHANNEL_INTERFACE` エントリが再処理される。

---

## 5. warm-reboot 影響

`buildIntfReplayList()` で `m_cfgLagIntfTable.getKeys()` の結果を `m_pendingReplayIntfList` に収集（`intfmgr.cpp:276`）。replay 完了で `REPLAYED` → `RECONCILED`（reconciliation ロジックなし）。

---

## 6. まとめ（書込み順依存一覧）

| 依存カテゴリ | 必須順序 | ソース |
|------------|---------|-------|
| PORTCHANNEL → PORTCHANNEL_INTERFACE | `PORTCHANNEL` + lagmgrd の STATE_LAG_TABLE ready が先 | `intfmgr.cpp:661-667` |
| VRF → PORTCHANNEL_INTERFACE | `VRF` + vrfmgrd の STATE_VRF_TABLE ready が先 | `intfmgr.cpp:839-842` |
| orchagent LAG 確認 | PortsOrch に LAG オブジェクトが登録済みであること | `intfsorch.cpp:905-924` |
| 属性ロウ → IP prefix | `PORTCHANNEL_INTERFACE|<name>` SET → STATE_INTF 反映後に IP prefix SET | `intfmgr.cpp:1115` |
| IP prefix DEL → 属性ロウ DEL | すべての IP prefix を DEL してから属性ロウを DEL | `intfmgr.cpp:1060-1063` |
| VRF 変更 2 ステップ | unbind (vrf_name="") → rebind (vrf_name=新VRF) | `intfmgr.cpp:846-849` |
| warm-reboot replay | LAG STATE_DB ready 後に PORTCHANNEL_INTERFACE replay 収束 | `intfmgr.cpp:276, 286-292` |
