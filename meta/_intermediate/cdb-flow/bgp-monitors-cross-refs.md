# BGP_MONITORS — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/bgp-monitors.md` Phase C 追加分。
`BGP_MONITORS` の YANG (`sonic-bgp-monitor.yang`) には leafref が宣言されていないため、外部テーブルへの参照はすべて bgpcfgd 実装上の暗黙参照となる。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | `BGPPeerMgrBase` — `BGP_MONITORS` 購読 (peer_type="monitors")。`DEVICE_METADATA.localhost/bgp_asn` + `bgp_router_id` に依存 |
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | `ROUTE_MAP` および `BGP_GLOBALS` ハンドラを管理。bgpcfgd が生成する `FROM_BGPMON`/`TO_BGPMON` route-map とは別管理だが、ROUTE_MAP テーブルとの干渉関係が発生しうる |

## YANG leafref

`sonic-bgp-monitor.yang` には leafref 宣言なし。全フィールドは `sonic-bgp-cmn-neigh` grouping (string / uint32 / enumeration 型) で、外部テーブルへの形式的な参照は宣言されていない。

## 暗黙参照 (実装レベル)

### 1. DEVICE_METADATA|localhost.bgp_asn および bgp_router_id (必須)

- **参照先テーブル**: `DEVICE_METADATA|localhost` の `bgp_asn`・`bgp_router_id` フィールド
- **参照方向**: 読み取り（`BGPPeerMgrBase` コンストラクタで `subscribe` + `add_peer` 内で `directory.get_slot`）
- **条件**: 常時。`add_peer()` の先頭でゲートチェック実施
- **参照元**:
  - `managers_bgp.py` L119: `("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn")` を依存宣言
  - `managers_bgp.py` L186-192: `lo_ipv4 is None and "bgp_router_id" not in DEVICE_METADATA["localhost"]` → `return False`（ガード）
  - `managers_bgp.py` L192: `bgp_asn = directory.get_slot(DEVICE_METADATA)["localhost"]["bgp_asn"]`
  - `managers_bgp.py` L205, L251, L429, L475: テンプレートコンテキストに `CONFIG_DB__DEVICE_METADATA` を渡す
- **意味**:
  - `bgp_asn` は FRR の `remote-as <asn>` および `router bgp <asn>` に使用される。CONFIG_DB の `BGP_MONITORS|<addr>|asn` フィールドは **参照されない**（dead field）。
  - `bgp_router_id` は Loopback0 IPv4 が未設定の場合のフォールバック。どちらも未設定なら `add_peer()` は `return False` し再試行待ちとなる。
- **ブロッキング依存**: `subscribe` リストにより、`DEVICE_METADATA` 受信前は `BGP_MONITORS` の set_handler が実行されない。

### 2. BGP_GLOBALS (frrcfgd 経路のみ — 間接)

- **参照先テーブル**: `BGP_GLOBALS`（VRF と `local_asn` を管理）
- **参照方向**: `frrcfgd.py` が `BGP_GLOBALS` ハンドラを持ち、FRR の `router bgp <asn> [vrf <vrf>]` コンテキストを管理する
- **条件**: `frrcfgd` 経路のみ。`bgpcfgd` (`BGP_MONITORS` を直接購読する経路) は `BGP_GLOBALS` テーブルを直接購読しない
- **参照元**: `frrcfgd.py` L81 (`BGP_GLOBALS` → `bgpd` マッピング), L2106, L2175, L2685, L2771
- **意味**: bgpcfgd は `DEVICE_METADATA.bgp_asn` を使用して FRR BGP コンテキストに入るため、`BGP_GLOBALS` への直接依存はない。ただし同一 FRR デーモン内で `BGP_GLOBALS` ハンドラ (`frrcfgd`) と `BGP_MONITORS` ハンドラ (`bgpcfgd`) が共存するため、bgp_asn/local_asn が一致している必要がある（設定整合性要件）。

### 3. ROUTE_MAP — FROM_BGPMON / TO_BGPMON (テンプレートハードコード)

- **参照先テーブル**: `ROUTE_MAP`（FRR route-map 管理。`frrcfgd.py` が購読）
- **参照方向**: bgpcfgd が `policies.conf.j2` テンプレートを用いて FRR に直接注入する（CONFIG_DB `ROUTE_MAP` テーブルを経由しない）
- **条件**: `BGP_MONITORS` エントリ追加時に常時
- **参照元**:
  - `managers_bgp.py` L26: `self.policy_template = tf.from_file(base_template + "policies.conf.j2")`
  - テスト証跡: `tests/data/monitors/peer-group.conf/result_all.conf` — `neighbor BGPMON route-map FROM_BGPMON in` / `neighbor BGPMON route-map TO_BGPMON out`
- **意味**:
  - `FROM_BGPMON deny 10`: 全受信拒否（BGP モニター隣接は経路を受け取らない設計）
  - `TO_BGPMON permit 10`: 全送信許可（自分の RIB をモニターに公開）
  - これらの route-map は bgpcfgd が直接 FRR vtysh に投入するため、CONFIG_DB の `ROUTE_MAP` テーブルには存在しない。`frrcfgd` による ROUTE_MAP ハンドラとは独立した名前空間で動作する。
- **注意**: CONFIG_DB に `ROUTE_MAP|FROM_BGPMON` や `ROUTE_MAP|TO_BGPMON` を手動で追加しても、bgpcfgd が注入する route-map と重複・競合の恐れがある。

## 参照関係サマリ

```
BGP_MONITORS  (bgpcfgd 経路)
  ├─ [暗黙・必須] DEVICE_METADATA|localhost.bgp_asn     (FRR remote-as / router bgp <asn>)
  ├─ [暗黙・条件付き] DEVICE_METADATA|localhost.bgp_router_id  (Loopback0 未設定時フォールバック)
  ├─ [暗黙・間接] BGP_GLOBALS                            (frrcfgd 経路との bgp_asn 整合性要件)
  └─ [暗黙・出力] ROUTE_MAP 名前空間                      (FROM_BGPMON / TO_BGPMON を直接 FRR に注入)
```

## evidence

- `managers_bgp.py`: L119-120 (`DEVICE_METADATA` subscribe 宣言), L186-192 (`bgp_router_id` / `lo_ipv4` ガード), L192 (`bgp_asn` 取得), L205 / L251 / L429 / L475 (テンプレートへの `CONFIG_DB__DEVICE_METADATA` 渡し), L26 (`policies.conf.j2` ロード), L501 (`bgp_asn` 取得 + `bgp suppress-fib-pending` 注入)
- `frrcfgd.py`: L81 (`BGP_GLOBALS` → bgpd マッピング), L86 (`ROUTE_MAP` → bgpd マッピング), L2106 (`BGP_GLOBALS` key_map), L2175 (`glb_table = config_db.get_table('BGP_GLOBALS')`), L2206 (`rtmap_table = config_db.get_table('ROUTE_MAP')`), L2295-2302 (テーブルハンドラ登録)
- テスト証跡: `tests/data/monitors/peer-group.conf/result_all.conf` L8-9 (FROM_BGPMON / TO_BGPMON route-map 適用)
