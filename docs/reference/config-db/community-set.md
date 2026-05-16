---
title: COMMUNITY_SET テーブル
description: "COMMUNITY_SET テーブル — BGP コミュニティ集合を CONFIG_DB に登録するテーブル。sonic-routing-policy-sets.yang の COMMUNITY_SET コンテナで定義され、ROUTE_MAP の match community 等から参照される。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - COMMUNITY_SET
    - EXTENDED_COMMUNITY_SET
    - ROUTE_MAP
  cli: []
  yang:
    - sonic-routing-policy-sets
hard: 0
---

# COMMUNITY_SET テーブル

## 概要

[BGP](../../reference/glossary.md#term-bgp) コミュニティ集合を [CONFIG_DB](../../reference/glossary.md#term-config_db) に登録するテーブル[^1]。`sonic-routing-policy-sets.yang` の `COMMUNITY_SET` コンテナで定義され、`ROUTE_MAP` の `match community` 等から参照される。`EXTENDED_COMMUNITY_SET` も同モジュール内で並行定義される（同フィールド構成）。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>COMMUNITY_SET")]
  DM["bgpcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
COMMUNITY_SET|<name>
EXTENDED_COMMUNITY_SET|<name>
```

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `name` | string | コミュニティ名（key） |
| `set_type` | enum `STANDARD` / `EXPANDED` | コミュニティタイプ |
| `match_action` | enum `ANY` / `ALL` | マッチ判定（任意一致/全一致） |
| `action` | enum `permit` / `deny` | コミュニティリストの action |
| `community_member` | leaf-list string (ordered-by user) | コミュニティ値の列。順序維持 |

`EXTENDED_COMMUNITY_SET_LIST` は同フィールド構成の Extended Community 用テーブル。

## 制約

- `community_member` は `ordered-by user`。ユーザ指定順をそのまま [FRR](../../reference/glossary.md#term-frr) の community-list に展開する前提
- `set_type` の選択により [FRR](../../reference/glossary.md#term-frr) 側で正規表現マッチ (`EXPANDED`) か数値マッチ (`STANDARD`) かが切り替わる

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **必須フィールド欠如 → FRR 設定なし (暗黙スキップ)**: `set_type` / `match_action` / `community_member` のいずれかが欠如している場合、Jinja2 テンプレートがそのエントリを無視し FRR コマンドを生成しない。エラーログは出力されない。<!-- evidence: bgpd.conf.db.comm_list.j2 L9 -->
- **match_action が `all` / `any` 以外 → FRR 設定なし**: `match_action` が想定外の値の場合、テンプレートはどちらの分岐にも入らず bgp community-list が生成されない。<!-- evidence: bgpd.conf.db.comm_list.j2 L11, L16 -->
- **vtysh 実行失敗 → syslog LOG_ERR のみ (再試行なし)**: FRR bgpd への vtysh コマンド投入が失敗した場合、`frrcfgd` は syslog に LOG_ERR を出力するが再試行は行わない。FRR 側との設定乖離が生じる可能性がある。<!-- evidence: frrcfgd.py L47-60 g_run_command -->
- **汎用例外 → catch + LOG_ERR + drop**: ハンドラ内で `Exception` が発生した場合 `LOG_ERR` を出力して次のエントリへ進む。当該更新はドロップされる。<!-- evidence: frrcfgd.py L1533-1534 -->

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `set_type` | `STANDARD` | FRR へ `bgp community-list standard <name> permit <value>` を生成。数値 community（`AS:value` 形式）および well-known community に対して完全一致でマッチ。 |
| `set_type` | `EXPANDED` | FRR へ `bgp community-list expanded <name> permit <pattern>` を生成。正規表現マッチが可能（例: `.*:100`）。`STANDARD` と誤って指定した場合、正規表現が数値として解釈されすべてのルートが reject される。 |
| `match_action` | `ANY` | community_member のいずれか 1 つにマッチするルートを対象（OR 条件）。 |
| `match_action` | `ALL` | community_member すべてを同時に保持するルートのみを対象（AND 条件）。 |
| `match_action` | その他の値 | Jinja2 テンプレートがどちらの分岐にも入らず FRR コマンドが生成されない（サイレント失敗）。 |
| `action` | `permit` | マッチしたルートを許可。 |
| `action` | `deny` | マッチしたルートを拒否。 |
<!-- /value-behavior -->

## 購読者

- `frr-mgmt-framework`: [BGP](../../reference/glossary.md#term-bgp) コミュニティ・リストとして [FRR](../../reference/glossary.md#term-frr) (`bgpd`) に反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `EXTENDED_COMMUNITY_SET`、[`AS_PATH_SET`](./as-path-set.md)、[`PREFIX_SET`](./prefix-set.md)、`ROUTE_MAP`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-routing-policy-sets`
- 関連 CLI: なし（`config_db.json` 投入）

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): `sonic-routing-policy-sets`

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-routing-policy-sets.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `COMMUNITY_SET|<name>`。
- `set_type`: `standard` / `expanded`。`match_action`: `any` / `all`。`community_member`: CSV。

### よくある誤設定

- `expanded` で正規表現を書いたのに `standard` 指定のままで全件 reject される。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'COMMUNITY_SET|*'
vtysh -c 'show bgp community-list'
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `COMMUNITY_SET` テーブルを購読する。

`COMMUNITY_SET` は SONiC の route policy 管理用 (OpenConfig 準拠)。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由で community-list を設定)

### 段階 3 — APPL→SAI

なし (FRR BGP policy のみ)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR に `ip community-list` コマンドを発行。次回 BGP route-map 評価から適用。

**副作用**: community-list 変更は route-map を通じて BGP 経路のフィルタリング/属性に影響。soft-clear により即時反映が可能。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `COMMUNITY_SET`

### CLI
- `config route-map community-set add <name> <match-action> <community-list>`
- `config route-map community-set delete <name>`
  - ソース: `sonic-utilities/config/main.py (route-map グループ)`

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- sonic-mgmt-common OpenConfig routing policy 経由

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
| 派生なし（COMMUNITY_SET は CLI または gNMI/OpenConfig 経由でのみ書き込まれる） | — | frrcfgd は読み取り専用消費 |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `frrcfgd.BGPConfigDaemon` が `COMMUNITY_SET` を購読（`comm_set_handler`） | `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:2300` |

### grep カバレッジ

- frrcfgd.py L2300: COMMUNITY_SET 購読（条件なし）
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `BGPConfigDaemon` | `hdl_com_set()` | `len(args) < 2` または必須フィールド欠如 | `return None`（コマンド生成スキップ） | `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:982` |
| `BGPConfigDaemon` | `hdl_com_set()` | `op == CachedDataWithOp.OP_DELETE` | FRR `no bgp community-list` のみ発行（member 追加なし） | `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:991` |
| `BGPConfigDaemon` | `hdl_com_set()` | `match_action == 'all'` | `permit <all members>` を 1 行コマンドで生成 | `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:993-999` |
| `BGPConfigDaemon` | `hdl_com_set()` | `match_action == 'any'` | member ごとに `permit <member>` を個別コマンドで生成 | `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:1000-1006` |

> **スキャン証跡**: `hdl_com_set` L981-1006 全行読了。match_action ('all' vs 'any') による分岐が核心。4 件抽出。
<!-- /handler-branching -->
<!-- cross-refs -->
## 暗黙参照 — `BGPConfigDaemon` が参照する関連 CONFIG_DB テーブル (Phase C / EXTENDED_COMMUNITY_SET)

`frrcfgd` の `BGPConfigDaemon` は起動時に `get_table('EXTENDED_COMMUNITY_SET')` で全エントリを `self.extcomm_set_list` キャッシュに一括ロードする (frrcfgd.py:2221-2226)。以下は `frrcfgd.py` のスキャンで検出した暗黙参照テーブル。

### ROUTE_MAP からの被参照 (name leafref)

`ROUTE_MAP` テーブルは `EXTENDED_COMMUNITY_SET` を 2 つのフィールド経由で参照する。

| 参照フィールド | FRR コマンド | 依存タイミング | evidence |
|---|---|---|---|
| `ROUTE_MAP.match_ext_community` | `match extcommunity <name>` | ランタイム: FRR に名前文字列をそのまま渡す。YANG leafref により DB 整合は保証されるが FRR 側での名前解決は自前 | frrcfgd.py:1939; sonic-route-map.yang:L256-260 |
| `ROUTE_MAP.set_ext_community_ref` | `set extcommunity rt/soo <members>` | ランタイム: `hdl_set_extcomm()` が `daemon.extcomm_set_list.get(name)` でキャッシュを参照し、未設定または `is_configurable()` が False の場合 `LOG_ERR` を出力して FRR コマンド生成をスキップする | frrcfgd.py:423-427; sonic-route-map.yang:L355-358 |

> `set_ext_community_ref` は `EXTENDED_COMMUNITY_SET` エントリが先にキャッシュされていないと FRR への `set extcommunity` が生成されない。`EXTENDED_COMMUNITY_SET` → `ROUTE_MAP` の設定順序が重要。

### BGP_NEIGHBOR_AF — 間接参照 (ランタイムキャッシュ経由)

`BGP_NEIGHBOR_AF` が直接 `EXTENDED_COMMUNITY_SET` を参照するフィールドはないが、`ROUTE_MAP` 経由で `set_ext_community_ref` を利用する場合、`hdl_set_extcomm()` が `daemon.extcomm_set_list` を参照するため間接的に連動する。

| 参照種別 | タイミング | evidence |
|---|---|---|
| 起動時一括ロード | `get_table('EXTENDED_COMMUNITY_SET')` → `self.extcomm_set_list` キャッシュ | frrcfgd.py:2221-2226 |
| ランタイム間接参照 | `ROUTE_MAP` の `set_ext_community_ref` 処理時に `hdl_set_extcomm()` がキャッシュを参照 | frrcfgd.py:423-427, 856-863 |

詳細スキャン手順と grep 結果は `meta/_intermediate/cdb-flow/ext-community-set-cross-refs.md` を参照。
<!-- /cross-refs -->
<!-- glossary-links-injected: 3c93d6c0b6a4 -->
