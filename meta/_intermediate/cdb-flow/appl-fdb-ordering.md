# APPL_DB FDB_TABLE — Phase B 書込み順依存スキャンノート

対象テーブル: `APPL_DB FDB_TABLE`（および同 Consumer 経路の `APP_VXLAN_FDB_TABLE` / `APP_MCLAG_FDB_TABLE`）
Consumer: `FdbOrch::doTask(Consumer&)` / `FdbOrch::addFdbEntry()` / `FdbOrch::removeFdbEntry()` (`sonic-swss/orchagent/fdborch.cpp`)
スキャン範囲: L1-1802 全行精読 (主に L707-921 doTask, L1240-1275 updateVlanMember, L1277-1455 addFdbEntry, L1631-1710 removeFdbEntry)

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() 先行必須（doTask 全体ガード）

- `doTask(Consumer&)` L711-714: `m_portsOrch->allPortsReady()` が false の間、関数冒頭で `return` し APPL_DB の入力イベントを一切処理しない。`m_toSync` には積まれたまま、PortsOrch が全 PORT の SAI 作成を終えるまで保留される。
- 順序依存: **PortsOrch 全 PORT 初期化完了 → FDB_TABLE SET/DEL 処理開始**。
- evidence: `fdborch.cpp:711-714`

### 2. VLAN（`Vlan<id>`）先行必須（SET / DEL の両方）

- `doTask()` L739-761: key の `keys[0]`（`Vlan<id>`）について `m_portsOrch->getPort(keys[0], vlan)` を呼び、VLAN が PortsOrch に登録されていなければ `SWSS_LOG_INFO("Failed to locate ...")` で:
  - `op == SET_COMMAND`: `it++` して **次周回で再試行**（VLAN 作成完了まで自動ポーリング）
  - `op == DEL_COMMAND`: `saved_fdb_entries` から該当 MAC を削除して `m_toSync.erase(it)`（再試行なし）
- 順序依存: `VLAN|<name>` が VlanMgr → VlanOrch 経由で PortsOrch に登録済みであること。
- evidence: `fdborch.cpp:735-761`

### 3. PORT 先行必須（addFdbEntry 内 saved_fdb_entries retry）

- `addFdbEntry()` L1297-1304: `m_portsOrch->getPort(port_name, port)` が false、または `port.m_bridge_port_id == SAI_NULL_OBJECT_ID` のとき、エントリを `saved_fdb_entries[port_name]` に push して `return true`（= doTask 側からは「成功扱い」で `m_toSync.erase`）。
- このため doTask の周回再試行ではなく、**PortsOrch が当該 PORT の bridge_port を作成した時点で PortsOrch 側から `update()` 経由で replay** される（後述 #5）。
- 順序依存: `PORT|<alias>` が PortsOrch で bridge_port 作成完了（VLAN メンバー化と同時に発生）まで FDB が pending。
- evidence: `fdborch.cpp:1297-1304`

### 4. VLAN メンバーシップ先行必須（addFdbEntry 内 isVlanMember retry）

- `addFdbEntry()` L1312-1319: PORT が解決済みでも `m_portsOrch->isVlanMember(vlan, port, end_point_ip)` が false なら、再度 `saved_fdb_entries[port_name]` に push して `return true`。
- 順序依存: `VLAN_MEMBER|<vlan>|<port>` の SET が完了し、PortsOrch 内部の m_vlanMembers に登録されるまで FDB pending。
- evidence: `fdborch.cpp:1312-1319`

### 5. PortsOrch からの VLAN_MEMBER 通知で saved_fdb_entries を自動 replay

- `FdbOrch::updateVlanMember()` L1240-1275 (`update.add == true` 時): `saved_fdb_entries[port_name]` を `std::move` で取り出し、各エントリについて `vlanId` が一致するものだけ `addFdbEntry()` を再呼出し。再 pending になったものは push back で残す。
- これにより #3 / #4 の保留エントリは **VLAN_MEMBER 追加イベント駆動で自動 replay** される。doTask 再周回は不要。
- 順序依存: 自動調停（PortsOrch observer pattern）。
- evidence: `fdborch.cpp:1240-1275, L39 m_portsOrch->attach(this)`

### 6. VXLAN tunnel 先行必須（VXLAN_FDB origin）

- `doTask()` L832-856 (`origin == FDB_ORIGIN_VXLAN_ADVERTIZED`):
  - DIP tunnel サポート時: `tunnel_orch->getTunnelPortName(remote_ip)` で port 名解決。`remote_ip` 未指定なら `m_toSync.erase` で破棄（再試行なし）。
  - SIP tunnel 時: `EvpnNvoOrch::getEVPNVtep()` で sip tunnel が未作成なら同様に `m_toSync.erase`。
- 順序依存: `APP_VXLAN_FDB_TABLE` 経路では **VxlanTunnelOrch / EvpnNvoOrch の tunnel 作成完了が事前必須**。tunnel 未作成時は **再試行されず破棄** される点に注意。
- evidence: `fdborch.cpp:832-856`

### 7. VXLAN tunnel 経由の保留はその後 PORT 解決で救済（saved_fdb_entries）

- L843 / L854 で得た `port` 名（`tunnel_orch->getTunnelPortName(...)` の戻り値）が #3 の PortsOrch getPort で見つからない場合は通常の saved_fdb_entries 経路に乗る。
- evidence: `fdborch.cpp:1298-1304`

### 8. DEL_COMMAND の特殊順序: VLAN 未解決でも saved_fdb から削除

- `doTask()` L742-754: DEL で VLAN が見つからない場合 `keys[0].substr(4)` から vlan_id を文字列パースし、`deleteFdbEntryFromSavedFDB()` で saved_fdb_entries から該当 MAC を取り除いて erase。
- これは「VLAN が消えた後に届いた DEL」を保留 FDB 側から消すための救済。順序依存ではないが **VLAN DEL → FDB DEL の到着順が逆転しても整合する** よう設計されている点を記録。
- evidence: `fdborch.cpp:742-754, deleteFdbEntryFromSavedFDB()`

### 9. removeFdbEntry: origin 不一致時の DEL は無視（順序ではなく所有権制約）

- `removeFdbEntry()` L1663-1690: 既存エントリの `fdbData.origin` と DEL の `origin` が不一致なら、原則 **DEL は無視** して `return true`（ただし MCLAG ピアポート down のときだけ LEARN として削除）。
- 例: VXLAN_ADVERTIZED で書かれた MAC を APPL_DB FDB_TABLE 経路（PROVISIONED/LEARN）で DEL しても消えない。
- 運用順序の含意: **MAC を投入した origin と同じ origin から DEL すべき**。混在 DEL は silently ignored。
- evidence: `fdborch.cpp:1663-1690`

### 10. removeFdbEntry: 既存エントリ未登録なら saved_fdb のみクリーンアップ

- L1646-1654: `m_entries` にエントリがなければ `deleteFdbEntryFromSavedFDB()` だけ呼んで `return true`。SAI への DEL 要求は発行されない。
- 既に flush 済み / 学習前 / saved 状態のいずれであっても **冪等な DEL** が保証される。
- evidence: `fdborch.cpp:1646-1654`

### 11. assert(type) による fail-fast（順序ではなく入力検証）

- `doTask()` L830: `assert(type == "dynamic" || type == "dynamic_local" || type == "static")`。不正値は orchagent クラッシュ。
- 順序依存ではないがレコード内必須性として併記。
- evidence: `fdborch.cpp:830`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | PortsOrch `allPortsReady()` → FDB_TABLE 処理開始 | 強制先行 | doTask 冒頭で return（自動待機） |
| 2 | `VLAN|<name>` 登録完了 → FDB_TABLE SET | 強制先行（SET は自動再試行、DEL は saved_fdb から削除） | `it++` 周回再試行 / `deleteFdbEntryFromSavedFDB` |
| 3 | `PORT|<alias>` bridge_port 作成完了 → FDB_TABLE SET | 強制先行（saved_fdb_entries で保留） | PortsOrch update() で自動 replay |
| 4 | `VLAN_MEMBER|<vlan>|<port>` 登録完了 → FDB_TABLE SET | 強制先行（saved_fdb_entries で保留） | `updateVlanMember()` で自動 replay |
| 5 | PortsOrch observer 経由 saved_fdb replay | 自動調停 | `m_portsOrch->attach(this)` (L39) |
| 6 | VxlanTunnelOrch / EvpnNvoOrch tunnel 作成 → VXLAN_FDB SET | 強制先行（**再試行なし、未満足 SET は破棄**） | tunnel を先に作る運用が必須 |
| 7 | VXLAN 経路の port 解決失敗 → saved_fdb 経由で救済 | 自動調停（#3 と同経路） | 同上 |
| 8 | VLAN DEL → FDB DEL の到着逆転 | 自動調停 | `deleteFdbEntryFromSavedFDB` |
| 9 | DEL の origin と既存 FDB の origin 一致 | 排他制約（順序ではない） | 同 origin から DEL する運用 |
| 10 | 二重 DEL / 学習前 DEL | 冪等 | saved_fdb のみクリーンアップして成功扱い |
| 11 | `type` フィールド値の妥当性 | 入力検証（fail-fast） | assert によるクラッシュ |

---

## Phase B 推奨書込み順序

```text
# 1. PortsOrch 全体準備（allPortsReady を待つ — orchagent 初期化フェーズ）
# 2. VLAN 作成
SET CONFIG_DB VLAN|Vlan100
# 3. PORT 準備（PortsOrch が bridge_port を作成）— 通常は config 投入で自然満足
# 4. VLAN メンバーシップ
SET CONFIG_DB VLAN_MEMBER|Vlan100|Ethernet0
# 5. （VXLAN MAC を投入する場合のみ）VxlanTunnelOrch の tunnel を先に作成
# 6. FDB エントリ投入
SET APPL_DB FDB_TABLE:Vlan100:00:11:22:33:44:55  port=Ethernet0  type=static
# 7. 削除は投入時と同じ origin の経路から DEL
```

#3, #4 を満たさない状態で SET しても自動的に saved_fdb で保留 → VLAN_MEMBER 確定時に replay されるが、**#6 の VXLAN tunnel 未満足だけは再試行されず破棄** される点を要注意。
