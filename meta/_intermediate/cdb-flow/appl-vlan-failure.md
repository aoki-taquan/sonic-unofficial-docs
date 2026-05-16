# APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE — 失敗挙動 (Task F Phase D intermediate)

Task F Phase D の作業メモ。`docs/reference/config-db/appl-vlan.md` の `<!-- failure -->` ブロックに反映する元情報。

ソース:

- `sonic-swss/cfgmgr/vlanmgr.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

## 1. vlanmgrd 側の書込失敗・retry 分岐

### 1.1 VLAN MAC 未確定による全タスク保留

`doVlanTask()` の冒頭で `isVlanMacOk()` (`vlanmgr.cpp:311-314`) を呼び出し、`gMacAddress` が未初期化なら APPL_DB への書込みを一切行わず即 return。`consumer.m_toSync` は erase されないため後続 tick で再評価される（暗黙の retry）。

```cpp
// vlanmgr.cpp:316-322
void VlanMgr::doVlanTask(Consumer &consumer)
{
    if (!isVlanMacOk())
    {
        SWSS_LOG_DEBUG("VLAN mac not ready, delaying VLAN task");
        return;
    }
    ...
```

### 1.2 PORT / LAG 未準備による retry (VLAN_MEMBER)

`doVlanMemberTask()` (`vlanmgr.cpp:608-712`):

- `isMemberStateOk(port_alias)` または `isVlanStateOk(vlan_alias)` が false なら `it++; continue;` で erase せずに次 tick へ繰り越す (`L642-647`)。
- `addHostVlanMember()` が false (Linux bridge コマンド失敗 = netdev 未準備) を返した場合も同様に `it++; continue;` で retry (`L682-687`)。
- コメントに明示: `/* Other than the case of member port/lag is not ready, no retry will be performed */` (`L711`)。
- 一方、`tagging_mode` 異常値や `Unknown operation type` は `consumer.m_toSync.erase(it)` で即破棄・retry なし (`L662-664`, `L709`)。

### 1.3 Linux bridge 設定失敗時の挙動

`addHostVlanMember()` (`vlanmgr.cpp:233-273`):

- 生成コマンドは `ip link set <port> master Bridge && bridge vlan del vid 1 && bridge vlan add vid <id> dev <port> <tagging>`。
- 1 回目失敗時:
  - port_alias が `LAG_PREFIX` (`PortChannel`) で始まる場合: `return false` → retry (race condition 想定; コメント `L260-261`)。
  - それ以外 (`Ethernet*` など): `EXEC_WITH_ERROR_THROW` で再実行 (`L268`)。2 度目も失敗すると例外伝播し vlanmgrd プロセスがクラッシュ (catch されない)。

### 1.4 setHostVlanMac の bridge down/up 失敗

`setHostVlanMac()` (`vlanmgr.cpp:198-231`) は `EXEC_WITH_ERROR_THROW` を 3 回連続実行 (`bridge_down` → `set vlan/bridge address` → `bridge_up`)。中間失敗時:

- 例外で関数を抜けるが Bridge は down のままになるためデータプレーン断が発生し得る。
- 上位ハンドラ (doVlanTask) が catch せず、vlanmgrd 全体が落ちる可能性がある。

### 1.5 key 形式異常 / 無効値

- `Vlan` プレフィクスなし、数値変換失敗: `SWSS_LOG_ERROR("Invalid key format ...")` を出し `erase(it)` で即破棄 (`vlanmgr.cpp:334-346`, `L605-621`)。
- 結果として APPL_DB には何も書かれない (silent drop)。CONFIG_DB の不正エントリは検出されず残る。

## 2. portsorch 側の SAI 失敗・retry 分岐

### 2.1 VLAN_TABLE: addVlan 失敗

`doVlanTask()` (`portsorch.cpp:5785-5791`):

```cpp
if (m_portList.find(vlan_alias) == m_portList.end())
{
    if (!addVlan(vlan_alias))
    {
        it++;
        continue;   // retry
    }
}
```

`addVlan()` (`L7381-7419`) は `sai_vlan_api->create_vlan()` 失敗時に `handleSaiCreateStatus(SAI_API_VLAN, status)` で SAI ステータスを分類:

- `task_success` 以外 → `parseHandleSaiStatusFailure(handle_status)` を返す。これは `task_need_retry` なら true 返却で続行、`task_failed` なら false 返却で外側 `it++; continue;` により retry ループへ。

### 2.2 VLAN_TABLE: createVlanHostIntf 失敗

`host_ifname` 指定時に `createVlanHostIntf()` が失敗した場合 (`portsorch.cpp:5822-5828`): retry せず `erase(it)` で破棄。コメント `// No need to fail in case of error as this is for monitoring VLAN.` の通り、host interface は付帯機能扱い。

### 2.3 VLAN_TABLE: removeVlan の retry 条件

`removeVlan()` (`portsorch.cpp:7421-7488`) は次のいずれかで `return false` → 外側で `it++` retry (`L5844-5847`):

| 条件 | コード | 意味 |
|------|-------|------|
| `vlan.m_fdb_count > 0` | `L7427-7431` | FDB エントリ残存 → fdborch 削除待ち |
| `m_port_ref_count > 0` | `L7433-7439` | RIF など参照中 |
| `vlan.m_members.size() > 0` | `L7442-7446` | メンバ未削除 |
| `vlan.m_vnid != VNID_NONE` | `L7449-7454` | VLAN-VNI マッピング残存 |
| `removeVlanHostIntf` 失敗 | `L7457-7461` | host intf 残存 |
| `sai_vlan_api->remove_vlan()` 失敗 | `L7469-7480` | SAI ステータス次第で retry / failure |

これらは VLAN_TABLE DEL がブロックされる典型原因。

### 2.4 VLAN_MEMBER_TABLE: PORT 未準備 retry

`doVlanMemberTask()` (`portsorch.cpp:5857-5972`):

- `getPort(vlan_alias)` 失敗 → `it++; continue;` retry (`L5900-5905`)。
- `getPort(port_alias)` 失敗 → `it++; continue;` retry (`L5907-5912`)。`SWSS_LOG_DEBUG("%s is not not yet created, delaying", ...)`。

### 2.5 VLAN_MEMBER_TABLE: 不正 tagging_mode

`tagging_mode` が `untagged`/`tagged`/`priority_tagged` 以外 → `SWSS_LOG_ERROR("Wrong tagging_mode ...")` + `erase(it)` で即破棄、retry なし (`L5924-5931`)。

### 2.6 VLAN_MEMBER_TABLE: addBridgePort / addVlanMember 失敗

```cpp
// portsorch.cpp:5940-5943
if (addBridgePort(port) && addVlanMember(vlan, port, tagging_mode))
    it = consumer.m_toSync.erase(it);
else
    it++;   // retry
```

- `addBridgePort()` (`L7189-`): `sai_bridge_api->create_bridge_port()` 失敗時に `handleSaiCreateStatus(SAI_API_BRIDGE, status)` 経由で retry / failure 判定 (`L7258-7268`)。port_type 不正の場合は `return false`。
- `addVlanMember()` (`L7511-7589`):
  - `end_point_ip` 指定で `SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED` capability 不在 → `SWSS_LOG_ERROR("Flood group with end point ip is not supported"); return false;` (`L7515-7524`)。外側で永続的に retry し続ける (前進せず stuck)。
  - `sai_vlan_api->create_vlan_member()` 失敗 → `handleSaiCreateStatus` で retry / failure 判定 (`L7554-7563`)。
  - `setPortPvid()` 失敗 (untagged 時のみ) → `return false` (`L7568-7574`)。

### 2.7 VLAN_MEMBER_TABLE: removeVlanMember 失敗

`removeVlanMember()` が false → `it++` retry (`L5949-5959`)。SAI remove 失敗・end_point_ip 経路の各種 SAI set 失敗が原因。

## 3. retry セマンティクスの違いまとめ

| 層 | 一時失敗 (retry) | 永続失敗 (erase / drop) |
|---|---|---|
| vlanmgrd VLAN | mac 未確定で関数全体保留 | key 形式不正は即 erase |
| vlanmgrd VLAN_MEMBER | port/lag/VLAN 未準備、`addHostVlanMember` 失敗 (LAG 限定) | 不正 tagging_mode、`Unknown operation`、`Ethernet*` の bridge 失敗 2 回目は例外伝播 |
| portsorch VLAN | `addVlan` SAI retryable、`removeVlan` の fdb/ref/member/vnid/host_intf 残存 | createVlanHostIntf 失敗、key 形式不正、SAI が non-retryable |
| portsorch VLAN_MEMBER | port/vlan 未取得、`addBridgePort`/`addVlanMember` SAI retryable、`removeVlanMember` SAI retryable | 不正 tagging_mode、duplicate (NOP erase)、`end_point_ip` + capability 不在は実質永続 stuck |

## 4. ドキュメント反映方針

`<!-- failure -->` ブロックは「書込みが失敗・retry される代表ケース」を表形式で簡潔に。詳細は本ファイル (intermediate) へ参照リンク。
