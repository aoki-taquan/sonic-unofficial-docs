# cdb-flow 中間ノート: VXLAN_FDB_TABLE — 書込み順依存 (Phase B)

## 調査対象

- `sonic-swss/orchagent/fdborch.cpp` — `FdbOrch::doTask(Consumer&)`
- `sonic-swss/fdbsyncd/fdbsync.cpp` — `macAddVxlan()` / `onMsgNbr()`

## 検出した順序依存

### 1. PortsOrch 全ポート初期化完了が必須

`doTask()` 冒頭で `m_portsOrch->allPortsReady()` を確認し、false なら即 return。
APP_VXLAN_FDB_TABLE_NAME のイベントは一切処理されず `m_toSync` に滞留する。
（`fdborch.cpp:710-713`）

### 2. VLAN 先行必須（SET の場合）

`doTask()` が `m_portsOrch->getPort(keys[0], vlan)` で VLAN OID を解決する。
VLAN が存在しない場合、SET は `it++` で次周回再試行（無限ポーリング）。
DEL は `deleteFdbEntryFromSavedFDB()` を呼んで `m_toSync.erase`（破棄）。
（`fdborch.cpp:736-754`）

### 3. VxlanTunnelOrch の tunnel 作成が必須（DIP サポートあり）

`isDipTunnelsSupported() == true` の場合、`tunnel_orch->getTunnelPortName(remote_ip)` で
トンネルポート名を解決する。`remote_ip` が空（バリデーション失敗）なら `m_toSync.erase` で破棄。
**再試行なし**。VXLAN_TUNNEL を先に作っておく必要がある。
（`fdborch.cpp:834-841`）

### 4. EvpnNvoOrch の source VTEP 作成が必須（DIP サポートなし）

`isDipTunnelsSupported() == false` の場合、`evpn_nvo_orch->getEVPNVtep()` が `NULL`
なら `m_toSync.erase` で破棄。**再試行なし**。
VXLAN_EVPN_NVO（NVO テーブル）を先に設定しておく必要がある。
（`fdborch.cpp:847-854`）

### 5. `remote_vtep` バリデーション

`IpAddress(remote_ip)` のコンストラクタで例外が発生した場合、`remote_ip = ""`
にセットされ、`m_toSync.erase` で破棄。rescue なし。
（`fdborch.cpp:795-808`）

## 推奨書込み順序

```
1. PortsOrch 初期化完了（orchagent 起動時に自然満足）
2. VXLAN_TUNNEL（トンネル作成）
3. VXLAN_EVPN_NVO（NVO 設定: DIP サポートなし時のみ）
4. VLAN（CONFIG_DB VLAN|VlanXXX）
5. VXLAN_FDB_TABLE エントリ（APP_DB）
```

## retry / 自動調停

- VLAN 未解決の SET: `m_toSync` に残り次周回再試行（無限ポーリング）
- VXLAN tunnel 未解決 / remote_vtep 不正: **再試行なし**、破棄

## 参照行番号

- fdborch.cpp:710-713: allPortsReady ガード
- fdborch.cpp:719-722: origin = FDB_ORIGIN_VXLAN_ADVERTIZED ハードコード
- fdborch.cpp:736-754: VLAN 解決失敗時の分岐
- fdborch.cpp:795-808: remote_vtep IpAddress バリデーション
- fdborch.cpp:834-841: DIP サポートあり tunnel 解決
- fdborch.cpp:847-854: DIP サポートなし EVPN NVO 解決
