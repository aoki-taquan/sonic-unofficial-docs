# INTERFACE — Phase B 書込み順依存 (intermediate)

ソース精読: `sonic-swss/cfgmgr/intfmgr.cpp` (1297 行) + `sonic-swss/orchagent/intfsorch.cpp` (1782 行)

---

## 1. 他テーブル先行必須

### intfmgrd 側 (CONFIG_DB → APP_DB)

| 前提テーブル | チェック箇所 | 理由 |
|-------------|-------------|------|
| `PORT` → STATE_DB `PORT_TABLE` | `isIntfStateOk()` L649–710、`doIntfGeneralTask()` L833–837 | `m_statePortTable.get(alias)` が成功しないと `SET` をスキップ (`return false`) |
| `PORTCHANNEL` → STATE_DB `LAG_TABLE` | 同 `isIntfStateOk()` L661–666 | LAG 系ポートは `m_stateLagTable.get(alias)` を要求 |
| `VLAN` → STATE_DB `VLAN_TABLE` | 同 L652–660 | VLAN IF は `m_stateVlanTable.get(alias)` を要求 |
| `VRF` → STATE_DB `VRF_TABLE` | `doIntfGeneralTask()` L839–843 | `vrf_name` 指定時に `isIntfStateOk(vrf_name)` を追加チェック |
| `VNET` → APP_DB / orchagent 内 vnet存在確認 | `intfsorch.cpp` L933–956 | `vnet_orch->isVnetExists(vnet_name)` が偽なら `it++; continue` でリトライ |

### orchagent (IntfsOrch) 側 (APP_DB → SAI)

| 前提 | チェック箇所 | 理由 |
|------|-------------|------|
| `gPortsOrch->allPortsReady()` | `intfsorch.cpp` L665 | 全ポート ready 前は `doTask()` 全体を抜ける |
| Port 存在 (`gPortsOrch->getPort`) | L904–926 | Port が未登録なら `it++; continue` |
| VRF 存在 (`m_vrfOrch->isVRFexists`) | L826–832 | VRF 未登録なら `it++; continue` |

---

## 2. SET 後 DEL 順序

### 属性ロウ DEL 前に IP アドレスロウを全削除

- `doIntfGeneralTask()` DEL ブロック L1056–1064:
  ```cpp
  if (getIntfIpCount(alias))
      return false;  // IP アドレスが残っている限り DEL をスキップ
  ```
- つまり IP プレフィクスロウ (`INTERFACE|EthernetN|<ip/pfx>`) の DEL が先行しないと、
  属性ロウ (`INTERFACE|EthernetN`) の DEL は Consumer キューに残り続ける。

### VRF 変更の 2 ステップ

- `isIntfChangeVrf()` + `doIntfGeneralTask()` L846–849:
  ```cpp
  SWSS_LOG_ERROR("%s can not change to %s directly, skipping");
  return true;  // エントリ消費 (再試行なし)
  ```
- 別 VRF へ直接書き換えると **エラーで破棄** される。
  正しい順序: ① `vrf_name` を空にした SET (VRF 除去) → ② 新 VRF 名で SET。

---

## 3. Notification 順 (Consumer → Producer)

1. `intfmgrd` が `INTERFACE` SET を受信
2. `isIntfStateOk()` で STATE_DB のポート/VRF ready を確認
3. `m_appIntfTableProducer.set(alias, data)` で APP_DB `INTF_TABLE` を更新
4. `m_stateIntfTable.hset(alias, "vrf", vrf_name)` で STATE_DB `INTERFACE_TABLE` に vrf を記録
5. `IntfsOrch` が APP_DB 変化を受信 → `addRouterIntfs()` で SAI RIF 作成
6. IP プレフィクスロウの SET は、さらに `isIntfCreated(alias)` (STATE_DB `INTERFACE_TABLE` 確認) が成功した後に `m_appIntfTableProducer.set(appKey)` でプレフィクスを APP_DB へ

**重要**: IP プレフィクス SET は属性ロウが STATE_DB に書かれた後でないと処理されない。
(`doIntfAddrTask()` L1115: `if (!isIntfStateOk(alias) || !isIntfCreated(alias)) return false;`)

---

## 4. select() ポーリング

- `intfmgrd.cpp`: `s.select(&sel, SELECT_TIMEOUT=1000ms)` → TIMEOUT 時に `intfmgr.doTask()` を呼ぶ
- pending 状態の Consumer エントリは `it++` でキューに残り、次の `select()` サイクルで再試行
- warm-reboot 中は `m_pendingReplayIntfList` が空になるまで RECONCILED 状態に移行しない

---

## 5. 起動時 boot order 依存

- `intfmgrd` コンストラクタ: `WarmStart::isWarmStart()` が偽の場合は `flushLoopbackIntfs()` を実行してループバックをクリア
- warm-start の場合は `buildIntfReplayList()` でリプレイリストを構築し、STATE_DB への書き込みが完了したエントリから順に削除
- `orchagent` の `IntfsOrch::doTask()`: `gPortsOrch->allPortsReady()` が真になる前は**全 INTERFACE 処理をブロック**する
  → portmgrd → portsorch が PORT テーブルを全て初期化するまで、L3 IF の SAI 作成は始まらない

---

## 6. warm-reboot 影響

- `intfmgrd` は `WarmStart::setWarmStartState("intfmgrd", WarmStart::WSDISABLED / REPLAYED / RECONCILED)` を管理
- warm-reboot 時: 既存 Linux netdev の IP 設定はカーネルに残る (flushLoopbackIntfs はスキップ)
- `m_pendingReplayIntfList` に含まれる全エントリが再処理完了するまで `RECONCILED` に移行しない
- 再処理中に STATE_DB への PORT ready 通知が遅れると、pending エントリが 1000ms 周期でリトライされ続ける

---

## 7. 制約まとめ (ordering ブロック向け)

| # | 順序ルール | 根拠コード |
|---|-----------|-----------|
| 1 | PORT (STATE_DB ready) → INTERFACE SET | `isIntfStateOk()` L833 |
| 2 | VRF (STATE_DB ready) → INTERFACE SET with vrf_name | L839 |
| 3 | VNET (APP_DB 存在) → INTERFACE SET with vnet_name | intfsorch L933 |
| 4 | INTERFACE 属性ロウ SET → IP プレフィクスロウ SET | `isIntfCreated()` L1115 |
| 5 | IP プレフィクスロウ DEL (全件) → INTERFACE 属性ロウ DEL | `getIntfIpCount()` L1060 |
| 6 | VRF 除去 SET → 新 VRF SET (VRF 変更は 2 ステップ必須) | `isIntfChangeVrf()` L846 |
| 7 | allPortsReady (orchagent) → SAI RIF 作成 | intfsorch L665 |
