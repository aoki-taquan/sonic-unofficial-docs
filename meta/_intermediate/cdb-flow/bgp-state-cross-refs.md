# BGP_PEER_CONFIGURED_TABLE 暗黙参照スキャン (Phase C)

`docs/reference/config-db/bgp-state.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` および同 `bgpcfgd/main.py`。
`BGPPeerMgrBase` が `BGP_PEER_CONFIGURED_TABLE` を書き込む前後に暗黙的に読み出す CONFIG_DB テーブル群と、FRR bgpd の状態参照経路を列挙する。

## スキャン手順

```bash
# BGPPeerMgrBase の subscribe 元テーブルを確認
grep -n "BGPPeerMgrBase\|CFG_BGP" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py

# deps リストから読み込む CONFIG_DB テーブルを確認
grep -n "CONFIG_DB.*CFG_\|swsscommon\.CFG_" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py

# FRR (bgpd) 状態読み出しを確認
grep -n "vtysh\|run_command\|load_peers" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py
```

## 検出された暗黙参照

### 1. CONFIG_DB 購読テーブル (BGPPeerMgrBase インスタンスが監視)

`main.py` L87-91 で `BGPPeerMgrBase` は以下の CONFIG_DB テーブルを `table_name` 引数に受け取り、変更イベントを購読する。`set_handler` → `add_peer` / `update_peer` → `update_state_db` の経路でテーブル内容が `BGP_PEER_CONFIGURED_TABLE` へ転写される。

| CONFIG_DB テーブル | peer_type | evidence |
|---|---|---|
| `BGP_NEIGHBOR` (`CFG_BGP_NEIGHBOR_TABLE_NAME`) | `"general"` (外部 eBGP ピア) | main.py:87 |
| `BGP_INTERNAL_NEIGHBOR` (`CFG_BGP_INTERNAL_NEIGHBOR_TABLE_NAME`) | `"internal"` (iBGP ピア) | main.py:88 |
| `BGP_MONITORS` | `"monitors"` (BGP モニタ用ピア) | main.py:89 |
| `BGP_PEER_RANGE` | `"dynamic"` (listen range による動的ピア) | main.py:90 |
| `BGP_VOQ_CHASSIS_NEIGHBOR` | `"voq_chassis"` (VOQ シャーシ間 iBGP) | main.py:91 |
| `BGP_SENTINELS` | `"sentinels"` (sentinel ピア) | main.py:91 |

> これらすべてのテーブルへの SET / DEL イベントが `update_state_db()` (managers_bgp.py:271-304) を呼び出し、`BGP_PEER_CONFIGURED_TABLE` に反映される。テーブルごとに独立した `BGPPeerMgrBase` インスタンスが動くため、同一 `vrf|neighbor` キーが複数テーブルに存在すると **重複エントリ** が生じうる点に注意。

### 2. CONFIG_DB 依存テーブル (add_peer 実行に必要な前提テーブル)

`BGPPeerMgrBase.__init__` の `deps` リスト (managers_bgp.py:118-127) により、以下のテーブルが揃うまでピア追加処理がブロックされる (Manager 基底クラスの依存解決機能)。

| テーブル | キー / フィールド | 用途 | evidence |
|---|---|---|---|
| `DEVICE_METADATA` (`CFG_DEVICE_METADATA_TABLE_NAME`) | `localhost/bgp_asn` | `router bgp <ASN>` コマンド生成に使用 | managers_bgp.py:119,192,501 |
| `DEVICE_METADATA` | `localhost/type` | デバイスロール判定 (spine / leaf 等) | managers_bgp.py:120 |
| `LOOPBACK_INTERFACE` (`CFG_LOOPBACK_INTERFACE_TABLE_NAME`) | `Loopback0` | ルータ ID の IPv4 アドレスを取得 | managers_bgp.py:121,186,216 |
| `BGP_DEVICE_GLOBAL` (`CFG_BGP_DEVICE_GLOBAL_TABLE_NAME`) | `tsa_enabled` | TSA (Traffic Shift Away) ルートマップ適用判定 | managers_bgp.py:122 |
| `BGP_DEVICE_GLOBAL` | `idf_isolation_state` | IDF isolation ルートマップ適用判定 | managers_bgp.py:123 |
| `LOCAL` `local_addresses` | — | ピアの `local_addr` がインタフェースに存在するか検証 | managers_bgp.py:124,197-202 |
| `LOCAL` `interfaces` | — | `local_addr` に対応するインタフェースのメタデータ | managers_bgp.py:125,534-543 |

条件付き追加依存:

| 条件 | テーブル | evidence |
|---|---|---|
| `use_neighbors_meta = true` のとき | `DEVICE_NEIGHBOR_METADATA` (`CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME`) | managers_bgp.py:140,220-224 |
| `use_deployment_id = true` のとき | `DEVICE_METADATA.localhost/deployment_id` | managers_bgp.py:143 |
| `peer_type == "internal"` のとき | `LOOPBACK_INTERFACE.Loopback4096` | managers_bgp.py:146 |

### 3. FRR bgpd 状態の暗黙読み出し

`BGPPeerMgrBase` は `update_state_db()` を呼び出す前に、FRR bgpd の動作状態を **`vtysh` 経由で暗黙読み出し** する。

| 参照先 | 呼び出し箇所 | 用途 |
|---|---|---|
| `vtysh -c 'show bgp vrfs json'` | `load_peers()` — managers_bgp.py:577 | 起動時に FRR に登録済みのピアセットを取得し `self.peers` を初期化 |
| `vtysh -c 'show bgp vrf <vrf> neighbors json'` | `load_peers()` — managers_bgp.py:587 | VRF ごとのネイバー一覧を取得 |
| `vtysh -c 'show bgp peer-group <name> json'` | `get_existing_ip_ranges()` — managers_bgp.py:398-400 | `BGP_PEER_RANGE` の動的ピアで ip_range 更新時に既存 range を取得 |
| `cfg_mgr.push(cmd)` (FRR への設定書き込み) | `apply_op()` — managers_bgp.py:507 | `update_state_db()` の直前に FRR に `neighbor` コマンドを投入。FRR 設定投入 **後** に STATE_DB を更新する (managers_bgp.py:239,353,444) |

> `BGP_PEER_CONFIGURED_TABLE` への書き込みは FRR への `vtysh` 設定投入が成功した場合のみ実行される (add_peer L239, apply_admin_status L353, apply_range_changes L443)。FRR bgpd が応答不能の場合、STATE_DB への反映も遅延・欠落する。

### 4. frrcfgd (bgpd) との非同期協調

`bgpcfgd` の `cfg_mgr.push()` は `FRR.write()` (frr.py:write) 経由で `vtysh -f <tmpfile>` を発行する。この投入が FRR 内部で処理される前後に BGP セッション状態が変化し、`bgpmon` が `NEIGH_STATE_TABLE` を更新するため、`NEIGH_STATE_TABLE` と `BGP_PEER_CONFIGURED_TABLE` の整合性は **非同期** となる。

| タイミング | 状態 |
|---|---|
| CONFIG_DB SET イベント受信直後 | FRR 未設定、STATE_DB 未更新 |
| `cfg_mgr.push()` 呼び出し後 (FRR キュー投入) | FRR 設定中、STATE_DB 未更新 |
| `update_state_db("SET")` 呼び出し後 | `BGP_PEER_CONFIGURED_TABLE` に記録済み、FRR bgpd はセッション確立を試行中 |
| bgpmon 次回ポーリング (最大 15 秒後) | `NEIGH_STATE_TABLE` に `Established` 等の状態が反映 |

### 範囲外 (誤解されやすい隣接テーブル)

- **ASIC_DB BGP セッション state**: bgpcfgd / bgpmon はいずれも ASIC_DB を参照しない。ASIC_DB への BGP 関連書き込みは SWSS の `routeorch` が担当し、`BGP_PEER_CONFIGURED_TABLE` の経路とは独立している。
- **`BGP_PEER_GROUP`**: CONFIG_DB テーブルとしては存在せず、FRR の peer-group 設定は Jinja2 テンプレート (`peer-group.conf.j2`) によって `BGP_NEIGHBOR` 等の内容から生成される。CONFIG_DB に独立テーブルはない。

## まとめ — `bgp-state.md` Phase C 記載対象

| カテゴリ | テーブル / コンポーネント |
|---|---|
| CONFIG_DB 購読テーブル (転写元) | `BGP_NEIGHBOR` / `BGP_INTERNAL_NEIGHBOR` / `BGP_MONITORS` / `BGP_PEER_RANGE` / `BGP_VOQ_CHASSIS_NEIGHBOR` / `BGP_SENTINELS` |
| CONFIG_DB 前提依存テーブル | `DEVICE_METADATA` / `LOOPBACK_INTERFACE` / `BGP_DEVICE_GLOBAL` |
| CONFIG_DB 条件付き依存 | `DEVICE_NEIGHBOR_METADATA` |
| FRR bgpd 状態読み出し | `vtysh show bgp vrfs/neighbors json` (起動時), `show bgp peer-group json` (ip_range 更新時) |
| 非同期協調 | `bgpmon` → `NEIGH_STATE_TABLE` (最大 15 秒遅延) |

## 検証コマンド

```bash
# BGPPeerMgrBase の登録テーブル一覧
grep -n "BGPPeerMgrBase" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py

# 依存テーブルの deps リスト
grep -n "deps\|CONFIG_DB.*CFG_\|swsscommon\.CFG_" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py | head -40

# FRR 状態読み出し
grep -n "vtysh\|run_command" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py
```

このスキャン結果から派生して `docs/reference/config-db/bgp-state.md` の `<!-- cross-refs -->` ブロックを生成する。
