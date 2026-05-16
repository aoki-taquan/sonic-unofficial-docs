# BGP_ALLOWED_PREFIXES — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-bgp-allowed-prefixes)

> 対象ページ: `docs/reference/config-db/bgp-allowed-prefixes.md`
> ソース: `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py`,
>        `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/policies.conf.j2`

<!-- failure -->
## Phase D: 失敗挙動マトリクス

`BGPAllowListMgr` (継承元 `Manager`) は `set_handler` / `del_handler` 戻り値を CONFIG_DB sub の上位 SubscriberStateTable ループに返す。
**`return False` は「未消化」扱いで Manager の SubscriberStateTable が次イテレーションで再投入する**ため、依存物（FRR の community-list / route-map / `CommunityList`）が準備されるまで暗黙にリトライが続く。
`return True` は「処理消化（成功または明示スキップ）」を意味する。

### SET 処理における失敗経路 (`managers_allow_list.py`)

| 失敗条件 | 検出箇所 | 戻り値 | 結果 / リトライ | ログ |
|---|---|---|---|---|
| `constants["bgp"]["allow_list"]["enabled"]` が `false` / 未定義 | `set_handler()` (enabled gate) | `True` (消化) | feature 無効。テーブル更新は warn log のみで完全スキップ。リトライなし | `LOG_WARN "Received 'SET' ..., but this feature is disabled in constants"` (`managers_allow_list.py:699-707`) |
| key が `key_re` パターン (`DEPLOYMENT_ID\|<id>[\|NEIGHBOR_TYPE\|<type>][\|<community>]`) に不一致 | `__set_handler_validate()` | `False` (**未消化 → 再投入**) | キー解析できない限り Manager ループが再試行を続ける | `LOG_ERR "Received BGP ALLOWED 'SET' message with invalid key: '%s'"` |
| `data` が `None` | `__set_handler_validate()` | `False` (未消化) | 同上 | `LOG_ERR "data shouldn't be None"` |
| `default_action` が `"permit"` / `"deny"` 以外 | `__set_handler_validate()` | `False` (未消化) | 値訂正まで再試行 | `LOG_ERR` |
| `prefixes_v4` に IPv6 表記が混入 | `__set_handler_validate()` (`ipaddress.IPv4Network` parse 例外) | `False` (未消化) | 訂正まで再試行 | `LOG_ERR` |
| `prefixes_v6` に IPv4 表記が混入 | 同上 | `False` (未消化) | 同上 | `LOG_ERR` |
| `prefixes_v4` と `prefixes_v6` が両方空 (`len(v4)+len(v6)==0`) | `__set_handler_validate()` (`managers_allow_list.py:107-109`) | `False` (未消化) | 訂正まで再試行 | `LOG_ERR "Received BGP ALLOWED 'SET' command without prefixes. Skip it."` |
| `<id>` (deployment_id) が CONFIG_DB の `DEVICE_METADATA.localhost.deployment_id` と不一致 | `__update_policy()` 内で参照される deployment_id 比較 | `True` (消化) but FRR ポリシー差し替えは行われず effective には no-op | リトライなし。ログは debug 程度 (silent skip 寄り) | (silent / debug) |
| FRR `community-list` (`drop_community` の前提) が未定義状態 | `__update_community_list()` → `vtysh -c "bgp community-list ..."` 失敗 | 例外伝播せず `False` で抜けるパス (vtysh CalledProcessError catch) → **未消化 → 再投入** | FRR 起動待ち or `drop_community` 設定待ちの間ループ。最終的に FRR 側で community-list が用意されると消化 | `LOG_ERR` (vtysh stderr) |
| vtysh コマンド (`__update_policy` / `__update_prefix_list` 内 `cfg_mgr.push_list()`) 失敗 | `cfg_mgr.push_list()` の戻り False | `False` (未消化) | FRR `bgpd` 起動待ち / route-map 文法エラー等の間リトライ | `LOG_ERR "BGPAllowListMgr::push_list failed"` |
| `__to_prefix_list()` で prefix 解析中に例外 | `__to_prefix_list()` (managers_allow_list.py:736-754) | 例外伝播 → caller の `False` | 未消化扱い | スタックトレース (未捕捉) |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 戻り値 | 結果 |
|---|---|---|---|
| `del_handler` で key が `key_re` 不一致 | `__del_handler_validate()` | `True` (消化) — DEL は値検証なしで silent skip | `LOG_ERR "Received BGP ALLOWED 'DEL' message with invalid key"` のみ。再投入されない |
| `constants` で `enabled=false` | `del_handler()` enabled gate | `True` (消化) | 何もせず return。`LOG_WARN` のみ |
| vtysh からの prefix-list / route-map 削除失敗 | `cfg_mgr.push_list()` 戻り False | `False` (未消化) | FRR セッション復旧まで再試行 | `LOG_ERR` |
| DEL 後のフォールバック (`data=None` で `__update_policy` 再呼び出し) で `default_action` を constants の値で再生成 | `managers_allow_list.py:197` | リトライ用ではなく**残置ポリシー再構築**経路 | DEL 後も最後の deployment_id に対しては constants 由来の default-action ルールが残る | (silent) |

### policies.conf.j2 (FRR テンプレ) 由来の暗黙失敗

| 条件 | 検出箇所 | 結果 |
|---|---|---|
| `switch_type == 'chassis-packet'` 配下で `route_eligible_for_fallback_to_default_tag` が未定義 | `policies.conf.j2:48,71` (Jinja undefined → render エラー) | テンプレ生成失敗 → `bgpcfgd` 起動シーケンスで FRR config が空。**`bgpcfgd` が再評価サイクルで `set_handler` を再呼び出し**、結果として **未消化 (`False`)** ループに陥り、constants の整備まで継続リトライ |
| `type == 'SpineRouter'` だが `subtype` が `UpstreamLC` 以外 | `policies.conf.j2:41,64` | DEFAULT_IPV4/V6 マッチブロックを**生成しない** (silent skip)。ALLOW_LIST 不一致経路は `permit 11 → permit 100` で素通り |
| `deployment_id` が constants の `bgp.allow_list.<id>` セクションと一致しない | `__update_policy()` 内で `deployment_id` 比較 | community / prefix-list 生成スキップ。SET は消化 (`True`) するが effective には no-op |

### リトライ機構の補足

- `BGPAllowListMgr` は `Manager` 基底クラスのループに従う。`set_handler` が `False` を返すと SubscriberStateTable 側で再投入され、依存物 (FRR `community-list` 準備、constants 整備、vtysh セッション復旧) が揃った時点で自然に消化される。
- リトライ回数の上限はなく、明示的なバックオフもない。CPU spike を防ぐのは sonic-py-swsssdk の sub-loop 側のイベント駆動構造のみ。
- `community-list` 未準備時 / FRR 起動直後の vtysh エラーは数秒〜十数秒の間に解決するのが通常。
- **deployment_id 不一致**は CONFIG_DB の `DEVICE_METADATA.localhost.deployment_id` を後から書き換えても、`BGPAllowListMgr` 側はテーブル再 SET でしかトリガされない (deployment_id 変化を sub していない) ため、`config reload` または各 entry の再書き込みが必要。

### grep カバレッジ

| 項目 | hit | 証跡 |
|---|---|---|
| `LOG_ERR` (`managers_allow_list.py`) | >=5 | invalid key / data None / default_action / prefixes both empty / push_list failed |
| `LOG_WARN` (`enabled` gate) | 2 | `set_handler` / `del_handler` 双方 (`managers_allow_list.py:699-707`) |
| `return False` (`set_handler` validate path) | >=4 | `__set_handler_validate()` 内の各 fail 経路 |
| `return True` (silent skip) | 2 | enabled gate (`SET`/`DEL`) |
| `cfg_mgr.push_list()` 失敗時 | 1 | vtysh write 失敗 |
| `policies.conf.j2` 分岐 | 2 | `switch_type=='chassis-packet'` (L48,71) / `type=='SpineRouter' and subtype=='UpstreamLC'` (L41,64) |

> **Evidence**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py` (set_handler enabled gate L699-707, validate L75-110, default_action fallback L197, __to_prefix_list L736-754, default action community L773-785); `sonic-buildimage/dockers/docker-fpm-frr/frr/policies.conf.j2` L41,48,64,71。

<!-- /failure -->
