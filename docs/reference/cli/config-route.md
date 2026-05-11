---
title: config route サブコマンド（static route）
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - STATIC_ROUTE
    - VRF
    - PORTCHANNEL
    - VLAN_INTERFACE
    - INTERFACE
    - VLAN_SUB_INTERFACE
  cli:
    - config route
  yang: []
---

# config route サブコマンド（static route）

## 概要

`config route` は CONFIG_DB の `STATIC_ROUTE` テーブルに対する static route の add / del を行う。FRR の Zebra に対しては `bgpcfgd` 経由で反映される（CLI は CONFIG_DB のみを書く）。コマンドは `cli_sroute_to_config` という共通パーサで CLI トークンを解析し、`STATIC_ROUTE` テーブルのキー (`vrf|prefix` または `prefix`) と value 辞書 (`nexthop` / `nexthop-vrf` / `ifname` / `distance` / `blackhole`) に展開する[^1]。

multi-ASIC 対応として `-n / --namespace` を持ち、対象 namespace の CONFIG_DB に書く。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config route [-n NS] add prefix [vrf <vrf>] <A.B.C.D/M> nexthop [vrf <vrf>] <NH> [dev <intf>]` | 静的経路追加 |
| `config route [-n NS] del prefix [vrf <vrf>] <A.B.C.D/M> [nexthop ...]` | 静的経路削除（特定 nexthop だけ抜く / 全削除） |

## 構文

`add` / `del` 共通の引数構造（`cli_sroute_to_config` の解析対象）:

```
prefix [vrf <vrf_name>] <A.B.C.D/M>
       nexthop [vrf <vrf_name>] <A.B.C.D>
       nexthop [vrf <vrf_name>] dev <dev_name>
       nexthop [vrf <vrf_name>] <A.B.C.D> dev <dev_name>
```

- `vrf` の省略は `default` VRF を意味する。
- ECMP は **`,` 区切り** で複数の nexthop / ifname を 1 文字列に並べることで表現する（CLI 1 回の呼び出しで複数 nexthop を入れる）。
- `dev null` を渡すと `blackhole=true` の経路として登録される（discard route）。

## 各コマンドの詳細

### `config route add prefix ... nexthop ...`

**動作**:

1. `cli_sroute_to_config` が `prefix` / `nexthop` の語をキーに分割し、`ipaddress.ip_network(ip_prefix)` と `ip_address(nh)` で書式検証。
2. `ifname` が指定されたら、`PortChannel*` は `PORTCHANNEL`、`Vlan*` は `VLAN_INTERFACE`、それ以外は `INTERFACE` / `VLAN_SUB_INTERFACE` に該当エントリがあるか確認。`null` のみ「ブラックホール」用として通す。
3. nexthop が `,` 区切り複数の場合、`distance` / `blackhole` も同じ要素数に揃えてカラム化する。`distance` が省略されたら `'0'`、`blackhole` は `ifname=='null'` を見て `'true'` / `'false'` を埋める。
4. 既存エントリがある場合は **値を merge** して `set_entry` で書く（同じ prefix への追加 nexthop は既存に対して append される）。

書き込み先: `STATIC_ROUTE|<vrf>|<prefix>` または `STATIC_ROUTE|<prefix>`（VRF 指定なし）。

<!-- evidence:
source: sonic-net/sonic-utilities/config/main.py#L7812-L7889 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @route.command('add', context_settings={"ignore_unknown_options": True})
  def add_route(ctx, command_str):
      key, route, vrf = cli_sroute_to_config(ctx, command_str)
      ...
      config_db.set_entry("STATIC_ROUTE", key, current_entry)
-->

### `config route del prefix ...`

**動作**:

1. `cli_sroute_to_config(strict_nh=False)` で同じ語句を解析（`nexthop` の省略可）。
2. `nexthop` も `ifname` も指定されない場合は **エントリ全削除**（`set_entry(..., None)`）。
3. 指定された場合は既存エントリの ECMP nexthop リストから当該 tuple を `index` で探して 1 件抜き、残りを再書き込みする。残ゼロなら全削除。
4. 一度に 1 nexthop しか削除できない（`,` 区切り複数を渡すと `Only one nexthop can be deleted at a time` でエラー）。

## 関連する CONFIG_DB

| テーブル | key | フィールド |
|----------|-----|----------|
| `STATIC_ROUTE` | `<vrf>\|<prefix>` または `<prefix>` | `nexthop` / `nexthop-vrf` / `ifname` / `distance` / `blackhole`（すべてカンマ連結文字列） |
| `VRF` | `<vrf_name>` | 参照のみ。`is_vrf_exists` で存在確認 |
| `PORTCHANNEL` / `VLAN_INTERFACE` / `INTERFACE` / `VLAN_SUB_INTERFACE` | `<intf>` | 参照のみ。dev 指定時の存在確認 |

## multi-ASIC

- `-n / --namespace` 必須（multi-ASIC 環境）。
- 各 namespace の CONFIG_DB に対して個別に書く。FRR への反映は namespace 内の `bgpcfgd` が担当する。

## 制限・癖

- ECMP の表現は **CLI 1 行に `,` 区切りで詰め込む** 方式で、設定ファイル系統からは扱いにくい。
- `dev null` 経路は `blackhole=true` として登録される。
- `distance`（admin distance）は CLI 引数として直接は受けない。コードは `,0` をデフォルトで埋めるため、現状 CLI からは distance のカスタマイズは不可。

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`STATIC_ROUTE`](../config-db/static-route.md) / [`VRF`](../config-db/vrf.md) / [`PORTCHANNEL`](../config-db/portchannel.md) / [`VLAN_INTERFACE`](../config-db/vlan-interface.md) / [`INTERFACE`](../config-db/interface.md) / [`VLAN_SUB_INTERFACE`](../config-db/vlan-sub-interface.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `cli_sroute_to_config` の実装は `config/main.py` L1395-L1481。`prefix` / `nexthop` キーを基準に分割し、IP / VRF / interface の存在を検証する。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L1395>
