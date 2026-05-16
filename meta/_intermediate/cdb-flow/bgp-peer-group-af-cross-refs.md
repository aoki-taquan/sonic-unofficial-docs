# BGP_PEER_GROUP_AF テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/bgp-peer-group-af.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`。`BGP_PEER_GROUP_AF` テーブル変更時に `frrcfgd` (`BGPConfigDaemon`) が間接的に読み出す・依存する関連 CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -n "BGP_PEER_GROUP_AF\|BGP_PEER_GROUP\b\|BGP_GLOBALS_AF\|ROUTE_MAP\|PREFIX_LIST\|nbr_af_key_map\|route_map_in\|route_map_out\|prefix_list_in\|prefix_list_out" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py
```

## 検出された暗黙参照テーブル

### 1. `BGP_PEER_GROUP` — peer-group 存在ガード (必須前提)

`frrcfgd.py` は `BGPConfigDaemon.__init__()` (L2187) で `BGP_PEER_GROUP` テーブルを `get_table()` で一括ロードし、`self.bgp_peer_group[vrf][pg_name]` キャッシュを構築する。

`BGP_PEER_GROUP_AF` の SET 処理 (L2865) は `bgp_table_handler_common()` に渡り、FRR `router bgp ... / address-family ... / neighbor <pg_name> ...` コマンドを発行する。この時点で FRR 内に peer-group が存在しない場合、vtysh コマンドが失敗し `LOG_ERR` が出力される。つまり `BGP_PEER_GROUP` が先に設定されていることが前提。

| 参照種別 | タイミング | evidence |
|---|---|---|
| 起動時一括ロード | `get_table('BGP_PEER_GROUP')` → `self.bgp_peer_group` キャッシュ構築 | frrcfgd.py:2187-2191 |
| ランタイム前提 | peer-group 存在なしでは AF コマンドが FRR で失敗 | frrcfgd.py:2865,2873 |

### 2. `BGP_GLOBALS` — VRF local_asn ガード (必須前提)

`bgp_table_handler_common()` は全 VRF ベーステーブルで `self.__get_vrf_asn(vrf)` を呼び出し (L2658-2662)、`local_asn` が未設定の場合は `LOG_DEBUG` して skip する。`BGP_GLOBALS.local_asn` が設定されるまで `BGP_PEER_GROUP_AF` の変更は無効。

| 参照種別 | タイミング | evidence |
|---|---|---|
| ランタイム guard | `__get_vrf_asn(vrf)` が None → continue (skip) | frrcfgd.py:2658-2662 |
| 起動時ロード | `get_table('BGP_GLOBALS')` → `self.bgp_asn[vrf]` キャッシュ | frrcfgd.py:2165-2179 |

### 3. `BGP_GLOBALS_AF` — address-family 有効化の前提

`BGP_GLOBALS_AF` は address-family レベルのグローバル設定 (redistribute / max-med 等) を保持する。`frrcfgd` は起動時に `BGP_GLOBALS_AF` も vrf_tables として同一 VRF スコープで購読 (L2136,2297)。`BGP_PEER_GROUP_AF` が有効に機能するには、対応する AF (`ipv4_unicast` 等) が `BGP_GLOBALS_AF` で初期化されている必要がある（`router bgp ... / address-family ... {}` コンテキストが存在しない場合 vtysh が失敗する）。

| 参照種別 | タイミング | evidence |
|---|---|---|
| 処理順序依存 | BGP_GLOBALS_AF の AF 設定が先行して `address-family` コンテキストを確立 | frrcfgd.py:2297,2771-2781 |
| 購読 (同 daemon 内) | `table_handler_list` で `BGP_GLOBALS_AF` → `BGP_PEER_GROUP_AF` の順で登録 | frrcfgd.py:2297,2305 |

### 4. `ROUTE_MAP` — `route_map_in` / `route_map_out` / `default_rmap` の参照先

`nbr_af_key_map` (L1903-1904) に `route_map_in` / `route_map_out` / `default_rmap` のエントリがある。これらフィールドの値は ROUTE_MAP テーブルのエントリ名を文字列参照する。`frrcfgd` は起動時に `get_table('ROUTE_MAP')` でキャッシュし (L2206-2211)、ROUTE_MAP が先行して存在していることを前提に FRR `neighbor <pg> route-map <name> in/out` コマンドを発行する。

| フィールド | FRR コマンド | evidence |
|---|---|---|
| `route_map_in` | `neighbor <pg> route-map <name> in` | frrcfgd.py:1903, nbr_af_key_map |
| `route_map_out` | `neighbor <pg> route-map <name> out` | frrcfgd.py:1904, nbr_af_key_map |
| `default_rmap` | `neighbor <pg> default-originate route-map <name>` | frrcfgd.py:1900, nbr_af_key_map |

起動時ロード (L2206) は FRR との整合確認のため。FRR 側で未定義の route-map 名を参照しても vtysh はコマンドを受理するが、実際の転送動作は不定になる。

### 5. `PREFIX_LIST` (PREFIX / PREFIX_SET) — `prefix_list_in` / `prefix_list_out` の参照先

`nbr_af_key_map` (L1918-1919) に `prefix_list_in` / `prefix_list_out` がある。これらの値は FRR prefix-list 名を文字列参照する。`frrcfgd` は起動時に `PREFIX_SET` / `PREFIX` テーブルを一括ロードして `self.prefix_set_list` キャッシュを構築し (L2227-2247)、AF 判定 (ipv4/ipv6) に利用する。

| フィールド | FRR コマンド | evidence |
|---|---|---|
| `prefix_list_in` | `neighbor <pg> prefix-list <name> in` | frrcfgd.py:1918, nbr_af_key_map |
| `prefix_list_out` | `neighbor <pg> prefix-list <name> out` | frrcfgd.py:1919, nbr_af_key_map |

`filter_list_in` / `filter_list_out` は AS_PATH_SET を参照するが、frrcfgd は文字列をそのまま FRR に渡すだけで DB ルックアップしない（FRR 側で解決）。

## まとめ — `bgp-peer-group-af.md` Phase C 記載対象

| カテゴリ | テーブル | 関係 |
|---|---|---|
| 必須前提 (peer-group 実体) | `BGP_PEER_GROUP` | AF 設定前に peer-group が存在しないと FRR コマンド失敗 |
| 必須前提 (VRF/ASN) | `BGP_GLOBALS` | `local_asn` 未設定 VRF の更新は silent skip |
| 処理順序依存 | `BGP_GLOBALS_AF` | AF コンテキストを事前確立する必要がある |
| 文字列参照 (route policy) | `ROUTE_MAP` | `route_map_in` / `route_map_out` / `default_rmap` の値として名前参照 |
| 文字列参照 (prefix filter) | `PREFIX` / `PREFIX_SET` | `prefix_list_in` / `prefix_list_out` の値として名前参照 |

## 検証コマンド

```bash
grep -n "BGP_PEER_GROUP_AF\|nbr_af_key_map\|route_map_in\|prefix_list_in\|get_table\|bgp_peer_group\b" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py | head -40
```

このスキャン結果から派生して `docs/reference/config-db/bgp-peer-group-af.md` の `<!-- cross-refs -->` ブロックを生成する。
