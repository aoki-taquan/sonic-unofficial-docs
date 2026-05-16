---
title: BGP_GLOBALS_AF_AGGREGATE_ADDR テーブル
description: "BGP_GLOBALS_AF_AGGREGATE_ADDR テーブル — BGP_GLOBALS_AF で AF レベルの設定（multipath、route distance、L2VPN advertise-all-vni 等）を行い、その AF 配下の aggregate prefix をこのテーブルで列挙する。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-global.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BGP_GLOBALS_AF_AGGREGATE_ADDR
    - BGP_GLOBALS_AF
    - BGP_GLOBALS
    - BGP_AGGREGATE_ADDRESS
  cli:
    - config bgp
  yang:
    - sonic-bgp-global
---

# BGP_GLOBALS_AF_AGGREGATE_ADDR テーブル

## 概要

**[VRF](../../reference/glossary.md#term-vrf) × アドレスファミリ単位の [BGP](../../reference/glossary.md#term-bgp) aggregate-address 設定** を保持する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル[^1]。`frr-mgmt-framework` (DEVICE_METADATA の `frr_mgmt_framework_config = true` 経路) が [CONFIG_DB](../../reference/glossary.md#term-config_db) から読み、[FRR](../../reference/glossary.md#term-frr) `bgpd` の `router bgp <as>` → `address-family <afi> <safi>` → `aggregate-address <prefix>` 系コマンドに反映する。

`BGP_GLOBALS_AF` で AF レベルの設定（multipath、route distance、L2VPN advertise-all-vni 等）を行い、その AF 配下の **aggregate prefix** をこのテーブルで列挙する。

なお、似た名前の `BGP_AGGREGATE_ADDRESS` テーブル ([YANG](../../reference/glossary.md#term-yang) `sonic-bgp-aggregate-address`) は **AF/[VRF](../../reference/glossary.md#term-vrf) を持たないフラットな** aggregate 定義で、別経路 ([bgpcfgd](../../reference/glossary.md#term-bgpcfgd) テンプレ) で利用される。両者は実装パスが異なる点に注意。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>BGP_GLOBALS_AF_AGGREGATE_ADDR")]
  DM["frrcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
BGP_GLOBALS_AF_AGGREGATE_ADDR|<vrf_name>|<afi_safi>|<ip_prefix>
```

- `<vrf_name>`: `BGP_GLOBALS.vrf_name` への leafref (例: `default`, `Vrf01`)
- `<afi_safi>`: 例 `ipv4_unicast`, `ipv6_unicast`, `l2vpn_evpn`
- `<ip_prefix>`: 集約対象プレフィックス (`inet:ip-prefix`)

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `vrf_name` (key) | leafref → `BGP_GLOBALS.vrf_name` | 所属 [VRF](../../reference/glossary.md#term-vrf) |
| `afi_safi` (key) | string | アドレスファミリ |
| `ip_prefix` (key) | inet:ip-prefix | 集約プレフィックス |
| `as_set` | boolean | AS_SET path 情報を生成 (RFC 4271) |
| `summary_only` | boolean | より詳細 (more-specific) ルートを抑止し summary のみ広告 |
| `policy` | leafref → `ROUTE_MAP_SET.name` | aggregate に適用する route-map |

## 制約

- 3 つのキー (`vrf_name` / `afi_safi` / `ip_prefix`) で一意。
- `vrf_name` は `BGP_GLOBALS_LIST.vrf_name` への leafref のため、対応する VRF の [BGP](../../reference/glossary.md#term-bgp) インスタンスが先に存在している必要がある。
- `summary_only = true` を指定すると aggregate に含まれる more-specific ルートは [BGP](../../reference/glossary.md#term-bgp) UPDATE から抑制される（[FRR](../../reference/glossary.md#term-frr) の `aggregate-address ... summary-only` 相当）。

## 購読者

- `frr-mgmt-framework`: 本テーブルを vtysh の `aggregate-address` コマンドに変換し `bgpd` に投入
- `bgpd` ([FRR](../../reference/glossary.md#term-frr)): RIB から該当プレフィックス配下のルートを集約し、設定に応じて抑制・AS_SET 生成・route-map 適用を行う

`bgpcfgd` (テンプレベース) ではこのテーブルではなく `BGP_AGGREGATE_ADDRESS` を使う。設定経路を明確にするため、両方を併用するのは避ける。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_GLOBALS`, `BGP_GLOBALS_AF`, `BGP_GLOBALS_AF_NETWORK`, `BGP_AGGREGATE_ADDRESS`, `ROUTE_MAP_SET`
- 関連 CLI: `config bgp` ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities) 経由)、vtysh の `aggregate-address` (直接)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-bgp-global`

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| key の IP prefix 形式不正 | `normalize_ip_prefix()` が None → syslog ERR & continue、FRR 未反映 |
| AF_TYPE フォーマット不正（`_` 区切り不可） | ValueError が上位に伝播 |
| FRR コマンド実行失敗 | syslog ERR & continue、内部キャッシュ更新なし |
| `BGP_GLOBALS` が未設定（bgp_asn 不在） | 上位ハンドラで依存待機、または KeyError 伝播 |
| DEL 操作で `af_aggr_list[vrf]` に存在しない prefix | `pop(None)` で KeyError なし |
| `as_set`/`summary_only` フィールド欠如 | デフォルト `false` 扱い（`data.get(attr)` で None） |
| 更新操作 | FRR に `aggregate-address` を再投入（既存エントリの削除と新規追加の組み合わせ） |

<!-- evidence: sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:3187L -->
<!-- /cdb-exceptions -->

<!-- defaults -->
## コード由来の暗黙デフォルト

YANG の `sonic-bgp-global.yang` は `as_set`、`summary_only`、`policy` すべてで `default` 文を宣言していない。実装上の fallback は frrcfgd.py のコードで定義される。

| フィールド | YANG default | 実装 fallback | FRR コマンド影響 |
|-----------|-------------|--------------|----------------|
| `as_set` | 未宣言 | `False`（`AggregateAddr.__init__` L1704） | キーワード `as-set` なし |
| `summary_only` | 未宣言 | `False`（`AggregateAddr.__init__` L1705） | キーワード `summary-only` なし |
| `policy` | 未宣言 | 空文字列（`+` optional フィールド） | `route-map` 指定なし |

### as_set / summary_only の fallback 根拠

`frrcfgd.py` の `AggregateAddr` クラス（L1702-1705）は `__init__` で両フィールドを `False` に初期化する。フィールドが CONFIG_DB に存在しないか `"true"` でない場合、`setattr` が呼ばれないため初期値 `False` が維持される。`CommandArgument.__format__` の `bool_format`（L815-816）で `"false"` または空は FRR キーワードなしに変換される。

### policy の fallback 根拠

`af_aggregate_key_map`（L1982）で `policy` は `'+policy'`（`+` = optional）として宣言される。フィールド欠如時は `cmd_data` に空文字列 `''` が渡り、`aggr-policy` format（L928-930）は空文字列にプレフィックスを追加しないため、FRR コマンドに `route-map` が付加されない。

### Discrepancy: Jinja2 テンプレート経路で `policy` が無視される

`bgpd.conf.db.addr_family.j2`（L48-61）の bgpcfgd テンプレート経路は `as_set`/`summary_only` のみを処理し、`policy` フィールドを完全に無視する。frr-mgmt-framework 経路（`frrcfgd.py`）は `policy` を `route-map <name>` として反映するが、Jinja2 経路では同フィールドが読まれない。通常は両経路が同一エントリを処理しないため実害は限定的だが、設定経路の混在時に `policy` が反映されないリスクがある。

<!-- evidence: sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:1702-1705,1982; sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.addr_family.j2:48-61 -->
<!-- /defaults -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### enum 型フィールド

該当無し (key の `afi_safi` は string だが YANG enum ではなく任意文字列)

### boolean フィールド

| フィールド | `true` の効果 | `false` の効果 | evidence |
|---|---|---|---|
| `summary_only` | FRR `aggregate-address <prefix> summary-only` を生成。contributing route が BGP UPDATE から抑制される | キーワードなし。contributing route と aggregate を両方広告 | `sonic-bgp-global.yang; frrcfgd.py:3187` |
| `as_set` | FRR `aggregate-address <prefix> as-set` を生成。集約経路に AS_SET path 属性を付与 | キーワードなし | `sonic-bgp-global.yang` |

### `policy` (leafref → ROUTE_MAP_SET.name)

| 値 | 効果 | evidence |
|---|---|---|
| 文字列 (route-map 名) | `aggregate-address <prefix> route-map <name>` を生成。aggregate に route-map を適用して属性を加工 | `frrcfgd.py:3187` |
| 空/未設定 | route-map 指定なし | — |

### 複合条件

- `summary_only=true` かつ contributing route が RIB に 0 本 → FRR で aggregate 生成されない (BGP 仕様)
- frr-mgmt-framework 経路 (`DEVICE_METADATA.frr_mgmt_framework_config=true`) でのみ有効。bgpcfgd テンプレ経路では `BGP_AGGREGATE_ADDRESS` テーブルを使い、両者を混在させると干渉する可能性がある
<!-- /value-behavior -->

<!-- platform -->
## プラットフォーム差

`frrcfgd.py` (`src/sonic-frr-mgmt-framework/frrcfgd/`) および `bgpcfgd` (`src/sonic-bgpcfgd/bgpcfgd/`) を全文走査した結果、`BGP_GLOBALS_AF_AGGREGATE_ADDR` の挙動はコミュニティ master 上で **プラットフォーム非依存**である。経路は `frrcfgd` → vtysh → FRR `bgpd` (ユーザ空間ルーティングデーモン) で完結し、SAI / ASIC SDK を直接呼び出さないため、CONFIG_DB スキーマ・キー構造・適用ロジックには ASIC / chassis / multi-asic 差が現れない。

| 観点 | 差の有無 | 根拠 |
|---|---|---|
| ASIC ベンダー (Broadcom / Mellanox / Marvell 等) 分岐 | なし | `frrcfgd.py` 全体を `platform|asic|chassis|vendor` で grep して 0 ヒット (偽陽性 1 件は L3384 `'Basic mode...'` の `asic` 部分一致)。aggregate-address 適用は FRR `bgpd` のソフト処理 |
| switch type (voq / chassis / fabric) 分岐 | なし | `frrcfgd.py` に `voq` / `chassis` / `fabric` 参照 0 件。`hdl_af_aggregate()` (L1313)・`af_aggregate_key_map` (L1982-1983)・per-table 分岐 (L3169, L3187) いずれも ASIC 形態に依存しない |
| multi-asic / namespace 特殊化 | なし | `frrcfgd.py` に `is_multi_npu()` / `namespace` 参照 0 件。各 asic-namespace は独立 BGP container で同一ロジックを実行 |
| 一次経路の重複 (bgpcfgd テンプレ vs frr-mgmt-framework) | あり (プラットフォーム非依存) | `BGP_GLOBALS_AF_AGGREGATE_ADDR` を購読するのは `frrcfgd.py` のみ (`DEVICE_METADATA.frr_mgmt_framework_config=true` 経路)。`bgpcfgd/` 配下と `dockers/docker-fpm-frr/` 配下を grep しても 0 ヒット。bgpcfgd テンプレ経路は別テーブル `BGP_AGGREGATE_ADDRESS` を使う点に注意 (ASIC 差ではなく機能経路の切替) |
| ビルド時 platform オーバライド | なし | `device/<vendor>/<platform>/` 配下に本テーブルを差し替える j2 / json / hwsku-d 由来の差分は検出されず |

詳細な走査ログは `meta/_intermediate/cdb-flow/bgp-globals-af-aggregate-addr-platform.md` を参照。
<!-- /platform -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-bgp-global`](../yang/sonic-bgp-global.md)
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-bgp-global.yang` (`BGP_GLOBALS_AF_AGGREGATE_ADDR` container). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-global.yang>

## 関連ページ
- [CONFIG_DB: BGP_GLOBALS_AF](bgp-globals-af.md)
- [CONFIG_DB: BGP_AGGREGATE_ADDRESS](bgp-aggregate-address.md)
- [YANG: sonic-bgp-global](../yang/sonic-bgp-global.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BGP_GLOBALS_AF_AGGREGATE_ADDR|<vrf>|<afi_safi>|<prefix>` (例 `BGP_GLOBALS_AF_AGGREGATE_ADDR|default|ipv4_unicast|10.0.0.0/8`)。
- `summary_only=true` で more-specific を抑制、`as_set=true` で AS_SET 生成。

### よくある誤設定

- 同一 AF に対して `BGP_AGGREGATE_ADDRESS` (フラット) と本テーブル (frr-mgmt-framework 経路) を併用し、設定経路が衝突。
- 集約に含まれる more-specific ルートが RIB に無く、aggregate が広告されない (BGP では 1 本以上の構成ルートが必要)。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BGP_GLOBALS_AF_AGGREGATE_ADDR|*'
vtysh -c "show ip bgp summary"
vtysh -c "show running-config bgpd" | grep aggregate-address
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`bgpcfgd` が CONFIG_DB の `BGP_GLOBALS_AF_AGGREGATE_ADDR` テーブルを購読する。

`BGP_GLOBALS_AF_AGGREGATE_ADDR` は `<vrf>|<af>|<prefix>` の key 構造。

### 段階 2 — CFG→APPL 翻訳

なし (FRR vtysh 経由)

### 段階 3 — APPL→SAI

なし (FRR BGP のみ)

### 段階 4 — タイミングと副作用

**適用タイミング**: 変化検知後 FRR に AF 固有の aggregate-address コマンドを発行。

**副作用**: AF 毎の集約ルート広告が変化。`summary-only` 有効時は子プレフィクスが withdraw される。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `BGP_GLOBALS_AF_AGGREGATE_ADDR`

### CLI
- `vtysh` 経由 aggregate-address コマンド (bgpcfgd が CONFIG_DB へ書き戻し)
  - ソース: `sonic-frr bgpcfgd`

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
- `bgpcfgd` が FRR running-config を読み CONFIG_DB と同期
<!-- /entry-points -->

<!-- ordering -->
## 書込み順依存 (Phase B)

### `BGP_GLOBALS` 先行必須 (bgp_asn)

`bgp_table_handler_common()` の `BGP_GLOBALS_AF_AGGREGATE_ADDR` 分岐は `self.bgp_asn[vrf]` から `local_asn` を取得し、`router bgp <as> vrf <vrf>` プレフィクスを組み立てる。対応 VRF の `BGP_GLOBALS.local_asn` が CONFIG_DB に**先に**存在しないと vtysh コマンドが組み立てられず、aggregate-address は FRR に流れない。`table_handler_list` (frrcfgd.py L2296-2317) では `BGP_GLOBALS` (3 番目) が `BGP_GLOBALS_AF_AGGREGATE_ADDR` (23 番目) より先に登録されているため load フェーズでは自動保証だが、runtime に aggregate のみ先着した場合は `KeyError` 系の握り潰しで非反映となり、後続で `BGP_GLOBALS` が届いても aggregate は自動再投入されない（再 SET が必要）。<!-- evidence: frrcfgd.py:3169-3186, 2296-2317 -->

### `BGP_GLOBALS_AF` 先行推奨 (address-family コンテキスト)

aggregate-address は FRR で `router bgp <as>` → `address-family <afi> <safi>` → `aggregate-address <prefix>` の階層下に置かれる。`BGP_GLOBALS_AF|<vrf>|<afi_safi>` を先に書いてから aggregate を投入することで、AF レベル属性 (`multipath`、route distance、L2VPN advertise-all-vni 等) と aggregate が同一適用ウィンドウで揃う。順序が逆でも aggregate 自体は反映されるが、AF 属性は AF 設定到着まで非反映。`table_handler_list` では `BGP_GLOBALS_AF` (4 番目) が先のため load フェーズでは自動保証。<!-- evidence: frrcfgd.py:2297, 2317, 3169-3186 -->

### `__init__` snapshot のコード固定順

`BGPConfigDaemon.__init__()` は `BGP_GLOBALS` テーブル取得 (L2207-2213) で `bgp_asn[vrf]` を構築した後、`BGP_GLOBALS_AF_AGGREGATE_ADDR` テーブル取得 (L2257-2266) で `af_aggr_list[vrf][prefix] = AggregateAddr()` を構築する。コード上の固定順序により daemon 起動時のスナップショットでは `BGP_GLOBALS` → aggregate の順で読まれる。aggregate 単独で CONFIG_DB にある状態で daemon が起動すると、`af_aggr_list` キャッシュは作られても後続 SET イベントで `bgp_asn[vrf]` 不在となり vtysh 投入は失敗する。<!-- evidence: frrcfgd.py:2207-2213, 2257-2266 -->

### `frrcfgd` 起動順 — bgpd 先行必須

aggregate-address コマンドは `vtysh -c 'configure terminal' -c 'router bgp ...'` 経由で `bgpd` に投入される。`bgpd` の vty socket (`/var/run/frr/bgpd.vty`) が未生成の状態で vtysh を実行すると `failed to connect to any daemon` で失敗、`key_map.run_command()` が False を返し syslog ERR を出して continue する。frrcfgd は失敗時に再試行しないため、bgpd 復活後に CONFIG_DB へ再 SET するか `frrcfg.sh restart` で replay する必要がある。docker-fpm-frr の supervisord は `bgpd` → `frrcfgd` の順を狙うが、warm-restart や crash 復旧時はレースし得る。<!-- evidence: frrcfgd.py:3179-3186 -->

### bgpd CLI 順 — `no aggregate-address` 先行 → `aggregate-address <new>`

`hdl_af_aggregate()` は UPDATE 操作で対象 vrf+prefix が既に `af_aggr_list` に存在する場合、先に `no aggregate-address <prefix>` を生成してから `get_command_cmn()` で実 SET コマンドを追加する。Update = (Delete + Add) の合成で、`as_set` / `summary_only` / `policy` の欠落フィールドが意図せず引き継がれる事故を避けるための CLI 順。同一 vtysh セッションで連続投入されるが、`summary_only=true` 運用中はこの 1 瞬の aggregate 消失で more-specific ルートが一時的に広告される副作用に注意。CLI 順自体は逆転できない（コード固定）。<!-- evidence: frrcfgd.py:1313-1326 -->

### DEL 時の vtysh 投入 → cache pop の順

DEL 操作では `key_map.run_command` で `no aggregate-address` を vtysh に投入してから `self.af_aggr_list[vrf].pop(norm_ip_prefix, None)` を呼ぶ。pop は `None` デフォルトで KeyError は出ない。vtysh 投入失敗時もキャッシュは pop されないが、次回 UPDATE 時の `no` 先行発行のキーとして残るのみでリーク影響は小さい。<!-- evidence: frrcfgd.py:3187-3197 -->

### 不正 `ip_prefix` キーの早期 continue

`normalize_ip_prefix()` が None を返す不正キーは当該 entry のみ skip され、後続エントリの処理は継続する。順序依存なしだが、ログ (`invalid IP prefix format`) を見落とすと該当 aggregate のみ未適用となる。<!-- evidence: frrcfgd.py:3172-3175 -->

詳細スキャンログは `meta/_intermediate/cdb-flow/bgp-globals-af-aggregate-addr-ordering.md` を参照。
<!-- /ordering -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### Redis 購読方式

`BGP_GLOBALS_AF_AGGREGATE_ADDR` テーブルへの変更通知は **`frrcfgd` (sonic-frr-mgmt-framework) のみ** が受信する。`frrcfgd` は `ConfigDBConnector` を継承した独自 `ExtConfigDBConnector.subscribe()` + `listen()` で **Redis keyspace 通知 (`PSUBSCRIBE __keyspace@<dbId>__:*`)** を購読する。`swsscommon.SubscriberStateTable` (channel ベース PUBLISH/SUBSCRIBE) は本経路では使用しない。CONFIG_DB は永続前提のため TTL は設定されない。

`bgpcfgd` のテンプレ経路 (`bgpd.conf.db.addr_family.j2`) は別テーブル `BGP_AGGREGATE_ADDRESS` (フラット) を使用し、本テーブルは購読しない (Phase F `<!-- side-effects -->` で確認済)。両者は同一機能の異なる設定経路のため、混在は避ける。

| 購読者 | 対象テーブル | 購読 API | 通信方式 | ハンドラ |
|--------|------------|---------|---------|---------|
| `frrcfgd` | `BGP_GLOBALS_AF_AGGREGATE_ADDR` | `ExtConfigDBConnector.subscribe()` + `listen()` (keyspace 通知) | Redis `PSUBSCRIBE __keyspace@<dbId>__:*` | `bgp_table_handler_common` → `hdl_af_aggregate` |

`orchagent` / `syncd` 等の APPL_DB / ASIC_DB レイヤは本テーブルを購読しない (FRR `bgpd` のソフト処理で完結、SAI 非経由)。

### keyspace 通知 → ハンドラ呼び出しの流れ (frrcfgd 経路)

```
sonic-db-cli CONFIG_DB hset 'BGP_GLOBALS_AF_AGGREGATE_ADDR|default|ipv4_unicast|10.0.0.0/8' summary_only true
  ↓ HSET 後に Redis 側で keyspace 通知発火
Redis keyspace PUBLISH "__keyspace@4__:BGP_GLOBALS_AF_AGGREGATE_ADDR|default|ipv4_unicast|10.0.0.0/8" "hset"
  ↓ ExtConfigDBConnector.listen_thread() がパターンマッチ
sub_msg_handler() → client.hgetall(key)  ← 通知後に値を再取得
raw_to_typed() で型変換
  ↓ _ConfigDBConnector__fire("BGP_GLOBALS_AF_AGGREGATE_ADDR", "default|ipv4_unicast|10.0.0.0/8", data)
bgp_table_handler_common(table, key, data) → bgp_message キューへ enqueue
  ↓ __update_bgp() で順次処理 (frrcfgd.py:3169-3196)
  ↓ key を vrf / af_type / ip_prefix に分解、normalize_ip_prefix() で正規化
  ↓ cmd_prefix = ['configure terminal', 'router bgp <asn> vrf <vrf>', 'address-family <af> <ip_type>']
  ↓ vtysh -c "aggregate-address 10.0.0.0/8 summary-only"
  ↓ AggregateAddr() を self.af_aggr_list[vrf][prefix] にキャッシュ
```

- keyspace 通知のペイロードは操作名 (`hset` / `del` 等) のみ。フィールド値は `client.hgetall(key)` で再取得 (`frrcfgd.py:1527-1528`)。
- `data is None ? DEL : SET` の 2 値判定 (`ConfigDBConnector` 標準動作)。`HDEL` / `HSET` の Redis 操作種別は区別しない。
- DEL では `self.af_aggr_list[vrf].pop(norm_ip_prefix, None)` でキャッシュから除去 (`frrcfgd.py:3194-3196`、`pop(..., None)` のため未登録 prefix でも KeyError は出ない)。
- `listen_thread` は専用スレッドで動作 (`frrcfgd.py:1551`)。テーブルハンドラは同スレッド内で逐次実行され、内部キュー `bgp_message` 経由で `__update_bgp` に直列化される。
- 起動時は `subscribe_all()` (`frrcfgd.py:2359-2361`) 開始前に `config_db.get_table_data([...])` で `table_handler_list` 全テーブルの一括スナップショットを取得し (`frrcfgd.py:2340`)、`config_mode == "unified"` であれば各エントリを `bgp_message` 経由で config replay する (`frrcfgd.py:2344-2357`)。

### サービス再起動トリガー

| 契機 | 操作 | コード |
|------|------|--------|
| `BGP_GLOBALS_AF_AGGREGATE_ADDR` 変更 | FRR `bgpd` への vtysh `(no )aggregate-address <prefix> [as-set] [summary-only] [route-map <name>]` 送出のみ。`bgpd` プロセス restart **なし** | `frrcfgd.py:3169-3196`, `1982-1983` |
| IP prefix 形式不正 | `MatchPrefix.normalize_ip_prefix()` → `None` で syslog ERR & continue | `frrcfgd.py:3172-3175` |
| `BGP_GLOBALS` (`bgp_asn`) 未設定 | `local_asn` 未解決のため当該 update は依存待ちで保留 | `frrcfgd.py:__update_bgp` 上層 |

vtysh コマンド送出のみで BGP セッション自体は再起動されない。集約広告の反映は **FRR の RIB 計算ループ** の次サイクルで行われ、contributing route が RIB に 1 本以上存在する場合のみ aggregate が広告される (BGP 仕様)。

> **Evidence**: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:98, 1313, 1506-1555, 1982-1983, 2118, 2257, 2317, 2340-2357, 2359-2361, 3169-3196, 3955-3956` (keyspace listen / subscribe / `bgp_table_handler_common` / `hdl_af_aggregate` / 起動スナップショット / config replay); 詳細分析 `meta/_intermediate/cdb-flow/bgp-globals-af-aggregate-addr-pubsub.md`
<!-- /pubsub -->

<!-- glossary-links-injected: fcbe746ecf8b -->
