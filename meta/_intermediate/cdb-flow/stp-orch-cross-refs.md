# stp-orch — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/stp-orch.md` Phase C 追加分。
本ページの主題は `StpOrch` が購読する **APPL_DB の 4 テーブル**
（`STP_VLAN_INSTANCE_TABLE` / `STP_PORT_STATE_TABLE` / `STP_FASTAGEING_FLUSH_TABLE` / `STP_INST_PORT_FLUSH_TABLE`）
と、`StpOrch` が書き込む **STATE_DB `STP_TABLE|GLOBAL`** エントリ。
ここでの「暗黙参照」とは、各テーブルのエントリ処理・フィールド値・タイミングが依存する
**入力側テーブル / Orch / SAI / DB** を指す。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/stporch.cpp` | `StpOrch` コンストラクタ (L17–43), `addVlanToStpInstance()` (L115), `removeVlanFromStpInstance()` (L164), `addStpPort()` (L207), `doStpTask()` (L380), `doStpPortStateTask()` (L429), `doStpFastageTask()` (L488), `doMstInstPortFlushTask()` (L521), `doTask()` (L574), `updateMaxStpInstance()` (L603) |
| `sonic-swss/orchagent/stporch.h` | `StpInstEntry`, `m_vlanAliasToStpInstanceMap`, `m_defaultStpId`, `m_maxStpInstance` |
| `sonic-swss/orchagent/orchdaemon.cpp` | `StpOrch` 登録 (L256–262): APPL_DB 4 テーブルを Subscribe |
| `sonic-swss-common/common/schema.h` | `STATE_STP_TABLE_NAME = "STP_TABLE"` (L445), テーブル名定数 |

## YANG leafref

APPL_DB の STP_VLAN_INSTANCE_TABLE / STP_PORT_STATE_TABLE / STP_FASTAGEING_FLUSH_TABLE / STP_INST_PORT_FLUSH_TABLE は YANG 未モデル化。STATE_DB `STP_TABLE` も YANG 未モデル化。全依存が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. stpd / stpmgrd (APPL_DB 書き手)

- **参照先**: stpd (STP デーモン) → stpmgrd (`cfgmgr/stpmgrd.cpp`) → APPL_DB 4 テーブル
- **参照方向**: 書き込み（`StpOrch` から見ると読み取りトリガ）
- **条件**: 常時。stpmgrd が CONFIG_DB `STP` / `STP_VLAN` / `STP_PORT` 等を購読し、stpd との IPC を仲介して APPL_DB に SET/DEL を書く。`StpOrch` はその結果を Consumer 経由で受け取る。
- **evidence**: `stporch.cpp:44-64` (orchdaemon への渡し方), `orchdaemon.cpp:256-262`

### 2. PORT テーブル / PortsOrch (起動順序ガード)

- **参照先テーブル / Orch**: `PORT` (`PortsOrch::allPortsReady()`)
- **参照方向**: 起動順序ガード
- **条件**: 常時。`StpOrch::doTask()` 冒頭で `allPortsReady()` が false の間はすべてのテーブル処理をスキップ
- **意味**: PortsOrch が `PORT_INIT_DONE` を受信するまで `m_toSync` の全エントリが保留される。エラーログなし。
- **evidence**: `stporch.cpp:578-581`

### 3. VLAN テーブル / PortsOrch (`STP_VLAN_INSTANCE_TABLE` の VLAN 解決)

- **参照先テーブル**: `VLAN` (PortsOrch 内部 Port オブジェクト)
- **参照方向**: 読み取り（PortsOrch::getPort() 経由）
- **条件**: `STP_VLAN_INSTANCE_TABLE` の SET / DEL を処理するとき常時
- **意味**: `addVlanToStpInstance()` / `removeVlanFromStpInstance()` は `gPortsOrch->getPort(vlan_alias, vlan)` で VLAN OID を取得する。VLAN が未登録の場合は `false` を返し、`doStpTask()` が `it++` で残置する。
- **evidence**: `stporch.cpp:123-126`, `stporch.cpp:172-174`

### 4. PORT / LAG テーブル / PortsOrch (`STP_PORT_STATE_TABLE` のポート解決)

- **参照先テーブル**: `PORT`, `LAG` (PortsOrch 内部 Port オブジェクト)
- **参照方向**: 読み取り（PortsOrch::getPort() 経由）
- **条件**: `STP_PORT_STATE_TABLE` の SET / DEL を処理するとき常時
- **意味**: `doStpPortStateTask()` は `gPortsOrch->getPort(port_alias, port)` でポートを取得。未登録の場合は **`return`** で抜ける（コンシューマ全体ブロック）。ポートが登録されても bridge port OID が未作成なら `addBridgePort()` を自動試行する。
- **evidence**: `stporch.cpp:449-453`, `stporch.cpp:218-227`

### 5. SAI STP API (データプレーンへの書き込み先)

- **参照先**: SAI `sai_stp_api` (`create_stp`, `remove_stp`, `create_stp_port`, `remove_stp_port`, `set_stp_port_attribute`)
- **参照方向**: 書き込み（SAI 呼び出し）
- **条件**: 常時。各テーブルの処理関数が SAI STP オブジェクトを作成・更新・削除する。
- **意味**: `STP_VLAN_INSTANCE_TABLE` → `create_stp` + `SAI_VLAN_ATTR_STP_INSTANCE`; `STP_PORT_STATE_TABLE` → `create_stp_port` (初期 `SAI_STP_PORT_STATE_BLOCKING`) + `set_stp_port_attribute`。SAI 失敗時は `it++` 残置または `SAI_NULL_OBJECT_ID` 返却でエントリ保留。
- **evidence**: `stporch.cpp:115-163`, `stporch.cpp:207-258`, `stporch.cpp:314-361`

### 6. SAI Switch 属性 (起動時クエリ)

- **参照先**: `SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID`, `SAI_SWITCH_ATTR_MAX_STP_INSTANCE`
- **参照方向**: 読み取り（起動時 1 回）
- **条件**: `StpOrch::StpOrch()` コンストラクタ内
- **意味**: `m_defaultStpId` (VLAN 削除時の復帰先 OID) と `m_maxStpInstance` (使用上限) の決定。取得失敗時は未初期化のまま動作継続 (silent failure)。
- **evidence**: `stporch.cpp:17-43`

### 7. STATE_DB `STP_TABLE|GLOBAL` (書き込み先)

- **参照先**: STATE_DB `STP_TABLE|GLOBAL.max_stp_inst`
- **参照方向**: 書き込み（StpOrch が producer）
- **条件**: 起動時 (`updateMaxStpInstance()` が SAI クエリ成功時に呼ばれる)
- **意味**: `max_stp_instances - 1` の値を書き込む。`show spanning-tree` 系 CLI / デバッグスクリプトが参照する。
- **evidence**: `stporch.cpp:603-616`, `schema.h:445` (`STATE_STP_TABLE_NAME = "STP_TABLE"`)

### 8. `STP_INST_PORT_FLUSH_TABLE` → `STP_VLAN_INSTANCE_TABLE` (内部 Map 依存)

- **参照先**: `m_vlanAliasToStpInstanceMap` (内部状態、`STP_VLAN_INSTANCE_TABLE` 処理時に更新)
- **参照方向**: 内部 Map 参照（StpOrch 内部の状態遷移）
- **条件**: `STP_INST_PORT_FLUSH_TABLE` の SET 処理時
- **意味**: `doMstInstPortFlushTask()` は `m_vlanAliasToStpInstanceMap[instance]` でフラッシュ対象 VLAN リストを引く。このマップは `addVlanToStpInstance()` が `STP_VLAN_INSTANCE_TABLE` を処理したときにのみ更新される。VLAN→インスタンス割当前にフラッシュ指示が届いても no-op となる。
- **evidence**: `stporch.cpp:553-561`, `stporch.cpp:151-160` (map 更新)

## 参照関係サマリ

```
APPL_DB STP 4 テーブル (StpOrch が購読)
  書き手: stpd → stpmgrd

入力依存 (暗黙参照):
  ├─ [起動ガード] PORT (PortsOrch::allPortsReady)
  │   false の間は全テーブル処理をブロック
  ├─ [VLAN 解決] VLAN (PortsOrch::getPort) — STP_VLAN_INSTANCE_TABLE
  │   未登録なら it++ 残置
  ├─ [ポート解決] PORT / LAG (PortsOrch::getPort) — STP_PORT_STATE_TABLE
  │   未登録なら return (コンシューマ全体ブロック)
  ├─ [SAI 書き込み先] SAI stp_api — 全テーブルが最終的に SAI へ反映
  ├─ [起動時クエリ] SAI Switch 属性 (DEFAULT_STP_INST_ID / MAX_STP_INSTANCE)
  ├─ [内部 Map] m_vlanAliasToStpInstanceMap — STP_INST_PORT_FLUSH_TABLE の前提
  └─ [STATE_DB 出力] STATE_DB STP_TABLE|GLOBAL.max_stp_inst (書き出し先)
```
