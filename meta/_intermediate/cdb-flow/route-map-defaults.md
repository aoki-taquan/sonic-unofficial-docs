# ROUTE_MAP — Phase A: コード由来の暗黙デフォルト調査結果

調査日: 2026-05-14
対象ファイル:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_rm.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang`

---

## 1. `route_operation` 欠落 → 全フィールド処理スキップ

frrcfgd は startup 時に `self.route_map[map_name][seq_no] = entry['route_operation']` でキャッシュする。
`route_operation` が CONFIG_DB エントリに存在しない場合、キャッシュに登録されず、後続の全フィールド処理
（`key_map.run_command`）が `route-map {} seq {} not found for update` エラーでスキップされる。
YANG では `route_operation` に default 宣言なし、MANDATORY でもない → silent drop。

**証拠**: frrcfgd.py L3131-3132

---

## 2. `match_ipv6_prefix_set` — YANG にあるが frrcfgd の `route_map_key_map` に存在しない (dead field)

YANG (`sonic-route-map.yang`) には `match_ipv6_prefix_set` leaf が定義されているが、
`frrcfgd.py` の `route_map_key_map` に対応エントリがない。
CONFIG_DB に書き込んでも frrcfgd は無視する。

FRR に IPv6 prefix-list match を設定するには `match_prefix_set` を使い、
参照する `PREFIX_SET` の `mode=IPv6` で AF を決定させる必要がある。

**証拠**: frrcfgd.py L1927-1955 (route_map_key_map 全体に match_ipv6_prefix_set なし)

---

## 3. `set_tag` — YANG にあるが frrcfgd の `route_map_key_map` に存在しない (dead field)

YANG には `set_tag` (uint32) が定義されているが `route_map_key_map` に対応エントリなし。
frrcfgd は処理しない。

**証拠**: frrcfgd.py L1927-1955

---

## 4. `match_prefix_set` / `match_next_hop_set` — AF はランタイム動的決定

frrcfgd は `PREFIX_SET.mode` を参照して ipv4/ipv6 を動的に判定する (L2669-2676)。
参照先 PREFIX_SET が CONFIG_DB に存在しない（未作成）場合、`tbl_key` に AF が設定されず、
`route_map_key_map` のキー `match_prefix_set|ipv4` / `match_prefix_set|ipv6` が
マッチしないため、コマンド生成がスキップされる (silent drop)。

書き込み順依存: PREFIX_SET を先に作成してから ROUTE_MAP に match_prefix_set を設定しないと
FRR への反映が起きない。

**証拠**: frrcfgd.py L2669-2676

---

## 5. `set_metric_action` + `set_metric` の組み合わせ依存

`handle_rmap_set_metric` (frrcfgd.py L467-508):
- `set_metric_action == METRIC_SET_VALUE/ADD_VALUE/SUBTRACT_VALUE` かつ `set_metric` が未設定の場合:
  `metric_param == ''` となり `syslog LOG_ERR` + `return None` (silent drop, FRR 未設定)
- `set_metric_action == METRIC_SET_RTT/ADD_RTT/SUBTRACT_RTT` は `set_metric` 不要 (metric_param = "rtt"等)
- `set_metric_action` なしで `set_med` のみの場合: `metric_param = med_value` (フォールバック)
- `set_med` と `set_metric_action+set_metric` が同時設定の場合:
  `set_metric_action` 側が優先 (`metric_param != ''` なので med_value の条件分岐は非実行)

**YANG 注記**: `set_metric` の when 条件はコメントアウトされており (`/* when */`) 実際は型検証のみ。

---

## 6. `set_repeat_asn` の単独設定 — silent drop

`hdl_set_asn` (frrcfgd.py L446-455):
```python
if 0 not in args[0]:
    return None
```
`set_asn` (index 0) が未設定で `set_repeat_asn` のみ設定した場合 `return None` → FRR コマンド生成なし。
`set_repeat_asn` は `set_asn` とセットで設定する必要がある。

デフォルト繰り返し回数: `set_repeat_asn` 省略時は frrcfgd format `{:repeat}` が
`rep_cnt = 1` にフォールバックし、ASN を 1 回だけ prepend する (L864-870)。

---

## 7. `set_asn_list` — カンマ区切り → スペース区切り変換

CONFIG_DB に `"1111,2222,3333"` と格納されたものが FRR コマンド上 `"1111 2222 3333"` に変換される。
format handler `asn_list` が `' '.join(value.split(','))` を実行 (frrcfgd.py L932)。

削除時 (`OP_DELETE`): `hdl_set_asn_list` が args を `('',)` に置換し `no set as-path prepend ` を発行 (L458-460)。

---

## 8. `call_route_map` — `{:enable-only}` 形式の挙動

format `enable-only` は `self.enabled == False` (OP_DELETE) のとき空文字列を返す (L829-830)。
削除操作時に `no call ` (空) が発行される点に注意。存在チェックなし。

---

## 9. `match_protocol` — zebra daemon 限定

`route_map_key_map` で `[zebra]{no:no-prefix}match source-protocol {:src-proto}` と定義。
bgpd インスタンスでは `match_protocol` が無視される。
また `ospf3` は frrcfgd により `ospf6` に変換される (L925-927)。

---

## 10. `match_neighbor` — max-elements 1 だがリスト型

YANG は `leaf-list max-elements 1` だが frrcfgd の format `{:peer-ip}` は
list の場合 `return self.value[0]` (最初の要素のみ使用, L877-881)。
複数要素書き込んでも 2 番目以降は silent drop。

---

## 11. BGPRouteMapMgr (managers_rm.py) のハードコード

BGPRouteMapMgr が処理するのは `FROM_SDN_SLB_ROUTES` / `FROM_SDN_APPLIANCE_ROUTES` の 2 キーのみ。
これらには以下がハードコードされる:
- シーケンス番号: `permit 100` (固定)
- `set origin incomplete` (固定)
- `set as-path prepend <bgp_asn> <bgp_asn>` (ASN を 2 回 prepend、固定)
- `set community <community_id>` (community_id フィールドから)

BGP ASN は `constants['deployment_id_asn_map']['2']` から取得。
未設定時は `log_debug` のみでスキップ (既存 route-map は残る)。

---

## 12. `set_community_ref` — 参照先 COMMUNITY_SET 未設定時 silent drop

`format 'com-ref'` (frrcfgd.py L831-834):
```python
com_set = self.daemon.comm_set_list.get(self.value, None)
if com_set is not None and com_set.is_configurable():
    return ' '.join(com_set.mbr_list)
```
COMMUNITY_SET が未作成または `is_configurable()` が False の場合 `None` 返却 → FRR コマンドスキップ。

---

## 13. `set_ext_community_inline` / `set_ext_community_ref` — 前置 no コマンド発行

`hdl_set_extcomm` (frrcfgd.py L416-444):
OP_DELETE でない場合でも既存の `no set extcommunity rt` / `no set extcommunity soo` を
先に発行してからセット。rt/soo の混在時はそれぞれ別コマンドに分割発行。

---

## 14. YANG default 宣言なしフィールド一覧

すべてのオプションフィールドに YANG `default` 宣言なし。
欠落時はプロセス非発行 (frrcfgd は key_map でフィールドの有無チェック後コマンド生成)。
FRR 側のデフォルト値が実質の動作デフォルトとなる:
- `set_local_pref`: FRR デフォルト 100
- `set_med`: FRR デフォルト なし (未設定)
- `set_origin`: FRR デフォルト なし
