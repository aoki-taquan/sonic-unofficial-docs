---
title: BGP_PEER_RANGE テーブル
description: "BGP_PEER_RANGE テーブル — BGP_PEER_RANGE テーブルは BGP の dynamic neighbor 用 listen-range / peer-range を CONFIG_DB に定義する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-peerrange.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BGP_PEER_RANGE
    - BGP_GLOBALS
    - VRF
    - VNET
  cli:
    - config bgp
  yang:
    - sonic-bgp-peerrange
hard: 0
---

# BGP_PEER_RANGE テーブル

## 概要

`BGP_PEER_RANGE` テーブルは [BGP](../../reference/glossary.md#term-bgp) の dynamic neighbor 用 listen-range / peer-range を [CONFIG_DB](../../reference/glossary.md#term-config_db) に定義する[^1]。`bgpcfgd` テンプレが `bgpd` の `bgp listen range <prefix> peer-group <name>` 相当を生成するための入力。

定義は 2 list:

- `BGP_PEER_RANGE_LIST` (vrf_name, peer_range_name): [VRF](../../reference/glossary.md#term-vrf) または [VNET](../../reference/glossary.md#term-vnet) 別の peer range
- `BGP_PEER_RANGE_TEMPLATE_LIST` (peer_range_name): テンプレベース

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>BGP_PEER_RANGE")]
  DM["bgpcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
BGP_PEER_RANGE|<vrf_name>|<peer_range_name>      # generic
BGP_PEER_RANGE_TEMPLATE|<peer_range_name>        # template
```

| キー | 型 | 説明 |
|------|----|------|
| `vrf_name` | union (leafref to `VRF.name` または `VNET.name`) | 所属 [VRF](../../reference/glossary.md#term-vrf) または [VNET](../../reference/glossary.md#term-vnet) |
| `peer_range_name` | string | peer range の一意名 |

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `name` | string | 表示名。`must` で `peer_range_name` と一致を強制 |
| `src_address` | inet:ip-address | コネクションのソース IP |
| `peer_asn` | uint32 (1..4294967295) | 隣接 AS 番号 |
| `ip_range` | leaf-list `sonic-ip-prefix` (`ordered-by user`) | listen-range のプレフィックス集合 |

## 制約

- `vrf_name` は `VRF` か `VNET` のいずれかへの leafref（union）
- `name` は `peer_range_name` と完全一致必須
- `peer_asn` は AS4 範囲

## 購読者

- `bgpcfgd` (`docker-fpm-frr`)

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_GLOBALS`、`VRF`、`VNET`、`BGP_PEER_GROUP`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-bgp-peerrange`、`sonic-vrf`、`sonic-vnet`
- 関連 CLI: `config bgp`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-bgp-peerrange`](../yang/sonic-bgp-peerrange.md)
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-bgp-peerrange.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-peerrange.yang>

## 関連ページ
- [CONFIG_DB: BGP_NEIGHBOR](bgp-neighbor.md)
- [CONFIG_DB: BGP_PEER_GROUP](bgp-peer-group.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BGP_PEER_RANGE|<vrf>|<range-name>`。
- `ip_range`: CIDR、`peer_asn`: 対向 AS、`name`: 識別子。dynamic neighbor 用途。

### よくある誤設定

- `listen limit` を超えると新規 dynamic neighbor が拒否される。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BGP_PEER_RANGE|*'
vtysh -c 'show bgp listen range'
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

このテーブルには enum フィールドはない。

### `vrf_name` (key、VRF/VNET 分岐)

| 型 | 動作 |
|----|------|
| `VRF.name` への leafref | VRF コンテキストで `bgp listen range <prefix> peer-group <name>` を生成 |
| `VNET.name` への leafref | VNET 対応 VRF で同様のコマンドを生成 |

### `ip_range` (leaf-list)

- 複数プレフィックスを user-ordered で指定可能
- `dynamic/update.conf.j2` が各プレフィックスに対して `bgp listen range <prefix> peer-group <name>` を展開
- 削除時は既存 range との差分を計算して `no bgp listen range` を発行

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 | ソース |
|------|------|--------|
| `deployment_id` が DEVICE_METADATA に未設定で `peer_asn` も未設定 | Jinja2 で `UndefinedError` / `KeyError` → `log_err` + `return True` (drop) | `dynamic/instance.conf.j2`, `managers_bgp.py` |
| `ip_range` が空または未設定 | `bgp listen range <empty>` が vtysh に送られ FRR エラー | `dynamic/instance.conf.j2` |
| `ip_range` 更新時の既存 range 取得失敗 | `LOG_ERR` して空リスト返却 → 全 range を新規追加として処理 | `managers_bgp.py` `get_existing_ip_ranges()` |
| `src_address` 未設定 | Loopback1 の IPv4 アドレスで補完。Loopback1 が未設定の場合 Jinja2 エラー → drop | `dynamic/instance.conf.j2` |
| FRR 10.1 以降: listen range 削除失敗後も peer-group 削除を続行 | range 削除の `log_err` 後、peer-group 削除を試みる → FRR 側エラーの可能性 | `managers_bgp.py` `del_handler()` |
<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_PEER_RANGE` テーブルを購読する。

`BGP_PEER_RANGE` は `<vrf>|<prefix>` の key 構造。dynamic neighbor 機能。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR BGP dynamic peer 設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR に `bgp listen range <prefix> peer-group <pg>` を発行。指定プレフィクスからの接続を dynamic に受け入れ開始。

**副作用**: 指定プレフィクス内からの BGP 接続が自動的に対象 peer-group として処理される。既存の static ネイバーとは独立。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `BGP_PEER_RANGE`

### CLI
- `config bgp peer-range add/del <prefix>`
  - ソース: `sonic-utilities/config/main.py (bgp グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
<!-- /entry-points -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 値による他フィールド自動派生

| 条件 | 派生先 | evidence |
|---|---|---|
| minigraph XML に `<BGPPeerRange>` エントリが存在する | `BGP_PEER_RANGE` テーブルに `ip_range` エントリを生成 | `sonic-buildimage/src/sonic-config-engine/minigraph.py:1401-1408,2275` |
| `PeerRange.Address` が IPv4/IPv6 のどちらか | `ip_range` の CIDR 文字列として格納 | `sonic-buildimage/src/sonic-config-engine/minigraph.py:1401` |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `BGPPeerMgrBase(peer_type="dynamic")` が `BGP_PEER_RANGE` を購読 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:90` |

### grep カバレッジ

- minigraph.py L2275: BGP_PEER_RANGE 代入
- bgpcfgd/main.py L90: 条件なし登録
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `BGPPeerMgrBase` | `set_handler()` | `peer_key NOT IN self.peers` | `add_peer()` 新規追加 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:167` |
| `BGPPeerMgrBase` | `update_peer()` | `"ip_range" in data AND peer_type == "dynamic"` | `change_ip_range()` を呼び出し（動的 BGP range 更新） | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:317` |
| `BGPPeerMgrBase` | `del_handler()` | `peer_type == "dynamic" OR peer_type == "sentinels"` | `no bgp listen range` コマンドを送出 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:461` |

> **スキャン証跡**: peer_type="dynamic" 固有の ip_range 更新分岐と del_handler の `no listen range` テンプレート使用を確認。3 件分岐抽出。
<!-- /handler-branching -->

<!-- platform -->
## プラットフォーム差分 (Phase H)

> **調査根拠**: `bgpcfgd/managers_bgp.py` および `dynamic/policies.conf.j2`、`dynamic/instance.conf.j2` を精読 (2026-05-16)。詳細証跡: `meta/_intermediate/cdb-flow/bgp-peer-range-platform.md`

`BGP_PEER_RANGE` の処理経路（`BGPPeerMgrBase` / dynamic テンプレート群）には `switch_type`、`sub_role`、`DEVICE_METADATA.localhost.type` を**条件分岐として使用する箇所は存在しない**。

### 根拠

| 検索対象 | 結果 |
|---------|------|
| `switch_type` in `managers_bgp.py` | ヒットなし |
| `sub_role` in `managers_bgp.py` | ヒットなし |
| `localhost/type` の分岐利用 | deps 登録のみ（存在チェック）、値による動作切り替えなし |
| `dynamic/policies.conf.j2` の platform 分岐 | なし（`FROM_BGP_SPEAKER` / `TO_BGP_SPEAKER` route-map のみ） |
| `dynamic/instance.conf.j2` の platform 分岐 | なし（`peer_asn` / `src_address` の有無分岐のみ） |

`localhost/type` は swsscommon deps ガードの「キー存在チェック」として登録されているが、値を読んで動作を切り替えるコードは存在しない。`dynamic/instance.conf.j2` の分岐は CONFIG_DB フィールド（`peer_asn`、`src_address`）の有無であり、プラットフォーム種別とは無関係。

### 結論

`BGP_PEER_RANGE` は peer_type="dynamic" の固定ロールであり、FRR 経路（bgpcfgd + dynamic テンプレート）は全 SONiC プラットフォームで同一動作をする。switch_type / sub_role による挙動変化はない。
<!-- /platform -->

<!-- ordering -->
## 書込み順序依存 (Phase B)

### 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `BGP_GLOBALS.<vrf>.local_asn` → `BGP_PEER_RANGE` | 先行必須（欠如時 silent drop） | bgpcfgd は deps ガードで再試行待ち、frrcfgd は `continue` でスキップ（リトライなし） |
| 2 | `BGP_PEER_GROUP` → listen range 設定（frrcfgd 経路） | 自動 defer（逆順は後付け再適用） | `__apply_dep_vrf_table` で peer-group 作成後に自動再適用 |
| 3 | `no bgp listen range` → peer-group 削除（FRR 10.1+） | 強制順序（bgpcfgd が自動処理） | 外部直接操作時は `no bgp listen range` を先に発行すること |
| 4 | `DEVICE_METADATA.localhost.bgp_asn` → `BGP_PEER_RANGE` | 先行必須（deps guard） | 起動時は DEVICE_METADATA が先に読み込まれる前提 |
| 5 | `ip_range` 差分計算の逐次性 | 推奨（並行変更は重複リスク） | SET を逐次発行し vtysh 反映を確認してから次変更を送ること |

### 詳細

#### BGP_GLOBALS (local_asn) が先行必須

`frrcfgd` の `__update_bgp()` は VRF ベーステーブル処理前に `__get_vrf_asn(vrf)` を呼び出し、`local_asn` が未設定の場合は即座にスキップする（frrcfgd.py:2658–2662）。`BGP_GLOBALS_LISTEN_PREFIX` は `vrf_tables` に属するためこの guard が適用される。bgpcfgd も `bgp_asn`（`DEVICE_METADATA.localhost.bgp_asn`）を deps に登録しており、未設定時は `add_peer()` が `False` を返しリトライ待ちとなる（managers_bgp.py:192）。

#### listen range 削除順序（FRR 10.1+）

FRR 10.1 以降は peer-group に listen range が紐付いている場合、peer-group を先に削除すると FRR がエラーを返す。`del_handler()` はこれに対応し `no bgp listen range <prefix> peer-group <name>` を先に発行してから peer-group 削除コマンドを送る（managers_bgp.py:456–472）。listen range 削除失敗時は `log_err` のみで処理を続行するため、FRR 側でエラーが残るリスクがある。

> **ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:119,192,456-472,2658-2662`、`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:2658-2662,2847`。詳細は `meta/_intermediate/cdb-flow/bgp-peer-range-ordering.md` を参照。
<!-- /ordering -->

<!-- defaults -->
## フィールド暗黙デフォルトと fallback

### `peer_asn` — `deployment_id_asn_map` fallback

`peer_asn` を省略すると `instance.conf.j2` が `constants.deployment_id_asn_map` を参照して自動的に AS 番号を決定する。

```
peer_asn 未設定
  → constants.yml deployment_id_asn_map[DEVICE_METADATA.localhost.deployment_id]
    "1" → 65432
    "2" → 65433
  → DEVICE_METADATA に deployment_id が未設定 → Jinja2 KeyError → log_err + drop
```

YANG は `peer_asn` を optional としているが、この fallback の存在は YANG に記載がない。

### `src_address` — Loopback1 ハードコード fallback

`src_address` を省略すると `instance.conf.j2` は `Loopback1` の IPv4 アドレスをハードコード参照する。`"Loopback1"` という名前は CONFIG_DB 経由で変更できない。Loopback1 が未設定の場合は Jinja2 エラーで drop される。

### ハードコード固定値（CONFIG_DB 非依存）

以下は全 `BGP_PEER_RANGE` エントリに無条件で適用されるハードコード設定。フィールドで制御する手段はない。

| FRR コマンド | 固定値 |
|------------|--------|
| `neighbor <name> passive` | 常時 passive |
| `neighbor <name> ebgp-multihop` | 255 固定 |
| `neighbor <name> soft-reconfiguration inbound` | 常時有効 |
| `neighbor <name> route-map FROM_BGP_SPEAKER in` | route-map 名固定 |
| `neighbor <name> route-map TO_BGP_SPEAKER out` | route-map 名固定 |
| `address-family ipv4/ipv6 activate` | 両 AF 常時有効 |

### `ip_range` — 空値の silent no-op

`ip_range` が空文字の場合 `change_ip_range()` の `if data['ip_range']:` ガードでスキップされ、FRR に `bgp listen range` コマンドが発行されない（エラーなし・silent）。YANG の leaf-list はゼロ要素を許容するが実質的に意味をなさない。

### 書き込み経路依存乖離（gNMI bypass）

`sonic-gnmi` の `bypass.go` で `BGP_PEER_RANGE` は `AllowedTables` に登録されており、gNMI Set 時に DBUS/GCU 検証をバイパスして CONFIG_DB 直接書き込みが可能。ただし Cisco-8102/8101/8223 HwSku のみに制限される。

> **ソース**: `dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/instance.conf.j2`, `bgpcfgd/managers_bgp.py` L358-386, `files/image_config/constants/constants.yml`, `sonic-gnmi/pkg/bypass/bypass.go` L29

<!-- /defaults -->
<!-- cross-refs -->
## 暗黙参照 — Phase C (cross-table refs)

> **調査根拠**: `bgpcfgd/managers_bgp.py`, `frrcfgd/frrcfgd.py`, `dynamic/policies.conf.j2` 精読 (2026-05-16)
> 詳細証跡: `meta/_intermediate/cdb-flow/bgp-peer-range-cross-refs.md`

`BGP_PEER_RANGE` テーブルは YANG leafref を最小限しか持たないが、実行時に以下のテーブルを暗黙参照する。

| 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `DEVICE_METADATA\|localhost` (`bgp_asn`) | CONFIG_DB | 読み取り | なし | 必須 | managers_bgp.py:119,192,501 |
| `DEVICE_METADATA\|localhost` (`deployment_id`) | CONFIG_DB | 読み取り | なし | 条件付き必須 | managers_bgp.py:135-143 |
| `BGP_PEER_GROUP\|<vrf>\|<name>` | CONFIG_DB | 事前定義前提 | なし | 実質必須 | managers_bgp.py:156,227 |
| `ROUTE_MAP` (FROM_BGP_SPEAKER / TO_BGP_SPEAKER) | — (FRR 内部) | ハードコード適用 | なし | 固定 | dynamic/policies.conf.j2:4,6 |
| `BGP_GLOBALS` | CONFIG_DB | router bgp 確立前提 | なし | 実質必須 | frrcfgd.py:81 |

### DEVICE_METADATA — bgp_asn・deployment_id の強制依存

`BGPPeerMgrBase` は初期化時に `DEVICE_METADATA|localhost/bgp_asn` と `localhost/type` を依存リストに登録する (managers_bgp.py:119-120)。`add_peer()` および `del_handler()` は `bgp_asn` を `router bgp <asn>` コマンド生成に使用する。`bgp_asn` 未設定の場合は `KeyError` → `log_err` + drop。`constants.bgp.use_deployment_id=true` の場合は `localhost/deployment_id` も依存に追加され、AS 番号の自動決定に使用される (managers_bgp.py:135-143)。

### BGP_PEER_GROUP — dynamic peer-group の事前定義依存

`BGPPeerGroupMgr.update_pg()` が peer-group を FRR に定義してから `bgp listen range <prefix> peer-group <name>` を発行する (managers_bgp.py:156,227)。FRR 上に peer-group が存在しない状態で listen range を設定しようとすると FRR がエラーを返す。CONFIG_DB 上の `BGP_PEER_GROUP` テーブルへの YANG leafref は存在しないが、実装上は peer-group 事前定義が必須の暗黙前提条件となる。

### ROUTE_MAP — FROM_BGP_SPEAKER / TO_BGP_SPEAKER ハードコード適用

`dynamic/policies.conf.j2` が bgpcfgd テンプレートエンジン起動時に FRR へ適用され、dynamic peer-group に `FROM_BGP_SPEAKER permit 10` (inbound) と `TO_BGP_SPEAKER deny 1` (outbound) の route-map をハードコードで設定する。CONFIG_DB の `ROUTE_MAP` テーブルへの依存はないが、これらの route-map 名は変更不可であり、動作を上書きする手段はない。

### BGP_GLOBALS — router bgp インスタンスの前提

`frrcfgd.py:81` が `BGP_GLOBALS` を bgpd 管理テーブルとして登録しており、`BGP_PEER_RANGE` が有効になる前提として `BGP_GLOBALS` で BGP router インスタンスが確立済みである必要がある。また `BGP_GLOBALS_LISTEN_PREFIX` テーブル (frrcfgd.py:92) が `bgp listen range` を frrcfgd 経由でも管理できる別パスを提供しており、bgpcfgd と二重管理の構造になっている。

<!-- /cross-refs -->
<!-- glossary-links-injected: 9543a3643673 -->
