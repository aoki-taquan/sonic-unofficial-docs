# VLAN_INTERFACE — Phase A 暗黙デフォルト調査

調査日: 2026-05-14  
対象ファイル:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang`

---

## フィールド別デフォルト・暗黙挙動

### nat_zone

- **YANG default**: `"0"` (sonic-vlan.yang L111)
- **orchagent**: `nat_zone_id = 0` でローカル変数初期化 (intfsorch.cpp:713)
- **SAI 条件分岐**: `gIsNatSupported` が false の場合、`nat_zone_id=0` は SAI に送信されない。  
  `SWSS_LOG_NOTICE("Not set router interface %s NAT Zone Id to %u, as NAT is not supported")` が記録される (intfsorch.cpp:984)
- **結論**: YANG/APP_DB では常に `0`、ただし SAI への反映はプラットフォーム依存

### mpls

- **YANG default**: なし（フィールド省略可能）
- **intfmgr 暗黙 default**: `mpls.empty()` を `"disable"` と等価に扱う (intfmgr.cpp:178)  
  `(mpls == "disable") || mpls.empty()` → `sysctl net.mpls.conf.<IF>.input=0`
- **エラー抑制**: `ret && !mpls.empty()` の場合のみエラーログ (intfmgr.cpp:189) — mpls 省略時は sysctl 失敗を無視
- **SAI**: `Default value of ADMIN_MPLS_STATE is disabled` (コメント intfsorch.cpp:1278)  
  `port.m_mpls` が false の場合、RIF create 時に `ADMIN_MPLS_STATE` を attrs に含めない
- **orchagent 削除時**: `port.m_mpls = false` リセット (intfsorch.cpp:1362)
- **結論**: 省略 = `disable`。sysctl 失敗は mpls 未設定時に silent

### proxy_arp

- **YANG default**: なし
- **orchagent 初期化**: `IntfsEntry.proxy_arp = false` (intfsorch.cpp:501, 845)
- **intfmgr APP_DB 書込**: VLAN プレフィックス (`Vlan*`) のみ APP_DB に `proxy_arp` を書く (intfsorch.cpp:1031)  
  非 VLAN IF は syscall は実行するが APP_DB には書かない
- **orchagent 重複抑制**: `m_syncdIntfses[alias].proxy_arp == (proxy_arp == "enabled")` の場合はスキップ (intfsorch.cpp:396)
- **結論**: 省略時はカーネル操作なし、`proxy_arp = false` のまま

### grat_arp

- **YANG default**: なし
- **実装値の乖離 (既存ドキュメントとの差異)**:  
  `enabled` → `arp_accept` に **`2`** を書く (`garp_enabled = "2"`, intfmgr.cpp:582)  
  既存ドキュメントには `1` と記載あり — **不正確。正しくは `2`**
- **IPv6 副作用**: カーネルに `/proc/sys/net/ipv6/conf/<IF>/accept_untracked_na` が存在する場合のみ同値を書く (intfmgr.cpp:605-611)  
  カーネルバージョン依存の条件分岐 → プラットフォーム依存挙動
- **intfmgr APP_DB 書込**: `proxy_arp` 同様 VLAN プレフィックスのみ (intfmgr.cpp:1046)
- **結論**: `enabled` 時は `arp_accept=2` + 条件付き `accept_untracked_na=2`

### ipv6_use_link_local_only

- **YANG default**: `disable` (sonic-vlan.yang L138)
- **intfmgr**: `enable` → `m_ipv6LinkLocalModeList` に挿入、`disable` → 削除 + `delIpv6LinkLocalNeigh()` 呼出 (intfmgr.cpp:915-923)
- **非 VLAN**: VLAN/非 VLAN 共通処理 (VLAN限定ではない)
- **結論**: YANG デフォルト `disable`、実装確認済み

### mac_addr

- **YANG default**: なし（任意）
- **intfmgr fallback**: `mac.empty()` 時に `MacAddress().to_string()` (= `"00:00:00:00:00:00"`) を APP_DB へ push (intfmgr.cpp:1019)  
  カーネルへの `ip link set ... address` は呼ばない
- **orchagent fallback**: `port.m_mac` が falsy (zero) の場合、SAI RIF の `SRC_MAC_ADDRESS` に `gMacAddress`（スイッチ全体の MAC）を使う (intfsorch.cpp:1204-1205)
- **2段階 fallback**: CONFIG_DB 省略 → APP_DB に `00:00:00:00:00:00` → orchagent がスイッチ MAC に差し替えて SAI へ
- **結論**: ユーザー未設定時は実質スイッチ MAC が SAI に適用される (00:00:00 は中間表現)

### loopback_action

- **YANG default**: なし（任意）
- **intfmgr**: 省略時は APP_DB に書かない (intfmgr.cpp:895-898)
- **orchagent**: `loopbackAction.empty()` の場合 `setIntfLoopbackAction()` を呼ばない (intfsorch.cpp:999)  
  `addRouterIntfs()` でも `loopbackActionStr.empty()` なら SAI attr に含めない (intfsorch.cpp:1187)
- **SAI default**: SAI spec ではプラットフォーム依存 — 多くの実装では `forward` がデフォルト
- **結論**: 省略時は SAI デフォルト（実装依存）

### vrf_name

- **YANG default**: なし（任意）
- **orchagent**: 省略 → `gVirtualRouterId`（デフォルト VRF）を使用 (intfsorch.cpp:823)
- **変更禁止**: intfmgr の `isIntfChangeVrf()` で既存 IF の VRF 変更を検出し `SWSS_LOG_ERROR` + skip (intfmgr.cpp:847)
- **結論**: 省略 = default VRF

### vnet_name

- **YANG default**: なし（任意）
- **orchagent 優先順位**: `vnet_name` が存在する場合 `vrf_name` 経路ではなく VNET 経路を使う (intfsorch.cpp:933-957)  
  両方指定した場合 `vnet_name` が `vrf_name` を上書き
- **結論**: `vnet_name` が `vrf_name` より優先。同時指定は未定義動作に近い

---

## IP プレフィクスロウのフィールド

### scope

- **YANG**: enum `global`/`local`
- **intfmgr の上書き**: CONFIG_DB の `scope` 値を無視し、常に `"global"` を APP_DB へ書く (intfmgr.cpp:1134)
- **結論**: dead field（CONFIG_DB の値は参照されない）

### family

- **YANG**: enum `IPv4`/`IPv6`
- **intfmgr の上書き**: CONFIG_DB の `family` 値を無視し、IP prefix の型から自動判定して APP_DB へ書く (intfmgr.cpp:1129)  
  `ip_prefix.isV4() ? IPV4_NAME : IPV6_NAME`
- **結論**: dead field（CONFIG_DB の値は参照されない）

### secondary

- **YANG**: boolean
- **intfmgr**: `secondary` フィールドはパースされない（intfmgr.cpp:784-829 に処理なし）
- **orchagent**: 同様に参照なし（intfsorch.cpp:720-814 に処理なし）
- **結論**: 完全 dead field — どの consumer も消費しない

---

## 既存ドキュメントとの乖離 (discrepancy)

| フィールド | 既存ドキュメント記載 | 実装コード | 判定 |
|-----------|------------------|-----------|------|
| `grat_arp: enabled` | `arp_accept` に `1` | `arp_accept` に `2` | **不正確** |
| `mac_addr` 省略 | 「なし」のみ | `00:00:00:00:00:00` → orchagent がスイッチ MAC | 未記載 |
| `scope` | CONFIG_DB 値が使われる印象 | intfmgr が強制 `global` 上書き | dead field 未記載 |
| `family` | CONFIG_DB 値が使われる印象 | intfmgr が IP prefix から自動判定 | dead field 未記載 |
| `secondary` | 「secondary subnet フラグ」と説明 | 全 consumer で無視 | dead field 未記載 |
| `nat_zone` + NAT 非対応 | 記載なし | SAI に送信されない | プラットフォーム依存未記載 |

---

## ソース参照

- `sonic-swss/cfgmgr/intfmgr.cpp` — intfmgrd consumer, L169-1054
- `sonic-swss/orchagent/intfsorch.cpp` — IntfsOrch, L479-1044, L1167-1296
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang` — YANG定義, L71-205
