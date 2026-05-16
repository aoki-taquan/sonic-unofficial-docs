# BGP_PEER_GROUP — Phase C: 暗黙参照 (cross-table refs) 調査メモ

調査日: 2026-05-16
ソース:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`

---

## 調査対象

`docs/reference/config-db/bgp-peer-group.md` Phase C 追加分。
`BGP_PEER_GROUP` の YANG (`sonic-bgp-peergroup.yang`) には `vrf_name` への leafref があるが、
ハンドラ実装上の暗黙参照（`BGP_GLOBALS`、`ROUTE_MAP`、`BGP_PEER_GROUP_AF`）を調査する。

---

## YANG leafref

`sonic-bgp-peergroup.yang`:
- `vrf_name` → `BGP_GLOBALS_LIST.vrf_name` への leafref（YANG レベルの参照、本調査のスコープ外）

上記以外の外部テーブルへの leafref 宣言はなし。
残る参照はすべて frrcfgd / bgpcfgd 実装上の暗黙参照。

---

## 暗黙参照 (実装レベル)

### 1. BGP_GLOBALS（必須・ブロッキング）

- **参照先テーブル**: `BGP_GLOBALS|<vrf_name>` の `local_asn` フィールド
- **参照方向**: 読み取り（startup 時 `get_table` + ランタイム `__get_vrf_asn`）
- **条件**: 常時。`BGP_PEER_GROUP` の SET/DEL いずれでも先行チェック
- **参照元**:
  - 起動時: `frrcfgd.py` L2175–2180（`glb_table = self.config_db.get_table('BGP_GLOBALS')` で `bgp_asn` キャッシュ構築）
  - ランタイム: `frrcfgd.py` L2658–2662（`local_asn = self.__get_vrf_asn(vrf)` → None なら LOG_DEBUG して skip）
- **意味**: `BGP_PEER_GROUP` の処理には当該 VRF の `BGP_GLOBALS.local_asn` が必須。
  未設定 VRF のエントリは silently drop（LOG_DEBUG のみ、エラーなし）。
  FRR vtysh コマンド `router bgp <local_asn> vrf <vrf>` の `<local_asn>` として使用される。
- **ブロッキング依存**: `BGP_GLOBALS` が投入される前に `BGP_PEER_GROUP` が到達しても処理されない。

### 2. BGP_PEER_GROUP_AF（派生・依存）

- **参照先テーブル**: `BGP_PEER_GROUP_AF|<vrf_name>|<peer_group_name>|<afi_safi>` （派生テーブル）
- **参照方向**: 逆参照（peer-group の `asn` OP_ADD/DELETE 時に `BGP_PEER_GROUP_AF` を再適用）
- **条件**: `asn` フィールドの OP_ADD または OP_DELETE が発生したとき
- **参照元**: `frrcfgd.py` L2865（`elif table == 'BGP_NEIGHBOR_AF' or table == 'BGP_PEER_GROUP_AF':`）
  および `frrcfgd.py` `__nbr_impl_action` L2551–2563（`is_pg=True` 時 `chk_attrs=['asn']`、
  `apply` 返却時に `BGP_GLOBALS_LISTEN_PREFIX` と `BGP_NEIGHBOR` を再適用する cascade）
- **意味**: peer-group の `asn` が変更されると、紐づく `BGP_PEER_GROUP_AF`（アドレスファミリ設定）
  および `BGP_GLOBALS_LISTEN_PREFIX`（listen range）・`BGP_NEIGHBOR`（メンバー neighbor）を
  frrcfgd が内部キャッシュから再適用する（`__apply_dep_vrf_table` 呼び出し）。
  `BGP_PEER_GROUP_AF` が CONFIG_DB に存在しない状態で peer-group が作成された場合、
  AF 設定は後続の SET イベントで別途投入される（順序依存あり）。

### 3. ROUTE_MAP（条件付き参照）

- **参照先テーブル**: `ROUTE_MAP|<map_name>|<seq_no>` の `route_operation` フィールド
- **参照方向**: 内部キャッシュ参照（`self.route_map` dict）
- **条件**: `BGP_PEER_GROUP_AF` に `route_map_in` / `route_map_out` フィールドが設定されたとき（`BGP_PEER_GROUP_AF` の `bgp_table_handler_common` 経由）
- **参照元**:
  - `frrcfgd.py` L2206（`rtmap_table = self.config_db.get_table('ROUTE_MAP')` startup キャッシュ）
  - `frrcfgd.py` L2669–2678（`elif table == 'ROUTE_MAP':` の prefix-set 解決ロジック）
  - `frrcfgd.py` L86（`'ROUTE_MAP': ['zebra', 'bgpd', 'ospfd']` — frrcfgd が直接購読するテーブルリスト）
- **意味**: peer-group に適用する route-map 名は文字列として `BGP_PEER_GROUP_AF` フィールドに格納され、
  frrcfgd が FRR に `neighbor <pg> route-map <name> in/out` として投入する。
  参照先の `ROUTE_MAP` エントリが FRR に未投入でも frrcfgd はエラーを返さないが、
  FRR 側で no-op（指定名の route-map が存在しない場合は BGP ポリシーが適用されない）。
  `ROUTE_MAP` 自体も frrcfgd が購読しており（L86）、`ROUTE_MAP` 変更時は prefix-set AF 解決を再実行。

---

## 参照グラフ要約

```
BGP_GLOBALS.local_asn  ──[必須/ブロッキング]──→ BGP_PEER_GROUP 処理
BGP_PEER_GROUP          ──[asn 変更時 cascade]──→ BGP_PEER_GROUP_AF 再適用
BGP_PEER_GROUP_AF       ──[route_map フィールド]──→ ROUTE_MAP (FRR に投入)
```

---

## grep カバレッジ

| キーワード | ファイル | 行 | 内容 |
|-----------|---------|-----|------|
| `BGP_GLOBALS` (startup) | `frrcfgd.py` | L2175 | `get_table('BGP_GLOBALS')` でキャッシュ構築 |
| `local_asn` (skip 判定) | `frrcfgd.py` | L2659 | `table != 'BGP_GLOBALS' or 'local_asn' not in data` でスキップ |
| `BGP_PEER_GROUP_AF` (購読) | `frrcfgd.py` | L2305 | `('BGP_PEER_GROUP_AF', self.bgp_table_handler_common)` |
| `BGP_PEER_GROUP_AF` (分岐) | `frrcfgd.py` | L2865 | `elif table == 'BGP_NEIGHBOR_AF' or table == 'BGP_PEER_GROUP_AF'` |
| `ROUTE_MAP` (startup) | `frrcfgd.py` | L2206 | `get_table('ROUTE_MAP')` でキャッシュ |
| `ROUTE_MAP` (購読リスト) | `frrcfgd.py` | L86 | `'ROUTE_MAP': ['zebra', 'bgpd', 'ospfd']` |
| `__nbr_impl_action` (cascade) | `frrcfgd.py` | L2551 | `is_pg=True` 時 `chk_attrs=['asn']` |
| `__apply_dep_vrf_table` | `frrcfgd.py` | L2847 | `BGP_GLOBALS_LISTEN_PREFIX` cascade |
