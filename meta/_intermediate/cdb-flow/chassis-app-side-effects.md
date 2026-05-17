# chassis-app Phase F — 書き込み副作用 (side-effects)

調査日: 2026-05-17  
調査対象:
- `sonic-swss/orchagent/intfsorch.cpp` @ 4305596
- `sonic-swss/orchagent/neighorch.cpp` @ 4305596
- `sonic-swss/orchagent/portsorch.cpp` @ 4305596
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py` @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py` @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd

## 概要

CHASSIS_APP_DB への書き込みは単なるデータ保存ではなく、
リモートラインカード側の orchagent がそのエントリを購読し、
SAI プログラミング・STATE_DB 更新・FRR 設定変更などの連鎖処理を引き起こす。

---

## SYSTEM_INTERFACE 書き込みの副作用

### 書き込み元 (ローカル LC)
- `intfsorch.cpp:voqSyncAddIntf()` — `addRouterIntfs()` 完了後に呼出
- `intfsorch.cpp:voqSyncDelIntf()` — `removeRouterIntfs()` 完了後に呼出
- `intfsorch.cpp:voqSyncIntfState()` — ポート oper status 変化時に `hset`

### 購読側の処理 (リモート LC)
`IntfsOrch::addExecutor(SubscriberStateTable(chassisAppDb, SYSTEM_INTERFACE, ...))` で
リモートラインカードの orchagent が変化を受信する (`intfsorch.cpp:106`)。

SET イベント受信時:
- `isRemoteSystemPortIntf(alias)` が true の場合のみ処理
- `gNeighOrch->ifChangeInformRemoteNextHop(alias, isUp)` を呼出し、
  リモートポートの UP/DOWN に伴い既存ネクストホップの到達可否を更新する
  (`intfsorch.cpp:887`)
- インタフェースが DOWN になるとそのポートを nexthop とするルートが無効化される

---

## SYSTEM_NEIGH 書き込みの副作用

### 書き込み元 (ローカル LC)
- `neighorch.cpp:voqSyncAddNeigh()` — `addNeighbor()` 完了後に呼出 (`neighorch.cpp:1436`)
- `neighorch.cpp:voqSyncDelNeigh()` — `removeNeighbor()` 完了後に呼出 (`neighorch.cpp:1605`)

### 購読側の処理 (リモート LC)
`NeighOrch::addExecutor(SubscriberStateTable(chassisAppDb, SYSTEM_NEIGH, ...))` で受信。
`doVoqSystemNeighTask()` が処理する (`neighorch.cpp:2048`)。

SET イベント受信時:
1. Inband ポートが UP であることを確認 (ポートタイプ non-VLAN の場合は admin/oper 両方が UP 必須)
2. SAI に remote neighbor を追加 (`addNeighbor()`)
3. 成功した場合、**STATE_DB の `SYSTEM_NEIGH` テーブル** (`STATE_SYSTEM_NEIGH_TABLE_NAME`) に
   `neigh` (MAC アドレス) を書き込む (`neighorch.cpp:2223`)
4. STATE_DB への書き込みはカーネルへの neighbor/route プログラミングを
   `neighbor-manager` が行うためのシグナル

DEL イベント受信時:
1. SAI から remote neighbor を削除 (`removeNeighbor()`)
2. 成功した場合、STATE_DB の対応エントリを削除 (`neighorch.cpp:2260`)

encap_index 変更時:
- 既存 neighbor を SAI から削除 → STATE_DB 削除 → 再追加 (2 ステップ) (`neighorch.cpp:2173`)

---

## SYSTEM_LAG_TABLE 書き込みの副作用

### 書き込み元 (ローカル LC)
- `portsorch.cpp:voqSyncAddLag()` — ローカル LAG 作成完了後 (`portsorch.cpp:8039`)
- `portsorch.cpp:voqSyncDelLag()` — ローカル LAG 削除前 (`portsorch.cpp:8116`)

### 購読側の処理 (リモート LC)
`PortsOrch::addExecutor(SubscriberStateTable(chassisAppDb, CHASSIS_APP_LAG_TABLE_NAME, ...))` で受信。

SET イベント (リモート LAG) 受信時:
- `switch_id == gVoqMySwitchId` の場合はローカル LC 自身が書いたエントリなのでスキップ
- リモート LAG として `addLag(alias, lag_id, switch_id)` を呼出し SAI に system LAG を作成
  (`portsorch.cpp:6116-6140`)
- LAG 作成後、`operation_status` / `mtu` / `tpid` / `learn_mode` が存在すれば
  SAI への属性設定が連鎖して行われる

---

## SYSTEM_LAG_MEMBER_TABLE 書き込みの副作用

### 書き込み元 (ローカル LC)
- `portsorch.cpp:voqSyncAddLagMember()` — LAG メンバー追加後 (`portsorch.cpp:8213`)
- `portsorch.cpp:voqSyncDelLagMember()` — LAG メンバー削除後 (`portsorch.cpp:8261`)

### 購読側の処理 (リモート LC)
`PortsOrch::addExecutor(SubscriberStateTable(chassisAppDb, CHASSIS_APP_LAG_MEMBER_TABLE_NAME, ...))` で受信。

SET イベント受信時:
- `switch_id` 不一致チェック後、対応するリモート LAG に system port を member として追加
  (`portsorch.cpp:6297-6355`)
- member port の `status` フィールドに基づき SAI でメンバーステータスを設定

---

## BGP_DEVICE_GLOBAL|STATE 書き込みの副作用

### 書き込み元 (スーパーバイザー bgpcfgd)
`managers_device_global.py` が CONFIG_DB の `BGP_DEVICE_GLOBAL.tsa_enabled` 変化を受けて
CHASSIS_APP_DB に `BGP_DEVICE_GLOBAL|STATE` を書き込む。

### 購読側の処理 (ラインカード bgpcfgd: ChassisAppDbMgr)
`managers_chassis_app_db.py` が CHASSIS_APP_DB を購読し SET イベントを受信する。

`tsa_enabled` フィールド変化時:
1. ローカル LC の `lc_tsa` ステータスを確認
2. `lc_tsa == "false"` のときのみ `DeviceGlobalCfgMgr.isolate_unisolate_device(data["tsa_enabled"])` を呼出し
3. `isolate_unisolate_device()` は FRR に対して TSA (Traffic Shift Away) または TSB (Traffic Shift Back)
   route-map 設定を vtysh 経由で push する (`managers_device_global.py:183-200`)
4. `lc_tsa == "true"` の場合はスーパーバイザーの TSA 指示を無視（LC 側優先）
   (`managers_chassis_app_db.py:41-44`)

副作用の連鎖:
- FRR の BGP route-map が変更され、全出力ルートが「unreachable」相当にアドバタイズ（TSA）
  またはリストアされる（TSB）

---

## 副作用マトリクス (まとめ)

| テーブル書き込み | 直接の副作用 | 連鎖先 |
|----------------|-------------|--------|
| `SYSTEM_INTERFACE` SET/DEL | リモート LC の nexthop 到達性更新 | routeorch のルート有効/無効化 |
| `SYSTEM_INTERFACE` oper_status=down | リモート LC のリモートポートに向く nexthop を無効化 | — |
| `SYSTEM_NEIGH` SET | リモート LC: SAI neighbor 追加 → STATE_DB `SYSTEM_NEIGH` 書き込み | neighbor-manager がカーネル neighbor/route を追加 |
| `SYSTEM_NEIGH` DEL | リモート LC: SAI neighbor 削除 → STATE_DB エントリ削除 | neighbor-manager がカーネルエントリを削除 |
| `SYSTEM_LAG_TABLE` SET | リモート LC: SAI system LAG 作成 | LAG member 追加・MTU/TPID 設定 |
| `SYSTEM_LAG_TABLE` DEL | リモート LC: SAI system LAG 削除 | — |
| `SYSTEM_LAG_MEMBER_TABLE` SET | リモート LC: SAI LAG member 追加 | — |
| `SYSTEM_LAG_MEMBER_TABLE` DEL | リモート LC: SAI LAG member 削除 | — |
| `BGP_DEVICE_GLOBAL\|STATE` SET (tsa_enabled) | ラインカード bgpcfgd: TSA/TSB route-map push to FRR | BGP アドバタイズメント変更 |
