---
title: BGP_GLOBALS_AF_NETWORK テーブル
description: "BGP_GLOBALS_AF_NETWORK テーブル — BGP_GLOBALS_AF_AGGREGATE_ADDR が複数の動的ルートを 集約 するのに対し、こちらは管理者が 明示的に広告したいプレフィックス を列挙する用途。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-global.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BGP_GLOBALS_AF_NETWORK
    - BGP_GLOBALS_AF
    - BGP_GLOBALS
  cli:
    - config bgp
  yang:
    - sonic-bgp-global
---

# BGP_GLOBALS_AF_NETWORK テーブル

## 概要

**[VRF](../../reference/glossary.md#term-vrf) × アドレスファミリ単位** で [BGP](../../reference/glossary.md#term-bgp) に **静的に注入するネットワーク** (`network <prefix>` ステートメント) を定義する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル[^1]。[FRR](../../reference/glossary.md#term-frr) `bgpd` の `address-family <afi> <safi>` 配下の `network <ip_prefix>` に対応する。`frr-mgmt-framework` 経路 (DEVICE_METADATA `frr_mgmt_framework_config = true`) で使用される。

`BGP_GLOBALS_AF_AGGREGATE_ADDR` が複数の動的ルートを **集約** するのに対し、こちらは管理者が **明示的に広告したいプレフィックス** を列挙する用途。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>BGP_GLOBALS_AF_NETWORK")]
  DM["frrcfgd"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
BGP_GLOBALS_AF_NETWORK|<vrf_name>|<afi_safi>|<ip_prefix>
```

- `<vrf_name>`: `BGP_GLOBALS.vrf_name` への leafref
- `<afi_safi>`: `ipv4_unicast`, `ipv6_unicast` 等
- `<ip_prefix>`: 広告対象プレフィックス (`inet:ip-prefix`)

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `vrf_name` (key) | leafref → `BGP_GLOBALS.vrf_name` | 所属 [VRF](../../reference/glossary.md#term-vrf) |
| `afi_safi` (key) | string | アドレスファミリ |
| `ip_prefix` (key) | inet:ip-prefix | 広告するネットワーク |
| `policy` | leafref → `ROUTE_MAP_SET.name` | 属性を加工する route-map |
| `backdoor` | boolean | backdoor ルートとして指定 (RFC 1771 / [FRR](../../reference/glossary.md#term-frr) 拡張) |

## 制約

- 3 つのキーで一意。
- 対応する [VRF](../../reference/glossary.md#term-vrf) の [BGP](../../reference/glossary.md#term-bgp) インスタンスが先に必要 (leafref)。
- `network` で広告するためには、**実際にそのプレフィックスが RIB (ルーティングテーブル) に存在する** ことが [BGP](../../reference/glossary.md#term-bgp) の動作上の前提（`BGP_GLOBALS.network_import_check = true` の場合）。
- `backdoor` は IGP と BGP の同一プレフィックスで IGP を優先させたいときに使う。

## 購読者

- `frr-mgmt-framework`: vtysh の `network <prefix> [route-map <name>] [backdoor]` コマンドに変換
- `bgpd` ([FRR](../../reference/glossary.md#term-frr)): network 経由で BGP UPDATE に該当プレフィックスを注入

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_GLOBALS`, `BGP_GLOBALS_AF`, `BGP_GLOBALS_AF_AGGREGATE_ADDR`, `ROUTE_MAP_SET`, `STATIC_ROUTE`
- 関連 CLI: vtysh の `network <prefix>` (`frr-mgmt-framework` 経路では [CONFIG_DB](../../reference/glossary.md#term-config_db) 投入)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-bgp-global`

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| key の IP prefix 形式不正 | `normalize_ip_prefix()` が None → syslog ERR & continue、FRR 未反映 |
| AF_TYPE フォーマット不正（`_` 区切り不可） | ValueError が上位に伝播 |
| FRR コマンド実行失敗 | syslog ERR & continue、再試行なし |
| `policy`/`backdoor` フィールド欠如 | FRR コマンドの該当部分を空/省略で生成 |
| 重複 `network <prefix>` 投入 | FRR は冪等に処理、frrcfgd 側での重複チェックなし |
| `BGP_GLOBALS` が未設定（bgp_asn 不在） | 上位ハンドラで依存待機、または KeyError 伝播 |
| DEL 操作 | FRR への `no network <prefix>` のみ、内部キャッシュなし |

<!-- evidence: sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:3169L -->
<!-- /cdb-exceptions -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-bgp-global`](../yang/sonic-bgp-global.md)
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-bgp-global.yang` (`BGP_GLOBALS_AF_NETWORK` container). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-global.yang>

## 関連ページ
- [CONFIG_DB: BGP_GLOBALS_AF](bgp-globals-af.md)
- [CONFIG_DB: BGP_GLOBALS_AF_AGGREGATE_ADDR](bgp-globals-af-aggregate-addr.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BGP_GLOBALS_AF_NETWORK|<vrf>|<afi_safi>|<prefix>` (例 `BGP_GLOBALS_AF_NETWORK|default|ipv4_unicast|10.1.0.0/16`)。
- `policy`: route-map 名 (任意)。`backdoor`: 通常 `false`。

### よくある誤設定

- 対象 prefix が RIB に存在せず広告されない (`network_import_check=true` の既定で必須)。
- `BGP_GLOBALS_AF_AGGREGATE_ADDR` と用途を混同して、集約の代わりに network で多数の prefix を列挙してしまう。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BGP_GLOBALS_AF_NETWORK|*'
vtysh -c "show running-config bgpd" | grep "^ network"
vtysh -c "show ip bgp"
```
<!-- /ops-hint -->

<!-- glossary-links-injected: fcbe746ecf8b -->
