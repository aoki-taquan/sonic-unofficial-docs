# VLAN テーブル — Phase A: コード由来のデフォルト解析

生成日: 2026-05-14  
対象ファイル: `sonic-swss/cfgmgr/vlanmgr.cpp`、`sonic-swss/orchagent/portsorch.cpp`、`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang`

---

## フィールドごとのデフォルト・挙動まとめ

### `admin_status`

- **YANG デフォルト**: 未指定（optional leaf）
- **コード由来デフォルト**: `vlanmgrd` の `doVlanTask()` (vlanmgr.cpp:422-426) で、`fvVector` が空（`admin_status` フィールドが CONFIG_DB エントリになかった場合）のとき、`FieldValueTuple a("admin_status", "up")` を自動補完して APP_DB に書く。
- **結論**: `admin_status` 省略時は `"up"` がコードレベルで注入される。YANG には default 宣言なし。
- **証拠**: `vlanmgr.cpp:421-426`

### `mtu`

- **YANG デフォルト**: なし（optional leaf, range 1..9216）
- **コード由来デフォルト**: `doVlanTask()` の冒頭 (vlanmgr.cpp:357) で `string mtu = DEFAULT_MTU_STR;`（= `"9100"`）で初期化。フィールドが存在すれば上書きするが、**実際には `setHostVlanMtu()` を呼ばない**（TODO コメント vlanmgr.cpp:401-406）。
- **APP_DB への書き込み**: `mtu` は常に `fvVector` に追加されて APP_DB `VLAN_TABLE` へ書かれる（vlanmgr.cpp:428-429）。値は明示指定がなければ `"9100"`。
- **orchagent 側**: `portsorch.cpp:doVlanTask()` で APP_DB から `mtu` を読み、`mtu != 0` の場合 `vl.m_mtu` を更新してルータインタフェース MTU に反映するが、ホスト側 netdev への `ip link set mtu` は今も TODO 状態。
- **結論**: `mtu` 省略時は `9100` がハードコードで APP_DB に注入される。ホスト側 netdev MTU は**実際には変更されない**（silent drop / TODO）。
- **証拠**: `vlanmgr.cpp:19,357,428-429`, `vlanmgr.cpp:400-406`

### `mac`

- **YANG デフォルト**: なし
- **コード由来デフォルト**: `doVlanTask()` (vlanmgr.cpp:358) で `string mac = gMacAddress.to_string();` として初期化（グローバルスイッチ MAC）。`mac` フィールドが存在すれば上書き。
- **addHostVlan()**: VLAN インタフェース生成時 (vlanmgr.cpp:131) にも `gMacAddress.to_string()` を `ip link add ... address` に使用。
- **gMacAddress 未初期化ガード**: `isVlanMacOk()` (vlanmgr.cpp:312-314) が `!!gMacAddress` を確認し、未初期化なら全 VLAN タスクを delay する（vlanmgr.cpp:318-321）。
- **orchagent 側**: APP_DB の `mac` フィールドが非空なら `vl.m_mac` を更新し `gIntfsOrch->setRouterIntfsMac(vl)` を呼ぶ（portsorch.cpp:5811-5817）。
- **結論**: `mac` 省略時はスイッチ MAC (`gMacAddress`) が自動補完される。gMacAddress が未初期化の間はタスク全体が保留される（書き込み順依存）。
- **証拠**: `vlanmgr.cpp:131,312-321,358`

### `vlanid`

- **YANG デフォルト**: なし（optional leaf）
- **YANG 制約**: `must "substring-after(../name, 'Vlan') = current()"` — `name` 末尾と数値不一致で reject。
- **コード側**: `doVlanTask()` はキーの数値部分 (`key.substr(4)`) を `stoi()` して vlan_id を取得する（vlanmgr.cpp:342）。`vlanid` フィールドは**コードで直接使用されない**（dead consumer として機能）。
- **結論**: `vlanid` フィールドはコードでは読まれない。YANG バリデーション専用フィールド。省略可能で実害なし。
- **証拠**: `vlanmgr.cpp:339-349`（`vlanid` フィールドを iteration していない）

### `dhcp_servers` / `dhcpv6_servers`

- **YANG デフォルト**: なし（leaf-list, ordered-by user）
- **vlanmgrd での扱い**: `doVlanTask()` は `dhcp_servers` / `dhcpv6_servers` を一切読まない（`fvField` チェックなし）。APP_DB にも書かれない。
- **consumer**: `dhcprelayd`（sonic-dhcp-relay リポ）が CONFIG_DB `VLAN` テーブルを直接 subscribe して `dhcp_servers` を読む。vlanmgrd 経由の APP_DB 経路は存在しない。
- **結論**: `dhcp_servers`/`dhcpv6_servers` は vlanmgrd にとってデッドフィールド（読まれない）。dhcprelayd が CONFIG_DB を直接購読する経路依存構造。省略時は dhcprelayd が relay を起動しない（正常動作）。
- **証拠**: `vlanmgr.cpp:388-419`（`dhcp_servers` の case なし）

### `alias` / `description`

- **YANG デフォルト**: なし
- **コード**: `doVlanTask()` はどちらのフィールドも読まず、APP_DB にも書かない。
- **結論**: 完全 dead field（コードで消費されない）。CONFIG_DB に保存されるのみ。
- **証拠**: `vlanmgr.cpp:388-419`

### `host_ifname`（内部フィールド）

- YANG 定義にないが、vlanmgrd が `host_ifname` フィールドを APP_DB に書く（vlanmgr.cpp:418-419,434-435）。orchagent の `portsorch.cpp:doVlanTask()` がこれを読んで `createVlanHostIntf()` を呼ぶ。
- **デフォルト**: 省略時は空文字列 `""` が APP_DB に書かれる（vlanmgr.cpp:359,434-435）。orchagent は空なら `createVlanHostIntf()` を呼ばない（portsorch.cpp:5820）。
- **結論**: YANG に存在しない隠し伝達フィールド。ユーザは直接書かない。

### `members@`（内部フィールド）

- minigraph 系設定から来る `members@` フィールド（カンマ区切り）を vlanmgrd が読む（vlanmgr.cpp:408-409,451-454）。
- `processUntaggedVlanMembers()` を呼んで `VLAN_MEMBER` の untagged 設定を自動注入する。
- **結論**: minigraph 互換の内部フィールド。CLI 経由では設定されない。

---

## 経路依存乖離 / 書き込み順依存

1. **gMacAddress 未初期化**: スイッチの MAC アドレスが確定する前に VLAN 設定が届いても、vlanmgrd は全タスクを delay する。MAC 確定後に再処理。
2. **mtu ホスト側無視**: APP_DB には mtu が書かれるが、ホスト netdev (`ip link set Vlan<N> mtu`) は適用されない。member が設定され VLAN state が UNKNOWN でなくなった後に適用する設計だが未実装。
3. **dhcp_servers はvlanmgrd をバイパス**: CONFIG_DB を dhcprelayd が直接読む構造のため、vlanmgrd の処理順序に依存しない。

---

## SAI レベルのデフォルト（orchagent addVlan）

`portsorch.cpp:addVlan()` (line 7381-7419) は `SAI_VLAN_ATTR_VLAN_ID` のみ指定して `sai_vlan_api->create_vlan()` を呼ぶ。その他の SAI VLAN 属性（flooding control 等）は SAI/プラットフォームデフォルトに委ねられる。

- `vlan.m_vlan_info.uuc_flood_type` = `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL`（orchagent 内部構造体のみ、SAI に明示設定せず）
- `vlan.m_vlan_info.bc_flood_type` = `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL`（同上）

---

## `<!-- defaults -->` ブロック用テキスト案

```markdown
<!-- defaults -->
## コード由来の暗黙デフォルト

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `admin_status` | なし | `"up"` — fvVector 空時に自動補完 (vlanmgr.cpp:424) | vlanmgrd |
| `mtu` | なし | `9100` (`DEFAULT_MTU_STR`) — 省略時に APP_DB へ注入 (vlanmgr.cpp:19,357,428) | vlanmgrd |
| `mac` | なし | `gMacAddress`（スイッチ MAC）— 省略時に APP_DB へ注入 (vlanmgr.cpp:358) | vlanmgrd |
| `vlanid` | なし | コードで未使用（dead field）。YANG バリデーション専用 | - |
| `alias` | なし | コードで未使用（dead field） | - |
| `description` | なし | コードで未使用（dead field） | - |
| `dhcp_servers` | なし（leaf-list）| vlanmgrd は無視。dhcprelayd が CONFIG_DB を直接購読 | dhcprelayd |
| `dhcpv6_servers` | なし（leaf-list）| vlanmgrd は無視。dhcprelayd が CONFIG_DB を直接購読 | dhcprelayd |

### 注記

- **`mtu` の silent drop**: `mtu` は APP_DB に書かれるが、ホスト側 netdev (`ip link set Vlan<N> mtu`) への適用は TODO 状態（vlanmgr.cpp:401-406）。
- **`mac` の書き込み順依存**: `gMacAddress` が未初期化（スイッチ MAC 未確定）の間、vlanmgrd は全 VLAN タスクを保留する（vlanmgr.cpp:318-321）。
- **`dhcp_servers` の経路乖離**: vlanmgrd→APP_DB 経路を通らず、dhcprelayd が CONFIG_DB `VLAN` テーブルを直接購読する。
- **SAI デフォルト**: orchagent は VLAN ID のみ指定して `sai_vlan_api->create_vlan()` を呼ぶ（portsorch.cpp:7392）。flooding control 等はプラットフォーム SAI デフォルトに委ねられる。
<!-- /defaults -->
```
