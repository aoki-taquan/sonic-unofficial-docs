---
title: BGP_NEIGHBOR テーブル
description: "BGP_NEIGHBOR テーブル — BGP 隣接 (peer) を CONFIG_DB で定義するテーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-neighbor.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-common.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BGP_NEIGHBOR
    - BGP_GLOBALS
    - BGP_PEER_GROUP
  cli:
    - config bgp
  yang:
    - sonic-bgp-neighbor
    - sonic-bgp-common
hard: 0
---

# BGP_NEIGHBOR テーブル

## 概要

[BGP](../../reference/glossary.md#term-bgp) 隣接 (peer) を [CONFIG_DB](../../reference/glossary.md#term-config_db) で定義するテーブル。`bgpcfgd` (テンプレ展開) または `frr-mgmt-framework` (DEVICE_METADATA の `frr_mgmt_framework_config = true` のとき) が読み出し、[FRR](../../reference/glossary.md#term-frr) (`bgpd`) に反映する[^1]。テーブル定義は 2 形態に分かれる:

- `BGP_NEIGHBOR_TEMPLATE_LIST` (key: `neighbor`): [bgpcfgd](../../reference/glossary.md#term-bgpcfgd) テンプレ用の単純形式
- `BGP_NEIGHBOR_LIST` (key: `vrf_name`, `neighbor`): generic 形式。`frr_mgmt_framework_config = true` のときに使われる

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>BGP_NEIGHBOR")]
  DM["bgpcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
BGP_NEIGHBOR|<neighbor>                  # template 形式
BGP_NEIGHBOR|<vrf_name>|<neighbor>       # generic 形式
```

`<neighbor>` は IP アドレス、`PORT.name`、`PORTCHANNEL.name`、または `Vlan<id>` 文字列の union。`<vrf_name>` は `BGP_GLOBALS.vrf_name` への leafref。

## 主要フィールド (sonic-bgp-cmn より継承)

`sonic-bgp-common.yang` の `sonic-bgp-cmn` grouping を `uses` する。代表的フィールド:

| フィールド | 型 | 説明 |
|-----------|----|------|
| `local_asn` | as-number | local-as override |
| `asn` | as-number | 隣接 AS 番号 |
| `peer_type` | enum `internal`/`external` | iBGP / eBGP |
| `ebgp_multihop` | boolean | EBGP multihop |
| `ebgp_multihop_ttl` | uint8 | multihop TTL |
| `auth_password` | string | MD5 認証パスワード |
| `keepalive` | uint16 | keepalive interval [sec] |
| `holdtime` | uint16 | hold time [sec] |
| `conn_retry` | uint16 | 再試行間隔 |
| `min_adv_interval` | uint16 | minimum advertisement interval |
| `local_addr` | ip-address | source address (update-source) |
| `passive_mode` | boolean | passive listener |
| `capability_ext_nexthop` | boolean | RFC5549 ext-nexthop |
| `enforce_first_as` | boolean | first-AS enforce |
| `solo_peer` | boolean | solo peer |
| `ttl_security_hops` | uint8 | GTSM hops |
| `bfd` | boolean | [BFD](../../reference/glossary.md#term-bfd) multihop / [BFD](../../reference/glossary.md#term-bfd) enable |
| `peer_port` | uint16 | TCP port |
| `admin_status` | string `up`/`down` | セッション管理状態 |
| `local_as_no_prepend` / `local_as_replace_as` | boolean | local-as 動作 |
| `peer_group_name` (generic のみ) | leafref `BGP_PEER_GROUP.peer_group_name` | peer-group 参照 |

## 派生テーブル

- `BGP_NEIGHBOR_AF` ... 隣接 × afi_safi のアドレスファミリ別設定（route-map、prefix-list、send-community、weight 等）。grouping `sonic-bgp-cmn-af` を `uses`

## 制約

- `BGP_NEIGHBOR_TEMPLATE_LIST` の `asn` は 1 以上（[YANG](../../reference/glossary.md#term-yang) `must` で refine）
- 一部 leaf に `must` 経由のクロス参照（`BGP_GLOBALS.vrf_name`、`BGP_PEER_GROUP`）がある

## 購読者

- `bgpcfgd` (`docker-fpm-frr` 内): [CONFIG_DB](../../reference/glossary.md#term-config_db) → vtysh コマンド変換。テンプレベース
- `frr-mgmt-framework`: `DEVICE_METADATA.frr_mgmt_framework_config = true` のときに代替パスとして動作
- `bgpd` ([FRR](../../reference/glossary.md#term-frr)): vtysh / config 経由で間接反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_GLOBALS`、`BGP_PEER_GROUP`、`BGP_NEIGHBOR_AF`、`BGP_DEVICE_GLOBAL`
- 関連 CLI: [`config bgp`](../cli/config-bgp.md) (shutdown / startup / remove neighbor)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-bgp-neighbor`、`sonic-bgp-common`、`sonic-bgp-global`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-bgp-neighbor`](../yang/sonic-bgp-neighbor.md) / `sonic-bgp-common`
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-bgp-neighbor.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-neighbor.yang>; 共通 leaf 群は `sonic-bgp-common.yang` の `sonic-bgp-cmn` / `sonic-bgp-cmn-af` grouping

## 関連ページ
- [HLD: FRR-BGP Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md)
- [CLI: config bgp](../cli/config-bgp.md)
- [CLI: show bgp](../cli/show-bgp.md)
- [YANG: sonic-bgp-neighbor](../yang/sonic-bgp-neighbor.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BGP_NEIGHBOR|<neighbor-ip>` (frr 系) または `BGP_NEIGHBOR|<vrf>|<neighbor-ip>`。
- `asn`: 対向 AS 番号（4-byte ASN 可）。
- `local_addr`: 自身の IP。
- `admin_status`: `up`。
- `holdtime`: 180、`keepalive`: 60（標準）。
- `name`: 対向ホスト名（運用識別用）。

### よくある誤設定

- `local_addr` を未設定 or 誤ったインタフェース IP にすると update-source が解決できず neighbor 確立せず。
- `asn` を string で入れても通るが、4-byte ASN を `65000.1` 形式で書くと [bgpcfgd](../../reference/glossary.md#term-bgpcfgd) がパースに失敗する版がある。10 進で書く。
- iBGP で `local_addr` を物理 IF ではなく Loopback0 にしないと片側 down で [BGP](../../reference/glossary.md#term-bgp) が落ちる。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'BGP_NEIGHBOR|10.0.0.1'
show ip bgp summary
vtysh -c 'show bgp neighbor 10.0.0.1'
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `peer_type` (`bgp_peer_type`、最重要 enum)

| 値 | bgpcfgd テンプレディレクトリ | 主な差異 |
|----|----------------------------|---------|
| `internal` | `bgpd/templates/internal/` | timers 3/10、`send-community` 自動付与、BackEnd/chassis-packet で `next-hop-self force` |
| `external` / 未指定 (`general`) | `bgpd/templates/general/` | timers 60/180、ToRRouter で `allowas-in 1`、SpineRouter UpstreamLC で `table-map` |
| `dynamic` | `bgpd/templates/dynamic/` | `bgp listen range` 生成、`ip_range` フィールドを展開 |
| `monitors` | `bgpd/templates/monitors/` | BGP_MONITORS テーブル専用 |
| `voq_chassis` | `bgpd/templates/voq_chassis/` | VoQ chassis 間 iBGP |
| `sentinels` | `bgpd/templates/sentinels/` | sentinel ピア |

### `admin_status`

| 値 | bgpcfgd 動作 | FRR コマンド |
|----|-------------|-------------|
| `up` | `apply_admin_status("no shutdown")` | `no neighbor <addr> shutdown` |
| `down` | `apply_admin_status("shutdown")` | `neighbor <addr> shutdown` |

> **注意**: ライブ更新可能なのは `admin_status` のみ。他フィールドの変更は `managers_bgp.py:309` の制約でエラーログを出して drop。

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 | ソース |
|------|------|--------|
| Loopback0 IPv4 未設定 かつ `bgp_router_id` 未設定 | `log_warn` して `return False` (再試行待ち) | `managers_bgp.py` `add_peer()` |
| `local_addr` フィールドが欠如 | `Missing attribute 'local_addr'` を warn ログ、peer 追加は続行 | `managers_bgp.py` |
| `check_neig_meta=true` かつ `name` が DEVICE_NEIGHBOR_METADATA に未登録 | `DEVICE_NEIGHBOR_METADATA is not ready for neighbor` を log_info → return False (再試行) | `managers_bgp.py` `add_peer()` |
| `peer_group_name` に未存在 peer-group を参照 (frrcfgd) | `invalid peer-group %s was referenced` を LOG_ERR → continue | `frrcfgd.py` L2828 |
| interface 型 neighbor の作成失敗 | `failed to create neighbor of interface %s for VRF %s` を LOG_ERR → continue | `frrcfgd.py` L2810 |
| `admin_status` が `'up'`/`'down'` 以外 | `wrong attribute value` を LOG_ERR → drop | `managers_bgp.py` `change_admin_status()` |
| `local_asn` が未設定の VRF | frrcfgd が LOG_DEBUG して skip | `frrcfgd.py` L2660 |
| Jinja2 テンプレートレンダリング失敗 | `log_err` して `return True` (再試行なし) | `managers_bgp.py` `add_peer()` |
<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_NEIGHBOR` テーブルを購読する。

`BGP_NEIGHBOR` は `<vrf>|<neighbor>` の key 構造。peer-group を参照する場合がある。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR BGP ネイバー管理)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR にネイバー定義コマンドを発行。新規ネイバーは即座に接続試行を開始。削除は BGP session を即座に切断。

**副作用**: ネイバー削除は該当 BGP session の NOTIFICATION 送信と経路削除を引き起こす。パスワード変更は session リセットを引き起こす。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `BGP_NEIGHBOR`

### CLI
- `config bgp startup/shutdown all`
- `vtysh` 経由 neighbor コマンド群 (bgpcfgd が CONFIG_DB へ書き戻し)
  - ソース: `sonic-utilities/config/main.py, sonic-frr bgpcfgd`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- sonic-mgmt-common OpenConfig BGP neighbor 経由

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `bgpcfgd` が FRR running-config を CONFIG_DB と同期
<!-- /entry-points -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 値による他フィールド自動派生

| 条件 | 派生先 | evidence |
|---|---|---|
| minigraph XML の `<BGPSession>` エントリ（name != 'BGPMonitor'） | `BGP_NEIGHBOR` テーブルにエントリを生成 | `sonic-buildimage/src/sonic-config-engine/minigraph.py:1355,2273` |
| `type IN [MultiAsicInternalPeer]` | `internal_peers` に分類（loopback 参照） | `sonic-buildimage/src/sonic-config-engine/minigraph.py:1355-1360` |
| `admin_status` が VoQ chassis 構成時 | `enable_internal_bgp_session()` により `admin_status='up'` に強制設定 | `sonic-buildimage/src/sonic-config-engine/minigraph.py:1888-1901` |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `BGPPeerMgrBase(peer_type="general")` が `BGP_NEIGHBOR` を購読 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:87` |
| `check_neig_meta=True` のとき | `DEVICE_NEIGHBOR_METADATA` 依存関係を追加 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:137` |

### grep カバレッジ

- minigraph.py L2273: BGP_NEIGHBOR 代入
- bgpcfgd/main.py L87: 条件なし登録（check_neig_meta=True）
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `BGPPeerMgrBase` | `set_handler()` | `peer_key NOT IN self.peers` | `add_peer()` 新規追加 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:167` |
| `BGPPeerMgrBase` | `set_handler()` | `peer_key IN self.peers` | `update_peer()` 更新 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:169` |
| `BGPPeerMgrBase` | `add_peer()` | `lo_ipv4 is None AND bgp_router_id not configured` | 早期 `return False` | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:186-189` |
| `BGPPeerMgrBase` | `add_peer()` | `check_neig_meta AND data["name"] NOT IN neigmeta` | 早期 `return False`（DEVICE_NEIGHBOR_METADATA 未準備ガード） | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:221-223` |
| `BGPPeerMgrBase` | `update_peer()` | `"admin_status" in data` | `change_admin_status()` 委譲 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:314` |
| `BGPPeerMgrBase` | `change_admin_status()` | `admin_status == 'up'` | FRR に `no neighbor X shutdown` | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:333` |
| `BGPPeerMgrBase` | `change_admin_status()` | `admin_status == 'down'` | FRR に `neighbor X shutdown` | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:335` |
| `BGPPeerMgrBase` | `change_admin_status()` | `admin_status` が up/down 以外 | `log_err` のみ（処理継続） | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:337-339` |

> **スキャン証跡**: `BGPPeerMgrBase` 597 行全行読了。7 件分岐抽出。
<!-- /handler-branching -->
<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

YANG には `default` 文が一切ない。フィールドごとのランタイム実効値はテンプレートやコードで決まる。

### keepalive / holdtime

| 書き込み経路 | keepalive | holdtime | 根拠 |
|------------|-----------|----------|------|
| minigraph (XML `<HoldTime>` / `<KeepAliveTime>` 欠落時) | **60** | **180** | `minigraph.py:1316,1320` |
| bgpcfgd `general` テンプレート (CONFIG_DB 値が 60/180 のとき) | FRR デフォルトに委任 | FRR デフォルトに委任 | `general/instance.conf.j2:7-10` |
| bgpcfgd `internal` テンプレート | **3** (強制) | **10** (強制) | `internal/instance.conf.j2:6` |
| bgpcfgd `voq_chassis` テンプレート | **2** (強制) | **7** (強制) | `voq_chassis/instance.conf.j2:13` |
| frrcfgd 経路 (REST/gNMI) | CONFIG_DB 値をそのまま送出 | 同左 | `frrcfgd.py:1874` |

> **discrepancy**: `peer_type=internal` では CONFIG_DB の `keepalive`/`holdtime` 値は無視される。

### admin_status (フィールド未設定時)

bgpcfgd `general` テンプレート (`general/instance.conf.j2:13`):
- `admin_status` フィールドなし + `DEVICE_METADATA.localhost.default_bgp_status` が `'down'` → `neighbor X shutdown` を発行
- `admin_status` フィールドなし + `default_bgp_status` も未設定 → shutdown なし = **ピアは up**

minigraph 経路:
- external (general) ピア: `admin_status` フィールドを **書き込まない** (→ 上記フォールバックに委ねる)
- internal / VoQ chassis ピア: `admin_status = 'up'` を強制書き込み (`minigraph.py:1347-1353`)

### conn_retry (bgpcfgd 経路では無効)

bgpcfgd 全テンプレートで `neighbor X timers connect 10` をハードコード発行。CONFIG_DB の `conn_retry` 値は **bgpcfgd 経路では完全に無視される**。frrcfgd 経路では `frrcfgd.py:1875` で有効。

> **discrepancy**: YANG で `range "1..65535"` として定義されるが bgpcfgd パスでは機能しない。

### local_addr (未設定時)

`managers_bgp.py:194-202`: `local_addr` フィールドなし → `log_warn` のみ、peer 追加は続行 (FRR が送信元アドレスを自動選択)。`local_addr` ありでインタフェース未登録 → `return False` でリトライ待ち。

### name (実質必須)

YANG では optional leaf だが bgpcfgd `general`/`internal`/`voq_chassis` テンプレートが `bgp_session['name']` を直接参照する。未設定時は Jinja2 `UndefinedError` → テンプレートレンダリング失敗 → peer 追加不可。

### peer-group 自動付与 (bgpcfgd パスのみ)

| 設定 | general | internal |
|------|---------|---------|
| `soft-reconfiguration inbound` | 全 peer (常時) | 全 peer (常時) |
| `send-community` | なし | 全 peer (常時) |
| `allowas-in 1` | ToRRouter / LeafRouter+BBR enabled のみ | 全 peer (常時) |
| `next-hop-self force` | なし | `sub_role=BackEnd` または `switch_type=chassis-packet` |
| `update-source Loopback4096` | なし | `switch_type=chassis-packet` のみ |
| `ttl-security hops 1` | なし | `switch_type=chassis-packet` のみ |

### bgp suppress-fib-pending (暗黙副作用)

`managers_bgp.py:502-506`: neighbor の追加・変更のたびに `bgp suppress-fib-pending` を BGP インスタンス設定として注入。BGP_NEIGHBOR フィールドには現れない。

### peer_type と実テーブルのマッピング乖離

bgpcfgd は `constants.yml` の `peers.<type>.db_table` でテーブルを区別:
- `BGP_NEIGHBOR` → `general` (external) 専用
- `BGP_INTERNAL_NEIGHBOR` → `internal` 専用
- `BGP_VOQ_CHASSIS_NEIGHBOR` → `voq_chassis` 専用

YANG の `peer_type` フィールドは bgpcfgd 経路では **参照されない**。frrcfgd 経路でのみ有効。

> 中間調査詳細: `meta/_intermediate/cdb-flow/bgp-neighbor-defaults.md`
<!-- /defaults -->

<!-- side-effects -->
## SET/DEL の副次 DB 書込

### STATE_DB — `BGP_PEER_CONFIGURED_TABLE`

`bgpcfgd`（`BGPPeerMgrBase.update_state_db()`）が SET/DEL の都度 STATE_DB へ書き込む。

| 操作 | トリガー | key | 内容 |
|------|---------|-----|------|
| SET | `add_peer()` 成功後 | `<nbr>` (default VRF) / `<vrf>\|<nbr>` | CONFIG_DB の全フィールドを `sorted(data.items())` で格納 |
| SET | `apply_admin_status()` FRR 適用成功後 | 同上 | admin_status 変更後の data |
| SET | `change_ip_range()` 成功後（dynamic peer） | 同上 | ip_range 更新後の data |
| DEL | `del_handler()` FRR 削除成功後 | 同上 | エントリ削除 |

> **注意**: DEL 時に対象エントリが STATE_DB に存在しない場合は `log_warn` のみ（例外なし）。

key 構成: VRF が `"default"` なら `<nbr>` のみ、それ以外は `<vrf>|<nbr>`。

### APPL_DB — 書込なし

`bgpcfgd` / `frrcfgd` いずれも APPL_DB への直接書込は行わない。BGP neighbor の反映は FRR vtysh 経由で完結。

### FRR running-config への暗黙注入

`apply_op()` 呼び出しごとに `bgp suppress-fib-pending` が BGP インスタンス設定として自動プレフィックスされる（`managers_bgp.py:502-506`）。CONFIG_DB フィールドには現れない副次効果。

> **ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:271-300, 239, 353, 443, 487`; `sonic-swss-common/common/schema.h:511`
<!-- /side-effects -->
<!-- glossary-links-injected: 9133f44230c2 -->
