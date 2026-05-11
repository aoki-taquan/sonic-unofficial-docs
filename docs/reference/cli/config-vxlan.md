---
title: config vxlan サブコマンド
description: "config vxlan サブコマンド — config vxlan は VXLAN VTEP (VXLAN_TUNNEL)、EVPN NVO (VXLAN_EVPN_NVO)、および VLAN-VNI マッピング (VXLAN_TUNNEL_MAP) を管理する。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-utilities
    path: config/vxlan.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - VXLAN_TUNNEL
    - VXLAN_EVPN_NVO
    - VXLAN_TUNNEL_MAP
    - VLAN
    - VNET
    - VRF
  cli:
    - config vxlan
  yang: []
---

# config vxlan サブコマンド

## 概要

`config vxlan` は VXLAN VTEP (`VXLAN_TUNNEL`)、EVPN NVO (`VXLAN_EVPN_NVO`)、および VLAN-VNI マッピング (`VXLAN_TUNNEL_MAP`) を管理する。`config/vxlan.py` に分離されており、`config/main.py` 末尾の `config.add_command(vxlan.vxlan)` で登録される構造[^1]。

VTEP **1 デバイスにつき 1 つだけ**しか作れない（`vxlan add` 時に既存件数 > 0 でエラー）。EVPN NVO も 1 つだけ。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config vxlan add <vxlan_name> <src_ip>` | VTEP を作成 |
| `config vxlan del <vxlan_name>` | VTEP を削除 |
| `config vxlan evpn_nvo add <nvo_name> <vxlan_name>` | EVPN NVO を作成 |
| `config vxlan evpn_nvo del <nvo_name>` | EVPN NVO を削除 |
| `config vxlan map add <vxlan_name> <vlan_id> <vni>` | VLAN-VNI マップを 1 つ作成 |
| `config vxlan map del <vxlan_name> <vlan_id> <vni>` | VLAN-VNI マップを 1 つ削除 |
| `config vxlan map_range add <vxlan_name> <vlan_start> <vlan_end> <vni_start>` | VLAN 範囲をまとめてマップ |
| `config vxlan map_range del <vxlan_name> <vlan_start> <vlan_end> <vni_start>` | VLAN 範囲のマップを削除 |

`-n|--namespace` オプションは `vxlan` グループ全体に必須（`@multi_asic_util.multi_asic_click_option_namespace(required=True)`）。

## 各コマンドの詳細

### `config vxlan add <vxlan_name> <src_ip>`

**動作**:

- `src_ip` を `is_ipaddress` で検証
- `vxlan_name` の長さを `IFACE_NAME_MAX_LEN` でバリデート
- **既存 `VXLAN_TUNNEL` エントリが 1 件でもあればエラー**（VTEP は 1 つ限定）
- `VXLAN_TUNNEL|<vxlan_name>` を `{src_ip: <src_ip>}` で作成

<!-- evidence:
source: sonic-net/sonic-utilities/config/vxlan.py#L19-L51 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  if(vxlan_count > 0):
      ctx.fail("VTEP already configured.")
  fvs = {'src_ip': src_ip}
  config_db.set_entry('VXLAN_TUNNEL', vxlan_name, fvs)
-->

### `config vxlan del <vxlan_name>`

**動作**:
**削除前依存チェック**:

- 当該 VTEP が存在する
- `VXLAN_EVPN_NVO` が空（1 件でも残っているとエラー）
- `VXLAN_TUNNEL_MAP` が空
- `VNET` テーブルでこの VTEP を参照しているエントリが無い

依存が全部解消されていれば `set_entry('VXLAN_TUNNEL', name, None)`。

### `config vxlan evpn_nvo add <nvo_name> <vxlan_name>`

**動作**:

- 既存 `VXLAN_EVPN_NVO` が空であること（NVO も 1 つ限定）
- `<vxlan_name>` で指定された VTEP が存在すること
- `VXLAN_EVPN_NVO|<nvo_name>` を `{source_vtep: <vxlan_name>}` で作成

### `config vxlan evpn_nvo del <nvo_name>`

`VXLAN_TUNNEL_MAP` が空であることを確認した上で `VXLAN_EVPN_NVO|<nvo_name>` を削除。

### `config vxlan map add <vxlan_name> <vlan_id> <vni>`

**動作**:

- `vlan_id` 1-4094, `vni` 1-16777215 をバリデート
- `VXLAN_TUNNEL|<vxlan_name>` の存在確認
- `VLAN|Vlan<vlan_id>` の存在確認
- `VXLAN_TUNNEL_MAP` に同じ vlan / vni が他で使われていないか走査
- key を `<vxlan_name>|map_<vni>_Vlan<vlan_id>` の形で作成、value は `{vni: <vni>, vlan: Vlan<vlan_id>}`

### `config vxlan map del <vxlan_name> <vlan_id> <vni>`

**動作**:

- `<vni>` が `VRF` テーブルから参照されていればエラー（先に VRF VNI 関連付けを外す必要あり）
- key を **2 つのフォーマットで削除**を試みる: `map_<vni>_<vlan_id>` および `map_<vni>_Vlan<vlan_id>`（実装上は両方とも `set_entry(..., None)` で安全側）

### `config vxlan map_range add <vxlan_name> <vlan_start> <vlan_end> <vni_start>`

**動作**:
`vlan_start..vlan_end` まで連続的にループし、各 `vid` に対して `vni_start + (vid - vlan_start)` の VNI を割り当てる。VLAN が存在しなかったり VNI / VLAN がすでにマップ済みの行はスキップ（エラーではない）。各成功エントリは `<vxlan_name>|map_<vni>_Vlan<vid>` で作成。

### `config vxlan map_range del <vxlan_name> <vlan_start> <vlan_end> <vni_start>`

範囲内の各 (vlan, vni) について、**`is_vni_vrf_mapped` が真**（VRF に VNI 紐付け済み）の行のみ削除する仕様[^2]。それ以外の行はスキップしてメッセージを出すだけ。

## 関連する CONFIG_DB

| テーブル | 操作 | 操作するコマンド |
|----------|------|------------------|
| `VXLAN_TUNNEL` | エントリ作成・削除 | `add` / `del` |
| `VXLAN_EVPN_NVO` | エントリ作成・削除 | `evpn_nvo add` / `evpn_nvo del` |
| `VXLAN_TUNNEL_MAP` | エントリ作成・削除 (key 形式 `<tunnel>|map_<vni>_Vlan<id>`) | `map add/del` / `map_range add/del` |

`VLAN` / `VNET` / `VRF` は読み取りのみ（依存チェック）。

## 注意点

- VTEP / NVO は **デバイス 1 つあたり 1 つ限定**
- `map_range del` は VRF 紐付けがある VNI のみ削除する仕様で、削除されない行があっても警告は print のみ。完全削除には `map del` を使う

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`VXLAN_TUNNEL`](../config-db/vxlan-tunnel.md) / [`VXLAN_EVPN_NVO`](../config-db/vxlan-evpn-nvo.md) / [`VXLAN_TUNNEL_MAP`](../config-db/vxlan-tunnel-map.md) / [`VLAN`](../config-db/vlan.md) / [`VNET`](../config-db/vnet.md) / [`VRF`](../config-db/vrf.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `vxlan` グループ全体の定義は `config/vxlan.py` L14-L17。`-n` 必須。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/vxlan.py>

[^2]: `map_range del` の VRF 紐付けスキップは L353-L355。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/vxlan.py#L353>

<!-- usage-example -->
## 実行例

### 典型的な使い方

```bash
# 例 1: VxLAN tunnel と EVPN map を構成
sudo config vxlan add vtep1 10.0.0.1
sudo config vxlan map add vtep1 100 10100
```

### よくある引数の組み合わせ

```bash
sudo config vxlan evpn_nvo add nvo1 vtep1
sudo config vxlan map_range add vtep1 100 200 10100 10200
sudo config vxlan remove vtep1
```

### 期待される出力 (抜粋)

```
VxLAN tunnel vtep1 added.
```
<!-- /usage-example -->

## 関連ページ
- [HLD: VXLAN / VNet 全体設計](../../overlay/vxlan-sonic.md)
- [HLD: EVPN VXLAN](../../routing/evpn-vxlan-hld.md)
- [CONFIG_DB: VXLAN_TUNNEL](../config-db/vxlan-tunnel.md)
- [CONFIG_DB: VXLAN_TUNNEL_MAP](../config-db/vxlan-tunnel-map.md)
- [YANG: sonic-vxlan](../yang/sonic-vxlan.md)
