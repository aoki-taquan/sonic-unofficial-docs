# INTERFACE テーブル — Phase A: フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
調査対象: `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/orchagent/intfsorch.cpp`, `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-interface.yang`

---

## 属性ロウ フィールド別デフォルト・挙動

### `nat_zone`
- YANG default: `"0"` (uint8, 明示)
- intfmgr: 空の場合 APP_DB に書かない (nat_zone フィールドが push されない)
- intfsorch: `nat_zone` フィールドが APP_DB に存在しない場合 `nat_zone_id = 0` のまま (C++ 初期化値 = 0)
  → SAI 側も 0 がデフォルト (変更なし)
- **結論**: YANG の `default "0"` と実装の C++ 初期化値 `0` が一致。矛盾なし。
- ただし `gIsNatSupported` が false の場合 SAI に NAT zone を設定しない (プラットフォーム依存)

### `mpls`
- YANG default: なし (省略可)
- intfmgr.cpp L178: `mpls.empty()` のとき `sysctl input=0` を実行 → Linux kernel MPLS 無効化
- intfsorch.cpp L1276-1285: `port.m_mpls` が false なら SAI の `ADMIN_MPLS_STATE` 属性を RIF 作成時に送らない
  コメント: "Default value of ADMIN_MPLS_STATE is disabled and does not need to be explicitly included"
- **暗黙デフォルト**: `disable` (Linux: input=0, SAI: RIF 作成時省略 = SAI デフォルト disabled)
- **invalid 値**: `SWSS_LOG_ERROR("MPLS state is invalid")` → `setIntfMpls()` が false 返却 → intfmgr が `return false` しキューに残す (partial failure: mpls 設定失敗でもそのエントリが retry される)

### `ipv6_use_link_local_only`
- YANG default: `disable`
- intfmgr.cpp L912-928: 値が empty の場合処理をスキップ (APP_DB に送らない)
- enable 時: `m_ipv6LinkLocalModeList` に insert (in-memory only)
- disable 時: `m_ipv6LinkLocalModeList` から erase + `delIpv6LinkLocalNeigh()` で link-local neighbor 削除
- **暗黙 reset**: IF 削除時 (DEL_COMMAND) にも `m_ipv6LinkLocalModeList.erase()` + `delIpv6LinkLocalNeigh()` を実行
  → warm reboot 後は `m_ipv6LinkLocalModeList` が空リセット、再 replay されない点に注意
- **dead consumer**: IntfsOrch は `ipv6_use_link_local_only` を APP_DB から読んでも無視 (SAI に対応する RIF 属性なし)
  → Linux kernel の /proc/sys/net/ipv6 制御のみ (intfmgr が直接実行)

### `mac_addr`
- YANG default: なし
- intfmgr.cpp L1018-1021: `mac` が空の場合 `MacAddress().to_string()` (ゼロ MAC = "00:00:00:00:00:00") を APP_DB に書き込む
  → intfsorch.cpp L1198-1207: `port.m_mac` が falsy な場合 `gMacAddress` (switch global MAC) にフォールバック
- **書き込み時 vs 実行時乖離**: CONFIG_DB に mac_addr 未設定でも APP_DB に "00:00:00:00:00:00" が書かれ、SAI には switch global MAC が設定される
  → CONFIG_DB → APP_DB の値と SAI に実際に設定される値が乖離する
- **silent substitution**: 指定なし → SAI では switch global MAC が使われるが APP_DB 上は "00:00:00:00:00:00"

### `loopback_action`
- YANG default: なし
- intfmgr.cpp L895-899: 空の場合 APP_DB に書かない
- intfsorch.cpp L1187-1196: `loopbackActionStr.empty()` の場合 SAI 属性を RIF 作成時に省略 → SAI プラットフォームデフォルト動作
- intfsorch `getSaiLoopbackAction()`: `"drop"` or `"forward"` 以外の値 → `SWSS_LOG_WARN` + `return false` → loopback action は設定されない (silent drop of setting)
- **プラットフォーム依存**: 未設定時の SAI デフォルトはプラットフォーム (ASIC ベンダー) 依存

### `vrf_name` / `vnet_name`
- YANG default: なし (省略 = default VRF)
- intfmgr.cpp L789: `vnet_name` と `vrf_name` を同一変数 `vrf_name` にマップ (統合処理)
- 空の場合 intfmgr が `setIntfVrf(alias, "")` を呼ばない (非 DEL 時)
- intfsorch.cpp L823-832: `vrf_name` 空 → `vrf_id = gVirtualRouterId` (グローバル VRF)
- **VRF 変更禁止**: intfmgr.cpp L847: 別 VRF への直接変更 → `SWSS_LOG_ERROR` + `return true` (skip)
  2 ステップ必須: (1) vrf unbind して vrf_name 削除 → (2) 新 VRF 名で set

### `admin_status` (Loopback 専用)
- INTERFACE テーブルには `admin_status` フィールドは YANG に定義されていない
- intfmgr.cpp L862-869: Loopback IF の場合のみ処理: 空 → `"up"` に強制、`up`/`down` 以外 → `SWSS_LOG_WARN` + `"up"` に置換
- 物理 INTERFACE ではこのフィールドは無視される (Loopback 専用処理分岐)

## IP プレフィクスロウ フィールド別デフォルト・挙動

### `scope`
- YANG default: なし
- intfmgr.cpp L1134: `scope = "global"` を常に APP_DB に書き込む (CONFIG_DB の `scope` 値を無視)
- **dead consumer / silent substitution**: CONFIG_DB に `scope=local` を書いても intfmgr は常に `scope=global` を APP_DB に書く
  → CONFIG_DB の `scope` フィールドは実質 dead (intfmgr が読んでも使わない)

### `family`
- YANG: `must` で ip-prefix との整合チェック (`IPv4`/`IPv6`)
- intfmgr.cpp L1129: `ip_prefix.isV4() ? IPV4_NAME : IPV6_NAME` で常に ip-prefix から計算して APP_DB に書く
- **dead consumer**: CONFIG_DB の `family` フィールドは intfmgr が読まない (APP_DB には ip-prefix から自動計算した値を書く)
- IPv4 link-local (169.254.x.x) は APP_DB に送らない (L1132: skip 条件)

## 複合必須制約・前提条件依存

1. **IP プレフィクスロウ追加前に L3 enable 行が必要**:  
   YANG `must` で `INTERFACE_LIST[name=current()]` の存在を要求  
   → intfmgr.cpp L1115: `isIntfCreated(alias)` が false ならスキップ (L3 enable 行の SET が先に完了していること)

2. **PORT が STATE_DB に ready 状態で存在すること**:  
   intfmgr.cpp L833: `isIntfStateOk()` を確認 → 未 ready はキューに戻して再試行

3. **VRF が STATE_DB に ready 状態で存在すること**:  
   intfmgr.cpp L839-843: `isIntfStateOk(vrf_name)` を確認

## ハードコード値

| コード | 値 | 場所 |
|--------|-----|------|
| `DEFAULT_MTU_STR` | `9100` | intfmgr.cpp L29 — サブインターフェース MTU fallback |
| `LOOPBACK_DEFAULT_MTU_STR` | `"65536"` | intfmgr.cpp L28 — Loopback 作成時の MTU |
| `MTU_INHERITANCE` | `"0"` | intfmgr.cpp L24 — subintf に mtu 未設定時の APP_DB 値 |
| Loopback admin_status fallback | `"up"` | intfmgr.cpp L863 |

## サブインターフェース固有 (INTERFACE テーブルに同梱)

- `mtu` 未設定時: APP_DB に `mtu=0` (MTU_INHERITANCE) を書き込み、親 PORT の MTU を継承
- `admin_status` 未設定時: `"up"` にデフォルト
- 親 PORT が down の場合: subintf も `"down"` に強制 (setHostSubIntfAdminStatus の論理)

## eth0 / docker0 / usb0 の silent drop

intfsorch.cpp L817-821: `alias == "eth0"` or `"docker0"` or `"usb0"` のエントリは即 erase。SAI には届かない。
