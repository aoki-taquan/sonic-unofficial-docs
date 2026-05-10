---
title: config vrf サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - VRF
    - MGMT_VRF_CONFIG
    - VXLAN_TUNNEL_MAP
    - SYSLOG_SERVER
  cli:
    - config vrf
    - config interface vrf
  yang: []
---

# config vrf サブコマンド

## 概要

`config vrf` は VRF (Virtual Routing and Forwarding) インスタンスの作成・削除と、L3 VNI マッピング（VXLAN EVPN 用）を提供する。`config/main.py` 内に二重定義があり、上段（L6569）の `vrf` グループは古い定義で実際の `config` 直下に登録されているのは後段（L7673）の `@config.group(cls=clicommon.AbbreviationGroup, name='vrf')`。CONFIG_DB の `VRF` テーブルに対する add/del と、`MGMT_VRF_CONFIG` に対する管理 VRF の有効化を扱う[^1]。

ManagementVRF (`mgmt` / `management`) は通常データプレーン用の `Vrf<name>` とは扱いが異なり、`vrf_add_management_vrf` / `vrf_delete_management_vrf` が `MGMT_VRF_CONFIG` を直接操作する。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config vrf add <vrf_name>` | データ VRF または management VRF を追加 |
| `config vrf del <vrf_name>` | VRF を削除（ヒットする interface IP も全消去） |
| `config vrf add_vrf_vni_map <vrf-name> <vni>` | VRF に L3 VNI を割り当て |
| `config vrf del_vrf_vni_map <vrf-name>` | VRF の VNI マッピングを 0 にリセット |

## 各コマンドの詳細

### `config vrf add <vrf_name>`

**引数**:

- `<vrf_name>` ... `Vrf` で始まる任意名、もしくは `mgmt` / `management`

**動作**:
名前のバリデーション → `Vrf` で始まる、または `mgmt`/`management` のみ許可。`isInterfaceNameValid` で長さ制限（`IFACE_NAME_MAX_LEN`）もチェックする[^2]。

- データ VRF: `VRF|<vrf_name>` を `set_entry(..., {"NULL": "NULL"})` で作成。
- 管理 VRF: `vrf_add_management_vrf` が `MGMT_VRF_CONFIG|vrf_global` の `mgmtVrfEnabled = "true"` を立てる。

既存 VRF を再追加するとエラーで終了する。

<!-- evidence:
source: sonic-net/sonic-utilities/config/main.py#L7682-L7700 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @vrf.command('add')
  def add_vrf(ctx, vrf_name):
      ...
      elif (vrf_name == 'mgmt' or vrf_name == 'management'):
          vrf_add_management_vrf(config_db)
      else:
          config_db.set_entry('VRF', vrf_name, {"NULL": "NULL"})
-->

### `config vrf del <vrf_name>`

**動作**:

1. `SYSLOG_SERVER` テーブルを走査し、`vrf` フィールドが当該 VRF を指すエントリがあれば失敗。
2. `check_dhcpv4_relay_dependencies` で DHCPv4 リレーから参照されていないか確認。
3. `del_interface_bind_to_vrf` で `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` テーブルの該当 IP エントリを連鎖削除。
4. `VRF|<vrf_name>` を `set_entry(None)` で削除。

管理 VRF (`mgmt` / `management`) は `vrf_delete_management_vrf` 経由で `MGMT_VRF_CONFIG` 側を操作する。

### `config vrf add_vrf_vni_map <vrf-name> <vni>`

**動作**:

- 対象 VRF が `VRF` テーブルにあること
- `vni` が数値かつ `clicommon.vni_id_is_valid` (1 - 16777215)
- `VXLAN_TUNNEL_MAP` テーブル内に同じ VNI を持つ VLAN-VNI マップが既に存在していること（先に作成しておくこと）
- 同じ VNI が他の VRF に既に割り当てられていないこと

すべて満たしたら `mod_entry('VRF', vrfname, {"vni": vni})` で `VRF|<vrf>` の `vni` フィールドを更新する。

### `config vrf del_vrf_vni_map <vrf-name>`

`VRF|<vrf>` の `vni` を `0` に設定（エントリ削除ではなく値リセット）。

## 関連する CONFIG_DB

| テーブル | key | フィールド | 操作 |
|----------|-----|----------|------|
| `VRF` | `<vrf_name>` (`Vrf*`) | `NULL` (placeholder) / `vni` | add / del / add_vrf_vni_map / del_vrf_vni_map |
| `MGMT_VRF_CONFIG` | `vrf_global` | `mgmtVrfEnabled` | `mgmt` / `management` 名での add / del |
| `VXLAN_TUNNEL_MAP` | `<map>` | `vni` (依存) | `add_vrf_vni_map` の事前条件 |
| `SYSLOG_SERVER` | `<host>` | `vrf` (依存) | `del` の安全性チェック |

## 制約

- VRF 名は `Vrf` プレフィックス、または `mgmt` / `management` の固定名のみ。
- ManagementVRF と Data VRF は内部の格納先テーブルが異なるが、CLI 上では同じ `config vrf add` で透過に扱える。
- `del` は IP・SYSLOG・DHCPv4 relay から参照されている VRF を拒否する（依存解消が先）。

## 引用元

[^1]: `config vrf` グループの正式な登録は `config/main.py` L7673。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L7673>

[^2]: VRF 名のバリデータ `isInterfaceNameValid` と `IFACE_NAME_MAX_LEN` は `config/main.py` 上部のヘルパで定義される。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py>

## 関連ページ
- [HLD: VRF サポート](../../routing/sonic-vrf-support-design-spec-draft.md)
- [CONFIG_DB: VRF](../config-db/vrf.md)
- [CONFIG_DB: MGMT_VRF_CONFIG](../config-db/mgmt-vrf-config.md)
- [YANG: sonic-vrf](../yang/sonic-vrf.md)
