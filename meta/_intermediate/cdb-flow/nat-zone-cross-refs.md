# nat-zone — Phase C 暗黙参照テーブルスキャンノート

対象ページ: `docs/reference/config-db/nat-zone.md`
対象フィールド: `nat_zone` (INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE / LOOPBACK_INTERFACE)
処理系: `natmgrd` (`NatMgr`) / `orchagent` (`IntfsOrch`)
スキャン範囲: `natmgr.cpp:isPortStateOk/isIntfStateOk/doNatZoneIntfTask(L7380-7720)` / `intfsorch.cpp:doTask(L660-990)`

---

## 検出した暗黙参照

### 1. STATE_PORT_TABLE / STATE_LAG_TABLE / STATE_VLAN_TABLE (STATE_DB) — natmgrd

`isPortStateOk(port)` (`natmgr.cpp:96-131`) が参照。
- `Vlan` prefix → `m_stateVlanTable.get(port, temp)` = `STATE_VLAN_TABLE_NAME`
- `PortChannel` prefix → `m_stateLagTable.get(port, temp)` = `STATE_LAG_TABLE_NAME`
- `Ethernet` prefix → `m_statePortTable.get(port, temp)` = `STATE_PORT_TABLE_NAME`

`doNatZoneIntfTask` のゾーン単位エントリ（key サイズ 1）SET 処理時、Loopback 以外のインタフェースは `isPortStateOk()` が false の間 `it++; continue` でキューに残す（`natmgr.cpp:7493-7499`）。

### 2. STATE_INTERFACE_TABLE (STATE_DB) — natmgrd

`isIntfStateOk(interface)` (`natmgr.cpp:135-145`) が参照。
`m_stateInterfaceTable.get(interface, temp)` = `STATE_INTERFACE_TABLE_NAME`

IP プレフィックス付きエントリ（key サイズ 2）の SET 処理時に参照（`natmgr.cpp:7595-7601`）。インタフェースが STATE_DB に出現するまで再キュー。

### 3. `m_natIpInterfaceInfo` 内部キャッシュ — natmgrd

同一 `doNatZoneIntfTask` 関数内で、IP プレフィックス付きエントリ（key サイズ 2）の SET が `m_natIpInterfaceInfo[port]` に追加される（`natmgr.cpp:7622-7628`）。ゾーン単位エントリのゾーン変更時（`natmgr.cpp:7532-7568`）は、このキャッシュの存在確認で Static / Dynamic NAT ルールの再構築を制御する。
- キャッシュあり → `removeStaticNatIptables()` / `addStaticNatIptables()` 等を呼び出す
- キャッシュなし → mangle iptables のみ更新

### 4. `gPortsOrch->allPortsReady()` — orchagent (IntfsOrch)

`IntfsOrch::doTask()` (`intfsorch.cpp:665-668`) の冒頭ガード。`PortsOrch` が保持する内部フラグ（全 PORT_TABLE エントリの orchagent 処理完了を示す）が false の間、`nat_zone` を含む全 INTERFACE テーブルイベントの SAI 書き込みをスキップ。

### 5. `gIsNatSupported` グローバルフラグ — orchagent (IntfsOrch)

`intfsorch.cpp:978` で参照。初期化時に `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` をクエリし、`0` の場合 `gIsNatSupported = false` となる。`nat_zone_id` の SAI 設定（`setRouterIntfsNatZoneId()`）はこのフラグが false の場合 `SWSS_LOG_NOTICE` のみで実行されない。

---

## 暗黙参照テーブルまとめ

| 依存方向 | 参照元 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---------|--------|--------------|--------------|---------|------|
| natmgrd → STATE_DB | `isPortStateOk()` | `STATE_PORT_TABLE` / `STATE_LAG_TABLE` / `STATE_VLAN_TABLE` | `<port_name>` | Ethernet/PortChannel/Vlan の nat_zone 設定前にポートが STATE_DB に登録されている必要あり。未登録の場合 `it++; continue` で再キュー | `natmgr.cpp:96-131`, `natmgr.cpp:7493-7499` |
| natmgrd → STATE_DB | `isIntfStateOk()` | `STATE_INTERFACE_TABLE` | `<intf>\|<ip>/<prefix>` | IP プレフィックス付きエントリ処理前にインタフェースが STATE_DB に登録されている必要あり。未登録の場合再キュー | `natmgr.cpp:135-145`, `natmgr.cpp:7595-7601` |
| natmgrd 内部 | `doNatZoneIntfTask` | `m_natIpInterfaceInfo` キャッシュ (内部) | `port → set<ip_prefix>` | ゾーン変更時に IP インタフェースキャッシュの有無で Static/Dynamic NAT ルール再構築の要否を判定。IP プレフィックスエントリが先に処理されている場合のみ NAT ルールが再構築される | `natmgr.cpp:7532-7568` |
| orchagent → PortsOrch | `allPortsReady()` | PortsOrch 内部フラグ (PORT_TABLE 処理完了) | — | 全ポート初期化完了前は nat_zone の SAI 反映がスキップされる | `intfsorch.cpp:665-668` |
| orchagent → SAI switch | `gIsNatSupported` | SAI `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` | — | SNAT capability が 0 のプラットフォームでは nat_zone の SAI zone_id 設定が silent skip される | `intfsorch.cpp:978-985` |

---

## ページ反映方針

- `<!-- cross-refs -->` ブロックを `<!-- /ordering -->` と `<!-- entry-points -->` の間に挿入する。
- 主要な STATE_DB 依存（ポート/インタフェース ready 確認）と内部キャッシュ依存、および orchagent の `allPortsReady()` / `gIsNatSupported` 依存を表形式で記述する。
