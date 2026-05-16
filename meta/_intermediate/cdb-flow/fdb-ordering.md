# FDB — Phase B 書込み順依存スキャンノート

対象テーブル: `FDB`
Consumer: `FdbOrch::doTask()` (`sonic-swss/orchagent/fdborch.cpp`)
スキャン範囲: L707-922（doTask）、L1277-1330（addFdbEntry）、L280-540（fdbEvent AGED/LEARNED）全行精読

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード（ポート初期化先行必須）

- `doTask()` L711-714: `m_portsOrch->allPortsReady()` が false の間は即 return。
- PortsOrch の起動完了前に書き込まれた FDB エントリは、ポート初期化完了後に一括処理される。
- `doTask(NotificationConsumer&)` L927-930 も同様のガードが存在する。
- 順序依存: `PORT` テーブルの初期化完了（PortsOrch 全ポート ready）が FDB エントリ処理より**先行必須**。
- evidence: `fdborch.cpp:711-714`, `fdborch.cpp:927-930`

### 2. VLAN 先行必須（VLAN OID 解決）

- `doTask()` L739-760: `m_portsOrch->getPort(keys[0], vlan)` が失敗した場合、DEL ならエントリを erase して skip、SET なら `it++` で待機ループに入る。
- FDB キーの `<VlanName>`（例: `Vlan100`）が PortsOrch の VLAN テーブルに未登録の場合、SET は毎ループ再試行される。
- `addFdbEntry()` L1291-1294 でも再度 `getPort(entry.bv_id, vlan)` を呼び、失敗時は `return false`。
- 順序依存: `VLAN|Vlan<id>` が CONFIG_DB に存在し、VlanOrch が SAI VLAN OID を割り当て済みであること（FDB SET より先行必須）。
- evidence: `fdborch.cpp:739-760`, `fdborch.cpp:1291-1294`

### 3. PORT 先行必須（ブリッジポート OID 解決）

- `addFdbEntry()` L1298-1305: `m_portsOrch->getPort(port_name, port)` が失敗、または `port.m_bridge_port_id == SAI_NULL_OBJECT_ID` の場合、FDB エントリを `saved_fdb_entries[port_name]` に退避して `return true`（待機）。
- ポートが後からブリッジポートとして登録されると `SUBJECT_TYPE_PORT_OPER_STATE_CHANGE` イベント経由（L661）で saved エントリが再処理される（L1264-1268）。
- 順序依存: `port` フィールドに指定したポートが PortsOrch に登録済みかつブリッジポート OID が確定していること（FDB SET より先行必須。ただし違反時は自動待機 + 自動再試行）。
- evidence: `fdborch.cpp:1298-1305`, `fdborch.cpp:1260-1268`

### 4. VLAN_MEMBER 先行必須（VLAN メンバーシップ確認）

- `addFdbEntry()` L1313-1318: `m_portsOrch->isVlanMember(vlan, port, end_point_ip)` が false の場合、`saved_fdb_entries[port_name]` に退避して `return true`（待機）。
- ポートが VLAN メンバーになると `SUBJECT_TYPE_VLAN_MEMBER_CHANGE` イベント（L655）で saved エントリが再処理される。
- 順序依存: `VLAN_MEMBER|Vlan<id>|<port>` が VlanOrch に処理済み（FDB SET より先行必須。ただし違反時は自動待機 + 自動再試行）。
- evidence: `fdborch.cpp:1313-1318`, `fdborch.cpp:655-669`

### 5. FDB エントリ作成の必要順序まとめ

CONFIG_DB への書き込み推奨順序:
1. `PORT` / `PORTCHANNEL` — PortsOrch 初期化
2. `VLAN` — VlanOrch VLAN 作成・SAI VLAN OID 確定
3. `VLAN_MEMBER` — VlanOrch ポート → VLAN 紐付け
4. `FDB` — FdbOrch エントリ作成

ステップ 3 が未完了でも FDB エントリは `saved_fdb_entries` に退避され、VLAN_MEMBER 追加後に自動投入される（soft dependency）。ステップ 1 が未完了の場合のみ hard block（doTask が即 return）となる。

### 6. age out（SAI_FDB_EVENT_AGED）動作順序

- `fdbEvent()` で `SAI_FDB_EVENT_AGED` を受信すると L427-540 が実行される。
- **static エントリの age out**: ポートが VLAN メンバーに残っている場合 → SAI FDB エントリを再作成（L463-483）。VLAN メンバーでない場合（ポート削除後）→ `saved_fdb_entries` に退避（L456-462）。
- **dynamic エントリの age out**: `update.add = false` + `storeFdbEntryState()` + `notify(SUBJECT_TYPE_FDB_CHANGE)` で内部キャッシュおよび STATE_DB から削除（L534-543）。
- **MCLAG remote エントリの age out**: age event を無視して SAI にエントリを再追加（`SAI_FDB_ENTRY_TYPE_STATIC` に格上げ）する（L490-517）。
- 順序依存: static エントリは VLAN_MEMBER 再追加で自動復元。dynamic エントリはハードウェアの MAC aging タイマー（SAI `sai_switch_attr_t::SAI_SWITCH_ATTR_FDB_AGING_TIME`）に従って削除される。

### 7. PORT down 時の FDB flush 順序

- `onPortStateChangeNotification()` L1206-1248: ポートが `SAI_PORT_OPER_STATUS_DOWN` になると、そのポートの全 VLAN に対して `flushFDBEntries()` を呼ぶ。
- `flushFDBEntries()` L1090-1147: `sai_fdb_api->flush_fdb_entries()` で SAI 上の dynamic エントリを削除（static エントリは対象外: L1121-1127）。
- flush 後、各エントリに `is_flush_pending = true` を設定（L1143）し、次の SAI `SAI_FDB_EVENT_FLUSHED` 通知で内部キャッシュを削除する。
- 順序依存: ポート down イベント → VLAN per-flush → `SAI_FDB_EVENT_FLUSHED` 受信 → 内部キャッシュ削除。Static エントリは flush されないため CONFIG_DB の FDB|static エントリは手動削除が必要。
- evidence: `fdborch.cpp:1206-1248`, `fdborch.cpp:1090-1147`, `fdborch.cpp:1121-1127`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | allPortsReady() 完了 → FDB doTask 実行 | 強制先行（hard block） | なし（PortsOrch 起動待ち） |
| 2 | VLAN SAI OID 確定 → FDB SET | 強制先行（待機ループで自動調停） | 待機 + 自動再試行 |
| 3 | PORT ブリッジポート OID 確定 → FDB SET | 先行推奨（違反時: saved_fdb_entries 退避 + 自動再試行） | PORT_OPER_STATE_CHANGE イベントで復元 |
| 4 | VLAN_MEMBER 登録 → FDB SET | 先行推奨（違反時: saved_fdb_entries 退避 + 自動再試行） | VLAN_MEMBER_CHANGE イベントで復元 |
| 5 | FDB エントリ推奨投入順: PORT → VLAN → VLAN_MEMBER → FDB | 推奨順序 | ステップ 3/4 は soft、ステップ 1 のみ hard |
| 6 | age out: static は VLAN_MEMBER 再追加で復元、dynamic は aging タイマーで削除 | age out 時の自動挙動 | MCLAG remote は再追加 |
| 7 | PORT down flush: dynamic のみ。static は手動削除必要 | flush 後の挙動 | static エントリはポート down でも残存 |
