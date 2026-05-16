# VLAN_INTERFACE — 暗黙参照テーブル調査 (Phase C)

調査日: 2026-05-15  
対象テーブル: `VLAN_INTERFACE`  
調査方針: `grep VLAN_INTERFACE` 1 回実行後、ヒットした各ファイルを LSP + 全行精読。

## 調査対象ファイル

### sonic-swss
- `cfgmgr/intfmgr.cpp` — VLAN_INTERFACE の主購読者

### sonic-utilities
- `config/main.py` — CLI 書き込み元
- `utilities_common/cli.py` — インターフェース種別判定
- `show/vlan.py` — VLAN + IP 表示
- `show/vnet.py` — VNET 表示 (VLAN_INTERFACE 読み取り)
- `show/main.py` — NAT zone 確認コマンド
- `scripts/natconfig` — NAT 設定スクリプト
- `scripts/neighbor_advertiser` — neighbor_advertiser デーモン
- `fdbutil/filter_fdb_entries.py` — FDB エントリフィルタ
- `generic_config_updater/services_validator.py` — GCU サービス検証

### sonic-buildimage
- `src/sonic-config-engine/minigraph.py` — ネットワークデバイス初期設定生成
- `src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py` — DHCP server 監視
- `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py` — DHCP server 設定生成

### sonic-dhcp-relay
- `dhcp4relay/src/dhcp4relay.cpp` — DHCPv4 relay (VRF 取得 + VLAN_INTERFACE_UPDATE イベント)
- `dhcp6relay/src/config_interface.cpp` — DHCPv6 relay (VLAN_INTERFACE 存在確認)

### sonic-mgmt-common
- `translib/transformer/xfmr_intf.go` — REST/gNMI OpenConfig interface 変換
- `translib/transformer/sw_vlan.go` — VLAN OpenConfig 変換

## 暗黙参照関係の全量

### 1. VLAN (必須前提: leafref VLAN.name)

**種別**: YANG leafref (`sonic-vlan.yang` 内 `leafref "/sonic-vlan/VLAN_INTERFACE_LIST/VLAN_INTERFACE_LIST_ENTRY/name"` が `VLAN_LIST.name` を参照)

**根拠**:
- YANG `sonic-vlan.yang`: `VLAN_INTERFACE_LIST.name` は `leafref "/sonic-vlan/VLAN/VLAN_LIST/name"` で VLAN テーブルへの公式 leafref が定義済み。
- `intfmgr.cpp`: VLAN インターフェースが VLAN テーブルより先に処理された場合 `task_need_retry`。
- `show/vlan.py:130`: `vlan_ip_data = db.cfgdb.get_table('VLAN_INTERFACE')` で VLAN 表示に VLAN_INTERFACE を結合。

**実装上の挙動**: VLAN テーブルが orchagent で未処理の場合、`IntfsOrch` は `task_need_retry` を返し VLAN_INTERFACE の処理を保留する。

### 2. VRF (条件付き: vrf_name フィールド)

**種別**: YANG leafref (`vrf_name` は `leafref "/sonic-vrf/VRF/VRF_LIST/name"`)

**根拠**:
- YANG `sonic-vlan.yang` で公式 leafref 定義済み。
- `intfmgr.cpp`: `isIntfChangeVrf()` で VRF 変更検出。`VRF` が STATE_DB に未登録の場合リトライ待ち。
- `dhcp4relay/src/dhcp4relay.cpp:885`: `/* get VRF attached to the vlan from VLAN_INTERFACE table */` — dhcp4relay が VLAN_INTERFACE から VRF 名を読み取り、VRF 対応ソケットを生成する。

**実装上の挙動**: `vrf_name` 設定時、intfmgrd が STATE_DB `VRF_TABLE|<name>` の存在を確認してから処理。未登録なら `m_toSync` に積みリトライ。

### 3. VNET (条件付き: vnet_name フィールド)

**種別**: YANG leafref (`vnet_name` は `leafref "/sonic-vnet/VNET/VNET_LIST/name"`)

**根拠**:
- YANG `sonic-vlan.yang` で公式 leafref 定義済み。
- `show/vnet.py:92`: `VLAN_INTERFACE` テーブルを VNET 表示の一環として読み取り。

**実装上の挙動**: `vnet_name` 指定時、orchagent が `VNET` テーブルの対応エントリを参照して Overlay ルーティングを設定。

### 4. DHCP_RELAY / DHCP_SERVER_IPV4 (間接依存: 読み取り元)

**種別**: 暗黙参照（YANG leafref なし、実行時読み取り）

**根拠**:
- `dhcp6relay/src/config_interface.cpp:130,135`: dhcp6relay が `VLAN_INTERFACE|<vlan>|*` パターンで IPv6 プレフィックスを検索し、エントリがなければ `LOG_WARNING: "%s doesn't exist in VLAN_INTERFACE table, skip it"` でスキップ。
- `dhcp4relay/src/dhcp4relay.cpp:885-887`: dhcp4relay が `VLAN_INTERFACE|<vlan>` から `vrf_name` を読み取り、VRF 対応ソケットを生成。
- `src/sonic-dhcp-utilities/dhcpservd/dhcp_cfggen.py:69`: dhcpservd が `VLAN_INTERFACE` 全量を読み取り、サブネット・GW を kea-dhcp4 設定に変換。

**実装上の挙動**: DHCP relay/server コンテナが起動時・設定変更時に VLAN_INTERFACE を読み取り、IPv6/IPv4 アドレスをリレー対象アドレスとして使用。VLAN_INTERFACE に IP が設定されていないと DHCP 転送が機能しない。

### 5. NAT (条件付き: nat_zone フィールド)

**種別**: 暗黙参照（YANG では uint8 型、実行時に natmgr が参照）

**根拠**:
- `scripts/natconfig:205`: `interfaces = ['INTERFACE', 'VLAN_INTERFACE', 'PORTCHANNEL_INTERFACE', 'LOOPBACK_INTERFACE']` — NAT 設定スクリプトが全インターフェーステーブルを走査。
- `show/main.py:1609`: `interface = "VLAN_INTERFACE"` — NAT zone 表示コマンドが VLAN_INTERFACE を対象に含む。

**実装上の挙動**: `nat_zone` に `1`〜`3` を設定すると natmgr が対応 zone の SNAT/DNAT ルールを VLAN インターフェースに紐づける。

### 6. neighbor_advertiser (間接依存: 読み取り元)

**種別**: 暗黙参照（実行時読み取り）

**根拠**:
- `scripts/neighbor_advertiser:101,172,212,289`: `vlan_interface_query = config_db.get_table('VLAN_INTERFACE')` — neighbor_advertiser が VLAN_INTERFACE の IP アドレスリストを取得し、arp/nd パケットを送出する対象を決定。

**実装上の挙動**: VLAN L3 インターフェースに IP が付与されていると neighbor_advertiser が gratuitous ARP / ND を送出。

### 7. FDB フィルタ (fdbutil)

**種別**: 暗黙参照（実行時読み取り）

**根拠**:
- `fdbutil/filter_fdb_entries.py:30-31`: `if "VLAN_INTERFACE" in config_db_entries and "VLAN" in config_db_entries:` — VLAN が L3 として有効化されている場合に FDB フィルタ動作が変わる。

**実装上の挙動**: VLAN_INTERFACE が存在する VLAN では、FDB エントリのフィルタロジックが調整される（L3 ルーティング対象 VLAN の FDB エントリをフィルタ）。

### 8. GCU (generic_config_updater) サービス検証

**種別**: 暗黙参照（設定変更時の再起動対象判断）

**根拠**:
- `generic_config_updater/services_validator.py:163-164`: `old_vlan_intf = old_config.get("VLAN_INTERFACE", {})` — GCU が VLAN_INTERFACE 変更時にサービス再起動が必要か判断。
- `gcu_services_validator.conf.json:52`: `"VLAN_INTERFACE": {...}` — GCU のサービス検証設定に VLAN_INTERFACE が含まれる。

### 9. REST/gNMI OpenConfig (sonic-mgmt-common)

**種別**: 暗黙参照（OpenConfig to ConfigDB 変換）

**根拠**:
- `translib/transformer/xfmr_intf.go:152`: `intfTN: "VLAN_INTERFACE"` — OpenConfig `interfaces/interface` (type=VLAN) が VLAN_INTERFACE テーブルにマッピング。
- `translib/transformer/xfmr_intf.go:416-418`: VLAN インターフェース検索時に VLAN_INTERFACE を対象に追加。
- `translib/transformer/sw_vlan.go:1179-1181`: VLAN 削除時に `VLAN_INTERFACE` テーブルの関連エントリを削除処理。

**実装上の挙動**: REST/gNMI 経由で OpenConfig `interfaces` を GET すると VLAN_INTERFACE が参照される。VLAN 削除時に VLAN_INTERFACE も連動して削除される。

## 結論: YANG leafref vs 実装上の暗黙参照

| 参照先テーブル | YANG leafref | 実装上の必須度 | 参照方向 |
|---|---|---|---|
| `VLAN` | ✅ あり | 必須 (task_need_retry) | VLAN_INTERFACE → VLAN |
| `VRF` | ✅ あり | 条件付き必須 | VLAN_INTERFACE → VRF |
| `VNET` | ✅ あり | 条件付き必須 | VLAN_INTERFACE → VNET |
| `DHCP_RELAY` / `DHCP_SERVER_IPV4` | なし | 実質必須 (IP なしで機能不全) | 被参照 (DHCP → VLAN_INTERFACE) |
| NAT (`nat_zone`) | なし | 条件付き (nat_zone≥1 時) | VLAN_INTERFACE → natmgr |
| `neighbor_advertiser` | なし | 間接 | 被参照 |
| FDB フィルタ | なし | 間接 | 被参照 |
| GCU 検証 | なし | 間接 | 被参照 |
| OpenConfig REST/gNMI | なし | 間接 | 被参照 (OpenConfig → VLAN_INTERFACE) |
