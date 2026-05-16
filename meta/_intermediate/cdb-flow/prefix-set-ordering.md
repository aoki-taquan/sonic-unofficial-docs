# PREFIX_SET — 書込み順依存調査 (Phase B)

## スキャン対象

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang`

## 調査結果

### PREFIX_SET → PREFIX の先行必須

frrcfgd の init フェーズ（L2227-2246）は以下の順序で CONFIG_DB を読み込む:

1. `PREFIX_SET` テーブルを全件取得して `self.prefix_set_list` に格納 (L2228-2232)
2. `PREFIX` テーブルを全件取得し、各エントリの `pfx_set_name` が `self.prefix_set_list` に存在する場合のみ `add_prefix()` 呼出 (L2243-2245)

runtime の `bgp_table_handler_common()` (L2894-2950) でも同様:
- `PREFIX` イベント受信時 (L2914-2916): `pfx_set_name not in self.prefix_set_list` の場合 LOG_ERR を出して `continue`（完全スキップ）

→ **`PREFIX_SET|<name>` の SET が `PREFIX` の SET より先行していなければ PREFIX エントリが DROP される**

### ROUTE_MAP との順序依存 (sonic-route-map.yang)

YANG leafref (L163-187):
- `ROUTE_MAP.*.match_prefix_set` → `PREFIX_SET.PREFIX_SET_LIST.name`
- `ROUTE_MAP.*.match_ipv6_prefix_set` → `PREFIX_SET.PREFIX_SET_LIST.name`
- `ROUTE_MAP.*.match_next_hop_set` → `PREFIX_SET.PREFIX_SET_LIST.name`

YANG 経路での書き込み: `PREFIX_SET` が存在しない状態で `ROUTE_MAP.match_prefix_set` に書こうとすると leafref validation reject。

直書き経路(redis-cli等): YANG バリデーションをスキップするため ROUTE_MAP に未定義 prefix-set 名を書けるが、frrcfgd の `bgp_table_handler_common()` が ROUTE_MAP を処理する際に `get_prefix_set_name()` で set を検索し `prefix_set_list` に存在しなければ af_mode が不明 → FRR コマンド生成時に IPv4 として扱われる（L2673-2676）

### PREFIX_SET SET 更新時の挙動（UPDATE 時に上書き不可）

runtime で既存 `PREFIX_SET|<name>` に SET イベントが届いた場合 (L2896-2900):
```python
if pfx_set_name in self.prefix_set_list:
    # already exists — skip (continue)
```
`mode` 変更は**静かに無視**される。mode 変更には:
1. `PREFIX_SET|<name>` DEL → `PREFIX` 全メンバ DEL → `PREFIX_SET|<name>` SET（新 mode）→ `PREFIX` 再投入

という順序が必要。

### DEL 順序

YANG leafref により、`ROUTE_MAP.match_prefix_set` が参照している `PREFIX_SET|<name>` を DEL しようとすると YANG 経路では reject。直書きの場合は DEL が通るが frrcfgd は `prefix_set_list` から削除しても関連する FRR `ip prefix-list` を自動削除しない（`PREFIX` 側の DEL イベントが別途必要）。

推奨 DEL 順:
1. `ROUTE_MAP.match_prefix_set` / `match_next_hop_set` の当該 prefix-set 参照を削除
2. `PREFIX|<name>|*` の各エントリを DEL
3. `PREFIX_SET|<name>` を DEL

### TABLE_DAEMON との関係

- `PREFIX_SET`: `['bgpd']` (L83)
- `PREFIX`: `['zebra', 'bgpd', 'ospfd', 'pimd']` (L87)

`PREFIX` 変更は zebra/ospfd/pimd 等複数 FRR デーモンに影響する。

## 証跡

- `frrcfgd.py:83,87` — TABLE_DAEMON 定義
- `frrcfgd.py:2227-2246` — init 時の PREFIX_SET → PREFIX 読み込み順
- `frrcfgd.py:2894-2916` — runtime handler の PREFIX_SET / PREFIX 処理
- `frrcfgd.py:2663-2676` — ROUTE_MAP handler の prefix_set_list 参照
- `sonic-route-map.yang:163-187` — leafref 定義
