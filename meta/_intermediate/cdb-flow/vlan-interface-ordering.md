# VLAN_INTERFACE テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-15
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

---

## 1. 他テーブル先行必須

### VLAN が STATE_DB で ready になること

`intfmgrd` は `doIntfGeneralTask()` 冒頭で `isIntfStateOk(alias)` を呼ぶ。
VLAN_INTERFACE の alias が `Vlan` プレフィクスであるため、内部で `m_stateVlanTable.get(alias, temp)` を呼び、エントリが存在しなければ `return false` → Consumer キューに残す（retry）。

```cpp
// intfmgr.cpp:649-660
bool IntfMgr::isIntfStateOk(const string &alias)
{
    if (!alias.compare(0, strlen(VLAN_PREFIX), VLAN_PREFIX))
    {
        if (m_stateVlanTable.get(alias, temp))
        {
            SWSS_LOG_DEBUG("Vlan %s is ready", alias.c_str());
            return true;
        }
    }
    ...
    return false;
}
```

**VLAN テーブル書込み（`VLAN|Vlan<N>`）+ vlanmgrd による STATE_VLAN_TABLE 登録が完了する前に VLAN_INTERFACE を書いても適用されない。**

### VRF が STATE_DB で ready になること

`vrf_name` が指定された場合、`isIntfStateOk(vrf_name)` で VRF の STATE_DB エントリを確認する。

```cpp
// intfmgr.cpp:839-842
if (!vrf_name.empty() && !isIntfStateOk(vrf_name))
{
    SWSS_LOG_DEBUG("VRF is not ready, skipping %s", vrf_name.c_str());
    return false;
}
```

**`VRF` テーブル書込み + vrfmgrd の STATE_VRF_TABLE 登録が完了する前に `vrf_name` を持つ VLAN_INTERFACE を書いても適用されない。**

### orchagent 側の VNET 確認

`intfsorch.cpp` の `doTask()` では `vnet_name` が指定されている場合に `vnet_orch->isVnetExists(vnet_name)` を確認し、存在しなければキューに戻す（intfsorch.cpp:933-939）。
`vnet_name` を使う場合は VNetOrch が VNET エントリを処理済みである必要がある。

### orchagent 側の Port（VLAN）確認

`intfsorch.cpp` の `doTask()` では `gPortsOrch->getPort(alias, port)` で VLAN ポートオブジェクトの存在を確認する（intfsorch.cpp:905）。
PortsOrch が VLAN オブジェクトを作成していない場合はキューに戻す（CONFIG_DB → APP_DB を超えた二段階の依存）。

---

## 2. 属性ロウ → IP プレフィクスロウ の順序依存

`doIntfAddrTask()` で `isIntfCreated(alias)` を確認する。`isIntfCreated()` は STATE_DB `STATE_INTERFACE_TABLE` に alias エントリが存在するかで判断する。

```cpp
// intfmgr.cpp:1112-1118
/*
 * Don't proceed if port/LAG/VLAN/subport and intfGeneral is not ready yet.
 * The pending task will be checked periodically and retried.
 */
if (!isIntfStateOk(alias) || !isIntfCreated(alias))
{
    SWSS_LOG_DEBUG("Interface is not ready, skipping %s", alias.c_str());
    return false;
}
```

`isIntfCreated()` の実装:

```cpp
// intfmgr.cpp:295-306
bool IntfMgr::isIntfCreated(const string &alias)
{
    vector<FieldValueTuple> temp;
    if (m_stateIntfTable.get(alias, temp))
    {
        SWSS_LOG_DEBUG("Intf %s is ready", alias.c_str());
        return true;
    }
    return false;
}
```

intfmgrd は属性ロウ（`VLAN_INTERFACE|Vlan<N>`）を処理完了後に `m_stateIntfTable.hset(alias, "vrf", vrf_name)` を書く（intfmgr.cpp:1054）。

**`VLAN_INTERFACE|Vlan<N>` (属性ロウ) を先に SET し、intfmgrd が STATE_INTERFACE_TABLE に書いた後でなければ、`VLAN_INTERFACE|Vlan<N>|<ip_prefix>` は適用されない。逆順でも retry で最終収束するが収束が遅れる。**

---

## 3. SET 後 DEL 順依存

### 属性ロウの DEL はすべての IP プレフィクスロウ削除が先

```cpp
// intfmgr.cpp:1058-1063
/* make sure all ip addresses associated with interface are removed */
if (getIntfIpCount(alias))
{
    return false;
}
```

IP カウントが 0 でなければ DEL を受け付けない → retry。
**手順: すべての `VLAN_INTERFACE|Vlan<N>|<ip_prefix>` を DEL してから `VLAN_INTERFACE|Vlan<N>` を DEL。**

### VRF 変更は 2 ステップ必須

```cpp
// intfmgr.cpp:846-849
if (isIntfChangeVrf(alias, vrf_name))
{
    SWSS_LOG_ERROR("%s can not change to %s directly, skipping", alias.c_str(), vrf_name.c_str());
    return true;
}
```

**手順: `vrf_name` を空に SET（unbind）→ 新 VRF を SET（rebind）の 2 ステップ。直接変更は SWSS_LOG_ERROR が記録され SAI には反映されない。**

---

## 4. warm-reboot 影響

### `buildIntfReplayList()` に VLAN_INTERFACE が含まれる

warm-start 時、intfmgrd は `buildIntfReplayList()` で `m_cfgVlanIntfTable.getKeys()` の結果を `m_pendingReplayIntfList` に追加する（intfmgr.cpp:277-278）。

```cpp
// intfmgr.cpp:277-278
m_cfgVlanIntfTable.getKeys(intfList);
std::copy(intfList.begin(), intfList.end(), std::inserter(m_pendingReplayIntfList, ...));
```

リストが空になった時点で `setWarmReplayDoneState()` を呼び `REPLAYED` → `RECONCILED` と遷移する。**reconciliation ロジックはなく、カーネルへの再 replay で完了とみなされる。**

### `ipv6_use_link_local_only` はメモリ状態がリセットされる

`m_ipv6LinkLocalModeList` は in-memory の `std::set`。warm-reboot 後は空に戻るため、CONFIG_DB の `ipv6_use_link_local_only: enable` エントリが replay されて再 SET されない限り、link-local モードは失われる。warm-reboot 後の replay で CONFIG_DB 内容が再処理されれば収束する。

---

## 5. まとめ（書込み順依存一覧）

| 依存カテゴリ | 必須順序 | ソース |
|------------|---------|-------|
| VLAN → VLAN_INTERFACE | `VLAN` エントリ + vlanmgrd の STATE_VLAN_TABLE ready が先 | `intfmgr.cpp:653-660` |
| VRF → VLAN_INTERFACE | `VRF` エントリ + vrfmgrd の STATE_VRF_TABLE ready が先 | `intfmgr.cpp:839-842` |
| VNET → VLAN_INTERFACE | VNetOrch が VNET 処理済みであること | `intfsorch.cpp:933-939` |
| 属性ロウ → IP prefix | `VLAN_INTERFACE|Vlan<N>` SET → STATE_INTF 反映後に `VLAN_INTERFACE|Vlan<N>|<ip>` SET | `intfmgr.cpp:1115` |
| IP prefix DEL → 属性ロウ DEL | すべての IP prefix を DEL してから属性ロウを DEL | `intfmgr.cpp:1060-1063` |
| VRF 変更 2 ステップ | unbind (vrf_name="") → rebind (vrf_name=新VRF) | `intfmgr.cpp:846-849` |
| warm-reboot replay | VLAN STATE_DB ready 後に VLAN_INTERFACE replay 収束 | `intfmgr.cpp:277-278, 286-292` |
