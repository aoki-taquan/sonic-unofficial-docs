# BGP_DEVICE_GLOBAL — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py` (フィールド値定数、route-map / community 名、フィールド名文字列、ロール文字列、内部キー)
- `sonic-swss/orchagent/bfdorch.cpp` L114-200, L729-829 (`BgpGlobalStateOrch` 内 `tsa_enabled` 文字列マッチ / 初期値リテラル / SAI BFD offload 属性 ID)
- `dockers/docker-fpm-frr/frr/bgpd/wcmp/bgpd.wcmp.conf.j2` (FRR ルートマップ名 / extcommunity リテラル)
- `dockers/docker-fpm-frr/frr/bgpd/idf_isolate/idf_isolate.conf.j2` / `idf_unisolate.conf.j2` (route-map 名、`isolation_status` 文字列、community no-export リテラル)
- `dockers/docker-fpm-frr/frr/bgpd/tsa/bgpd.tsa.isolate.conf.j2` / `bgpd.tsa.unisolate.conf.j2` (TSA route-map permit 20/30/deny 40 リテラル)

---

## 1. クラス定数 (managers_device_global.py L12-14)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `TSA_DEFAULTS` | `"false"` | `tsa_enabled` の Python 側既定値。`__init__` / `del_handler` / `configure_tsa(data=None)` fallback で利用 | managers_device_global.py L12 |
| `WCMP_DEFAULTS` | `"false"` | `wcmp_enabled` の Python 側既定値。`__init__` / `del_handler` / `configure_wcmp(data=None)` fallback で利用 | managers_device_global.py L13 |
| `IDF_DEFAULTS` | `"unisolated"` | `idf_isolation_state` の Python 側既定値。`__init__` / `del_handler` / `configure_idf(data=None)` fallback で利用 | managers_device_global.py L14 |

> CONFIG_DB の値も同じ文字列リテラル (`"true"` / `"false"` / `"unisolated"` / `"isolated_no_export"` / `"isolated_withdraw_all"`) を直接やり取りする (bool 変換しない)。

---

## 2. フィールド値リテラル — 受理セット (managers_device_global.py L103, L146, L256)

| フィールド | 受理する文字列 | 拒否時の挙動 | ソース |
|-----------|---------------|--------------|--------|
| `tsa_enabled` | `"true"` / `"false"` のみ | `state in ["true", "false"]` 偽だと directory に書き込まず、`chassis_tsa=="false"` 経路でも `isolate_unisolate_device(state)` が呼ばれて `log_err("TSA: invalid value(...)")` で reject | L103, L186-188 |
| `wcmp_enabled` | `"true"` / `"false"` のみ | `set_wcmp(status)` が `log_err("W-ECMP: invalid value(...)")` で False 返却 | L146-148 |
| `idf_isolation_state` | `"unisolated"` / `"isolated_withdraw_all"` / `"isolated_no_export"` のみ | `downstream_isolate_unisolate()` が `log_err("IDF: invalid value(...)")` で False 返却 | L256-258 |

> `tsa_enabled` / `wcmp_enabled` の判定は **小文字リテラル文字列の厳密一致**。`"True"` / `"FALSE"` / `"1"` / `"0"` はすべて拒否される。Python `bool` でも YANG `boolean` 真理値 (RFC 7950 = `"true"` / `"false"`) でもない。

---

## 3. switch_role 受理リスト (managers_device_global.py L260)

| 文字列 | 用途 |
|--------|------|
| `"SpineRouter"` | IDF isolate / unisolate の FRR push を実行する 3 ロールの 1 つ |
| `"LowerSpineRouter"` | 同上 (T2 chassis lower spine) |
| `"UpperSpineRouter"` | 同上 (T2 chassis upper spine) |

> `if self.switch_role and self.switch_role not in [...]: return True` の早期 return ガード。Spine 系 3 ロール以外 (`ToRRouter` / `LeafRouter` / 空文字列) では IDF テンプレート未送出。switch_role は `DEVICE_METADATA.localhost.type` から `handle_type_update()` 経由で取得。

---

## 4. chassis 内 BGP セッション識別子 (managers_device_global.py L215)

| 文字列 | 用途 | ソース |
|--------|------|--------|
| `"_INTERNAL_"` | route-map 名にこの substring を含むものは VOQ chassis 内 LC 間 iBGP として扱い、TSA isolate 時も isolate 対象に含める (`internal_route_map="1"`) | L215 |
| `"VOQ_"` | 同上 (VOQ chassis fabric session 識別) | L215 |
| `"V4"` | route-map 名に含めば `ip_version="V4"` / `ip_protocol="ip"` を j2 に渡す | L219-220 |
| `"V6"` | route-map 名に含めば `ip_version="V6"` / `ip_protocol="ipv6"` を j2 に渡す | L221-222 |

---

## 5. CHASSIS_APP_DB 参照キー (managers_device_global.py L247)

| 項目 | 値 | 用途 |
|------|----|------|
| DB | `CHASSIS_APP_DB` (`swsscommon.SonicV2Connector` 経由) | シャーシ全体 TSA 状態 |
| Key | `"BGP_DEVICE_GLOBAL|STATE"` (リテラル) | 行キー |
| Field | `"tsa_enabled"` (リテラル) | フィールド名 |
| 失敗時 fallback | `"false"` | `is_chassis()` False / 例外時の chassis_tsa デフォルト (L239) |

---

## 6. directory 上の フィールドキー文字列 (managers_device_global.py L42-49)

| キー | 用途 |
|------|------|
| `"tsa_enabled"` | directory put / get / path_exist のフィールド名 |
| `"wcmp_enabled"` | 同上 |
| `"idf_isolation_state"` | 同上 |

> directory.put の table 名は呼び出し側から渡される `self.table_name` = `BGP_DEVICE_GLOBAL` (`swsscommon.CFG_BGP_DEVICE_GLOBAL_TABLE_NAME` 経由でも参照、L173, L281)。

---

## 7. extracted route-map 名抽出 regex (managers_device_global.py L231)

| 定数 | 値 | 用途 |
|------|----|------|
| `out_route_map` regex | `r'^\s*neighbor \S+ route-map (\S+) out$'` | bgpd 現行 config からアウトバウンド route-map 名を抽出。1 行ごと match して capture group 1 を route_map_names set に追加 |

---

## 8. FRR テンプレートが投入するリテラル

### 8.1 TSA isolate 時 (bgpd.tsa.isolate.conf.j2)

| FRR コマンドリテラル | 役割 | ソース |
|----------------------|------|--------|
| `route-map {name} permit 20` + `set community no-export additive` | `internal_route_map="1"` 経路 (chassis 内 iBGP) | L1-3 |
| `route-map {name} permit 20` + `match {ip} address prefix-list PL_Loopback{V4,V6}` + `set community {{constants.bgp.traffic_shift_community}}` | 通常 eBGP 経路の Loopback 広告のみ TSA community を付与 | L6-8 |
| `route-map {name} permit 30` + `match tag {{constants.bgp.internal_community_match_tag}}` + `set community {{constants.bgp.traffic_shift_community}}` | internal tag 経路 | L9-11 |
| `route-map {name} deny 40` | 上記以外のすべての経路を拒否 (= TSA 主機能) | L12 |

### 8.2 TSA unisolate 時 (bgpd.tsa.unisolate.conf.j2)

通常運用の route-map を再投入する Jinja2 テンプレート (chassis_tsa 偽 / `tsa_enabled="false"` 時)。`no route-map ... permit 20 / 30 / deny 40` でリテラル削除。

### 8.3 W-ECMP (bgpd.wcmp.conf.j2)

| FRR コマンドリテラル | 条件 | ソース |
|----------------------|------|--------|
| `route-map TO_BGP_PEER_V4 permit 100` (固定 route-map 名 / seq) | 常時 | L4 |
| `route-map TO_BGP_PEER_V6 permit 100` (同上 V6) | 常時 | L12 |
| `set extcommunity bandwidth num-multipaths` | `wcmp_enabled == 'true'` | L6, L14 |
| `no set extcommunity bandwidth` | `wcmp_enabled` その他 (= `'false'` 含む) | L8, L16 |

> route-map 名 `TO_BGP_PEER_V4` / `TO_BGP_PEER_V6`、seq 番号 `100`、extcommunity 名 `bandwidth num-multipaths` はすべて FRR 側ハードコード。

### 8.4 IDF isolate (idf_isolate.conf.j2)

| FRR コマンドリテラル | 条件 | ソース |
|----------------------|------|--------|
| `route-map CHECK_IDF_ISOLATION permit 1` + `match ip address prefix-list PL_LoopbackV4` + `set community {{constants.bgp.traffic_shift_community}}` | 常時 | L1-3 |
| `route-map CHECK_IDF_ISOLATION permit 2` + `match ipv6 address prefix-list PL_LoopbackV6` + community 同上 | 常時 | L4-6 |
| `route-map CHECK_IDF_ISOLATION permit 3` + `match tag {{constants.bgp.internal_community_match_tag}}` + community 同上 | 常時 | L7-9 |
| `route-map CHECK_IDF_ISOLATION deny 4` | `isolation_status == "isolated_withdraw_all"` のみ | L13 |
| `route-map CHECK_IDF_ISOLATION permit 10` + `no set community no-export additive` | `isolated_withdraw_all` (= deny 4 と組合せで全 prefix drop) | L14-15 |
| `route-map CHECK_IDF_ISOLATION permit 10` + `set community no-export additive` | `isolated_no_export` (AS 外への再広告のみ抑制) | L20-21 |
| `no route-map CHECK_IDF_ISOLATION deny 4` | `isolated_no_export` 移行時の deny 4 撤去 | L19 |

### 8.5 IDF unisolate (idf_unisolate.conf.j2)

| FRR コマンドリテラル | ソース |
|----------------------|--------|
| `no route-map CHECK_IDF_ISOLATION permit 1` / `permit 2` / `permit 3` | L1-3 |
| `no route-map CHECK_IDF_ISOLATION deny 4` | L4 |
| `route-map CHECK_IDF_ISOLATION permit 10` + `no set community no-export additive` | L5-6 |

> `CHECK_IDF_ISOLATION` という route-map 名 / seq 番号 (1/2/3/4/10) はすべて IDF テンプレート側ハードコード。bgpcfgd 側からの動的変更不可。

---

## 9. BgpGlobalStateOrch (bfdorch.cpp) 側リテラル

| 項目 | 値 | 用途 | ソース |
|------|----|------|--------|
| `tsa_enabled` 初期値 | `false` (C++ bool) | コンストラクタで初期化 | bfdorch.cpp L733 |
| `bfd_offload` 評価 | `offload_supported(IPv4) && offload_supported(IPv6)` 両対応で `true` | hardware BFD offload 可否判定 | L735 |
| field 名マッチ | `"tsa_enabled"` (リテラル) | `doTask()` 内 `if (type == "tsa_enabled")` | L813 |
| value 比較 | `value == "true"` (リテラル) | true なら C++ bool true、それ以外は false | L815 |
| SAI attr id (v4) | `SAI_SWITCH_ATTR_SUPPORTED_IPV4_BFD_SESSION_OFFLOAD_TYPE` | offload capability 照会 (get_ipv6=false) | L761 |
| SAI attr id (v6) | `SAI_SWITCH_ATTR_SUPPORTED_IPV6_BFD_SESSION_OFFLOAD_TYPE` | offload capability 照会 (get_ipv6=true) | L764 |
| offload 判定値 | `SAI_BFD_SESSION_OFFLOAD_TYPE_NONE` 以外なら true | `attr.value.u32list.list[0] != NONE` | L787 |
| capability list 要求サイズ | `1` | `u32list.count = 1` 固定 | L780-782 |

> `BgpGlobalStateOrch` は CONFIG_DB 上の `tsa_enabled` 文字列を読むだけで `wcmp_enabled` / `idf_isolation_state` は完全に無視する。これらは bgpcfgd 側だけで処理される。

---

## 10. CONFIG_DB → directory の対応 (固定キー)

| CONFIG_DB key | directory 上の table_name (subscribe 経由) |
|---------------|-------------------------------------------|
| `BGP_DEVICE_GLOBAL|STATE` | `BGP_DEVICE_GLOBAL` (STATE / CONFED は同一 table、key の組合せで分離) |
| `BGP_DEVICE_GLOBAL|CONFED` | 同上 (ただし DeviceGlobalCfgMgr は CONFED を購読しない) |

> `swsscommon.CFG_BGP_DEVICE_GLOBAL_TABLE_NAME` は `"BGP_DEVICE_GLOBAL"` を返す swsscommon 定数。Manager 基底クラス経由でこのテーブル名がそのまま directory key に使われる。

---

## 特記事項

1. **`tsa_enabled` のセマンティックが 2 重定義**: CONFIG_DB 上は文字列 `"true"` / `"false"`、bgpcfgd 内 directory にも文字列、orchagent (`BgpGlobalStateOrch`) では C++ bool に変換。文字列マッチは bgpcfgd と orchagent の双方で **`value == "true"`** という小文字厳密一致 (`bool(value)` ではない)。
2. **IDF テンプレート側 route-map 名は固定**: `CHECK_IDF_ISOLATION` という名前は `idf_isolate.conf.j2` / `idf_unisolate.conf.j2` にリテラル埋め込み。constants.yml / CONFIG_DB から差し替え不可。
3. **W-ECMP route-map 名は `TO_BGP_PEER_V4` / `TO_BGP_PEER_V6`**: 同様にハードコード。seq `100` も固定。bgpcfgd 側は j2 への変数注入なし (`wcmp_template.render(wcmp_enabled=status)` のみ)。
4. **TSA テンプレート permit 20 / 30 / deny 40 の seq 番号**: `bgpd.tsa.isolate.conf.j2` で固定。bgpcfgd 側で route-map 名のみ動的選択し seq は固定 3 段 (20=Loopback、30=internal tag、40=catch-all deny)。
5. **chassis_tsa fallback `"false"`**: `is_chassis()` False または例外時に必ず `"false"` 返却 (L239, L242, L249-251)。非シャーシ環境では常に個別 LC の `configure_tsa` が動く前提。
6. **`switch_role` 空文字列 (初期値 / DEVICE_METADATA 未設定)**: `downstream_isolate_unisolate` は `self.switch_role and ...` の短絡評価で先に進む (= 空文字列は falsy で early return せず、IDF FRR push を実行)。これは非 Spine ロール (空) でも IDF 設定を投入する潜在挙動。ただし init_cfg.json.j2 で `DEVICE_METADATA.localhost.type` が必ず設定されるので実機では到達しない経路。
7. **`out_route_map` regex の `\S+`**: route-map 名にスペース文字が含まれた場合は最初のスペースで打ち切られる。FRR では route-map 名にスペース不可なので実害なし。
8. **TSA isolate route-map seq 30 と IDF route-map seq 3 の community**: 両者とも `constants.bgp.traffic_shift_community` を `match tag {{constants.bgp.internal_community_match_tag}}` 経路に貼る。constants.yml 由来で、bgpcfgd 自体には数値リテラルなし (例: 値は通常 `5060:12345` 付近、constants.yml 参照)。
9. **`wcmp_enabled` の C++ side は存在しない**: `BgpGlobalStateOrch::doTask` は `wcmp_enabled` フィールドを無視 (`if (type == "tsa_enabled")` のみ)。W-ECMP は完全に bgpcfgd → FRR 経路で閉じる。
10. **CONFIG_DB に `BGP_DEVICE_GLOBAL|CONFED` セクションがない場合**: bgpcfgd は CONFED を処理しない (Manager subscribe 対象外)。FRR confederation 設定は CLI / minigraph 経由でのみ投入される。

---

## 出典

- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py` L1-288 (全体読了)
- `sonic-net/sonic-swss/orchagent/bfdorch.cpp` L114-200 (BfdOrch 連携), L729-829 (`BgpGlobalStateOrch` 本体)
- `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/wcmp/bgpd.wcmp.conf.j2` L1-22
- `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/idf_isolate/idf_isolate.conf.j2` L1-23
- `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/idf_isolate/idf_unisolate.conf.j2` L1-7
- `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/tsa/bgpd.tsa.isolate.conf.j2` L1-16
