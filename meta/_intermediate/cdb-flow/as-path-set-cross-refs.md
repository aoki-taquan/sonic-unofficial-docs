# AS_PATH_SET テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/as-path-set.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-buildimage` の以下 2 経路:

- `src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py` (`AsPathMgr`)
- `src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (`hdl_aspath_set` / `aspath_set_key_map`)

両経路を全行精読し、`AS_PATH_SET` テーブル変更時または `AS_PATH_SET` の効果が成立する前提として、間接的に読み出される (= 暗黙参照される) 関連 CONFIG_DB テーブルを抽出した。

## スキャン手順

```bash
grep -nE "config_db|get_table|get_entry|subscribe|tbl_to_key_map|table\s*==" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py

grep -nE "AsPathMgr|self\.directory|self\.cfg_mgr|DEVICE_METADATA" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py
```

## 検出された暗黙参照テーブル

### 1. `DEVICE_METADATA` (bgpcfgd `AsPathMgr` の購読テーブル)

`AsPathMgr` は `AS_PATH_SET` を購読しない。代わりに `DEVICE_METADATA` テーブルを購読し (`bgpcfgd/main.py:129` — `AsPathMgr(common_objs, "CONFIG_DB", "DEVICE_METADATA")`)、`localhost` 行の `t2_group_asns` leaf-list を読んで **固定名 `T2_GROUP_ASNS`** の AS path access-list を生成する。

| 参照箇所 | 用途 | evidence |
|---|---|---|
| `managers_as_path.py:31` (`if key != "localhost": return True`) | DEVICE_METADATA の `localhost` 行のみ処理 | bgpcfgd/managers_as_path.py:31,61 |
| `managers_as_path.py:35` (`if key_inside == "t2_group_asns"`) | `t2_group_asns` フィールドのみ読み出し | bgpcfgd/managers_as_path.py:35 |
| `managers_as_path.py:40` (`asns.split(",")`) | カンマ区切り ASN 列を集合化 | bgpcfgd/managers_as_path.py:40 |
| `managers_as_path.py:56` | `bgp as-path access-list T2_GROUP_ASNS permit _<asn>_` を発行 | bgpcfgd/managers_as_path.py:56 |
| `sonic-device_metadata.yang:330` | `t2_group_asns` leaf-list の YANG 定義 | sonic-device_metadata.yang:330 |

> 意味するところ: `AS_PATH_SET` テーブル自体の購読者は `frrcfgd` のみ。bgpcfgd 経路は別テーブル `DEVICE_METADATA.localhost.t2_group_asns` を入り口として **`AS_PATH_SET` テーブルとは独立に** 固定名 `T2_GROUP_ASNS` の access-list を生成する。`AS_PATH_SET|T2_GROUP_ASNS` 行と名前が衝突した場合、両経路が同じ FRR access-list 名へ書き込み、UPDATE 時の全削除→再 ADD パターン (`frrcfgd.py:1015`) と AsPathMgr の差分追記が競合する。

### 2. `ROUTE_MAP` (frrcfgd 同一テーブルマップ経由の消費者)

`AS_PATH_SET` が「access-list として登録される」だけでは効果を持たない。`ROUTE_MAP` の `match as-path <name>` から参照されて初めて BGP UPDATE フィルタリングが成立する。frrcfgd は両テーブルを **同じ `tbl_to_key_map` 経由・同じ bgp_table_handler_common で処理** する。

| 参照箇所 | 用途 | evidence |
|---|---|---|
| `frrcfgd.py:86` (`'ROUTE_MAP': ['zebra', 'bgpd', 'ospfd']`) | ROUTE_MAP の daemon バインド (bgpd 経由で as-path 参照が成立) | frrcfgd.py:86 |
| `frrcfgd.py:1940` (`('match_as_path', '[bgpd]{no:no-prefix}match as-path {}')`) | `route_map_key_map` の `match_as_path` で AS_PATH_SET の `name` をリテラル参照 | frrcfgd.py:1940 |
| `frrcfgd.py:2113` / `frrcfgd.py:2116` | `tbl_to_key_map['ROUTE_MAP']` と `tbl_to_key_map['AS_PATH_SET']` が同一 dict に登録 | frrcfgd.py:2113,2116 |
| `frrcfgd.py:2205-2211` (`self.route_map = {}` 起動時スキャン) | ROUTE_MAP 全件を保持。AS_PATH_SET 名との整合性は frrcfgd 側で検証されない | frrcfgd.py:2205-2211 |

> 暗黙参照の方向: `ROUTE_MAP.match_as_path` の値は **AS_PATH_SET の `name` (key) に対する文字列参照** で、frrcfgd / FRR どちらにも参照整合性チェックがない。AS_PATH_SET 削除後も `ROUTE_MAP` 側に古い名前が残ると FRR 側で「未定義 access-list 参照」となる。

### 3. `BGP_GLOBALS` (vrf スコープと bgpd プロセス前提)

`AS_PATH_SET` 自体は VRF を持たない (`frrcfgd.py:2136-2140` の `vrf_tables` set に含まれない) グローバルテーブルだが、生成される FRR コマンド (`bgp as-path access-list ...`) は **`bgpd` プロセスのグローバルコンフィグ** に投入され、`BGP_GLOBALS` で定義された `local_asn` 等の BGP インスタンスが起動している前提でしか効果を持たない。

| 参照箇所 | 用途 | evidence |
|---|---|---|
| `frrcfgd.py:81` (`'BGP_GLOBALS': ['bgpd']`) | bgpd プロセスへのバインド宣言 | frrcfgd.py:81 |
| `frrcfgd.py:96` (`'AS_PATH_SET': ['bgpd']`) | AS_PATH_SET も同じく bgpd 専用 | frrcfgd.py:96 |
| `frrcfgd.py:2175` (`glb_table = self.config_db.get_table('BGP_GLOBALS')`) | 起動時に BGP_GLOBALS を全件読み込み (frrcfgd 内部で BGP インスタンス管理) | frrcfgd.py:2175 |
| `frrcfgd.py:2296` (`('BGP_GLOBALS', self.bgp_global_handler)`) | BGP_GLOBALS の subscribe — bgpd 起動前提が変化したら as-path も再評価 | frrcfgd.py:2296 |

> 厳密には `AS_PATH_SET` ハンドラ (`hdl_aspath_set` — frrcfgd.py:1009-1020) が `BGP_GLOBALS` の値を読み出すわけではない。だが、bgpd プロセスが立っていない (= `BGP_GLOBALS` が空) 環境では FRR 側で `bgp as-path access-list` コマンド自体は受理されるものの、参照側の BGP UPDATE 評価が起こらず無効化される。実質的な共依存テーブル。

## 範囲外 (誤解されやすい隣接テーブル)

- **`COMMUNITY_SET`** / **`PREFIX_SET`** / **`AS_PATH_LIST`** (= `BGP_COMMUNITY_LIST`): いずれも `sonic-routing-policy-sets.yang` 配下の兄弟テーブルで、`ROUTE_MAP` から並列に参照される。`AS_PATH_SET` 側からは読み出さない (frrcfgd の `hdl_aspath_set` 内で参照無し)。 `関連 CONFIG_DB` セクションに留め、Phase C `cross-refs` ブロックには含めない。
- **`BGP_GLOBALS_AF` / `BGP_GLOBALS_LISTEN_PREFIX` / `BGP_NEIGHBOR`** などの BGP 派生テーブル: frrcfgd 内では同じ `tbl_to_key_map` を共有するが、`AS_PATH_SET` ハンドラ経路は触らない。`bgpd` プロセスを共有するという意味では間接前提だが、`BGP_GLOBALS` で代表させて Phase C には個別記載しない。
- **`DEVICE_METADATA.localhost.hostname`** / **`localhost.bgp_asn`**: 同じ `DEVICE_METADATA` テーブルだが `AsPathMgr` は `t2_group_asns` のみ読み出す (`managers_as_path.py:35`)。`hostname` / `bgp_asn` は `AsPathMgr` の判定経路に出てこない。

## まとめ — `as-path-set.md` Phase C 記載対象

| カテゴリ | テーブル / フィールド | 経路 |
|---|---|---|
| 別経路の購読入り口 (bgpcfgd 専用) | `DEVICE_METADATA.localhost.t2_group_asns` | `AsPathMgr` が固定名 `T2_GROUP_ASNS` の access-list を生成 |
| 同一テーブルマップ上の消費者 (frrcfgd 共有) | `ROUTE_MAP.match_as_path` | `ROUTE_MAP` の `match as-path <name>` で AS_PATH_SET 名を参照 |
| bgpd プロセス前提 | `BGP_GLOBALS` | `bgp as-path access-list` 投入先 bgpd の起動前提 |

## 検証コマンド

```bash
grep -n "AS_PATH_SET\|aspath_set\|as_path_set\|hdl_aspath_set\|match_as_path" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py

grep -n "T2_GROUP_ASNS\|t2_group_asns\|DEVICE_METADATA" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py
```

このスキャン結果から派生して `docs/reference/config-db/as-path-set.md` の `<!-- cross-refs -->` ブロックを生成する。
