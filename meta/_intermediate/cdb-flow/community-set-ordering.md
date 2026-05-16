# COMMUNITY_SET — Phase B 書込み順依存 証跡

生成日: 2026-05-16
対象ページ: `docs/reference/config-db/community-set.md`
調査ソース: sonic-buildimage (frrcfgd/frrcfgd.py), sonic-buildimage (src/sonic-frr-mgmt-framework)

---

## 1. 書込み経路と順序依存の概要

`COMMUNITY_SET` は `frrcfgd`（`BGPConfigDaemon`）が購読し、FRR の `bgp community-list` へ変換する。
`ROUTE_MAP` の `match_community` / `set_community_ref` フィールドは COMMUNITY_SET の名前を参照するため、
ROUTE_MAP を適用する前に COMMUNITY_SET が FRR に登録済みである必要がある。

---

## 2. 順序依存の詳細

### 2-1. COMMUNITY_SET → ROUTE_MAP 先行必須

`ROUTE_MAP.match_community` フィールドは COMMUNITY_SET の名前（`bgp community-list <name>`）を参照する。
frrcfgd は ROUTE_MAP の `match community` コマンドを vtysh に送る際、COMMUNITY_SET が **FRR に登録済み**
であることを前提とする（is_configurable チェックなし）。

先行未充足の場合: FRR `match community <name>` は存在しない community-list 名を参照し、
route-map の評価で常に no-match となる（サイレント失敗、エラーなし）。

evidence: `frrcfgd.py:1938` `('match_community', '[bgpd]{no:no-prefix}match community {}')`

### 2-2. is_configurable による community_member 列の順序保証

`CommunityList.is_configurable()` は `match_action`・`is_std`・`mbr_list` の **3 フィールドがすべて揃った時点**
で `True` を返す。frrcfgd はこの条件が満たされるまで `bgp community-list` コマンドを FRR へ送らない。
これにより、`set_type` / `match_action` / `community_member` の書込みが揃う前に community-list が
中途半端な状態で登録されることを防ぐ。

YANG `community_member` は `ordered-by user` leaf-list であり、frrcfgd は DB から取得した順序を
`mbr_list` にそのまま保持する。FRR へのコマンド生成（`hdl_com_set`）は `mbr_list` を順序通りに展開する。

evidence: `frrcfgd.py:1580-1582` `is_configurable()`、`frrcfgd.py:993-1006` `hdl_com_set` member 展開

### 2-3. set_community_ref / set_ext_community_ref の先行必須

ROUTE_MAP の `set_community_ref` フィールド（FRR `set community {:com-ref}`）は
`comm_set_list` から COMMUNITY_SET を引き当ててメンバーを展開する。
対象の COMMUNITY_SET が `comm_set_list` に存在しない場合、`format('com-ref')` が `None` を返し
FRR コマンドが生成されない（サイレントスキップ）。

evidence: `frrcfgd.py:831-834` `CommandArgument.__format__` の `com-ref` 分岐

---

## 3. 書込み順依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `COMMUNITY_SET` 登録が ROUTE_MAP `match_community` 参照より先行 | **先行必須** | 未先行時: FRR community-list が未定義 → match は常に no-match（サイレント失敗） |
| 2 | `set_type` / `match_action` / `community_member` の 3 フィールドが揃った時点で FRR へ反映 | **原子的反映** | `is_configurable()` が False の間はコマンド生成がスキップ（中途半端な登録を防止） |
| 3 | `community_member` の順序は DB 投入順が FRR に伝播（`ordered-by user`） | **順序保持** | mbr_list の順序を変更した場合は DELETE → re-ADD が必要 |
| 4 | ROUTE_MAP `set_community_ref` 参照は COMMUNITY_SET が `comm_set_list` 登録済みであること | **先行必須** | 未先行時: `com-ref` format が None → FRR `set community` コマンドがスキップ（サイレント） |

---

## 4. evidence 一覧

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:831-834` — `CommandArgument.__format__` `com-ref` 分岐
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:988-1006` — `hdl_com_set` member 列展開
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:1580-1582` — `CommunityList.is_configurable()`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:1938-1939` — route_map_key_map `match_community` / `match_ext_community`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:1953` — route_map_key_map `set_community_ref`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:2300-2301` — `COMMUNITY_SET` 購読登録
