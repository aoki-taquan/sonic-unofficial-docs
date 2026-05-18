# APPL_DB LAG_TABLE (portchannel-status) — Phase B: 書込み順依存調査メモ

調査日: 2026-05-18
対象: `docs/reference/config-db/portchannel-status.md`
証跡ソース: `teamsyncd/teamsync.cpp` (sonic-swss)、`cfgmgr/teammgr.cpp` (sonic-swss)、`orchagent/portsorch.cpp` (sonic-swss)

---

## 1. 書き込み元プロセスと APPL_DB 書込みタイミング

### teamsyncd — カーネル RTM_NEWLINK 駆動

- `teamsync.cpp:140-157` — `RTM_NEWLINK` を受信すると `addLag()` を呼び出す。
- `addLag()` は **APPL_DB LAG_TABLE を先に書き込み**（`m_lagTable.set()`）、成功した場合のみ続けて **STATE_DB LAG_TABLE を書き込む**（`m_stateLagTable.set()`）。
- コードコメント: "STATE_DB is written only after the team instance is successfully created to prevent dependent services (e.g. intfmgrd) from acting on a LAG that teamd has not yet finished setting up" (`teamsync.cpp:191-196`)
- **順序**: `APPL_DB LAG_TABLE` 書込み → `TeamPortSync` オブジェクト生成成功 → `STATE_DB LAG_TABLE` 書込み
- warm reboot 時は `m_stateLagTablePreserved` に蓄積し、reconcile 完了後にまとめて適用する（`teamsync.cpp:199-200`）。

### teammgrd — CONFIG_DB PORTCHANNEL 変更駆動

- `teammgr.cpp:303-323` — `doLagTask()` が SET を処理する際の順序:
  1. `addLag()` — teamd プロセスを起動して Linux bond デバイスを作成。失敗した場合 `task_need_retry` で保留。
  2. `setLagAdminStatus()` — `ip link set dev <lag> up|down` をカーネルに発行。APPL_DB への直接書込みはなく、カーネル状態変化が RTM_NEWLINK として teamsyncd に伝達される。
  3. `setLagMtu()` — `ip link set dev <lag> mtu <mtu>` 後、`m_appLagTable.set(alias, fvs)` で APPL_DB の `mtu` フィールドを直接書き込む (`teammgr.cpp:512-515`)。
  4. `setLagLearnMode()` — APPL_DB に `learn_mode` フィールドを直接書き込む (`teammgr.cpp:553-559`)。
  5. `setLagTpid()` — APPL_DB に `tpid` フィールドを直接書き込む (`teammgr.cpp:538-545`)。

---

## 2. 先行必須テーブル (SET 受信前に充足が必要な依存)

### PORT_CONFIG_DONE / allPortsReady が必須

- `portsorch.cpp:6513-6517` — orchagent は `allPortsReady()` が true になるまで LAG 含む全 SET をブロックする。
- **順序依存**: portsyncd が CONFIG_DB|PORT を全件処理して `PortConfigDone` → `PortInitDone` が発行されるまで、APPL_DB LAG_TABLE からの orchagent 処理は開始されない。

### STATE_LAG_TABLE (STATE_DB) が先行必須 — PORTCHANNEL_MEMBER 追加時

- `teammgr.cpp:89-102, 357` — `isLagStateOk()` が false（STATE_DB の LAG エントリ未存在）の場合、`PORTCHANNEL_MEMBER` タスクをスキップしてリトライ待機する。
- **順序依存**: LAG メンバーの追加は teamsyncd が STATE_DB LAG_TABLE を書き込んだ後でなければ処理されない。

---

## 3. APPL_DB → orchagent 処理の順序

orchagent (`PortsOrch::doLagTask()`) が APPL_DB LAG_TABLE を ConsumerStateTable で受信した場合の処理順:

1. `m_portList.find(alias)` で LAG オブジェクトが存在しない場合 → `addLag()` で SAI `create_lag()` を呼ぶ (`portsorch.cpp:6133-6139`)。
2. `oper_status` フィールドが存在する場合 → `updatePortOperStatus()` で SAI / 内部ポートオブジェクトを更新 (`portsorch.cpp:6153-6157`)。
3. `mtu` フィールドが存在する場合 → `l.m_mtu` を更新し、L3 インタフェース (`m_rif_id`) があれば `setRouterIntfsMtu()` を呼び出す。子インタフェースの MTU も連動して更新 (`updateChildPortsMtu()`) される (`portsorch.cpp:6158-6168`)。
4. `tpid` フィールドが存在する場合 → `setLagTpid()` で SAI 属性を更新 (`portsorch.cpp:6170-6184`)。
5. `learn_mode` フィールドが存在する場合 → `setBridgePortLearnMode()` で SAI 属性を更新 (`portsorch.cpp:6186-6200`)。

---

## 4. DEL 順 (先行削除が必要なエントリ)

APPL_DB LAG_TABLE エントリを DEL する前に orchagent が要求する先行削除:

1. **LAG_MEMBER_TABLE の全エントリ** — `LagOrch::removeLag()` は `non-empty LAG` の場合エラーを返す。
2. **INTF_TABLE のルータインタフェース** — `ref_count > 0` の LAG は SAI DEL が拒否される。
3. **VLAN 所属** — LAG が VLAN メンバーのまま DEL すると `"Failed to remove LAG ... it is still in VLAN"` エラー。

---

## 5. warm reboot 時の書込み順序変化

- teamsyncd は warm reboot モード時に `m_lagTable.create_temp_view()` を作成し、RTM_NEWLINK イベントを temp view に集積する (`teamsync.cpp:41-43`)。
- warm reboot タイマー満了後 `m_lagTable.apply_temp_view()` で一括適用する (`teamsync.cpp:88-89`)。
- この間、STATE_DB LAG_TABLE への書込みは `m_stateLagTablePreserved` に蓄積され、reconcile 完了後にまとめて適用される。
- **consumer が観測しうる中間状態**: warm reboot 期間中は APPL_DB LAG_TABLE が古い値を保持したまま STATE_DB LAG_TABLE が更新されない状態が続く。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | APPL_DB LAG_TABLE 書込み → STATE_DB LAG_TABLE 書込み | 強制先行（teamsyncd 内） | team instance 生成成功後のみ STATE_DB に書かれる |
| 2 | `PortConfigDone` / `allPortsReady()` → orchagent LAG 処理開始 | 強制先行 | portsyncd ready まで orchagent はブロック |
| 3 | STATE_DB LAG_TABLE ready → PORTCHANNEL_MEMBER SET | 強制先行 | teammgrd が自動リトライ待機 |
| 4 | LAG_MEMBER_TABLE DEL → LAG_TABLE DEL | 推奨先行 | 逆順では orchagent が non-empty LAG エラー |
| 5 | INTF_TABLE / VLAN_MEMBER DEL → LAG_TABLE DEL | 強制先行（ref_count / VLAN 制約） | 参照解放まで SAI DEL が拒否される |

---

## ソース証跡

| 知見 | ファイル | 行 |
|------|---------|-----|
| APPL_DB 先書き → STATE_DB 後書き | `sonic-swss/teamsyncd/teamsync.cpp` | 157, 175, 203 |
| STATE_DB 遅延書込みコメント | `sonic-swss/teamsyncd/teamsync.cpp` | 191-196 |
| addLag() → setLagAdminStatus() → setLagMtu() 順 | `sonic-swss/cfgmgr/teammgr.cpp` | 303-323 |
| setLagMtu() APPL_DB 直接書込み | `sonic-swss/cfgmgr/teammgr.cpp` | 512-515 |
| isLagStateOk() STATE_DB 先行チェック | `sonic-swss/cfgmgr/teammgr.cpp` | 89-102, 357 |
| allPortsReady() ブロック | `sonic-swss/orchagent/portsorch.cpp` | 6513-6517 |
| orchagent doLagTask() フィールド処理順 | `sonic-swss/orchagent/portsorch.cpp` | 6133-6200 |
