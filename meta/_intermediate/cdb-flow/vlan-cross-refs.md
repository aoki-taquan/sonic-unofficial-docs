# VLAN テーブル — 暗黙参照 (Phase C) 調査メモ

調査日: 2026-05-14
対象ソース:
- `sonic-swss/cfgmgr/vlanmgr.cpp`
- `sonic-swss/cfgmgr/vlanmgrd.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py`

---

## 検出した暗黙参照

### 1. DEVICE_METADATA (CONFIG_DB) — `mac` フィールド

- **場所**: `vlanmgrd.cpp` L56-63
- **方向**: `VLAN` 処理開始前に CONFIG_DB `DEVICE_METADATA|localhost.mac` を READ (1 回限り)
- **内容**: `vlanmgrd` は起動直後に `DEVICE_METADATA|localhost` の `mac` フィールドを読み込み、グローバル変数 `gMacAddress` を初期化する。このフィールドが存在しない場合は `runtime_error` をスローして起動失敗となる。`VLAN` エントリの `mac` フィールドが省略されているとき `gMacAddress` がブリッジ MAC として注入される (`vlanmgr.cpp:358`)。
- **YANG leafref としては記述されていない実装上の暗黙依存**。

### 2. STATE_PORT_TABLE (STATE_DB) — readiness ガード

- **場所**: `vlanmgr.cpp` L29, L503-511
- **方向**: `VLAN_MEMBER` の SET 処理時に STATE_DB `STATE_PORT_TABLE` を READ
- **内容**: `VLAN_MEMBER` にポートを追加する前に `isMemberStateOk()` が `STATE_PORT_TABLE` でポートの readiness を確認する (`state=ok`)。ポートが未 ready ならキューに積み直して再試行する。`VLAN` テーブルの処理は直接ではないが、`VLAN_MEMBER` に依存する VLANs のポート割当が STATE_PORT_TABLE の状態に間接依存する。

### 3. STATE_LAG_TABLE (STATE_DB) — readiness ガード

- **場所**: `vlanmgr.cpp` L30, L495-501
- **方向**: `VLAN_MEMBER` の SET 処理時に STATE_DB `STATE_LAG_TABLE` を READ
- **内容**: メンバーポートが `PortChannel` プレフィクスを持つ場合、`isMemberStateOk()` は `STATE_LAG_TABLE` で LAG readiness を確認する。YANG では `PORTCHANNEL_LIST` への leafref で記述されているが、実行時ガードは STATE_DB 側。

### 4. VLAN_MEMBER (CONFIG_DB) — 同一 `vlanmgrd` が共同購読

- **場所**: `vlanmgr.cpp` L28, L555-698, L987
- **方向**: `VLAN_MEMBER` を CONFIG_DB から READ して APP_DB `APP_VLAN_MEMBER_TABLE` に翻訳
- **内容**: `vlanmgrd` は `VLAN` テーブルと `VLAN_MEMBER` テーブルを同一プロセス内で共同購読し、`VLAN` エントリが作成されたタイミングで pending な `VLAN_MEMBER` エントリをフラッシュするロジックを持つ。`VLAN` と `VLAN_MEMBER` の処理は相互依存する順序制約がある。
- `VLAN_MEMBER` の `tagging_mode` が `untagged` / `tagged` / `priority_tagged` 以外の場合、当該エントリは破棄される。

### 5. VLAN_INTERFACE (CONFIG_DB) — 排他制約 (YANG must)

- **場所**: `sonic-vlan.yang` L83-85 (VLAN_INTERFACE_LIST.name leafref)
- **方向**: `VLAN_INTERFACE_LIST.name` は YANG leafref で `VLAN.VLAN_LIST.name` を参照する (READ, バリデーション時)
- **内容**: `VLAN_INTERFACE` を作成するとき、その `name` が既存の `VLAN` エントリを指していることが leafref によって強制される。`VLAN` エントリが存在しない状態で `VLAN_INTERFACE` を投入すると YANG バリデーションが reject する。

### 6. VNET (CONFIG_DB) — vnet_name leafref

- **場所**: `sonic-vlan.yang` L95-99 (VLAN_INTERFACE_LIST.vnet_name leafref)
- **方向**: `VLAN_INTERFACE_LIST.vnet_name` は YANG leafref で `sonic-vnet::VNET_LIST.name` を参照する (READ, バリデーション時)
- **内容**: VXLAN VNET オーバレイ設定時、`VLAN_INTERFACE` に `vnet_name` を指定する場合は対応する `VNET` エントリが先行して存在しなければならない。leafref 違反で reject。

### 7. VRF (CONFIG_DB) — vrf_name leafref

- **場所**: `sonic-vlan.yang` L88-91 (VLAN_INTERFACE_LIST.vrf_name leafref)
- **方向**: `VLAN_INTERFACE_LIST.vrf_name` は YANG leafref で `sonic-vrf::VRF_LIST.name` を参照する (READ, バリデーション時)
- **内容**: `VLAN_INTERFACE` を VRF 内に配置するとき `vrf_name` を指定するが、対応する `VRF` エントリが存在しなければ reject。

### 8. PORT (CONFIG_DB) & PORTCHANNEL (CONFIG_DB) — VLAN_MEMBER leafref

- **場所**: `sonic-vlan.yang` L291-296 (VLAN_MEMBER_LIST.port leafref union)
- **方向**: `VLAN_MEMBER_LIST.port` は `PORT_LIST.name` または `PORTCHANNEL_LIST.name` への leafref (READ, バリデーション時)
- **内容**: `VLAN_MEMBER` に追加できるポートは `PORT` または `PORTCHANNEL` として登録されているものに限られる。
- さらに `must` 制約で以下を禁止:
  - `MIRROR_SESSION` の宛先ポートである場合
  - `PORTCHANNEL_MEMBER` のメンバーである場合
  - `INTERFACE_LIST` にルータインタフェースとして登録されている場合

### 9. DHCP_RELAY (CONFIG_DB) — minigraph から同時生成

- **場所**: `minigraph.py` L1063-1078, L2645
- **方向**: `VLAN` エントリの `dhcpv6_servers` フィールドがある場合、`minigraph.py` は `DHCP_RELAY` テーブルを同時生成する (WRITE)
- **内容**: `minigraph.py` が VLAN XML から `<Dhcpv6Relays>` 要素を見つけると `VLAN.dhcpv6_servers` とともに `DHCP_RELAY|Vlan<N>` エントリを生成する。`VLAN.dhcp_servers` (v4) は `DHCP_RELAY` には書かれず `VLAN` テーブル本体に格納される。CLI では `config vlan dhcp_relay` で個別に `DHCP_RELAY` を管理する。

### 10. dhcprelayd (CONFIG_DB の VLAN を直接購読)

- **場所**: `dhcprelayd.py` L19, L83, L101
- **方向**: `dhcprelayd` は `VLAN` テーブルを CONFIG_DB から直接 READ して relay agent を構成する
- **内容**: `vlanmgrd` が APP_DB `VLAN_TABLE` に書き込む経路とは別に、`dhcprelayd` は CONFIG_DB の `VLAN` テーブルを直接購読して `dhcp_servers` / `dhcpv6_servers` を読む。`VlanTableEventChecker` と `VlanIntfTableEventChecker` という 2 つのチェッカーで `VLAN` と `VLAN_INTERFACE` の変化を監視する。vlanmgrd の処理順序に依存しない独立した購読経路。

### 11. ACL_TABLE (CONFIG_DB) — minigraph での VLAN メンバー展開

- **場所**: `minigraph.py` L1163-1165, L2671
- **方向**: ACL テーブルのバインド先 (AttachTo) に VLAN が指定された場合、`minigraph.py` はその VLAN の全メンバーポートに ACL をバインドする (READ → WRITE 変換)
- **内容**: ACL がエグレスモードで VLAN に attach される場合、`minigraph.py` は `vlan_member_list[vlan_name]` を展開して個々のポートを `ACL_TABLE` のバインド先として登録する。`VLAN_MEMBER` の内容が `ACL_TABLE` に間接的に影響する。

### 12. APP_FDB_TABLE (APP_DB) — PAC (Port Authentication Control)

- **場所**: `vlanmgr.cpp` L35, L822-836, L995
- **方向**: `STATE_OPER_FDB_TABLE` の変化を監視し `APP_DB::APP_FDB_TABLE` に WRITE
- **内容**: ポート認証制御 (PAC) が有効な場合、`vlanmgrd` は `STATE_DB::STATE_OPER_FDB_TABLE` の変化を購読し、FDB エントリを `APP_DB::APP_FDB_TABLE` に書き込む。`VLAN` テーブルへの変更とは直接関係しないが、同一プロセスが担当する暗黙的な副作用。

---

## 参照タイプ別サマリ

| テーブル | DB | 方向 | 契機 | 備考 |
|---------|-----|------|------|------|
| `DEVICE_METADATA.mac` | CONFIG_DB | READ | vlanmgrd 起動時 1 回 | `gMacAddress` 初期化、欠如で起動失敗 |
| `STATE_PORT_TABLE` | STATE_DB | READ | VLAN_MEMBER SET 時 | ポート readiness ガード |
| `STATE_LAG_TABLE` | STATE_DB | READ | VLAN_MEMBER SET 時 | LAG readiness ガード |
| `VLAN_MEMBER` | CONFIG_DB | READ+WRITE | VLAN SET と連動 | 同一プロセス共同購読、順序制約あり |
| `VLAN_INTERFACE.name` | CONFIG_DB | READ (leafref) | YANG バリデーション | VLAN 先行作成必須 |
| `VNET` | CONFIG_DB | READ (leafref) | YANG バリデーション | vnet_name 指定時 |
| `VRF` | CONFIG_DB | READ (leafref) | YANG バリデーション | vrf_name 指定時 |
| `PORT` / `PORTCHANNEL` | CONFIG_DB | READ (leafref+must) | YANG バリデーション | VLAN_MEMBER.port の制約 |
| `MIRROR_SESSION` | CONFIG_DB | READ (must) | YANG バリデーション | dst_port 排他 |
| `INTERFACE` | CONFIG_DB | READ (must) | YANG バリデーション | ルータ IF 排他 |
| `DHCP_RELAY` | CONFIG_DB | WRITE | minigraph 生成時 | dhcpv6_servers から同時生成 |
| `ACL_TABLE` | CONFIG_DB | READ→WRITE | minigraph 生成時 | VLAN メンバー展開 |
| `APP_FDB_TABLE` | APP_DB | WRITE | PAC / FDB 変化 | 同一 vlanmgrd プロセスの副作用 |
