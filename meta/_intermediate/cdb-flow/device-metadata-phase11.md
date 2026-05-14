# DEVICE_METADATA — Phase 11 extended context extraction

生成日: 2026-05-14  
対象 tier: tier_high  
slug: device-metadata  
レビュー対象 evidence 行数: 47 行  
拡張 scope で新発見の識別子数: 14  
constants.yml 解決した定数値数: 8  

---

## 方法

各 evidence 行が含まれる Jinja2 ブロック全体（`{% if %}` から `{% endif %}` まで、`{% set %}` を含む外側ブロック）を読み、evidence 行外の `set` 変数、`constants.*` 参照、macro 呼び出し、生成される文字列リテラルを追記。

---

## bgpd.main.conf.j2 — ブロック全体レビュー

### L1–L30: set 変数群（disagg_t2 / disagg_rh）

| evidence 行 | 拡張 scope で見つかった識別子 |
|---|---|
| L20: `type.lower() in ['lowerspinerouter','upperspinerouter','fabricspinerouter']` | ↳ `{% set disagg_t2 = "true" %}` (L21): 変数 `disagg_t2` はファイル全体で L63, L78, L97, L159 の分岐条件として使用 |
| L27: `type.lower() in ['lowerregionalhub','fabricregionalhub','upperregionalhub']` | ↳ `{% set disagg_rh = "true" %}` (L28): 変数 `disagg_rh` は L97 の `disagg_t2 or disagg_rh` 条件で confederation iBGP 設定を有効化 |

### L56–L63: multi_asic / voq_chassis set 変数

| evidence 行 | 拡張 scope で見つかった識別子 |
|---|---|
| L56: `sub_role == 'FrontEnd' or 'BackEnd'` | ↳ `{% set multi_asic = True %}` (L57): `multi_asic` は L159, L176 で p2p prefix-list / loopback 広告分岐条件 |
| L59: `switch_type == 'voq'` | ↳ `{% set voq_chassis = True %}` (L61): `voq_chassis` は L97, L141, L159, L170, L176 で分岐 |

### L78–L90: HIDE_INTERNAL route-map 内 constants 参照

| evidence 行 | 拡張 scope で見つかった識別子 | constants.yml 解決値 |
|---|---|---|
| L79: `constants.bgp.hide_internal_community is defined` | ↳ `constants.bgp.hide_internal_community` → L83: `set community <value> additive` を HIDE_INTERNAL route-map に追加 | = `55555:55555` |
| L86: `constants.bgp.peers.internal.community is defined` | ↳ `constants.bgp.peers.internal.community` → 値はネストキー: `peers.internal` は db_table `BGP_INTERNAL_NEIGHBOR` に対応 (constants.yml:54-56)。community 値は constants.yml に直接未定義 (peers.internal.community キーなし) | → 未定義のため このブロックは実行されない |

### L114–L123: multipath_relax / graceful_restart ブロック

| evidence 行 | 拡張 scope で見つかった識別子 | constants.yml 解決値 |
|---|---|---|
| L114: `constants.bgp.multipath_relax.enabled` | ↳ ブロック内で `bgp bestpath as-path multipath-relax` を出力。この分岐に `type` 条件はない（全ロールで有効） | = `true` |
| L118: `constants.bgp.graceful_restart.enabled and type == 'ToRRouter'` | ↳ `constants.bgp.graceful_restart.restart_time \| default(240)` (L119) → 実値 **240** (default と一致) | = `true`, restart_time = `240` |
| L122: `constants.bgp.graceful_restart.select_defer_time \| default(45)` | ↳ `select_defer_time` は constants.yml に定義なし → fallback default **45** 秒が適用 | = (未定義 → 45) |

### L207–L215: maximum_paths ブロック

| evidence 行 | 拡張 scope で見つかった識別子 | constants.yml 解決値 |
|---|---|---|
| L207: `constants.bgp.maximum_paths.enabled` | ↳ `constants.bgp.maximum_paths.ipv4 \| default(64)` (L210) → 実値 **514** | = `true`, ipv4 = `514` |
| L213: `maximum-paths ipv6` | ↳ `constants.bgp.maximum_paths.ipv6 \| default(64)` → 実値 **514** | = `514` |

---

## peer-group.conf.j2 (general) — ブロック全体レビュー

| evidence 行 | 拡張 scope で見つかった識別子 |
|---|---|
| L7: `type == 'ToRRouter'` → `allowas-in 1` | ↳ ブロック内で参照される `CONFIG_DB__BGP_BBR['status']` は LeafRouter 分岐 (L10) でのみ使用。ToRRouter では BBR チェックなし |
| L10: `CONFIG_DB__BGP_BBR['status'] == 'enabled'` | ↳ `CONFIG_DB__BGP_BBR` テーブルへの参照。`bgp-bbr` テーブルの `status` フィールドを参照（BGP_BBR テーブル） |
| L17: `type == 'SpineRouter' and subtype == 'UpstreamLC'` | ↳ 生成されるリテラル: `table-map SELECTIVE_ROUTE_DOWNLOAD_V4`, `SELECTIVE_ROUTE_DOWNLOAD_V6` (L18, L33) |

---

## init_cfg.json.j2 — ブロック全体レビュー

| evidence 行 | 拡張 scope で見つかった識別子 |
|---|---|
| L69 (pmon): `type == 'SpineRouter'` → `has_per_asic_scope=False` | ↳ `{% set features = [...] %}` (L67) のリスト内で定義される tuple: `("pmon", "enabled", "<J2_expr>", "enabled")` — 3 番目要素が `has_per_asic_scope` の J2 展開式 |
| L76 (dhcp_relay): `type not in ['ToRRouter','EPMS','MgmtTsToR','MgmtToRRouter','BmcMgmtToRRouter']` | ↳ `{% do features.append(...) %}` マクロ呼び出し。`features` リストは L101 の `{% for feature, state, delayed, autorestart in features %}` で展開 |
| L81 (mux): `subtype == 'DualToR'` | ↳ 生成される feature state: `enabled` or `always_disabled`。`include_mux == "y"` のビルド変数依存 |
| L85 (restapi): `type not in ['LeafRouter','BackEndLeafRouter']` | ↳ さらに `BUILD_REDUCE_IMAGE_SIZE == "y" and sonic_asic_platform == "broadcom"` という build-time 条件が外側に存在（L84）。Broadcom 限定の条件 |
| L90 (macsec): `type in ['SpineRouter','UpperSpineRouter','LowerRegionalHub']` | ↳ `DEVICE_RUNTIME_METADATA['MACSEC_SUPPORTED']` という runtime metadata を参照。MACSEC_SUPPORTED は DEVICE_RUNTIME_METADATA（ランタイム）から取得、CONFIG_DB ではない |

---

## constants.yml 解決サマリ

| constants 参照 | 実値 (constants.yml) |
|---|---|
| `constants.bgp.graceful_restart.enabled` | `true` |
| `constants.bgp.graceful_restart.restart_time` | `240` (秒) |
| `constants.bgp.graceful_restart.select_defer_time` | 未定義 → fallback `45` (秒) |
| `constants.bgp.multipath_relax.enabled` | `true` |
| `constants.bgp.maximum_paths.enabled` | `true` |
| `constants.bgp.maximum_paths.ipv4` | `514` |
| `constants.bgp.maximum_paths.ipv6` | `514` |
| `constants.bgp.hide_internal_community` | `55555:55555` |
| `constants.bgp.peers.internal.community` | 未定義 (constants.yml にキーなし) → ブロック非実行 |

---

## 代表 3 サンプル（evidence 外で見つかった識別子）

1. **`set disagg_t2 = "true"` / `set disagg_rh = "true"`** (bgpd.main.conf.j2:L21,28)  
   evidence 行 L20, L27 は type チェックのみ記載していたが、これらの `{% set %}` がファイル全体の分岐（L63, L78, L97, L159）の根幹を担う。disagg_t2 は FabricSpineRouter / LowerSpineRouter / UpperSpineRouter で true になり、HIDE_INTERNAL route-map に `constants.bgp.hide_internal_community` (= 55555:55555) を追加する。

2. **`constants.bgp.maximum_paths.ipv4/ipv6 = 514`** (bgpd.main.conf.j2:L210,213)  
   evidence 行ではブロック存在のみ言及していたが、実際の最大パス数は `default(64)` ではなく `514`（constants.yml:29-30）。多数の ECMP パス設定が有効であることを示す。

3. **`CONFIG_DB__BGP_BBR['status']`** (peer-group.conf.j2:L10,25)  
   evidence 行 L9 `LeafRouter → allowas-in 1` の条件は BBR status に依存するが、この参照は evidence 行外の L10 で初めて現れる。`BGP_BBR` テーブルの `status` フィールド（`enabled`/`disabled`）との複合条件であることが block 全体読みで判明。

---

## wred-profile / acl-rule / acl-table の Phase 11 分析

### wred-profile (tier_mid)

対象 evidence: `qosorch.cpp:36-44` (ecn_map), `qosorch.cpp:743` (SAI_WRED_ATTR_ECN_MARK_MODE)

qosorch.cpp は C++ ファイル。関数スコープで読む:
- `WredMapHandler::addWredProfile()` 内の `ecn_map.at(fvValue(*i))` — map は `std::map<std::string, sai_ecn_mark_mode_t>` で `ecn_map` (L36-44) に定義
- ブロック内 `set` 変数: なし（C++ ローカル変数 `ecn_val` が `.at()` の結果を受ける）
- ブロック内 macro 相当: なし（constants.yml 参照なし）
- 新発見: `SAI_WRED_ATTR_ECN_MARK_MODE`, `SAI_WRED_ATTR_GREEN_ENABLE`/`YELLOW`/`RED` 系 attr が同関数内で設定される（evidence は ECN mode のみ言及していたが WRED enable 系 attr も同ブロック内）

### acl-rule / acl-table (tier_mid)

対象 evidence: `aclorch.cpp:5520` (doAclRuleTask), `aclorch.cpp:5346` (doAclTableTask)

C++ 関数スコープ: Phase 10 intermediate (acl-rule.md, acl-table.md) が既に関数全体を網羅。
constants.yml 参照: なし（ACL orch は constants.yml を参照しない）
新発見 block 内識別子:
- `doAclRuleTask`: `TCP_PROTOCOL_NUM = 6` (L5640 近傍のローカル定数定義)
- `doAclTableTask`: `TABLE_TYPE_UNDERLAY_SET_DSCP` → `TABLE_TYPE_MARK_META` への変換マップ（ローカル static map）
- いずれも constants.yml と無関係、追記済みの内容を confirm

---

## 統計サマリ

| 項目 | 数値 |
|---|---|
| レビュー evidence 行数 | 47 |
| 拡張 scope read で新発見の識別子 | 14 |
| うち set 変数 | 4 (`disagg_t2`, `disagg_rh`, `multi_asic`, `voq_chassis`) |
| うち constants.* 参照 | 7 |
| うち CONFIG_DB 外テーブル参照 | 2 (`CONFIG_DB__BGP_BBR`, `DEVICE_RUNTIME_METADATA['MACSEC_SUPPORTED']`) |
| うち build-time 変数参照 | 1 (`BUILD_REDUCE_IMAGE_SIZE`, `sonic_asic_platform`) |
| constants.yml から解決した定数値 | 8 |
