---
title: BGP_MONITORS テーブル
description: "BGP_MONITORS テーブル — BGP_MONITORS テーブルは BGP Monitoring Protocol (BMP) ではなく、BGP モニター用の特殊隣接（route-monitor）を定義する。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-monitor.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-common.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BGP_MONITORS
    - BGP_NEIGHBOR
  cli:
    - config bgp
  yang:
    - sonic-bgp-monitor
    - sonic-bgp-common
hard: 0
---

# BGP_MONITORS テーブル

## 概要

`BGP_MONITORS` テーブルは [BGP](../../reference/glossary.md#term-bgp) Monitoring Protocol (BMP) ではなく、[BGP](../../reference/glossary.md#term-bgp) モニター用の特殊隣接（route-monitor）を定義する。`bgpcfgd` がテンプレ展開して `bgpd` の `neighbor` 設定を生成する[^1]。各エントリは [BGP](../../reference/glossary.md#term-bgp) 隣接共通プロパティ (`sonic-bgp-cmn-neigh` grouping) を流用する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>BGP_MONITORS")]
  DM["bgpcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
BGP_MONITORS|<addr>
```

| キー | 型 | 説明 |
|------|----|------|
| `addr` | inet:ip-address | モニター隣接の IP |

## フィールド

`sonic-bgp-common.yang` の `sonic-bgp-cmn-neigh` grouping を `uses` する。代表的 leaf:

| フィールド | 型 | 説明 |
|-----------|----|------|
| `name` | string | 隣接名。`must "current() = 'BGPMonitor'"` で `BGPMonitor` に固定 |
| `asn` | as-number | モニター AS |
| `local_addr` | ip-address | source address |
| `admin_status` | up/down | 管理状態 |
| 他 `sonic-bgp-cmn-neigh` 由来の leaf | — | keepalive/holdtime/peer_type/auth_password 等 |

## 制約

- `name` は `BGPMonitor` 固定（[YANG](../../reference/glossary.md#term-yang) `must` で強制）。複数モニターは `addr` で区別する

## 購読者

- `bgpcfgd` (`docker-fpm-frr`)
- 間接的に `bgpd` ([FRR](../../reference/glossary.md#term-frr))

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_NEIGHBOR`、`BGP_GLOBALS`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-bgp-monitor`、`sonic-bgp-common`
- 関連 CLI: `config bgp`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-bgp-monitor`](../yang/sonic-bgp-monitor.md) / `sonic-bgp-common`
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-bgp-monitor.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-monitor.yang>; 共通 leaf grouping は `sonic-bgp-common.yang` の `sonic-bgp-cmn-neigh`

## 関連ページ
- [CONFIG_DB: BGP_NEIGHBOR](bgp-neighbor.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BGP_MONITORS|<ip>`。
- `asn`: 監視先 AS。`admin_status`: `up`。`name`: 識別名。

### よくある誤設定

- BGP monitor を普通の neighbor と混同して route policy を当ててしまうと、本番経路に副作用が出る。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BGP_MONITORS|*'
vtysh -c 'show bgp summary'
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `admin_status` (sonic-bgp-cmn-neigh 由来)

| 値 | FRR コマンド | 備考 |
|----|-------------|------|
| `up` | `no neighbor <addr> shutdown` | `managers_bgp.py:334` |
| `down` | `neighbor <addr> shutdown` | `managers_bgp.py:336` |

### `name` (固定値制約)

| 値 | 動作 |
|----|------|
| `BGPMonitor` | YANG `must` 制約で強制。monitors テンプレ (`bgpd/templates/monitors/`) を使用 |
| それ以外 | YANG 検証段階で拒否 |

> **注意**: `admin_status` のみがライブ更新可能。他フィールドの変更は `bgpcfgd` に到達しても drop される (例外条件参照)。

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 | ソース |
|------|------|--------|
| Loopback0 IPv4 未設定 かつ `bgp_router_id` 未設定 | `log_warn` して `return False` (再試行待ち) | `managers_bgp.py` `add_peer()` |
| `local_addr` フィールドが欠如 | `Missing attribute 'local_addr'` を warn ログ、処理は続行 (interface 紐付けなし) | `managers_bgp.py` |
| local address に対応する interface が未登録 | `wait for the corresponding interface to be set` → return False (再試行) | `managers_bgp.py` `get_local_interface()` |
| 既存ピアへの `admin_status` 以外のフィールド更新 | `Can't update the peer. Only 'admin_status' attribute is supported` を LOG_ERR → drop | `managers_bgp.py` `update_peer()` |
| `admin_status` が `'up'`/`'down'` 以外 | `wrong attribute value` を LOG_ERR → drop | `managers_bgp.py` `change_admin_status()` |
| Jinja2 テンプレートレンダリング失敗 | `log_err` して `return True` (再試行なし、drop) | `managers_bgp.py` `add_peer()` |
| `check_neig_meta=False` | BGP_MONITORS は DEVICE_NEIGHBOR_METADATA への依存なし (monitors peer_type で固定) | `managers_bgp.py` `main.py` L89 |
<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_MONITORS` テーブルを購読する。

`BGP_MONITORS` は BMP target server を定義。`bmpcfgd` との連携もある。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (BMP / FRR モニタリング設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR に BGP モニタリング設定を注入。BMP セッションは設定適用後に確立を試みる。

**副作用**: BMP サーバへの接続が開始/停止される。既存 BGP セッションには影響なし。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `BGP_MONITORS`

### CLI
- `config bgp monitor add/del <address>`
  - ソース: `sonic-utilities/config/main.py (bgp グループ)`

### minigraph / sonic-cfggen
- なし

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
| minigraph XML に `<BGPPeer name="BGPMonitor">` エントリが存在する | `BGP_MONITORS` テーブルに peer エントリを生成 | `sonic-buildimage/src/sonic-config-engine/minigraph.py:1423,2274` |
| bgp_sessions の `name == 'BGPMonitor'` かつ `asn` が存在する | BGP_MONITORS へフィルタリング | `sonic-buildimage/src/sonic-config-engine/minigraph.py:1423` |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `BGPPeerMgrBase(peer_type="monitors")` が `BGP_MONITORS` を購読 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:89` |

### grep カバレッジ

- minigraph.py L1423: BGP_MONITORS 生成（filter by name=='BGPMonitor'）
- bgpcfgd/main.py L89: 条件なし登録
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `BGPPeerMgrBase` | `set_handler()` | `peer_key NOT IN self.peers` | `add_peer()` を呼び出し（新規追加） | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:167` |
| `BGPPeerMgrBase` | `set_handler()` | `peer_key IN self.peers` | `update_peer()` を呼び出し（更新） | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:169` |
| `BGPPeerMgrBase` | `add_peer()` | `lo_ipv4 is None AND bgp_router_id not in DEVICE_METADATA` | 早期 `return False`（loopback 未設定ガード） | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:186-189` |
| `BGPPeerMgrBase` | `add_peer()` | `"local_addr" not in data` | `log_warn` のみ（スキップしない） | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:194` |
| `BGPPeerMgrBase` | `add_peer()` | `interface = self.get_local_interface(data["local_addr"])` が None | 早期 `return False`（インターフェース未設定ガード） | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:199-202` |
| `BGPPeerMgrBase` | `update_peer()` | `"admin_status" in data` | `change_admin_status()` へ委譲 | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:314` |

> **スキャン証跡**: `BGPPeerMgrBase` 597 行・public メソッド set_handler/add_peer/update_peer/change_admin_status 読了。monitors は peer_type="monitors"（内部 BGP セッション向け）、loopback 依存ガードが核心分岐。
<!-- /handler-branching -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### 購読方式: `swsscommon.SubscriberStateTable` + `bgpcfgd Runner`

`BGP_MONITORS` は `bgpcfgd` の `Runner` クラスが `swsscommon.SubscriberStateTable` を直接生成して購読する。`ConfigDBConnector.subscribe()` ラッパは使用しない。

```python
# bgpcfgd/runner.py:49-52
subscriber = swsscommon.SubscriberStateTable(conn, "BGP_MONITORS")
self.selector.addSelectable(subscriber)
self.callbacks["CONFIG_DB"]["BGP_MONITORS"].append(manager.handler)
```

`Runner.run()` が `swsscommon.Select.select(timeout=1000ms)` でポーリングし、イベント到着時に `subscriber.pop()` で `(key, op, fvs)` を取り出してコールバックへ渡す。

### イベントディスパッチ

| CONFIG_DB 操作 | bgpcfgd 受信 | 処理メソッド |
|---------------|-------------|------------|
| `BGP_MONITORS\|<addr>` HSET | `handler("<addr>", "SET", {フィールド dict})` | `add_peer()` または `update_peer()` |
| `BGP_MONITORS\|<addr>` DEL  | `handler("<addr>", "DEL", {})` | `del_handler()` → `del_peer()` |

### 登録経路

`bgpcfgd/main.py:89` で `BGPPeerMgrBase(common_objs, "CONFIG_DB", "BGP_MONITORS", "monitors", False)` を生成。`runner.add_manager(mgr)` がデータベース名 `"CONFIG_DB"` とテーブル名 `"BGP_MONITORS"` を取得して `SubscriberStateTable` を作成する (`runner.py:38-52`)。

### frrcfgd との非重複

`frrcfgd`（`sonic-frr-mgmt-framework`）の購読テーブルリスト (`frrcfgd.py:2293-2338`) に `BGP_MONITORS` は含まれない。`frrcfgd` は BGP_NEIGHBOR / BGP_PEER_GROUP 等の sonic-mgmt-framework 経由テーブルを担当し、`BGP_MONITORS` は `bgpcfgd` 専用。二重購読は発生しない。

### 依存関係と再試行

`wait_for_all_deps=False` のため SET は即座に処理試行される。Loopback0 / bgp_router_id 依存が未解決なら `add_peer()` が `return False` し、`set_queue` に退避。依存が揃い次第 `on_deps_change()` が再処理する (`manager.py:55-63`)。

> 詳細解析: `meta/_intermediate/cdb-flow/bgp-monitors-pubsub.md`
<!-- /pubsub -->
<!-- glossary-links-injected: a1dd9e34d62e -->
