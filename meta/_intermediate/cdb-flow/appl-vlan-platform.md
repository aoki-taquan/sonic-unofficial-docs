# APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE — プラットフォーム差調査

Task F Phase H: APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` の書き込み・購読経路を ASIC / SAI capability / multi-asic / chassis 観点で `sonic-swss/cfgmgr/vlanmgr.cpp` (`vlanmgr.h` 含む) および `sonic-swss/orchagent/portsorch.cpp` から精読した結果。

## 結論

**プラットフォーム差はテーブル**スキーマ**および書き込み経路には存在しない**（vlanmgrd 側）。一方、購読側 (`PortsOrch`) では SAI capability query の結果に依存して **VLAN flood control type の有効/無効が分岐する**、および MLNX 限定の port-stat plugin 注入が存在する。multi-asic / VOQ chassis 構成について、VLAN テーブルは asic namespace の CONFIG_DB / APPL_DB に置かれ、`vlanmgrd` も `portsorch` も namespace ごとに独立に起動する（host namespace の VLAN は対象外）。

## 根拠

### 1. vlanmgrd: ASIC ベンダー / platform 文字列分岐なし

`cfgmgr/vlanmgr.cpp` / `cfgmgr/vlanmgr.h` 全体に対し `platform` / `asic_type` / `MLNX_PLATFORM_SUBSTRING` / `multi_npu` / `namespace` / `chassis` / 環境変数 `platform` 参照のいずれもヒットしない（`grep -niE 'platform|asic_type|multi.asic|namespace|chassis|MLNX|isMlnx'` で `using namespace std;` / `using namespace swss;` 以外 0 ヒット）。`vlanmgrd` の起動経路 (`cfgmgr/vlanmgrd.cpp`) も同様にプラットフォーム分岐を持たない。

すなわち **APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` に書き込まれるフィールド集合（`admin_status` / `mtu` / `mac` / `host_ifname` / `tagging_mode` / `dynamic`）と暗黙デフォルト値はすべてのプラットフォームで同一**。Linux bridge への `bridge vlan add` / `ip link set` 系コマンドもプラットフォーム非依存（Debian カーネル機能のみに依存）。

### 2. portsorch (購読側): SAI capability 依存の機能分岐

`orchagent/portsorch.cpp` で VLAN 系に関連する capability gate が複数存在する:

- **行 900–917 / 919–932**: `sai_query_attribute_enum_values_capability(gSwitchId, SAI_OBJECT_TYPE_VLAN, SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE, ...)` および `SAI_VLAN_ATTR_BROADCAST_FLOOD_CONTROL_TYPE` を初期化時に問い合わせ、`uuc_sup_flood_control_type` / `bc_sup_flood_control_type` セットに登録する。SAI が `SAI_STATUS_SUCCESS` を返さない ASIC では「This device does not support unknown unicast flood control types」を `SWSS_LOG_NOTICE` で記録し、以降の flood control 切替が抑止される。
- **行 7510–7524** (`addVlanMember()` 内): VLAN_MEMBER に `end_point_ip` を伴う EVPN 系経路では `SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED` capability が UUC / BC 両方で必須。capability がない ASIC では `Flood group with end point ip is not supported` を返して `addVlanMember()` が失敗する。
- **行 7605–7641 / 7781–7849**: VLAN ごとに `SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE` / `SAI_VLAN_ATTR_BROADCAST_FLOOD_CONTROL_TYPE` を `COMBINED` ⇔ `ALL` で切替。capability セットに `COMBINED` がない ASIC では分岐に入れず、デフォルトの `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL`（行 7409–7410 で初期化）のままとなる。
- **行 933–940**: `gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_HOSTIF, SAI_HOSTIF_ATTR_QUEUE)` で `m_supportsHostIfTxQueue` を決定。VLAN host interface (`host_ifname`) の TX queue 設定可否がプラットフォームで分岐するが、`VLAN_TABLE` スキーマ自体には影響しない。

### 3. portsorch: MLNX (Nvidia) 限定のカスタムプラグイン

`orchagent/portsorch.cpp:689–698` で環境変数 `platform` を読み `MLNX_PLATFORM_SUBSTRING` を含むかを判定する `isMlnxPlatform()` がある。行 858–865 で `isMlnxPlatform() && isPortStatSupported(SAI_PORT_STAT_TRIM_PACKETS) && ...` 成立時に `nvdaPortTrimSha` の Lua プラグインを port stat collector に追加する。これは port 統計プラグインの注入であり、VLAN テーブルや VLAN member の書き込み内容には影響しない。

### 4. multi-asic / VOQ chassis での namespace スコープ

`vlanmgrd` は asic namespace 内のコンテナ (`swss@<asicN>`) で起動し、その namespace の CONFIG_DB / APPL_DB のみを購読・書込みする。`vlanmgr.cpp` 自体に `is_multi_npu()` / `namespace_string` 等の判定は無く、host CONFIG_DB と asic CONFIG_DB の使い分けは `swss` コンテナ起動時の引数および `ConfigDBConnector` の namespace パラメータ（`vlanmgrd.cpp` の `Select` ループ初期化部）で決定される。`portsorch` も同様に asic namespace 内で完結する。

VOQ chassis 構成では、line card 各 asic で独立した `VLAN_TABLE` / `VLAN_MEMBER_TABLE` セットが存在する。chassis-wide で VLAN を統合する経路（`CHASSIS_APP_DB` への昇格）は VLAN 系には存在せず（`portsorch` で `CHASSIS_APP_DB` を参照する経路は SYSTEM_PORT / SYSTEM_NEIGH のみ）、APPL_DB レベルでは各 asic ローカル。

### 5. host_ifname の Linux bridge 経路

`vlanmgr.cpp` が APPL_DB に `host_ifname` を書く（vlanmgr.cpp:359, 434）一方で、`portsorch` が `createVlanHostIntf()` を呼ぶ実体は SAI `sai_hostif_api->create_hostif()` 経由。Linux bridge / netdev 名前空間の制約（IFNAMSIZ=16）はカーネル側の制約であり、ASIC ベンダーには依存しない。

## まとめ

- **APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` のスキーマおよびデフォルト値は全プラットフォーム共通**。`vlanmgrd` は ASIC / multi-asic / chassis を意識しない。
- 購読側 (`PortsOrch`) では **SAI capability query の結果に応じた振る舞いの差** が以下で発生する:
  - `SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED` 未対応 ASIC では VLAN flood control を `ALL` 固定（切替されない）。
  - `end_point_ip` 付き VLAN_MEMBER (EVPN VxLAN flood group) は capability 必須で、未対応 ASIC では `addVlanMember()` が失敗する。
  - `SAI_HOSTIF_ATTR_QUEUE` 未対応 ASIC では VLAN host interface の TX queue 設定が無効化される。
- **MLNX 限定**: `isMlnxPlatform()` が true の場合のみ port stat 用 Lua プラグイン (`nvdaPortTrimSha`) が追加される。これは VLAN テーブル書き込みではなく counter 系の差分。
- multi-asic / VOQ chassis 構成では `vlanmgrd` / `portsorch` が asic namespace ごとに独立に走り、APPL_DB の `VLAN_TABLE` も asic ローカル。chassis-wide 統合経路は VLAN には存在しない。
