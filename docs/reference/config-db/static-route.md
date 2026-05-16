---
title: STATIC_ROUTE テーブル
description: "STATIC_ROUTE テーブル — STATIC_ROUTE は静的経路を CONFIG_DB に保持するテーブル。YANG では template 形式 (STATIC_ROUTE|) と VRF-aware 形式 (STATIC_ROUTE||) の 2 つの list が定義されている。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-static-route.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - STATIC_ROUTE
  cli:
    - config route
  yang:
    - sonic-static-route
---

# STATIC_ROUTE テーブル

## 概要

`STATIC_ROUTE` は静的経路を [CONFIG_DB](../../reference/glossary.md#term-config_db) に保持するテーブル。[YANG](../../reference/glossary.md#term-yang) では template 形式 (`STATIC_ROUTE|<prefix>`) と [VRF](../../reference/glossary.md#term-vrf)-aware 形式 (`STATIC_ROUTE|<vrf_name>|<prefix>`) の 2 つの list が定義されている[^1]。nexthop、出力 interface、[BGP](../../reference/glossary.md#term-bgp) への advertise、[BFD](../../reference/glossary.md#term-bfd)、administrative distance、nexthop [VRF](../../reference/glossary.md#term-vrf)、blackhole 指定を扱う。テーブル名の実装側定数は `schema.h` も参照する[^2]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>STATIC_ROUTE")]
  DM["fpmsyncd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_ROUTE_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_route_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
STATIC_ROUTE|<prefix>
STATIC_ROUTE|<vrf_name>|<prefix>
```

`<prefix>` は IPv4 / IPv6 prefix。`<vrf_name>` は `default`、`mgmt`、または `Vrf...` 形式。

## 主要フィールド

| フィールド | 型 | 既定値 | 説明 |
|-----------|----|--------|------|
| `nexthop` | string | - | nexthop IP。interface route では `0.0.0.0` を指定する想定 |
| `ifname` | string | - | 出力 interface |
| `advertise` | comma-separated boolean string | `false` | [BGP](../../reference/glossary.md#term-bgp) へ広告するか。nexthop ごとに指定可能 |
| `bfd` | comma-separated boolean string | `false` | nexthop ごとの [BFD](../../reference/glossary.md#term-bfd) 監視有効化。template 形式のみ |
| `distance` | comma-separated uint8 string | `0` | administrative distance。[VRF](../../reference/glossary.md#term-vrf)-aware 形式のみ |
| `nexthop-vrf` | comma-separated VRF string | - | VRF leaking 用 nexthop VRF。VRF-aware 形式のみ |
| `blackhole` | comma-separated boolean string | `false` | 一致パケットを破棄する blackhole route。VRF-aware 形式のみ |

## 制約

- `advertise`、`bfd`、`blackhole` は `true` / `false` のカンマ区切り文字列。
- `distance` は 0..255 のカンマ区切り文字列。
- `nexthop-vrf` は `default`、`mgmt`、`Vrf...` のカンマ区切り文字列。
- [YANG](../../reference/glossary.md#term-yang) の VRF-aware key は `vrf_name prefix`。template 形式には `vrf_name` が無い。

## 購読者

- `staticd` / `zebra` ([FRR](../../reference/glossary.md#term-frr)): SONiC の設定生成パスを通じて static route を [FRR](../../reference/glossary.md#term-frr) に反映する。
- `bgpcfgd` / routing config パス: `advertise` が有効な static route を [BGP](../../reference/glossary.md#term-bgp) 広告対象として扱う。
- `orchagent` / route orch: kernel / [FRR](../../reference/glossary.md#term-frr) から [APPL_DB](../../reference/glossary.md#term-appl_db) 経由で転送経路を [SAI](../../reference/glossary.md#term-sai) route へ反映する。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VRF`、`INTERFACE`、`PORTCHANNEL_INTERFACE`、`VLAN_INTERFACE`、`LOOPBACK_INTERFACE`
- 関連 CLI: `config route`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-static-route`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-static-route`](../yang/sonic-static-route.md)
- CLI: [`config route`](../cli/config-route.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-static-route.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-static-route.yang>
[^2]: テーブル名定数参照: `schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `STATIC_ROUTE|<vrf>|<prefix>` (例 `STATIC_ROUTE|default|10.0.0.0/24`)。
- `nexthop`: カンマ区切り（[ECMP](../../reference/glossary.md#term-ecmp) 可）。
- `distance`: 1（規定）。
- `ifname`: 出力 IF（直接接続経路向け）。

### よくある誤設定

- `nexthop` の IP が到達不可だと FRR が経路を選択せず、`show ip route` で表示されない。
- BGP 学習経路と同じ prefix を static で入れると AD 値次第で意図しない切り替わり。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'STATIC_ROUTE|*'
show ip route static
vtysh -c 'show ip route'
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `advertise` 値別挙動
| 値 | 挙動 |
|----|------|
| `false` | BGP 広告なし（デフォルト）。`ROUTE_ADVERTISE_DISABLE_TAG` を付与して FRR に渡す。 |
| `true` | BGP に経路広告。`ROUTE_ADVERTISE_ENABLE_TAG` を付与。 |

### `bfd` 値別挙動
| 値 | 挙動 |
|----|------|
| `true` | `staticroutebfd` が [BFD](../../reference/glossary.md#term-bfd) セッションを監視。全セッション down で [APPL_DB](../../reference/glossary.md#term-appl_db) から経路削除。`bgpcfgd` の StaticRouteMgr は処理をスキップ（staticroutebfd 側が担う）。 |
| `false` | BFD 監視なし（デフォルト）。`bgpcfgd` が通常処理。 |

### `blackhole` 値別挙動
| 値 | 挙動 |
|----|------|
| `true` | blackhole route（パケット破棄）。nexthop / ifname 不要。FRR に `blackhole` で展開。 |
| `false` | 通常経路（デフォルト）。nexthop が必要。 |

### `distance` 値別挙動
| 値 | 挙動 |
|----|------|
| `0` | デフォルト AD（FRR は static デフォルト AD = 1 を使用）。 |
| 1..255 | 指定の AD で FRR 経路テーブルに挿入。値が小さいほど優先度高。 |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **IpNextHopSet 構築例外**: ネクストホップ解析中に例外が発生した場合 `log_crit` を出して `return False` でスキップ。その静的経路は FRR に設定されない。[^2]
- **[APPL_DB](../../reference/glossary.md#term-appl_db) の key フォーマット不正**: APPL_DB の key で VRF を含む場合 `<vrf>:<prefix>` 形式を期待し、コロン区切りで 2 要素に分割できない場合は `ValueError` で処理中断。[^2]
- **BFD 有効時の APPL_DB 削除スキップ**: `bfd=true` の静的経路で APPL_DB から削除イベントが来ても、[CONFIG_DB](../../reference/glossary.md#term-config_db) に経路が残っている場合は FRR からの削除をスキップする（staticroutebfd との race condition 防止）。[^2]
- **BGP ASN 未設定時の redistribute 保留**: 最初の静的経路設定時に `bgp_asn` が DEVICE_METADATA に存在しない場合、redistribute static コマンドは `vrf_pending_redistribution` に保留されて後で適用される。[^2]
- **BFD セッション全断時の自動削除**: BFD が有効な nexthop のすべての BFD セッションが down になると APPL_DB から経路エントリが削除されて FRR からも経路が削除される。[^2]

[^2]: [bgpcfgd](../../reference/glossary.md#term-bgpcfgd) StaticRouteMgr 実装: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`. <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py>


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

staticroutemgrd が `ip_prefix` の形式（`:` 含むか否か）から FRR コマンド種別を自動決定する。IPv6 → `ipv6 route`、IPv4 → `ip route`。`distance` 未設定の場合は FRR デフォルト distance (1) を使用する。

### Phase 7: 条件付き登録 (add_manager 条件)

staticroutemgrd は常時起動し `STATIC_ROUTE` テーブルを無条件購読する。VRF が `STATIC_ROUTE|<vrf>|<prefix>` 形式で指定される場合は FRR に VRF 付き static route を設定する。`bfd==true` の場合は BFD セッション連携が有効になる。

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `staticroutemgrd` | IPv6 プレフィクス | `ipv6 route <prefix> <nexthop>` | `staticroutemgrd` |
| `staticroutemgrd` | IPv4 プレフィクス | `ip route <prefix> <nexthop>` | `staticroutemgrd` |
| `staticroutemgrd` | `nexthop_vrf` フィールドあり | `ip route ... nexthop-vrf <vrf>` | `staticroutemgrd` |
| `staticroutemgrd` | `blackhole==true` | `ip route <prefix> blackhole` | `staticroutemgrd` |
| `staticroutemgrd` | `bfd==true` | BFD ダウン時に静的ルートを削除 | `staticroutemgrd` |
| `staticroutemgrd` | `distance` フィールドあり | FRR route distance を設定 | `staticroutemgrd` |
| `staticroutemgrd` | del_handler | FRR に `no ip route` 発行 | `staticroutemgrd` |

> **スキャン証跡**: `STATIC_ROUTE` は FRR 静的ルート設定の直接マッピング。IPv4/IPv6 の自動判定と VRF/BFD オプション分岐が主要。

<!-- /handler-branching -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / StaticRouteOrch** または **bgpcfgd**: `STATIC_ROUTE` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- orchagent が APP_DB `ROUTE_TABLE` / `INTF_TABLE` を更新してルートを RouteOrch に渡す。

### 段階 3: APPL → SAI

- RouteOrch が `sai_route_api->create_route_entry()` でスタティックルートをハードウェアに書き込む。
- nexthop の ARP 解決が必要な場合は NeighOrch と連携。

### 段階 4: タイミング + 副作用

- nexthop が到達可能であれば数十 ms 以内に SAI に反映。
- 副作用: `blackhole` nexthop 設定時はパケットが静かに DROP される。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

STATIC_ROUTE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config route add/del ...` — `config/main.py` が `set_entry('STATIC_ROUTE', key, route)` を呼ぶ (sonic-utilities/config/main.py:7886–7973)

### minigraph / sonic-cfggen

minigraph.py に STATIC_ROUTE 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での STATIC_ROUTE マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

**sonic-bgpcfgd** `static_rt_timer.py` が STATIC_ROUTE を監視し staticd に広告 (sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/static_rt_timer.py); **frrcfgd** も STATIC_ROUTE を監視

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- failure -->
## 失敗挙動 (Phase D)

### 失敗パス一覧

| # | トリガー | 発生箇所 | 結果 | retry |
|---|---------|---------|------|-------|
| 1 | nexthop/ifname/blackhole フィールドのリスト長不一致 | `IpNextHopSet.__init__()` → `log_err` + `raise ValueError` | `set_handler()` が `log_crit` + `return False` でエントリをスキップ | なし |
| 2 | nexthop が zero-IP かつ ifname 未指定（blackhole でない） | `IpNextHop.__init__()` → `log_err('Mandatory attribute not found for nexthop')` + `raise ValueError` | 対象 nexthop のみ `IpNextHopSet` に追加されずスキップ | なし |
| 3 | nexthop の IP 文字列が不正 (`socket.inet_pton` 失敗) | `IpNextHop.is_ip_valid()` → `socket.error` | 例外が `set_handler()` の `try/except` でキャッチされ `log_crit` + `return False` | なし |
| 4 | VRF 未解決（APPL_DB key の `:` 区切りが 1 要素以下） | `StaticRouteMgr.split_key()` → `log_debug` + `raise ValueError` | `set_handler()` / `del_handler()` が例外で中断。当該経路は FRR に設定されない | なし |
| 5 | vtysh への設定書き込み失敗（FRR デーモン未起動等） | `FRR.write()` → `log_err('can\'t push configuration from file ...')` | コマンドリストは破棄。FRR 設定に反映されない。retcode != 0 を返す | なし |
| 6 | FRR デーモン起動タイムアウト | `FRR.wait_for_daemons()` → `raise RuntimeError` | bgpcfgd プロセスが起動失敗。`systemctl restart bgp` が必要 | なし |
| 7 | fpmsyncd: VRF ifindex からの名前解決失敗 | `routesync.cpp` → `SWSS_LOG_ERROR("Fail to get the VRF name (ifindex %u)")` + `return` | 当該 netlink メッセージを破棄。APP_DB に反映されない | なし |
| 8 | fpmsyncd: VRF 名が `Vrf` プレフィクスで始まらない | `routesync.cpp` → `SWSS_LOG_ERROR("Invalid VRF name %s")` + `return` | 同上。APP_DB に反映されない | なし |
| 9 | fpmsyncd: RTN_BLACKHOLE / RTN_UNREACHABLE / RTN_PROHIBIT 型ルート受信 | `routesync.cpp` → `SWSS_LOG_ERROR("RTN_BLACKHOLE route not expected")` + `return` | static blackhole は FRR → fpmsyncd ではなく bgpcfgd 経路で処理すべき。fpmsyncd 側は破棄 | なし |
| 10 | BGP ASN 未設定時の redistribute static 保留 | `set_handler()` → `vrf_pending_redistribution.add(vrf)` | redistribute static コマンドを保留。`on_bgp_asn_change()` 呼び出しまで BGP 広告が行われない | 自動回復 (ASN 設定後) |

### IpNextHopSet 構築例外の詳細

```python
# managers_static_rt.py (bgpcfgd)
try:
    ip_nh_set = IpNextHopSet(is_ipv6, bkh_list, nh_list, intf_list, dist_list, nh_vrf_list)
    ...
except Exception as exc:
    log_crit("Got an exception %s: Traceback: %s" % (str(exc), traceback.format_exc()))
    return False  # エントリは FRR に設定されない
```

リスト長不一致の具体例: `nexthop=10.0.0.1,10.0.0.2` かつ `ifname=Ethernet0` (1 要素) → `nums = {2, 1}` → `len(nums) != 1` → `ValueError`。

### FRR vtysh 失敗の詳細

```python
# frr.py (bgpcfgd)
ret_code, out, err = run_command(["vtysh", "-f", tmp_filename])
if ret_code != 0:
    log_err("ConfigMgr::commit(): can't push configuration from file='%s', rc='%d', stdout='%s', stderr='%s'" % err_tuple)
return ret_code == 0
```

`push_list()` は `FRR.write()` を呼ぶ。`vtysh` の戻り値が非 0 の場合はエラーログのみで静的経路は FRR に未反映のまま。bgpcfgd プロセスは継続動作するが、内部の `static_routes` キャッシュは更新済みのため再試行されない。

### STATE_DB / ERROR_TABLE への記録

STATIC_ROUTE に関する `STATE_DB` への障害記録はなし。失敗は `syslog`（`log_crit` / `log_err`）への出力のみ。CONFIG_DB のエントリは失敗後も残る。

```bash
# bgpcfgd ログ確認
journalctl -u bgp | grep -i "static route"
# fpmsyncd ログ確認
journalctl -u swss | grep -i "VRF name\|RTN_BLACKHOLE"
```

> 中間調査ファイル: `meta/_intermediate/cdb-flow/static-route-failure.md`
<!-- /failure -->

<!-- defaults -->
## フィールドの暗黙デフォルト (Phase A)

以下はコード精読により判明したコード由来の暗黙デフォルト。YANG の `default` 宣言と実装が乖離している箇所を含む。

### `advertise` — YANG-実装乖離（重大）

| 状態 | YANG デフォルト | 実装挙動 |
|------|------------|------|
| フィールド不在 | `"false"`（広告無効） | `ROUTE_ADVERTISE_ENABLE_TAG='1'`（広告**有効**）が使われる |
| `"false"` を明示 | `"false"` | `ROUTE_ADVERTISE_DISABLE_TAG='2'`（無効）— 正しい |
| `"true"` を明示 | — | `ROUTE_ADVERTISE_ENABLE_TAG='1'`（有効）— 正しい |

`managers_static_rt.py` L46 の条件式 `'advertise' in data and data['advertise'] == "false"` のため、フィールド不在は有効タグになる。`config route add` CLI は `advertise` を書かないので、CLI 経由で追加した静的経路は BGP 広告有効として扱われることがある[^mgr]。

### `distance` — ゼロ値は FRR に渡さない

`IpNextHop.__format__` は `distance == 0` の場合 FRR コマンドに distance を含めない。結果として FRR の static route デフォルト AD=1 が使われる。YANG デフォルト `"0"` は「FRR デフォルトを使え」という意味[^mgr]。

### `blackhole` — フィールド不在は `'false'`

`IpNextHop.__init__` は `blackhole is None` または `''` の場合 `'false'` を設定する。`staticroutebfd` は `blackhole=true` の経路を完全スキップするため、BFD+blackhole の組み合わせは動作しない（dead consumer パス）[^mgr]。

### `nexthop-vrf` — staticroutebfd による自動補完

`staticroutebfd` では `nexthop-vrf` フィールドが不在の場合、route key の VRF 名でリストを自動補完する（`vrf * len(nh_list)`）。空要素も同様に補完される[^bfd]。

### BFD セッションのハードコードデフォルト

`bfd=true` 時に staticroutebfd が作成する BFD セッションの既定値[^bfd]:

| パラメータ | 値 |
|-----------|----|
| `multihop` | `false` |
| `rx_interval` | `50` ms |
| `tx_interval` | `50` ms |
| `multiplier` | `3` |

### ハードコード: route-map 名

BGP redistribute static に使われる route-map 名は `'STATIC_ROUTE_FILTER'`、シーケンス番号は `10` でハードコードされている（`managers_static_rt.py` L224）[^mgr]。

### 静的経路タイマー (APPL_DB)

`static_rt_timer.py` による APPL_DB エントリの有効期限管理:

| パラメータ | 値 |
|-----------|----|
| デフォルト有効期限 | 180秒 |
| タイマーポーリング間隔 | 60秒 |
| 最大有効期限 | 172800秒（2日） |

`expiry="false"` のエントリは削除されない。`refresh="true"` のエントリは次サイクルに持ち越し（`false` に更新）。その他は DELETE[^timer]。

[^mgr]: bgpcfgd StaticRouteMgr 実装: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`
[^bfd]: staticroutebfd 実装: `sonic-buildimage/src/sonic-bgpcfgd/staticroutebfd/main.py` および `vars.py`
[^timer]: static_rt_timer 実装: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/static_rt_timer.py`
<!-- /defaults -->

<!-- glossary-links-injected: 21a1d1474543 -->
