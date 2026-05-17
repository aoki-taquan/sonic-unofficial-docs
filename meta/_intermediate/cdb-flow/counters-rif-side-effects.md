# COUNTERS_DB RIF カウンタ — Phase F 副作用スキャンノート

対象テーブル: `COUNTERS_DB / COUNTERS_RIF_NAME_MAP`, `COUNTERS_RIF_TYPE_MAP`, `COUNTERS:<oid>`, `RATES:<oid>`
Consumer/Writer: `IntfsOrch` (`sonic-swss/orchagent/intfsorch.cpp`), `FlexCounterOrch` (`orchagent/flexcounterorch.cpp`), `syncd` FlexCounter
スキャン範囲: `intfsorch.cpp` 全行, `neighorch.cpp`, `routeorch.cpp`, `nhgorch.cpp`, `vnetorch.cpp`

---

## 検出した副作用

### 1. addRifToFlexCounter() — 3 DB への同時書き込み

`addRifToFlexCounter()` (intfsorch.cpp:1527-1552) は RIF 作成時に以下の **3 DB** に対して副作用書き込みを行う:

1. **COUNTERS_DB `COUNTERS_RIF_NAME_MAP`**: `hset "" <name> <oid>` (m_rifNameTable)
2. **COUNTERS_DB `COUNTERS_RIF_TYPE_MAP`**: `hset "" <oid> <type>` (m_rifTypeTable)
3. **FLEX_COUNTER_DB `RIF_STAT_COUNTER:<oid>`**: `set RIF_COUNTER_ID_LIST <id_list>` (startFlexCounterPolling)

これら 3 件の書き込みは直列で行われる（トランザクションなし）。障害時に部分書き込み状態が生じる可能性がある（Phase D 参照）。

### 2. removeRifFromFlexCounter() — 3 DB への同時削除

`removeRifFromFlexCounter()` (intfsorch.cpp:1556-1568) は RIF 削除時に以下を副作用として削除する:

1. **COUNTERS_DB `COUNTERS_RIF_NAME_MAP`**: `hdel "" <name>`
2. **COUNTERS_DB `COUNTERS_RIF_TYPE_MAP`**: `hdel "" <oid>`
3. **FLEX_COUNTER_DB**: `stopFlexCounterPolling()` → syncd がポーリングを停止

`COUNTERS:<oid>` は IntfsOrch が直接削除しない。syncd の FlexCounter 停止後も古い値が COUNTERS_DB に残留する（syncd がクリーンアップを実施する）。

### 3. gPortsOrch->setPort() — Port オブジェクト更新（addRouterIntfs / removeRouterIntfs）

RIF 作成時 (`addRouterIntfs()`, intfsorch.cpp:1309) および削除時 (`removeRouterIntfs()`, intfsorch.cpp:1363) に `gPortsOrch->setPort()` を呼び出し、Port オブジェクトの `m_rif_id` / `m_vr_id` フィールドを更新する。

- RIF 作成後: `port.m_rif_id = <SAI OID>`, `port.m_vr_id = vrf_id`
- RIF 削除後: `port.m_rif_id = 0`, `port.m_vr_id = 0`, `port.m_nat_zone_id = 0`, `port.m_mpls = false`

この Port オブジェクト更新は PortsOrch のインメモリ状態を書き換えるが、APP_DB / STATE_DB への書き込みは発生しない（PortsOrch の内部 map のみ）。

### 4. IntfsOrch::ref_count — NeighOrch / RouteOrch / NhgOrch / VnetOrch からの参照カウント変更

`m_syncdIntfses[alias].ref_count` は以下の orchs から **読み書き**される:

| Orch | 増加 (`increaseRouterIntfsRefCount`) | 減少 (`decreaseRouterIntfsRefCount`) |
|------|-------------------------------------|--------------------------------------|
| NeighOrch | neighbor 追加時 | neighbor 削除時 |
| RouteOrch | nexthop alias を持つルート追加時 | ルート削除時 |
| NhgOrch | nexthop group メンバ追加時 | メンバ削除時 |
| VnetOrch | VNET nexthop 追加時 | VNET nexthop 削除時 |

`ref_count > 0` の RIF は `removeRouterIntfs()` が即座に `false` を返してブロックされ、SAI の `remove_router_interface()` は呼ばれない（intfsorch.cpp:1327-1330）。このブロックは COUNTERS_DB への副作用が生じない（FlexCounter 登録は残ったまま）。

### 5. VoQ 環境での CHASSIS_APP_DB への副作用書き込み

`isChassisDbInUse()` が true の場合（VOQ モード）:

- RIF 作成時: `voqSyncAddIntf()` (intfsorch.cpp:1317) → **CHASSIS_APP_DB `SYSTEM_INTERFACE_TABLE`** に `oper_status` を書き込む
- RIF 削除時: `voqSyncDelIntf()` (intfsorch.cpp:1370) → **CHASSIS_APP_DB `SYSTEM_INTERFACE_TABLE`** の当該エントリを削除
- ポート状態変化時: `voqSyncIntfState()` (intfsorch.cpp:1750) → **CHASSIS_APP_DB `SYSTEM_INTERFACE_TABLE`** の `oper_status` フィールドを更新

これらはシャーシ構成（VOQ）専用であり、通常の非シャーシ構成では発生しない。

### 6. IntfsOrch コンストラクタ — COUNTERS_DB への Lua プラグイン登録

`IntfsOrch::IntfsOrch()` (intfsorch.cpp:61-100) の初期化時に以下の副作用が発生する:

1. `rif_rates.lua` スクリプトを Redis にロード → **COUNTERS_DB にスクリプト SHA が登録される**
2. `setFlexCounterGroupParameter(RIF_STAT_COUNTER_FLEX_COUNTER_GROUP, ...)` → **FLEX_COUNTER_DB** の `RIF_STAT_COUNTER` グループにポーリング間隔・stats_mode・Lua プラグイン SHA が書き込まれる

これらはシステム起動時に一度だけ行われる副作用で、CONFIG_DB の変化とは無関係に IntfsOrch 初期化と同時に発生する。

---

## 副作用まとめ表

| 操作 | 副作用 DB | 対象キー | 方向 |
|------|----------|---------|------|
| RIF 作成 (addRifToFlexCounter) | COUNTERS_DB | `COUNTERS_RIF_NAME_MAP` | 書き込み |
| RIF 作成 (addRifToFlexCounter) | COUNTERS_DB | `COUNTERS_RIF_TYPE_MAP` | 書き込み |
| RIF 作成 (addRifToFlexCounter) | FLEX_COUNTER_DB | `RIF_STAT_COUNTER:<oid>` | 書き込み |
| RIF 作成 (addRouterIntfs) | PortsOrch 内部 | Port.m_rif_id, m_vr_id | 更新 |
| RIF 作成 (VOQ) | CHASSIS_APP_DB | `SYSTEM_INTERFACE_TABLE` | 書き込み |
| RIF 削除 (removeRifFromFlexCounter) | COUNTERS_DB | `COUNTERS_RIF_NAME_MAP` | 削除 |
| RIF 削除 (removeRifFromFlexCounter) | COUNTERS_DB | `COUNTERS_RIF_TYPE_MAP` | 削除 |
| RIF 削除 (removeRifFromFlexCounter) | FLEX_COUNTER_DB | `RIF_STAT_COUNTER:<oid>` | 削除 |
| RIF 削除 (removeRouterIntfs) | PortsOrch 内部 | Port.m_rif_id, m_vr_id | リセット |
| RIF 削除 (VOQ) | CHASSIS_APP_DB | `SYSTEM_INTERFACE_TABLE` | 削除 |
| ref_count 増減 | IntfsOrch 内部 | m_syncdIntfses[alias].ref_count | 更新 |
| IntfsOrch 初期化 | FLEX_COUNTER_DB | `RIF_STAT_COUNTER` グループ設定 | 書き込み |
| syncd ポーリング開始後 | COUNTERS_DB | `COUNTERS:<oid>` | syncd が書き込み |
| Lua プラグイン実行後 | COUNTERS_DB | `RATES:<oid>` | Lua スクリプトが書き込み |

---

## 証跡一覧

| 事実 | ファイル:行 |
|------|-----------|
| addRifToFlexCounter 3 DB 書き込み | `intfsorch.cpp:1537-1551` |
| removeRifFromFlexCounter 削除 | `intfsorch.cpp:1559-1566` |
| addRouterIntfs での setPort() | `intfsorch.cpp:1309` |
| removeRouterIntfs での setPort() | `intfsorch.cpp:1363` |
| ref_count ブロック | `intfsorch.cpp:1327-1330` |
| NeighOrch increaseRouterIntfsRefCount | `neighorch.cpp:349,441` |
| RouteOrch increaseRouterIntfsRefCount | `routeorch.cpp:1362` |
| NhgOrch increaseRouterIntfsRefCount | `nhgorch.cpp:757` |
| VnetOrch increaseRouterIntfsRefCount | `vnetorch.cpp:211` |
| voqSyncAddIntf CHASSIS_APP_DB 書き込み | `intfsorch.cpp:1314-1317` |
| voqSyncDelIntf CHASSIS_APP_DB 削除 | `intfsorch.cpp:1367-1370` |
| voqSyncIntfState CHASSIS_APP_DB 更新 | `intfsorch.cpp:1778` |
| IntfsOrch コンストラクタ Lua/FC 設定 | `intfsorch.cpp:86-100` |
