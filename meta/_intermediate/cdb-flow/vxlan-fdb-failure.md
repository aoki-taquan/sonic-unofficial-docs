# vxlan-fdb failure-behavior 調査証跡

## 調査対象
`VXLAN_FDB_TABLE` (APP_DB) — Phase D 失敗挙動

## 調査ファイル
- `sonic-swss/fdbsyncd/fdbsync.cpp`
- `sonic-swss/orchagent/fdborch.cpp`
- `sonic-swss/fdbsyncd/fdbsync.h`

---

## fdbsyncd 側の失敗パターン

### warm-restart 中の書き込み抑制
`fdbsync.cpp:580-583` (macAddVxlan), `fdbsync.cpp:609-612` (macUpdateVxlan), `fdbsync.cpp:639-642` (macDelVxlan):
```cpp
if (m_AppRestartAssist->isWarmStartInProgress())
{
    m_AppRestartAssist->insertToMap(APP_VXLAN_FDB_TABLE_NAME, key, fvs, false);
    return;
}
```
warm-restart タイマー (DEFAULT_FDBSYNC_WARMSTART_TIMER = 120 秒、`fdbsync.h:15`) が完了するまで APP_DB への直接書き込みをせずキャッシュに蓄積する。タイマー完了後の reconcile フェーズで差分のみを反映する。

### netlink イベントが VXLAN インタフェース以外の場合
`fdbsync.cpp` の `onMsgNbr()` は VXLAN インタフェースでない場合、または MAC が `00:00:00:00:00:00` の場合は `VXLAN_FDB_TABLE` に書き込まない。IMET (BUM) エントリは `APP_VXLAN_REMOTE_VNI_TABLE_NAME` に書かれる。

---

## orchagent (FdbOrch) 側の失敗パターン

### A. PortsOrch allPortsReady() ガード
`fdborch.cpp:711-713`:
```cpp
if (!m_portsOrch->allPortsReady())
{
    return;
}
```
orchagent 起動時に全ポートの SAI 作成が完了するまで、`doTask()` は early return して `m_toSync` を処理しない。`m_toSync` に蓄積されたエントリは `allPortsReady()` が true になった後のイベントループで自動処理される（自動回復あり）。

### B. VLAN 未解決 (SET)
`fdborch.cpp:739-759`:
```cpp
if (!m_portsOrch->getPort(keys[0], vlan))
{
    // SET: it++  → m_toSync 保留、次周回で再試行
}
```
SET コマンドで VLAN が PortsOrch に登録されていない場合 `it++` で次周回に持ち越し（無限ポーリング）。

### C. VLAN 未解決 (DEL)
`fdborch.cpp:742-754`:
DEL コマンドで VLAN OID が未解決の場合は vlan_id を `stoi` で取り出し `deleteFdbEntryFromSavedFDB()` を呼んで消去後に `erase(it)` で破棄。`stoi` が例外を投げた場合も `erase(it)` で破棄（再試行なし）。

### D. remote_vtep 不正 IP
`fdborch.cpp:801-808`:
```cpp
try {
    IpAddress valid_ip = IpAddress(remote_ip);
} catch(exception &e) {
    SWSS_LOG_NOTICE("Invalid IP address in remote MAC %s", remote_ip.c_str());
    remote_ip = "";
    break;
}
```
不正 IP 文字列は `remote_ip = ""` にセットして以降のフィールド走査を break する。

### E. remote_vtep が空 → 即破棄 (DIP トンネルモード)
`fdborch.cpp:838-841`:
```cpp
if (!remote_ip.length())
{
    it = consumer.m_toSync.erase(it);
    continue;
}
```
DIP トンネルサポート時に `remote_ip` が空（不正 IP 後や欠落）の場合、エントリを `m_toSync` から即破棄。再試行なし。

### F. EVPN NVO source VTEP が NULL → 即破棄 (非 DIP トンネルモード)
`fdborch.cpp:848-852`:
```cpp
VxlanTunnel* sip_tunnel = evpn_nvo_orch->getEVPNVtep();
if (sip_tunnel == NULL)
{
    it = consumer.m_toSync.erase(it);
    continue;
}
```
非 DIP モードで EVPN NVO source VTEP が未設定の場合、即破棄。再試行なし。

### G. addFdbEntry() 失敗 → m_toSync 残留
`fdborch.cpp:870-895`:
```cpp
if (addFdbEntry(entry, port, fdbData))
{
    it = consumer.m_toSync.erase(it);
}
else
    it++;
```
`addFdbEntry()` が false を返した場合（ポートが bridge port ID を持たないなど）、`it++` で次周回再試行（自動回復あり）。ただし `addFdbEntry()` 内部でポート/VLAN 解決失敗時は `saved_fdb_entries` にパークして true を返すため、実際の `it++` ループになるケースはトンネルポート SAI 生成失敗時など。

### H. SAI create_fdb_entry 失敗
`fdborch.cpp:1531-1542`:
SAI `create_fdb_entry()` が `SAI_STATUS_SUCCESS` 以外を返した場合、`handleSaiCreateStatus(SAI_API_FDB, status)` でエラーハンドリング → `parseHandleSaiStatusFailure()` で false を返す。false が `doTask()` に返ると `it++` で次周回再試行となる（エラーログ出力あり）。

### I. 既存エントリで oldPort bridge_port_id 不明
`fdborch.cpp:1341-1345`:
既存エントリの `bridge_port_id` から `getPortByBridgePortId()` が失敗した場合 `return false`。`doTask()` での `it++` により次周回再試行。

### J. 不明 OP
`fdborch.cpp:917-918`:
```cpp
SWSS_LOG_ERROR("Unknown operation type %s", op.c_str());
it = consumer.m_toSync.erase(it);
```
SET / DEL 以外の op は即破棄（再試行なし）。

---

## saved_fdb_entries パーキング機構
`fdborch.cpp:1297-1318`:
`addFdbEntry()` 内でポートが PortsOrch に未登録、または bridge_port_id が SAI_NULL_OBJECT_ID、またはポートが VLAN メンバーでない場合、エントリを `saved_fdb_entries[port_name]` にパークして `return true`（成功扱い）。後でポートが作成されると `m_portsOrch` コールバック経由で `flushedFdbEntry()` / `notifyObservers()` を通じて再試行される。

---

## ログ出力先
- orchagent 関連: `SWSS_LOG_ERROR`, `SWSS_LOG_NOTICE`, `SWSS_LOG_INFO` → `/var/log/swss/orchagent.log`
- fdbsyncd 関連: `SWSS_LOG_NOTICE` → `/var/log/swss/fdbsyncd.log`
- STATE_DB / ERROR_TABLE への失敗記録: なし（VXLAN_FDB_TABLE は APP_DB のみ）
