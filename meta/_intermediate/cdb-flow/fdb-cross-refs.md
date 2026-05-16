# FDB — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/fdb.md` Phase C 追加分。
`sonic-swss/orchagent/fdborch.cpp` を精読し、`FDB` テーブルと外部テーブル・外部 Orch への依存を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/fdborch.cpp` | `FdbOrch::doTask()` / `addFdbEntry()` / `updateVlanMember()` / `updatePortOperState()` / `notifyObserversFDBFlush()` |
| `sonic-swss/orchagent/portsorch.h` | `PortsOrch` インタフェース（`getPort`, `getPortByBridgePortId`, `setPort`, `getPortVlanMembers`, `decrFdbCount` 等） |
| `sonic-swss/orchagent/observer.h` | `SUBJECT_TYPE_VLAN_MEMBER_CHANGE` / `SUBJECT_TYPE_PORT_OPER_STATE_CHANGE` / `SUBJECT_TYPE_FDB_CHANGE` / `SUBJECT_TYPE_FDB_FLUSH_CHANGE` の型定義 |
| `sonic-swss/orchagent/neighorch.cpp` | `NeighOrch::update()` — `SUBJECT_TYPE_FDB_FLUSH_CHANGE` 受信側 |

## YANG leafref

`FDB` テーブルは YANG 未定義のため leafref は存在しない。全参照が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. PORT テーブル（`port` フィールド — OID 解決）

- **参照先テーブル**: `PORT` / `PORTCHANNEL`（PortsOrch 管理）
- **参照方向**: 読み取り（ブリッジポート OID 解決）
- **条件**: 常時（全 `FDB` エントリ処理で必須）
- **参照元**: `fdborch.cpp:1277–1320` (`addFdbEntry()` 内 `m_portsOrch->getPort(port_name, port)` 呼び出し)
- **意味**: `port` フィールドの値を `PortsOrch::getPort()` で解決し、ブリッジポート OID を取得する。`port` が PORT テーブルに存在しない場合、エントリは `saved_fdb_entries[port_name]` に保留される（`fdborch.cpp:1301`）。後から PORT が登録されてもこの保留キューが自動的に消化されるわけではなく、VLAN_MEMBER への追加イベントをトリガとして再試行される（下記 §3 参照）。

### 2. VLAN テーブル（key の `<VlanName>` — VLAN OID 解決）

- **参照先テーブル**: `VLAN`（PortsOrch 管理）
- **参照方向**: 読み取り（VLAN Bridge Vector ID 解決）
- **条件**: 常時（全 `FDB` エントリ処理で必須）
- **参照元**: `fdborch.cpp:1289–1295` (`addFdbEntry()` 内 `m_portsOrch->getPort(vlan_alias, vlan)` 呼び出し)
- **意味**: キー `FDB|Vlan<id>|<MAC>` の `Vlan<id>` 部分を `PortsOrch::getPort()` で解決して `vlan_oid`（Bridge Vector ID）を取得する。VLAN が未作成の場合は `addFdbEntry()` が `return false` し、エントリは `saved_fdb_entries` に保留される（`fdborch.cpp:1301, 1316`）。

### 3. VLAN_MEMBER テーブル（ポート削除イベント — FDB フラッシュトリガ）

- **参照先テーブル**: `VLAN_MEMBER`（PortsOrch 経由で間接参照）
- **参照方向**: イベント受信（Observer パターン）
- **条件**: VLAN メンバーが追加または削除されたとき
- **参照元**: `fdborch.cpp:655–663` (`FdbOrch::update()` の `SUBJECT_TYPE_VLAN_MEMBER_CHANGE` ケース) → `updateVlanMember()` (L1240–1275)
- **意味**:
  - **削除時** (`update.add == false`): `flushFDBEntries(port.m_bridge_port_id, vlan.m_vlan_info.vlan_oid)` を呼び、当該ポート・VLAN 組み合わせの動的 FDB エントリを SAI 経由でフラッシュする（静的エントリは除外: `SAI_FDB_FLUSH_ENTRY_TYPE_DYNAMIC`）。その後 `notifyObserversFDBFlush()` で ARP flush イベントを上位に通知する。
  - **追加時** (`update.add == true`): `saved_fdb_entries[port_name]` に保留されていた FDB エントリを `addFdbEntry()` で再試行し、VLAN に一致するエントリのみ投入する（`fdborch.cpp:1263–1270`）。
- **注意**: `removeVlanMember` のコメント（L302）が示す通り、orchagent が VLAN メンバー削除を処理した後に FDB 通知が遅れて来ることがあり、その場合は「ポートが bv_id で見つからない」WARNING で無視される。

### 4. PORT oper-state（ポートダウン — FDB フラッシュトリガ）

- **参照先**: PORT oper-state（PortsOrch から `SUBJECT_TYPE_PORT_OPER_STATE_CHANGE` で通知）
- **参照方向**: イベント受信（Observer パターン）
- **条件**: ポートが DOWN になったとき
- **参照元**: `fdborch.cpp:661–665` (`FdbOrch::update()` の `SUBJECT_TYPE_PORT_OPER_STATE_CHANGE` ケース) → `updatePortOperState()` (L1203–1238)
- **意味**: 対象ポートが MCLAG インタフェースでない場合、`flushFDBEntries(bridge_port_id, SAI_NULL_OBJECT_ID)` でそのポートの全動的 FDB エントリをフラッシュする。さらに `PortsOrch::getPortVlanMembers()` でポートが属する全 VLAN を列挙し、各 VLAN に対して `notifyObserversFDBFlush()` を呼ぶ。MCLAG インタフェースの場合は flush をスキップ（`fdborch.cpp:1209`）。

### 5. MCLAG (MlagOrch) との連携

- **参照先**: `MlagOrch`（外部グローバル `gMlagOrch`）
- **参照方向**: 条件分岐（MCLAG ポートの判定）
- **条件**: ポートダウン時の flush 判定、AGE イベント処理
- **参照元**: `fdborch.cpp:1209` (`gMlagOrch->isMlagInterface()`), L490–515 (AGE イベントで MCLAG remote エントリを再追加する分岐)
- **意味**:
  - ダウンしたポートが MCLAG インタフェースの場合は FDB flush を行わない（MCLAG ピアが保持しているため）。
  - `FDB_ORIGIN_MCLAG_ADVERTIZED` origin を持つエントリは AGE イベントで削除されず、SAI に再追加される（`fdborch.cpp:490–515`）。MCLAG remote エントリの削除は `m_mclagFdbStateTable`（STATE_DB の `MCLAG_REMOTE_FDB_TABLE`）から行う。
  - MCLAG remote → local への MAC move（`FDB_ORIGIN_MCLAG_ADVERTIZED` エントリと同 MAC に LEARN が来た場合）は、`m_mclagFdbStateTable` から削除し、通常の動的エントリに切り替える（`fdborch.cpp:124–128`）。

### 6. NeighOrch — FDB flush 受信側（上流通知）

- **参照先**: `NeighOrch`（Observer として登録）
- **参照方向**: 通知送出（`notify(SUBJECT_TYPE_FDB_FLUSH_CHANGE, &flushUpdate)` — L1198）
- **条件**: VLAN メンバー削除またはポートダウン時に FDB エントリが消えたとき
- **参照元**: `fdborch.cpp:1178–1201` (`notifyObserversFDBFlush()`), `neighorch.cpp:195` (受信側)
- **意味**: `FdbOrch` が FDB エントリをフラッシュすると `SUBJECT_TYPE_FDB_FLUSH_CHANGE` を `notify()` で broadcast する。`NeighOrch` はこれを受け取り、該当ポート・VLAN の ARP/ND エントリを削除する。`FDB` テーブル自体には記載されないが、`FDB` エントリが消えると連鎖的に ARP エントリも消える副作用がある。

### 7. VxlanTunnelOrch との連携（EVPN remote MAC）

- **参照先**: `VxlanTunnelOrch`（`gDirectory.get<VxlanTunnelOrch*>()`）
- **参照方向**: 読み取り + 通知（`notifyTunnelOrch()`）
- **条件**: `FDB_ORIGIN_VXLAN_TUNNEL` origin の FDB エントリが AGE/MOVE で削除されるとき
- **参照元**: `fdborch.cpp:546, 621, 1738` (`notifyTunnelOrch()` 呼び出し), L1792–1800 (`notifyTunnelOrch()` 実装)
- **意味**: EVPN 経由で学習した remote MAC が aging/move で消える際に `VxlanTunnelOrch::deleteTunnelPort()` を呼び、不要なトンネルポートを解放する。`FDB` テーブルの `type` に依存するのではなく、`FdbData.origin` が `FDB_ORIGIN_VXLAN_TUNNEL` かどうかで判定する。

## 参照関係サマリ

```
FDB
  ├─ [暗黙・必須] PORT.name                     (port フィールド — ブリッジポート OID 解決、未解決時は保留)
  ├─ [暗黙・必須] VLAN.name (Vlan<id>)          (key の VlanName — VLAN OID 解決、未解決時は保留)
  ├─ [暗黙・イベント] VLAN_MEMBER (remove)       (メンバー削除 → 動的 FDB flush + NeighOrch 通知)
  ├─ [暗黙・イベント] VLAN_MEMBER (add)          (メンバー追加 → 保留 FDB エントリ再試行)
  ├─ [暗黙・イベント] PORT oper-state (down)     (ポートダウン → 動的 FDB flush + NeighOrch 通知)
  ├─ [暗黙・MCLAG] MlagOrch                      (MCLAG remote エントリの flush 抑制 / 再追加)
  ├─ [暗黙・上流通知] NeighOrch                  (FDB_FLUSH_CHANGE → ARP/ND エントリ連鎖削除)
  └─ [暗黙・EVPN] VxlanTunnelOrch               (VXLAN_TUNNEL origin MAC の aging/move → トンネルポート解放)
```

## evidence

- `fdborch.cpp`: L28–39 (コンストラクタ、`m_portsOrch->attach(this)`)
- `fdborch.cpp`: L1277–1320 (`addFdbEntry()` — PORT/VLAN OID 解決と保留ロジック)
- `fdborch.cpp`: L655–665 (`update()` — VLAN_MEMBER / PORT_OPER_STATE イベント受信)
- `fdborch.cpp`: L1240–1275 (`updateVlanMember()` — flush と保留再試行)
- `fdborch.cpp`: L1203–1238 (`updatePortOperState()` — MCLAG 判定 + flush)
- `fdborch.cpp`: L1178–1201 (`notifyObserversFDBFlush()` — NeighOrch への FDB_FLUSH_CHANGE 通知)
- `fdborch.cpp`: L490–515 (MCLAG remote エントリの AGE 抑制)
- `fdborch.cpp`: L1792–1800 (`notifyTunnelOrch()` — VxlanTunnelOrch::deleteTunnelPort)
- `fdborch.cpp`: L1086–1090 (コメント: SUBJECT_TYPE_VLAN_MEMBER_CHANGE でのフラッシュ説明)
- `neighorch.cpp`: L195 (`SUBJECT_TYPE_FDB_FLUSH_CHANGE` 受信)
