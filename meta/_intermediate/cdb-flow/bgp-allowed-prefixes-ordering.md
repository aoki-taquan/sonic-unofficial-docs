# BGP_ALLOWED_PREFIXES — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_ALLOWED_PREFIXES`
Consumer: `bgpcfgd / BGPAllowListMgr` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py`)
連動 j2 テンプレ: `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2`
スキャン範囲: `managers_allow_list.py` 全 786 行精読 + `policies.conf.j2` (general) 全 145 行精読 + `bgpcfgd/main.py` の Manager 起動順 (L73-104)

---

## 検出した順序依存・タイミング依存

### 1. `policies.conf.j2` 起動時テンプレ生成が先行必須 (FROM_BGP_PEER_V4/V6 / ALLOW_LIST_DEPLOYMENT_ID_0_V4 / community-list の初期化)

- `BGPAllowListMgr.__update_allow_route_map_entry` は `route-map ALLOW_LIST_DEPLOYMENT_ID_<id>_V4|V6 permit <seq>` を vtysh に流すだけで、**ルートマップを peer-group に紐付ける `route-map ... call ALLOW_LIST_DEPLOYMENT_ID_0_V4/V6` 行や `FROM_BGP_PEER_V4/V6` の枠組み、`allow_list_default_community` community-list は `policies.conf.j2` の起動時テンプレで一度だけ生成される** (`policies.conf.j2:34-78`)。
- `__update_default_route_map_entry` も `route-map <name> permit 65535 / set community ... additive` を投入するが、seq=65535 のデフォルト・トラップ自体は templateレンダ時にも `ALLOW_LIST_DEPLOYMENT_ID_0_V4/V6` 用に書き出されている (`policies.conf.j2:17-29`)。bgpcfgd は deployment_id≠0 の場合に追加で 65535 を書き、deployment_id=0 については templateと bgpcfgd が二重に同じ seq を更新する点に注意。
- **意味**: bgpcfgd 起動 (= `policies.conf.j2` レンダ) が BGP_ALLOWED_PREFIXES の書込みより前でないと、ALLOW_LIST 系の枠組みが存在せず `bgp community-list standard allow_list_default_community` も無いため、`__update_allow_route_map_entry` がルートマップを書いても `FROM_BGP_PEER_V4/V6 permit 10 → call ALLOW_LIST_DEPLOYMENT_ID_0_V4` のチェーンが未生成で **prefix-list は適用されない**。
- evidence: `policies.conf.j2:8,17-29,31-32,34-38,57-61` / `managers_allow_list.py:429-436, 449-452`

### 2. `DEVICE_METADATA.localhost.type` / `subtype` / `switch_type` の確定 (テンプレ条件分岐)

- `policies.conf.j2:40-54, 63-77` で `type=='SpineRouter' and subtype=='UpstreamLC'` のときだけ `route-map FROM_BGP_PEER_V4 permit 12` (`match ip address prefix-list DEFAULT_IPV4`) / `permit 13` (`set tag ... / set community internal_fallback_community`) が生成。さらに permit 13 内の `set tag` は `switch_type=='chassis-packet'` で値が分岐 (`route_do_not_send_appdb_tag` ↔ `route_eligible_for_fallback_to_default_tag`)。
- **意味**: `DEVICE_METADATA|localhost` の `type / subtype / switch_type` を bgpcfgd 起動前に確定させないと、ALLOW_LIST 末尾の DEFAULT fallback ブロックが欠落する。後から `DEVICE_METADATA` を書き換えても bgpcfgd は templateを再レンダしない (Manager 起点ではなく Jinja 起動時テンプレ生成のため) ので、bgpcfgd 再起動が必要。
- evidence: `policies.conf.j2:40-54, 63-77`

### 3. `constants.yml` (`bgp.allow_list.enabled` / `drop_community` / `default_action` / `default_pl_rules` / `prefix_match_tag`) の確定

- `BGPAllowListMgr.__init__` の `self.enabled = self.__get_enabled()` (L45) / `self.prefix_match_tag = self.__get_routemap_tag()` (L46) / `self.__load_constant_lists()` (L47) は**起動時に一度だけ** `self.constants` を読む。`set_handler` 冒頭で `if not self.enabled: log_warn(...); return True` (L56-58) なので constants で機能無効化されていれば SET は no-op 消化される。
- `policies.conf.j2:8` も `constants.bgp.allow_list.enabled` / `drop_community` の両方が定義されていないと ALLOW_LIST 全ブロックを生成しない。**bgpcfgd 起動時点で constants を確定**させる必要があり、後から constants を変更しても bgpcfgd 再起動まで効かない。
- evidence: `managers_allow_list.py:45-47, 56-58, 699-734, 764-785` / `policies.conf.j2:8`

### 4. `BGP_NEIGHBOR` / `BGP_PEER_RANGE` (peer-group 定義) 先行必須

- `__update_policy` の末尾で `__find_peer_group(deployment_id, neighbor_type)` を呼び、`self.cfg_mgr.restart_peer_groups(peer_groups)` で deployment_id にぶら下がる peer-group を soft-clear する (L177-178)。
- `__find_peer_group` は `self.cfg_mgr.get_text()` の vtysh running-config を grep し、`neighbor <pg> peer-group` (L601)、`neighbor <pg> route-map <rm> in` (L618) を抽出して deployment_id にひもづく peer-group 集合を再構成する (L686-697)。
- **順序依存**: BGP peer-group が vtysh 上に存在しない (= `BGP_NEIGHBOR` / `BGP_PEER_RANGE` 未投入) 状態で BGP_ALLOWED_PREFIXES を SET すると、prefix-list / route-map は作られるが**どの peer にも紐付かない** (peer-group が空集合)。後から peer-group を追加しても **BGP_ALLOWED_PREFIXES 側を再 SET しない限り soft-clear が起きない**ため、フィルタが有効化されない。
- 主に bgpcfgd の `BGPPeerMgrBase` (main.py L87-92) が `BGPAllowListMgr` (L94) より**前**に登録されるため、bgpcfgd フレームワークの初期スキャンでは peer-group が先に投入される設計だが、運用中の動的追加では順序逆転が発生しうる。
- evidence: `managers_allow_list.py:177-178, 595-697` / `main.py:87-94`

### 5. bgpcfgd Manager 登録順 (`main.py:73-104`)

- `BGPAllowListMgr` (L94) は以下より**後**に登録される:
  - `BGPDataBaseMgr` (DEVICE_METADATA / DEVICE_NEIGHBOR_METADATA, L75-76)
  - `InterfaceMgr` 一式 (L78-83)
  - `BGPPeerMgrBase` 一式 (L87-92)
- `BGPAllowListMgr` (L94) は以下より**前**に登録される:
  - `BBRMgr` / `StaticRouteMgr` / `AdvertiseRouteMgr` / `RouteMapMgr` / `DeviceGlobalCfgMgr` (L96-104)
- Manager 配列はそのままサブスクライバ生成順に使われ、初回スキャン時のテーブル処理順を規定する。`BGP_ALLOWED_PREFIXES` の処理時点で `BGP_NEIGHBOR` / `BGP_PEER_RANGE` は既に running-config に反映されているのが想定。
- evidence: `main.py:73-104`

### 6. vtysh push 順 (`__update_policy` 内 `cmds` 構築順)

`set_handler` → `__update_policy` の `cmds` は固定順で構築される (L167-176):

1. v4 prefix-list 更新 (`ip prefix-list <pl_v4>`)
2. v6 prefix-list 更新 (`ipv6 prefix-list <pl_v6>`)
3. community-list 更新 (`bgp community-list standard <name>` / EMPTY 時はスキップ)
4. v4 route-map "allow" entry 追加 (`route-map <rm_v4> permit <seq> / match ip address prefix-list <pl_v4> / match community <name> | set tag <prefix_match_tag>`)
5. v6 route-map "allow" entry 追加 (同上の v6 版)
6. v4 route-map "default action" 更新 (`route-map <rm_v4> permit 65535 / set community <action> additive`)
7. v6 route-map "default action" 更新 (同上の v6 版)

そして `self.cfg_mgr.push_list(cmds)` で**一括投入** (L176)。これにより prefix-list と community-list が route-map より先に存在することが保証される (FRR の前方参照は許容するが、ここでは順序を明示)。`__remove_policy` (L184-215) は逆順: route-map entry 削除 → prefix-list 削除 → community-list 削除 → default 行更新の順。

- evidence: `managers_allow_list.py:167-176, 200-207`

### 7. CommunityList と route-map の連動 (EMPTY_COMMUNITY 経路)

- key に `|<community>` が無い場合、`community_value = EMPTY_COMMUNITY = "empty"` (L15, L64, L67)。
- `__update_community` は `community_value == EMPTY_COMMUNITY` で早期 return (L360-362) → community-list は作らない。
- `__update_allow_route_map_entry` は `community_name.endswith(EMPTY_COMMUNITY)` のときに `match community` を出さず、代わりに `set tag <prefix_match_tag>` を出す (L432-435)。`prefix_match_tag` が constants に未定義なら set 行も出ない (`__get_routemap_tag` L652-664)。
- **意味**: EMPTY_COMMUNITY 経路で `constants.bgp.allow_list.prefix_match_tag` を有効化したい場合、constants 確定 → bgpcfgd 起動 → BGP_ALLOWED_PREFIXES 投入の順が必須。逆順では tag 設定が永続化されない。
- evidence: `managers_allow_list.py:15, 64, 67, 360-362, 432-435, 652-664`

### 8. seq=65535 デフォルト・トラップの上書き (template と bgpcfgd の二重書き)

- `policies.conf.j2:17-29` は **起動時に deployment_id=0 限定** で `route-map ALLOW_LIST_DEPLOYMENT_ID_0_V4|V6 permit 65535 / set community ... additive` を書く。`allow_list_default_action == 'deny'` なら `no-export`、それ以外なら `drop_community`。
- `BGPAllowListMgr.__update_default_route_map_entry` (L438-454) は SET ごとに seq=65535 の `set community` を上書きできる。**deployment_id=0** の場合は templateと bgpcfgd の両方が同じ entry を触ることになり、 bgpcfgd が**後勝ち**で `default_action` を更新する (`set_handler` 経由)。
- 一方、deployment_id≠0 では templateが 65535 entry を作らないため、**最初の SET が来るまで route-map は seq 10..29990 / 30000..65530 範囲の entry のみで、デフォルト・トラップが存在しない** → ALLOW_LIST 不一致経路は `FROM_BGP_PEER_V4 permit 11 → match community allow_list_default_community → ...` の二段目に頼ることになる。
- **順序意味合い**: deployment_id=0 を運用する場合、template起動時の `allow_list_default_action` 値 (j2 引数) と CONFIG_DB の `BGP_ALLOWED_PREFIXES|DEPLOYMENT_ID|0.default_action` が食い違うと、**bgpcfgd 起動直後の短時間は template 値、最初の SET 後は CONFIG_DB 値**となる遷移期間が発生する。
- evidence: `policies.conf.j2:15-29` / `managers_allow_list.py:438-454`

### 9. STATE_DB / 既存 running-config との整合 (`__is_prefix_list_valid` / `__parse_allow_route_map_entries`)

- `BGPAllowListMgr` は**他テーブルのような STATE_DB 副作用を持たない**。代わりに `self.cfg_mgr.get_text()` (vtysh running-config 文字列) を直接 grep し、prefix-list / route-map / community-list が既存かを判定する (L274, L322-350, L401-407, L418, L462-482, L520-567)。
- `set_handler` 冒頭で `self.cfg_mgr.update()` を呼び (L166)、最新の vtysh running-config をフェッチしてから書き込む。これは**他 Manager が同じ tick で push した結果を取り込まないと不整合になる**ため。
- **意味**: 同一 tick 内で BGP_PEER_RANGE / BGP_NEIGHBOR の peer-group 追加と BGP_ALLOWED_PREFIXES の SET が並ぶ場合、`cfg_mgr.update()` のタイミングで peer-group が反映されていれば `__find_peer_group` が正しく動くが、未反映なら restart_peer_groups が空集合になる。
- evidence: `managers_allow_list.py:166, 274, 322-350, 692-697`

---

## まとめ — 推奨書込み順

1. **constants.yml の確定** (`bgp.allow_list.enabled`, `drop_community`, `default_action`, `default_pl_rules`, `prefix_match_tag` 等)
2. **`DEVICE_METADATA|localhost`** の `type` / `subtype` / `switch_type` 確定 (テンプレ条件分岐用)
3. **bgpcfgd 起動** → `policies.conf.j2` レンダで `FROM_BGP_PEER_V4/V6` / `ALLOW_LIST_DEPLOYMENT_ID_0_V4/V6` / `allow_list_default_community` を初期化
4. **`BGP_NEIGHBOR` / `BGP_PEER_RANGE`** の投入で peer-group が vtysh 上に確定
5. **`BGP_ALLOWED_PREFIXES|DEPLOYMENT_ID|<id>[|...]`** の SET (1 deployment_id ごと)

DEL 操作は SET の逆を辿るが、`BGPAllowListMgr` の `__remove_policy` 内部順は固定 (route-map entry → prefix-list → community-list → default 行更新) のため、CONFIG_DB 側からは単純に `BGP_ALLOWED_PREFIXES` を DEL するだけで内部処理順が担保される。

deployment_id=0 を運用する場合は、template 引数 `allow_list_default_action` と CONFIG_DB の `default_action` を必ず一致させる (起動直後の短時間 mismatch を避ける)。
