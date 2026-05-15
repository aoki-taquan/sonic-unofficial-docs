# INTERFACE テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-14
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

---

## 1. 他テーブル先行必須

### PORT / LAG が STATE_DB で `state=ok` になること

`intfmgrd` は `doIntfGeneralTask()` 冒頭で `isIntfStateOk(alias)` を呼ぶ。
内部で `m_statePortTable.get(alias, temp)` / `m_stateLagTable.get(alias, temp)` し、エントリが存在しなければ `return false` → Consumer キューに残す。

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

**PORT テーブル書込み前に INTERFACE を書いても適用されない。portmgrd が STATE_DB に `state=ok` を書くまで retry。**

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

## 5. まとめ（書込み順依存一覧）

| 依存カテゴリ | 必須順序 | ソース |
|------------|---------|-------|
| PORT → INTERFACE | `PORT` エントリ + portmgrd の STATE_DB `state=ok` が先 | `intfmgr.cpp:833-837` |
| VRF → INTERFACE | `VRF` エントリ + vrfmgrd の STATE_DB ready が先 | `intfmgr.cpp:839-842` |
| L3 enable → IP prefix | `INTERFACE|<port>` SET → STATE_DB 反映後に `INTERFACE|<port>|<ip>` SET | `intfmgr.cpp:1115` |
| IP prefix DEL → L3 enable DEL | すべての IP prefix ロウを DEL してから L3 enable 行を DEL | `intfmgr.cpp:1060-1063` |
| VRF 変更 2 ステップ | unbind (vrf_name="") → rebind (vrf_name=新VRF) | `intfmgr.cpp:846-849` |
| warm-reboot replay | PORT STATE_DB ready 後に INTERFACE replay 収束 | `intfmgr.cpp:286-292` |
