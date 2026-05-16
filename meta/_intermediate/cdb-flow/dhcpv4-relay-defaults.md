# DHCPV4_RELAY — Phase A: コード由来の暗黙デフォルト調査

**調査日**: 2026-05-14  
**対象テーブル**: `DHCPV4_RELAY`  
**Consumer**: `sonic-dhcp-relay` (`dhcp4relay_mgr.cpp` + `dhcp4relay.cpp`)  
**YANG**: `sonic-dhcpv4-relay.yang`

---

## フィールド別 fallback / 挙動まとめ

### `link_selection` (mode-status)

- **YANG default**: `disable`
- **実装挙動**: `disable` → Option82 sub-opt 5 (Link Selection) なし。`enable` → 付与。
- **プラットフォーム依存 (DualToR)**: `DEVICE_METADATA.subtype = "DualToR"` のとき、設定値に関わらず Link Selection が**強制 enable** (`dhcp4relay.cpp:521` `m_config.is_dualTor || config->link_selection_opt == "enable"`)。また `source_interface` も `"Loopback0"` に**自動上書き** (`dhcp4relay.cpp:266`)。
- **複合必須制約 (YANG must)**: `link_selection = enable` のとき `source_interface` が必須。ただし must 違反は YANG バリデーション時のみ検出。ランタイムでは `source_interface` が空なら giaddr は VLAN の primary IP になる (fallback)。
- **dead field リスク**: DualToR 環境では DB の `link_selection` 値は実質無視される。

### `server_id_override` (mode-status)

- **YANG default**: `disable`
- **実装挙動**: `enable` → Option82 sub-opt 11 (Server-ID Override) 付与。値は VLAN の link address (primary IP) そのもの (`dhcp4relay.cpp:530`)。
- **fallback**: `disable` では付与なし。他分岐なし。

### `vrf_selection` (mode-status)

- **YANG default**: `disable`
- **実装挙動**: `enable` かつ client VRF が `"default"` 以外 かつ `server_vrf != client_vrf` のとき、Option82 sub-opt 151 (VSS) を付与。`enable` 設定時に上記3条件が揃わない場合は付与されない (silent no-op)。
- **経路依存**: client VRF は `vlan_vrf_map` から取得。これは `VLAN_INTERFACE.vrf_name` フィールドを参照 (`dhcp4relay.cpp:889`)。フィールド名は `"vrf_name"` (ヘッダ `dhcp4relay.h:30` のコメント: "typo 'vrf' caused VRF-update miss; field is 'vrf_name'")。

### `server_vrf` (leafref)

- **YANG default**: なし (optional)
- **実装 fallback**: `server_vrf` が未設定のとき、`dhcp4relay_mgr.cpp:422-431` で `VLAN_INTERFACE[vlan].vrf_name` を参照。空なら `relay_msg->vrf = "default"` を設定。つまり **server_vrf 未設定 → client VLAN の VRF が server VRF として使われる** (暗黙 fallback)。
- **書き込み順依存**: `DHCPV4_RELAY` エントリ SET より前に `VLAN_INTERFACE[vlan]` の `vrf_name` が書かれていないと、`"default"` が採用されてしまう。後から VRF が割り当てられても `VLAN_INTERFACE_UPDATE` イベントで上書きされる (`vlan_vrf_map` 更新)。

### `source_interface` (union)

- **YANG default**: なし (optional)
- **実装挙動**: 未設定の場合 `giaddr` は VLAN の primary IP address を使用 (`dhcp4relay.cpp:584`)。設定された場合は指定インタフェースの IP を使用 (`dhcp4relay.cpp:581`)。
- **DualToR 強制上書き**: `is_dualTor = true` のとき `source_interface = "Loopback0"` に強制上書き (設定値無視)。
- **giaddr=0 drop**: `source_interface` も VLAN IP も未割当の場合、giaddr=0 となりパケットがドロップされる (`dhcp4relay.cpp:587-592`)。この場合エラーログが出るが YANG バリデーションでは検出不可。

### `agent_relay_mode` (relay-agent-mode)

- **YANG default**: `forward_untouched`
- **実装挙動**: `dhcp4relay.cpp:607-620` で文字列比較。
  - `"append"` → Option82 を保持したまま自分のも追加
  - `"replace"` → Option82 を削除して自分のを追加
  - `"forward"` → Option82 を変更せずそのまま転送
  - それ以外 (未知値・空文字を含む) → **discard (drop)**
- **CRITICAL YANG-実装 discrepancy**: YANG default 値 `"forward_untouched"` はコードで**認識されない**。`"forward"` しか `forward_untouched` 動作をしない。DB に `agent_relay_mode = "forward_untouched"` が書かれると、else 分岐 (discard) に落ちて**全パケットがドロップ**される。
- **silent substitution**: 構造体初期値は `std::string agent_relay_mode` (空文字) であり、DB から field が届かなかった場合も else → discard になる。ただし YANG default が DB に書き込まれれば `"forward_untouched"` → discard という事態になる。

### `max_hop_count` (uint8, range 1..16)

- **YANG default**: `4`
- **C++ struct runtime default**: `uint8_t max_hop_count = MAX_HOP_COUNT` = `16` (dhcp4relay.h:120)
- **YANG-実装 discrepancy**: YANG は 4 を default としているが、C++ struct は 16 で初期化される。DB に値が書かれていない場合 (旧バージョンとの互換等)、`max_hop_count` が parse されずに struct の 16 が使われる可能性がある。ただし YANG を使う CLI/confgen 経由で書かれた設定は 4 が DB に入るため、通常は 4 が適用される。
- **parse 失敗時 silent fallback**: `dhcp4relay_mgr.cpp:411-416` で `stoi()` が例外を投げた場合、WARNING ログのみで struct の値 (初期値 16) のまま続行する。

### `dhcpv4_servers` (leaf-list, min 1)

- **YANG minimum**: min-elements 1 → YANG バリデーション時に強制
- **実装 silent drop**: `dhcp4relay_mgr.cpp:443-447` で servers が空かつ SET の場合、WARNING ログを出して config event を送らずにスキップ。VLAN の relay 設定が適用されない。YANG min-elements 制約は実装の二重チェックを提供するが、DB を直接書いた場合 YANG を通らないため実装の drop のみになる。
- **CSV parse**: DB から `"ip1,ip2"` 形式で届く。`','` で split (`dhcp4relay_mgr.cpp:392-396`)。空文字や不正 IP は parse 時に除外されず `servers` に push_back される。inet_pton での検証は `prepare_relay_server_config` で行われる。

### `hostname` (DEVICE_METADATA 経由・非フィールド)

- Circuit ID のエンコードに使用 (`m_config.hostname`)。
- **暗黙デフォルト**: `metadata_config` struct で `hostname = "sonic"` が初期値 (dhcp4relay.h:174)。DEVICE_METADATA の `hostname` が削除されたとき `dhcp4relay_mgr.cpp:280-282` で `"sonic"` にリセット。

---

## FEATURE=dhcp_server 有効時の挙動変化

`FEATURE.dhcp_server.state = "enabled"` のとき、`DHCPV4_RELAY` テーブルの watch が停止し、代わりに `DHCP_SERVER_IPV4` テーブルを watch する (`dhcp4relay_mgr.cpp:135-157`)。この場合 `DHCPV4_RELAY` への設定変更は完全に無視される (dead consumer)。

---

## discrepancy サマリ

| フィールド | 種別 | 詳細 |
|---|---|---|
| `agent_relay_mode` | YANG-実装 discrepancy | YANG default `"forward_untouched"` はコードで認識されず discard になる |
| `max_hop_count` | YANG-実装 discrepancy | YANG default 4、C++ struct default 16 |
| `link_selection` + DualToR | プラットフォーム依存 | is_dualTor=true のとき設定値無視・Loopback0 強制 |
| `server_vrf` | 書き込み順依存 + fallback | 未設定時に client VLAN VRF を使う。順序ずれで "default" 固定の危険 |
| `dhcpv4_servers` 空 | silent drop | YANG min-elements 違反を YANG 外で書くと silent skip |
| `vrf_selection` | 前提条件依存 | 3条件揃わないと silent no-op |
| feature_dhcp_server | dead consumer | dhcp_server feature=enabled のとき DHCPV4_RELAY 全フィールドが dead |

---

**Evidence sources**:
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay.h` lines 27, 39, 120, 174
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay_mgr.cpp` lines 280-282, 392-447, 422-431
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay.cpp` lines 263-270, 521-549, 577-620, 624-629, 884-895
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dhcpv4-relay.yang` lines 97-130
