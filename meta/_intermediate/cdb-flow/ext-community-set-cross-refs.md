# EXTENDED_COMMUNITY_SET テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/community-set.md` の Phase C (暗黙参照) ブロック裏付け資料。
`EXTENDED_COMMUNITY_SET` は `community-set.md` 内で併記されている。

ソースは `sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`。`EXTENDED_COMMUNITY_SET` テーブル変更時に `frrcfgd` (`BGPConfigDaemon`) が間接的に読み出す・依存する関連 CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -n "EXTENDED_COMMUNITY_SET\|extcomm_set_list\|comm_set_handler\|match_ext_community\|set_ext_community_ref\|set_ext_community_inline\|get_table.*EXTENDED\|hdl_set_extcomm\|hdl_com_set" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py
```

## 検出された暗黙参照テーブル

### 1. `ROUTE_MAP` — `match_ext_community` / `set_ext_community_ref` の参照先 (被参照)

`frrcfgd.py` の `route_map_key_map` (L1939, L1955) に `match_ext_community` と `set_ext_community_ref` が登録されている。

- `match_ext_community` フィールド: `ROUTE_MAP` エントリが `EXTENDED_COMMUNITY_SET.name` を文字列参照し、FRR へ `match extcommunity <name>` コマンドを発行する (sonic-route-map.yang L256-260)。
- `set_ext_community_ref` フィールド: `ROUTE_MAP` エントリが `EXTENDED_COMMUNITY_SET.name` を文字列参照し、`hdl_set_extcomm()` が `daemon.extcomm_set_list.get(args[0])` でランタイムキャッシュを参照してから FRR へ `set extcommunity rt/soo <members>` コマンドを生成する (frrcfgd.py:423-427, 856-863)。

`EXTENDED_COMMUNITY_SET` が先に設定されていないと `hdl_set_extcomm()` が `LOG_ERR` を出力し FRR コマンド生成をスキップする (frrcfgd.py:424-426)。

| 参照フィールド | FRR コマンド | YANG leafref | evidence |
|---|---|---|---|
| `ROUTE_MAP.match_ext_community` | `match extcommunity <name>` | `sonic-route-map.yang:L256-258` | frrcfgd.py:1939 |
| `ROUTE_MAP.set_ext_community_ref` | `set extcommunity rt/soo <members>` | `sonic-route-map.yang:L355-358` | frrcfgd.py:1955, 423-427 |

### 2. `BGP_NEIGHBOR_AF` — `set_ext_community_ref` 経由の間接参照

`BGP_NEIGHBOR_AF` は `nbr_af_key_map` (frrcfgd.py:2111) で管理されており、直接 `EXTENDED_COMMUNITY_SET` を参照するフィールドはない。ただし `set_ext_community_ref` は `ROUTE_MAP` 経由で `EXTENDED_COMMUNITY_SET` に依存するため、経路フィルタリングのコンテキストで間接的に連動する。`frrcfgd` は起動時に `get_table('EXTENDED_COMMUNITY_SET')` でキャッシュを構築し (frrcfgd.py:2221-2226)、`bgp_table_handler_common()` の実行中に `hdl_set_extcomm()` が `daemon.extcomm_set_list` を参照する。

| 参照種別 | タイミング | evidence |
|---|---|---|
| 起動時一括ロード | `get_table('EXTENDED_COMMUNITY_SET')` → `self.extcomm_set_list` キャッシュ構築 | frrcfgd.py:2221-2226 |
| ランタイム参照 | `hdl_set_extcomm()` が `daemon.extcomm_set_list.get(name)` を参照 | frrcfgd.py:423-427, 856-863 |

## まとめ — `community-set.md` Phase C 記載対象 (EXTENDED_COMMUNITY_SET 分)

| カテゴリ | テーブル | 関係 |
|---|---|---|
| 被参照 (name leafref) | `ROUTE_MAP` | `match_ext_community` / `set_ext_community_ref` フィールドが EXTENDED_COMMUNITY_SET.name を leafref で参照。set_ext_community_ref は frrcfgd のランタイムキャッシュ参照も伴う |
| 間接参照 (ランタイム) | `BGP_NEIGHBOR_AF` | ROUTE_MAP 経由で extcomm_set_list を参照。起動時に全エントリをキャッシュ |

## 検証コマンド

```bash
grep -n "EXTENDED_COMMUNITY_SET\|extcomm_set_list\|hdl_set_extcomm\|match_ext_community\|set_ext_community_ref" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py | head -30
grep -n "match_ext_community\|set_ext_community_ref\|set_ext_community_inline" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang
```

このスキャン結果から派生して `docs/reference/config-db/community-set.md` の `<!-- cross-refs -->` ブロック (EXTENDED_COMMUNITY_SET 節) を生成する。
