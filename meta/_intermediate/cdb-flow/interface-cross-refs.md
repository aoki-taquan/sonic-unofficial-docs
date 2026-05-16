# INTERFACE テーブル — 暗黙参照 (Phase C) 調査メモ

調査日: 2026-05-14 (更新: 2026-05-16)
対象ソース:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-interface.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-mgmt-common/translib/transformer/xfmr_intf.go`

---

## 検出した暗黙参照

### 0. PORT テーブル / PortOrch (CONFIG_DB + orchagent 内部)

- **場所**: `intfsorch.cpp` L403, L609, L905, L1085, L1216-1251
- **方向**: `INTERFACE` SET 時に `gPortsOrch->getPort(alias, port)` を呼び出して PORT オブジェクトを取得 (READ)
- **内容**: ポートの `m_type`（`Port::PHY` / `Port::LAG` / `Port::VLAN` / `Port::SUBPORT`）と SAI port oid を取得し、`SAI_ROUTER_INTERFACE_ATTR_TYPE` と `SAI_ROUTER_INTERFACE_ATTR_PORT_ID` に設定する。PortOrch に登録されていないポートは RIF 作成をスキップ。YANG leafref `PORT.name` とは独立した実行時依存。

### 0b. VLAN_INTERFACE / PORTCHANNEL_INTERFACE / LOOPBACK_INTERFACE (warm-reboot replay)

- **場所**: `intfmgr.cpp` L267-283 (`buildIntfReplayList()`)
- **方向**: warm-reboot 時のみ CONFIG_DB の兄弟テーブルを横断的に READ
- **内容**: `intfmgrd` の warm-start 時、`buildIntfReplayList()` が `INTERFACE`・`LOOPBACK_INTERFACE`・`VLAN_INTERFACE`・`LAG_INTERFACE` の全キーを収集して `m_pendingReplayIntfList` に追加する。通常起動では発生しない暗黙参照。

### 0c. STATE_VLAN_TABLE (STATE_DB)

- **場所**: `intfmgr.cpp` L39, L55-56, L653-659
- **方向**: alias が `Vlan` プレフィクスのとき `m_stateVlanTable.get()` を呼び出して VLAN readiness を確認 (READ)
- **内容**: `VLAN_INTERFACE` テーブルのエントリ処理時に使用されるガード。物理 `INTERFACE` エントリでは通常この分岐に入らないが、`isIntfStateOk()` は INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE を統一的に処理するため同じコードパスに存在する。

### 1. STATE_PORT_TABLE (STATE_DB)

- **場所**: `intfmgr.cpp` L37, L46-47, L553, L566, L686
- **方向**: `INTERFACE` → `STATE_PORT_TABLE` を参照 (READ)
- **内容**: `intfmgrd` は `INTERFACE` の SET を受け取ったとき、対象ポートが `STATE_DB::STATE_PORT_TABLE` に存在しかつ `state=ok` であることを確認してから処理を進める。ポートが未 ready なら Consumer キューに戻し再試行。
- **YANG 上の leafref とは別**に、実行時の readiness ガードとして機能する実装上の依存。

### 2. STATE_LAG_TABLE (STATE_DB)

- **場所**: `intfmgr.cpp` L38, L51-52, L548, L563, L663
- **方向**: `INTERFACE` → `STATE_LAG_TABLE` を参照 (READ)
- **内容**: 名前が `PortChannel` プレフィクスのとき LAG readiness を `STATE_LAG_TABLE` で確認する。物理ポートと同じガードロジック。

### 3. STATE_VRF_TABLE (STATE_DB)

- **場所**: `intfmgr.cpp` L40, L671-684
- **方向**: `INTERFACE` → `STATE_VRF_TABLE` を参照 (READ)
- **内容**: `vrf_name` または `vnet_name` が指定されたとき、VRF / VNET が `STATE_DB::STATE_VRF_TABLE` に登録済みであることを確認する。未登録なら SET をスキップ。YANG leafref で `VRF.name` を参照するが、runtime 依存は STATE_DB 側。

### 4. DEVICE_METADATA (CONFIG_DB)

- **場所**: `intfmgr.cpp` L71-75
- **方向**: `INTERFACE` 処理開始時に CONFIG_DB `DEVICE_METADATA|localhost` の `switch_type` フィールドを読む (READ, 1 回限り)
- **内容**: `switch_type == "voq"` のとき IPv6 アドレス追加コマンドに `metric 256` を付与する。VoQ スイッチ判定に使用。プラットフォーム固有の隠れた参照。

### 5. NAT_GLOBAL / gIsNatSupported (グローバルフラグ)

- **場所**: `intfsorch.cpp` L36, L978, L1287-1294
- **方向**: orchagent 起動時に `NAT_GLOBAL` テーブルから NAT サポートフラグを読み込み、グローバル変数 `gIsNatSupported` にセット。`INTERFACE` の処理時にこのフラグを参照する。
- **内容**: `gIsNatSupported == true` のとき SAI router interface 作成時に `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` を設定する。NAT が無効なプラットフォームでは `nat_zone` フィールドを設定しても SAI には渡らない。

### 6. gMacAddress (DEVICE_METADATA 由来グローバル)

- **場所**: `intfsorch.cpp` L1198-1207; `orchagent/main.cpp` L51, L494, L675-678, L877-888
- **方向**: orchagent 起動時に `DEVICE_METADATA|localhost|mac` を読み `gMacAddress` に格納。`INTERFACE` の router interface 作成時にポート固有の MAC が未指定 (`mac_addr` フィールドなし) の場合に `gMacAddress` をフォールバックとして使用。
- **内容**: `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` に設定される値が間接的に `DEVICE_METADATA` に依存する。

### 7. VLAN_MEMBER (CONFIG_DB) — 排他参照

- **場所**: `sonic-vlan.yang` L305
- **方向**: `VLAN_MEMBER_LIST` の `must` 制約が `INTERFACE_LIST` を参照する (READ)
- **内容**: `must "not(/intf:sonic-interface/intf:INTERFACE/intf:INTERFACE_LIST[intf:name=current()])"` — `VLAN_MEMBER` にポートを追加するとき、そのポートが既に `INTERFACE_LIST` に登録されていないことを YANG バリデーションで強制する。逆方向の排他ガード。

### 8. minigraph.py — port_config.ini (プラットフォーム JSON 参照)

- **場所**: `minigraph.py` L2064, L2394-2396
- **内容**: `sonic-cfggen -m <minigraph.xml>` 実行時に `get_port_config()` を呼び出して `port_config.ini` または `platform.json` からポート一覧を取得する。`INTERFACE` テーブルの key（ポート名）はこのポートリストと照合され、存在しないポート名は警告付きでスキップされる。プラットフォーム JSON がポート集合を決定するという暗黙参照。

### 9. CHASSIS_APP_DB::SYSTEM_INTERFACE_TABLE (VoQ 専用)

- **場所**: `intfsorch.cpp` L105-107, L1316-1317, L1369-1370, L1672-1750
- **方向**: VoQ スイッチ (`gMySwitchType == "voq"`) のとき、`INTERFACE` の ADD/DEL に連動して `CHASSIS_APP_DB::SYSTEM_INTERFACE_TABLE` に書き込む (WRITE)
- **内容**: ラインカード間でのインタフェース同期に使用。VoQ 以外では無関係。

### 10. APP_NEIGH_TABLE (APP_DB) — IPv6 link-local ネイバー削除

- **場所**: `intfmgr.cpp` L43, L712-738
- **方向**: `ipv6_use_link_local_only` を `disable` に変更したとき、`APP_DB::NEIGH_TABLE` を走査して対象 IF の link-local ネイバーエントリを削除する
- **内容**: `INTERFACE` フィールドの変更が APP_DB のネイバーテーブルを副作用として書き換える暗黙的な依存。

---

## 参照タイプ別サマリ

| テーブル | DB | 方向 | 契機 | 備考 |
|---------|-----|------|------|------|
| `PORT` (via PortOrch) | CONFIG_DB | READ | RIF 作成時 | port type / SAI oid 取得 |
| `VLAN_INTERFACE` | CONFIG_DB | READ | warm-reboot replay のみ | `buildIntfReplayList()` |
| `PORTCHANNEL_INTERFACE` | CONFIG_DB | READ | warm-reboot replay のみ | `buildIntfReplayList()` |
| `LOOPBACK_INTERFACE` | CONFIG_DB | READ | warm-reboot replay のみ | `buildIntfReplayList()` |
| `STATE_VLAN_TABLE` | STATE_DB | READ | `Vlan` プレフィクス alias のとき | `isIntfStateOk()` 共通コードパス |
| `STATE_PORT_TABLE` | STATE_DB | READ | SET 時 readiness ガード | ポート名が `PortChannel` / `Vlan` 以外 |
| `STATE_LAG_TABLE` | STATE_DB | READ | SET 時 readiness ガード | `PortChannel` プレフィクス / LAG サブ IF |
| `STATE_VRF_TABLE` | STATE_DB | READ | `vrf_name` / `vnet_name` 指定時 | VRF/VNET readiness |
| `DEVICE_METADATA` | CONFIG_DB | READ | intfmgrd 起動時 1 回 | `switch_type=voq` 判定 |
| `NAT_GLOBAL` / `gIsNatSupported` | CONFIG_DB | READ | orchagent 起動時 | NAT_ZONE_ID SAI 設定の可否 |
| `DEVICE_METADATA.mac` / `gMacAddress` | CONFIG_DB | READ | orchagent 起動時 | RIF MAC フォールバック |
| `VLAN_MEMBER` (YANG must) | CONFIG_DB | READ | YANG バリデーション | 排他制約 (逆方向) |
| `port_config.ini` / `platform.json` | ファイル | READ | `sonic-cfggen -m` | ポート名存在確認 |
| `CHASSIS_APP_DB::SYSTEM_INTERFACE_TABLE` | CHASSIS_APP_DB | WRITE | VoQ ADD/DEL | VoQ 専用 |
| `APP_NEIGH_TABLE` | APP_DB | WRITE | IPv6 LL disable 時 | link-local ネイバー削除 |
