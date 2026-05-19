# VXLAN_FDB_TABLE — Phase C 暗黙参照抽出ノート

ソース: `sonic-swss/orchagent/fdborch.cpp`  
対象ページ: `docs/reference/config-db/vxlan-fdb.md`  
抽出日: 2026-05-19

## 抽出した暗黙参照

### 1. PortsOrch (PORT テーブル群)

- **参照箇所**: `fdborch.cpp:711-714`
- **参照方法**: `m_portsOrch->allPortsReady()` — `doTask()` 冒頭のグローバルガード
- **依存関係**: 全 PORT の SAI 作成完了まで `APP_VXLAN_FDB_TABLE` のイベントは一切処理されず `m_toSync` に滞留する。PortsOrch 初期化は orchagent 起動時に自然に満足される。

### 2. VLAN (PortsOrch)

- **参照箇所**: `fdborch.cpp:739-759`
- **参照方法**: `m_portsOrch->getPort(keys[0], vlan)` — key の VlanName 部分から VLAN OID を解決する
- **依存関係**: VLAN が PortsOrch に登録されていない場合、SET イベントは `it++` で次周回に再試行（無限ポーリング）。DEL イベントは `deleteFdbEntryFromSavedFDB()` を呼んで `m_toSync.erase` で破棄される。

### 3. VxlanTunnelOrch (VXLAN_TUNNEL)

- **参照箇所**: `fdborch.cpp:834,836,843,883,890`
- **参照方法**: `gDirectory.get<VxlanTunnelOrch*>()` → `isDipTunnelsSupported()` / `getTunnelPortName(remote_ip)`
- **依存関係**: DIP トンネルサポートモード (`isDipTunnelsSupported() == true`) の場合、`remote_vtep` が空文字列ならば `m_toSync.erase` で**即破棄**（再試行なし）。`getTunnelPortName()` は VxlanTunnelOrch が VXLAN_TUNNEL エントリを処理し VTEP を作成済みである必要がある。

### 4. EvpnNvoOrch (VXLAN_EVPN_NVO)

- **参照箇所**: `fdborch.cpp:847-854`
- **参照方法**: `gDirectory.get<EvpnNvoOrch*>()` → `evpn_nvo_orch->getEVPNVtep()` — source VTEP オブジェクトを取得する
- **依存関係**: DIP トンネル非サポートモード (`isDipTunnelsSupported() == false`) の場合に参照。`getEVPNVtep()` が NULL を返す（VXLAN_EVPN_NVO 未作成）場合は `m_toSync.erase` で**即破棄**（再試行なし）。

## 依存解決順序まとめ

```
PORT (PortsOrch) ──→ (allPortsReady ガード)
VLAN (PortsOrch) ──→ VXLAN_FDB_TABLE 処理可能
VXLAN_TUNNEL    ──→ VxlanTunnelOrch が VTEP 作成 [DIP モード必須]
VXLAN_EVPN_NVO  ──→ EvpnNvoOrch が source VTEP 登録 [非DIPモード必須]
```

削除は依存関係が逆転しないため順不同。ただし VXLAN_FDB エントリを先にクリアしてからトンネルを削除するのが安全。

## ページ適用状況

- `docs/reference/config-db/vxlan-fdb.md` に `<!-- cross-refs -->` ブロックとして追加。
