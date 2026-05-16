---
title: SmartSwitch 関連テーブル (MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT)
description: "SmartSwitch NPU-DPU 間ミッドプレーンブリッジおよびポートベース DHCP 割り当てを管理する CONFIG_DB テーブル群。MID_PLANE_BRIDGE、DHCP_SERVER_IPV4_PORT の構造・デフォルト・ハードコード挙動を詳述。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-smart-switch.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-config-engine/config_samples.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MID_PLANE_BRIDGE
    - DHCP_SERVER_IPV4_PORT
    - DHCP_SERVER_IPV4
    - DPUS
    - DEVICE_METADATA
  yang:
    - sonic-smart-switch
    - sonic-dhcp-server-ipv4
---

# SmartSwitch 関連テーブル (MID_PLANE_BRIDGE / DHCP_SERVER_IPV4_PORT)

## 概要

SmartSwitch は SONiC NPU と複数の DPU (Data Processing Unit) を搭載した複合スイッチ筐体。
NPU-DPU 間はミッドプレーンブリッジ (`bridge-midplane`) を介して L2 接続され、DPU への IPv4 割り当ては
DHCP サーバ (`dhcp_server` feature) が `DHCP_SERVER_IPV4_PORT` テーブルを参照してポートごとに固定 IP を払い出す。

SmartSwitch 機能が有効化されるかどうかは `DEVICE_METADATA|localhost.subtype == "SmartSwitch"` で判定される。

---

## MID_PLANE_BRIDGE テーブル

### key 構造

```text
MID_PLANE_BRIDGE|GLOBAL
```

固定のシングルエントリ (`GLOBAL`) のみ。

### フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| `bridge` | string (`"bridge-midplane"` のみ) | - | ミッドプレーンブリッジ名。YANG の `pattern` 制約で `"bridge-midplane"` 固定 |
| `ip_prefix` | IPv4 prefix | - | ブリッジの IP プレフィックス。`bridge` が存在する場合は YANG `must` 制約で必須 |

!!! note "`bridge` フィールドの取りうる値"
    YANG (`sonic-smart-switch.yang:63-69`) の `type string { pattern "bridge-midplane"; }` により、
    `bridge` に設定できる値は `"bridge-midplane"` のみ。デフォルト宣言はなく、エントリ自体が任意だが、
    設定する場合は必ずこの値を使用する。

### 設定例

```json
{
  "MID_PLANE_BRIDGE": {
    "GLOBAL": {
      "bridge": "bridge-midplane",
      "ip_prefix": "169.254.200.254/24"
    }
  }
}
```

### 購読者

- `dhcpservd` (`dhcp_cfggen.py`): `GLOBAL.bridge` / `GLOBAL.ip_prefix` を読み取り DHCP サーバのサブネット設定を生成
- `dhcprelayd` (`dhcprelayd.py`): `GLOBAL.bridge` からブリッジ名を取得し、`DHCP_SERVER_IPV4` のインターフェース照合に使用

---

## DHCP_SERVER_IPV4_PORT テーブル

### key 構造

```text
DHCP_SERVER_IPV4_PORT|<dhcp_interface>|<port>
```

- `<dhcp_interface>`: `DHCP_SERVER_IPV4` のキー（SmartSwitch の場合 `"bridge-midplane"`）
- `<port>`: DPU ミッドプレーンインターフェース名（`dpu0`, `dpu1`, ...）

### フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| `ips` | IPv4 アドレスリスト | ※ | 静的 IP 割り当てリスト。`ranges` と排他 |
| `ranges` | leafref リスト | ※ | IP レンジ名参照リスト。`ips` と排他 |

※ `ips` または `ranges` のどちらか一方が必要。YANG の `must` 制約で両方同時設定は不可。

### SmartSwitch での使用パターン

SmartSwitch では `ips` が使用され、各 DPU に `169.254.200.<dpu_id+1>` が自動割り当てられる:

| エントリキー | `ips` |
|------------|-------|
| `bridge-midplane\|dpu0` | `["169.254.200.1"]` |
| `bridge-midplane\|dpu1` | `["169.254.200.2"]` |
| `bridge-midplane\|dpu2` | `["169.254.200.3"]` |
| `bridge-midplane\|dpu3` | `["169.254.200.4"]` |

```json
{
  "DHCP_SERVER_IPV4_PORT": {
    "bridge-midplane|dpu0": { "ips": ["169.254.200.1"] },
    "bridge-midplane|dpu1": { "ips": ["169.254.200.2"] },
    "bridge-midplane|dpu2": { "ips": ["169.254.200.3"] },
    "bridge-midplane|dpu3": { "ips": ["169.254.200.4"] }
  }
}
```

### 購読者

- `dhcpservd` (`dhcp_cfggen.py`): `DHCP_SERVER_IPV4_PORT` を `_parse_port()` で解析し、`dhcpd.conf` の `host` 節に展開

---

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動

<!-- evidence: meta/_intermediate/cdb-flow/smart-switch-defaults.md -->

### 1. MID_PLANE_BRIDGE|GLOBAL.bridge — YANG pattern で値を固定

YANG (`sonic-smart-switch.yang:63-69`) の定義:

```yang
leaf bridge {
    type string {
        pattern "bridge-midplane";
    }
    must "(current()/../ip_prefix)";
}
```

- `pattern "bridge-midplane"` により設定可能な文字列は `"bridge-midplane"` のみ。
- `default` 宣言はないが、設定する際は値が固定される。
- `must` 制約: `bridge` が存在するなら `ip_prefix` も必須（YANG レベル強制）。

証跡: `sonic-smart-switch.yang:63-69`、`config_samples.py:88`

### 2. MID_PLANE_BRIDGE|GLOBAL.ip_prefix — 事実上のデフォルト `169.254.200.254/24`

YANG に `default` 宣言なし。ただし SmartSwitch 設定生成コード (`config_samples.py:85-94`) でハードコードされる:

```python
mpbr_prefix = '169.254.200'
mpbr_address = '{}.254'.format(mpbr_prefix)  # "169.254.200.254"
data['MID_PLANE_BRIDGE'] = {
    "GLOBAL": {
        "bridge": bridge_name,
        "ip_prefix": "169.254.200.254/24"
    }
}
```

リンクローカル帯 `169.254.200.0/24` を使用。テスト用 mock データも同値。

証跡: `config_samples.py:85-94`、`tests/sample_output/t1-smartswitch.json`

### 3. DHCP_SERVER_IPV4_PORT.ips — DPU ID から計算されるハードコードルール

YANG に `default` 宣言なし。設定生成コード (`config_samples.py:99-103`):

```python
dpu_id = int(midplane_interface.replace('dpu', ''))
dhcp_server_ports['{}|{}'.format(bridge_name, midplane_interface)] = {
    'ips': ['{}.{}'.format(mpbr_prefix, dpu_id + 1)]
}
```

DPU ごとに `169.254.200.<dpu_id+1>` が計算・割り当てられる。これは YANG デフォルトではなく
`config_samples.py` のコード生成ルール。ユーザが手動設定する際は任意の値を指定可能。

証跡: `config_samples.py:99-103`

### 4. smart_switch フラグによるハンドラ分岐

`dhcp_cfggen.py:67, 76, 84` および `dhcprelayd.py:65, 102`:

```python
smart_switch = is_smart_switch(device_metadata)  # DEVICE_METADATA.subtype == "SmartSwitch"
mid_plane, dpus = self._parse_dpu(...) if smart_switch else ({}, {})
if smart_switch and "bridge" in mid_plane and "ip_prefix" in mid_plane:
    # MID_PLANE_BRIDGE の処理を実行
```

`MID_PLANE_BRIDGE` と `DHCP_SERVER_IPV4_PORT` の SmartSwitch 向け処理は `smart_switch` フラグが
`True` の場合のみ実行される。非 SmartSwitch 環境では両テーブルが存在しても DHCP サーバは
これらを SmartSwitch ブリッジとして扱わない。

証跡: `dhcp_cfggen.py:67-90`、`dhcprelayd.py:84-103`

### 5. DPUS.midplane_interface — dpu_name と等値の YANG 強制

YANG (`sonic-smart-switch.yang:94-103`):

```yang
leaf midplane_interface {
    type string { pattern "dpu[0-9]+"; }
    must "(current() = current()/../dpu_name)";
}
```

`must` 制約により `midplane_interface` は常に `dpu_name` と等しい値でなければならない。
これが `DHCP_SERVER_IPV4_PORT` の `port` フィールドへの leafref の根拠となる。

証跡: `sonic-smart-switch.yang:94-103`

### 暗黙デフォルト・乖離サマリー

| # | テーブル | フィールド | YANG default | 実装デフォルト/制約 | 種別 |
|---|---------|-----------|-------------|-------------------|------|
| 1 | MID_PLANE_BRIDGE\|GLOBAL | `bridge` | なし | `"bridge-midplane"` 固定 (YANG pattern 制約) | YANG 制約 |
| 2 | MID_PLANE_BRIDGE\|GLOBAL | `ip_prefix` | なし | `169.254.200.254/24` (`config_samples.py` ハードコード) | 実装デフォルト |
| 3 | DHCP_SERVER_IPV4_PORT | `ips` | なし | `169.254.200.<dpu_id+1>` (`config_samples.py` 計算式) | 実装生成ルール |
| 4 | DPUS | `midplane_interface` | なし | `== dpu_name` (YANG `must` 制約) | YANG 制約 |
| 5 | DHCP_SERVER_IPV4 | `lease_time` | なし | `3600` 秒 (`config_samples.py` ハードコード) | 実装デフォルト |
| 6 | DHCP_SERVER_IPV4 | `gateway` | なし | `169.254.200.254` (mpbr_address 計算値) | 実装生成ルール |

<!-- /defaults -->

---

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `DHCP_SERVER_IPV4`、`DPUS`、`DPU`、`DEVICE_METADATA`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-smart-switch`、`sonic-dhcp-server-ipv4`
- 関連 CLI: SmartSwitch 設定は主に `config_samples.py` / minigraph 経由で自動投入（手動 CLI は限定的）

## 参照

- [SmartSwitch IP アドレス割り当て設計](../../system/smart-switch-ip-address-assignment.md)
- [SmartSwitch データベース設計](../../architecture/smart-switch-database-design.md)
