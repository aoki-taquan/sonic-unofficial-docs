---
title: SmartSwitch DPU テーブル群
description: "SmartSwitch DPU 関連 CONFIG_DB テーブル — MID_PLANE_BRIDGE / DPUS / DPU / REMOTE_DPU / VDPU / DASH_HA_GLOBAL_CONFIG の構造・デフォルト・挙動を解説する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-smart-switch.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-config-engine/config_samples.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-config-engine/smartswitch_config.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: platform/mellanox/mlnx-platform-api/sonic_platform/module.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MID_PLANE_BRIDGE
    - DPUS
    - DPU
    - REMOTE_DPU
    - VDPU
    - DASH_HA_GLOBAL_CONFIG
    - DEVICE_METADATA
    - CHASSIS_MODULE
  yang:
    - sonic-smart-switch
---

# SmartSwitch DPU テーブル群

## 概要

SmartSwitch は NPU（スイッチ本体）に DPU（Data Processing Unit）を搭載した SONiC プラットフォームである。[CONFIG_DB](../../reference/glossary.md#term-config_db) には DPU の接続・アドレス・HA（High Availability）設定を保持する複数テーブルが存在する[^1]。

テーブル一覧:

| テーブル | 役割 |
|---------|------|
| `MID_PLANE_BRIDGE` | NPU〜DPU 間ミッドプレーンブリッジの IP 設定 |
| `DPUS` | DPU 名とミッドプレーンインターフェースのマッピング |
| `DPU` | 各 DPU の詳細設定（アドレス・サービスポート等）|
| `REMOTE_DPU` | ピア SmartSwitch 上のリモート DPU 情報 |
| `VDPU` | 複数 DPU を束ねる仮想 DPU 定義 |
| `DASH_HA_GLOBAL_CONFIG` | DPU 間 HA データパス・BFD のグローバル設定 |

<!-- cdb-mermaid -->
### データフロー

```mermaid
flowchart LR
  MG["minigraph /\nplatform.json"]
  CFGGEN["sonic-cfggen\n(config_samples.py)"]
  CDB[("CONFIG_DB\nMID_PLANE_BRIDGE\nDPUS / DPU")]
  DHCPD["dhcp_server\n(bridge-midplane)"]
  DASHHA["dashhaorch\n(orchagent)"]
  HACFG[("CONFIG_DB\nDASH_HA_GLOBAL_CONFIG")]

  MG --> CFGGEN
  CFGGEN --> CDB
  CDB --> DHCPD
  HACFG --> DASHHA
```

!!! note "凡例"
    `sonic-cfggen` が platform.json と minigraph から DPU 設定を生成して CONFIG_DB に書き込む。DHCP サーバーはミッドプレーンブリッジ経由で各 DPU に IP を払い出す。
<!-- /cdb-mermaid -->

---

## MID_PLANE_BRIDGE テーブル

### key 構造

```text
MID_PLANE_BRIDGE|GLOBAL
```

### フィールド

| フィールド | 型 | 範囲 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `bridge` | string | `bridge-midplane` のみ | `"bridge-midplane"` | ミッドプレーンブリッジ名（YANG で固定）|
| `ip_prefix` | IPv4 prefix | 任意 | `"169.254.200.254/24"` | ブリッジの IPv4 プレフィックス |

---

## DPUS テーブル

### key 構造

```text
DPUS|<dpu_name>
```

`<dpu_name>` は `dpu[0-9]+` パターン（例: `dpu0`, `dpu1`）。

### フィールド

| フィールド | 型 | 範囲 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `midplane_interface` | string | `dpu[0-9]+` | `<dpu_name>` と同値 | DPU に対応するミッドプレーンインターフェース名 |

---

## DPU テーブル

### key 構造

```text
DPU|<dpu_name>
```

`<dpu_name>` は `[a-zA-Z0-9_-]+[0-9]` パターン、最大 255 文字。

### フィールド

| フィールド | 型 | 範囲 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `state` | `admin_status` | `up` / `down` | なし | DPU の管理状態 |
| `local_port` | `interface_name` | — | なし | NPU 側の物理ポート名 |
| `vip_ipv4` | IPv4 address | — | なし | VIP IPv4（minigraph 由来）|
| `vip_ipv6` | IPv6 address | — | なし | VIP IPv6（minigraph 由来）|
| `pa_ipv4` | IPv4 address | — | なし | PA IPv4（minigraph 由来）|
| `pa_ipv6` | IPv6 address | — | なし | PA IPv6（minigraph 由来）|
| `midplane_ipv4` | IPv4 address | — | `169.254.200.(dpu_id+1)` | ミッドプレーン IPv4（platform 計算値）|
| `dpu_id` | string | `[0-7]` | なし | DPU ID（minigraph 由来）|
| `vdpu_id` | string | 1..255 文字 | なし | 所属 VDPU の guid（minigraph 由来）|
| `gnmi_port` | port-number | 1..65535 | なし（実例: `50052`）| gNMI サービスの TCP ポート |
| `orchagent_zmq_port` | port-number | 1..65535 | なし（実例: `50`）| ZMQ サービスの TCP ポート |
| `swbus_port` | port-number | 1..65535 | なし（実例: `23607`）| swbus サービスの TCP ポート |

---

## REMOTE_DPU テーブル

### key 構造

```text
REMOTE_DPU|<dpu_name>
```

ピア SmartSwitch 上の DPU を表す。`<dpu_name>` は `[a-zA-Z0-9_-]+[0-9]+` パターン。

### フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `type` | string 1..255 | DPU 種別 |
| `pa_ipv4` | IPv4 address | DPU の PA IPv4 |
| `pa_ipv6` | IPv6 address | DPU の PA IPv6 |
| `npu_ipv4` | IPv4 address | リモート NPU のループバック IPv4 |
| `npu_ipv6` | IPv6 address | リモート NPU のループバック IPv6 |
| `dpu_id` | string `[0-7]` | DPU ID |
| `swbus_port` | port-number | swbus サービスの TCP ポート |

---

## VDPU テーブル

### key 構造

```text
VDPU|<vdpu_id>
```

`<vdpu_id>` は VDPU の guid 文字列（1..255 文字）。

### フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `profile` | string 1..255 | VDPU プロファイル（将来用、現在未使用）|
| `tier` | string 1..255 | VDPU ティア（将来用、現在未使用）|
| `main_dpu_ids` | string | この VDPU に属する DPU 名（カンマ区切り）|

---

## DASH_HA_GLOBAL_CONFIG テーブル

### key 構造

```text
DASH_HA_GLOBAL_CONFIG|global
```

### フィールド

| フィールド | 型 | 実例値 | 説明 |
|-----------|----|--------|------|
| `vnet_name` | leafref (VNET) | — | **deprecated**。`dpu_vnet` を使用すること |
| `dpu_vnet` | leafref (VNET) | — | VNET トンネルルートで使用する vnet 名 |
| `dpu_vlan` | string 1..255 | — | DPU VLAN 識別子 |
| `cp_data_channel_port` | port-number | `11362` | コントロールプレーンデータチャネルポート（バルク同期用）|
| `dp_channel_dst_port` | port-number | `11368` | DPU 間データプレーンチャネルのトンネル宛先ポート |
| `dp_channel_src_port_min` | port-number | `49152` | データプレーンチャネルの最小送信元ポート |
| `dp_channel_src_port_max` | port-number | `53247` | データプレーンチャネルの最大送信元ポート |
| `dp_channel_probe_interval_ms` | uint32 | `100` | DPU 間データパスプローブ送信間隔（ミリ秒）|
| `dp_channel_probe_fail_threshold` | uint32 | `3` | データプレーンチャネル断判定に必要な連続失敗回数 |
| `dpu_bfd_probe_interval_in_ms` | uint32 | `100` | DPU BFD プローブ送信間隔（ミリ秒）|
| `dpu_bfd_probe_multiplier` | uint32 | `3` | DPU BFD プローブ失敗判定の乗数 |

---

## 暗黙デフォルト・コード由来挙動

<!-- defaults -->

### MID_PLANE_BRIDGE — 固定値の由来

`bridge` および `ip_prefix` の値は `sonic-cfggen` の `config_samples.py` でハードコードされている:

```python
# src/sonic-config-engine/config_samples.py:88-94
bridge_name = 'bridge-midplane'
data['MID_PLANE_BRIDGE'] = {
    "GLOBAL": {
        "bridge": bridge_name,
        "ip_prefix": "169.254.200.254/24"
    }
}
```

- `bridge` は YANG パターン制約 (`pattern "bridge-midplane"`) により他の値を設定不可
- `ip_prefix` の `169.254.200.254/24` は link-local ではなく APIPA 近接帯の固定アドレスブロック
- YANG の `must "(current()/../ip_prefix)"` 制約により、`ip_prefix` なしの `bridge` 設定は YANG バリデーション違反

### DPUS — midplane_interface は dpu_name と同値

YANG モデルに `must` 制約があり `midplane_interface` は必ず `dpu_name` と同値になる:

```yang
# sonic-smart-switch.yang:101
must "(current() = current()/../dpu_name)";
```

これにより `DPUS|dpu0` エントリの `midplane_interface` は常に `"dpu0"` となる。

### DPU — midplane_ipv4 のプラットフォーム計算値

Mellanox platform 実装では `midplane_ipv4` を `dpu_id` から計算する:

```python
# platform/mellanox/mlnx-platform-api/sonic_platform/module.py:490
return f"169.254.200.{int(self.dpu_id) + 1}"
# dpu_id=0 → 169.254.200.1
# dpu_id=1 → 169.254.200.2
# dpu_id=7 → 169.254.200.8
```

ゲートウェイ（NPU 側: `169.254.200.254`）と DPU 割り当て（`.1`〜`.8`）で同一 `/24` を共有する。この計算ロジックは Mellanox 固有であり、他ベンダー platform では異なる可能性がある。

DHCP サーバーへの IP 払い出しも同一規則に従う:

```python
# config_samples.py:102-103
dpu_id = int(midplane_interface.replace('dpu', ''))
dhcp_server_ports[...] = {'ips': ['{}.{}'.format(mpbr_prefix, dpu_id + 1)]}
```

### DPU — サービスポートのデフォルトなし

`gnmi_port`, `orchagent_zmq_port`, `swbus_port` は YANG に `default` 定義がなく、minigraph または `platform.json` からの書き込み値のみが有効である。テスト実例で観察される値（`gnmi_port=50052`, `orchagent_zmq_port=50`, `swbus_port=23607`）はリファレンスであり、platform・ベンダーによって異なる。

### DASH_HA_GLOBAL_CONFIG — テスト実例値の位置付け

すべてのフィールドが YANG の `default` 定義を持たない。`sonic-yang-models/tests/files/sample_config_db.json` に以下のテスト実例値が存在する:

```json
"DASH_HA_GLOBAL_CONFIG": {
  "global": {
    "cp_data_channel_port": "11362",
    "dp_channel_dst_port": "11368",
    "dp_channel_src_port_min": "49152",
    "dp_channel_src_port_max": "53247",
    "dp_channel_probe_interval_ms": "100",
    "dp_channel_probe_fail_threshold": "3",
    "dpu_bfd_probe_interval_in_ms": "100",
    "dpu_bfd_probe_multiplier": "3"
  }
}
```

`dp_channel_src_port_min: 49152` は Linux エフェメラルポート範囲開始と一致。`dp_channel_src_port_max: 53247` = 49152 + 4095（4096 ポート幅）。

### vnet_name の非推奨化

YANG revision 2025-07-20 で `dpu_vnet` が追加され、`vnet_name` は `status deprecated` に変更された。既存設定で `vnet_name` を使用している場合は `dpu_vnet` へ移行すること:

```yang
# sonic-smart-switch.yang:289-295
leaf vnet_name {
    status deprecated;
    description "Deprecated. Use dpu_vnet instead. Name of the vnet used for VNET tunnel route.";
    ...
}
```

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`dhcp_cfggen` (`dhcpservd`) は `generate()` 呼び出しごとに CONFIG_DB を全量読み直してミッドプレーン DHCP 設定を再生成する。このため書き込み順序がミッドプレーンブリッジの DHCP 払い出し動作に直結する。

### 他テーブル先行必須

| 先行テーブル / フィールド | 理由 | 違反時の挙動 |
|---|---|---|
| `DEVICE_METADATA\|localhost.subtype = "SmartSwitch"` | `is_smart_switch()` チェックで `False` になると `MID_PLANE_BRIDGE` / `DPUS` を完全無視 | ミッドプレーン DHCP 設定が生成されず DPU への IP 払い出し停止（`dhcp_cfggen.py:67,76`） |
| `MID_PLANE_BRIDGE\|GLOBAL` (`bridge` + `ip_prefix` 両フィールド) | `dhcp_cfggen.py:84` で両フィールドの存在を明示チェック。どちらか欠如すると `dhcp_interfaces` にブリッジが登録されない | `DPUS` エントリが存在しても処理スキップ。DPU への IP 割当なし |
| `VNET\|<vnet_name>` (→ `DASH_HA_GLOBAL_CONFIG.dpu_vnet`) | YANG `leafref` 制約。`VNET` エントリが先行していないと YANG バリデーション違反 | CLI 経由の書き込みは `ctx.fail()` で拒否 |

### 推奨書込み順序（ビルド時 / 手動設定共通）

```
# 1. デバイス種別の確定
SET DEVICE_METADATA|localhost  subtype=SmartSwitch

# 2. ミッドプレーンブリッジの定義
SET MID_PLANE_BRIDGE|GLOBAL  bridge=bridge-midplane  ip_prefix=169.254.200.254/24

# 3. DPU エントリの登録（複数ある場合は natsorted 順）
SET DPUS|dpu0  midplane_interface=dpu0
SET DPUS|dpu1  midplane_interface=dpu1
...

# 4. DHCP サーバー設定（DHCP_SERVER_IPV4 / DHCP_SERVER_IPV4_PORT）
SET DHCP_SERVER_IPV4|bridge-midplane  ...
SET DHCP_SERVER_IPV4_PORT|bridge-midplane|dpu0  ...

# 5. DASH HA 設定（VNET が先行していること）
SET DASH_HA_GLOBAL_CONFIG|global  dpu_vnet=<vnet_name>  ...
```

`config_samples.py:81-151` (`generate_t1_smartswitch_switch_sample_config`) はこの順序を自動保証している。

### ランタイム変更の反映タイミング

- `DPUS` の変更は `DpusTableEventChecker` が無条件にトリガー → dhcpservd 再生成 → kea-dhcp4 SIGHUP（最大 5000 ms ポーリング待ち）
- `MID_PLANE_BRIDGE` の変更は `MidPlaneTableEventChecker` が `bridge` フィールドを `enabled_dhcp_interfaces` と照合してから再生成をトリガー
- `DPU` / `REMOTE_DPU` / `VDPU` は dhcpservd の購読対象外。変更は dashhaorch / sonic-gnmi が別途処理する

> **Evidence**: `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:65-100`; `common/dhcp_db_monitor.py:349-386`; `src/sonic-config-engine/config_samples.py:81-151`; `src/sonic-dhcp-utilities/dhcp_utilities/common/utils.py:153-161`
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照 — Phase C (cross-table refs)

> **調査根拠**: `src/sonic-yang-models/yang-models/sonic-smart-switch.yang` 全行精読; `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:60-100`; `src/sonic-dhcp-utilities/dhcp_utilities/common/utils.py:153-161`; `src/sonic-config-engine/config_samples.py:80-157`; `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:355,749,1143,1187,1245-1270` (2026-05-17)
> 詳細証跡: `meta/_intermediate/cdb-flow/smart-switch-dpu-cross-refs.md`

各テーブルは YANG leafref の有無とは独立して、実装レベルで以下のテーブルを暗黙参照する。

### MID_PLANE_BRIDGE / DPUS の暗黙参照

| 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `DEVICE_METADATA\|localhost` (`subtype`) | CONFIG_DB | 読み取り (`is_smart_switch()` 判定) | なし | 必須（`"SmartSwitch"` でない場合 `MID_PLANE_BRIDGE`/`DPUS` を完全スキップ）| `dhcp_cfggen.py:65-67`; `utils.py:153-161` |
| `DHCP_SERVER_IPV4\|bridge-midplane` | CONFIG_DB | 書き込み (初期設定で自動生成) | なし | 派生（`config_samples.py` が `DPUS` エントリから自動生成）| `config_samples.py:133-143` |
| `DHCP_SERVER_IPV4_PORT\|bridge-midplane\|<dpu>` | CONFIG_DB | 書き込み (初期設定で自動生成) | なし | 派生（`DPUS` の `midplane_interface` から DPU ごとに生成）| `config_samples.py:105-109` |
| `FEATURE\|dhcp_server` | CONFIG_DB | 書き込み (初期設定で有効化) | なし | 派生（`DPUS` が存在する場合のみ生成）| `config_samples.py:113-131` |

#### DEVICE_METADATA.localhost.subtype — SmartSwitch 判定ゲート

`dhcp_cfggen.py:65-67` が `DEVICE_METADATA|localhost.subtype` を読み取り `is_smart_switch()` を呼ぶ (`utils.py:153-161`)。`subtype != "SmartSwitch"` の場合、`_parse_dpu()` が呼ばれず `MID_PLANE_BRIDGE` / `DPUS` テーブルの内容が完全に無視される。DPU への IP 払い出しは発生しない。

#### DHCP_SERVER_IPV4 / DHCP_SERVER_IPV4_PORT — DPUS から自動生成

`config_samples.py:105-143` は `DPUS` 内の各エントリから `DHCP_SERVER_IPV4_PORT|bridge-midplane|<midplane_interface>` を生成し、`DHCP_SERVER_IPV4|bridge-midplane` を `MODE=PORT` で設定する。`DPUS` が空の場合、これらのテーブルは生成されない。

---

### DASH_HA_GLOBAL_CONFIG の暗黙参照

| 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `VNET\|<name>` | CONFIG_DB | 読み取り (`dpu_vnet` / `vnet_name` の存在確認) | **あり** (`leafref`) | 条件付き必須（DASH HA 設定時。不在で YANG バリデーション違反）| `sonic-smart-switch.yang:292-303` |

#### VNET — YANG leafref による強制参照

`sonic-smart-switch.yang:291-303` は `DASH_HA_GLOBAL_CONFIG.global.vnet_name`（deprecated）と `dpu_vnet` の両フィールドを `VNET` テーブルへの `leafref` として定義する。`VNET|<name>` エントリが存在しない状態で `dpu_vnet` を書き込もうとすると、YANG バリデーションエラーが発生し CLI 経由の書き込みは拒否される。

---

### DPU / REMOTE_DPU / VDPU の暗黙参照

| 参照先 | DB | 参照方向 | YANG leafref | 実装上の必須度 | 証拠 |
|---|---|---|---|---|---|
| `DEVICE_METADATA\|localhost` (`switch_type = "dpu"`) | CONFIG_DB | 書き込み (DPU 側 config_samples) | なし | DPU 専用（DPU デバイスとして識別させる）| `config_samples.py:154-157` |
| `PORT\|*` | CONFIG_DB | 読み取り (DPU 側 chassisd dataplane state 判定) | なし | DPU 側のみ（NPU 側 chassisd は不参照）| `chassisd:1265-1272` |
| `CHASSIS_MODULE\|DPU*` | CONFIG_DB | 読み書き (chassisd による DPU admin state 制御) | なし | 必須（DPU モジュール管理）| `chassisd:44,355,749` |

#### CHASSIS_MODULE — chassisd による DPU 管理

`chassisd` は `CHASSIS_MODULE` テーブル（`CHASSIS_CFG_TABLE = "CHASSIS_MODULE"`）を唯一の CONFIG_DB 参照先として DPU の admin state を制御する（`chassisd:355,749,1143`）。`DPU` / `DPUS` テーブルを直接参照しない。DPU の物理状態は `CHASSIS_STATE_DB.DPU_STATE` テーブル経由で管理される。

### SAI 参照

`MID_PLANE_BRIDGE` / `DPUS` / `DPU` / `REMOTE_DPU` / `VDPU` はいずれも SAI を直接操作しない。`DASH_HA_GLOBAL_CONFIG` は `dashhaorch` (orchagent) 経由で DASH SAI に設定を渡すが、orchagent の SAI 呼び出し詳細は DASH 固有実装に依存する。
<!-- /cross-refs -->

## 制約

- `MID_PLANE_BRIDGE|GLOBAL` の `bridge` は `bridge-midplane` 固定。変更不可。
- `DPUS` の `dpu_name` および `midplane_interface` は `dpu[0-9]+` パターン必須。
- `DPU` の `dpu_id` は `[0-7]`（0〜7 の 1 文字）のみ。8 以上の DPU ID は YANG バリデーション違反。
- `REMOTE_DPU` の `dpu_id` も同様に `[0-7]` 制約。
- `DASH_HA_GLOBAL_CONFIG` の `vnet_name` は deprecated であり、YANG `leafref` によって `VNET` テーブル内の既存エントリのみ参照可能。

## 書き込み入り口

### sonic-cfggen（ビルド時 / 初期設定）

```python
# config_samples.py:81-106
# generate_t1_smartswitch_switch_sample_config() が
# MID_PLANE_BRIDGE, DPUS, DHCP_SERVER_IPV4 を生成
```

- `MID_PLANE_BRIDGE|GLOBAL`、`DPUS|dpu*` はビルド時 config_samples.py が生成
- `DPU|<name>` は minigraph から `sonic-cfggen` が展開

### minigraph パーサ

`DPU` テーブルの `vip_ipv4`, `pa_ipv4`, `dpu_id`, `vdpu_id`, `gnmi_port`, `orchagent_zmq_port`, `swbus_port` は minigraph XML の DPU セクションから読み込まれる。

### 直接操作（CONFIG_DB CLI / REST）

`sonic-db-cli CONFIG_DB` または `config` CLI から手動設定も可能だが、通常は自動生成設定を使用する。

## 購読者

| コンポーネント | 購読テーブル | 処理内容 |
|--------------|------------|---------|
| `dhcp_server` | `MID_PLANE_BRIDGE`, `DPUS` | ミッドプレーンブリッジ上の DHCP サービス設定 |
| `chassisd` | `CHASSIS_MODULE` | DPU の admin state 制御（CHASSIS_MODULE テーブル経由）|
| `dashhaorch` (orchagent) | `DASH_HA_GLOBAL_CONFIG` | DASH HA データパス設定を SAI に反映 |
| `sonic-gnmi` | `DPU` | DPU gNMI エンドポイント接続 |

## 関連 CONFIG_DB / YANG

- 関連 CONFIG_DB: `CHASSIS_MODULE`（DPU の admin state）、`DEVICE_METADATA`（`subtype: SmartSwitch`）
- 関連 YANG: `sonic-smart-switch`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: `sonic-smart-switch` (`src/sonic-yang-models/yang-models/sonic-smart-switch.yang`)
- CONFIG_DB: [`CHASSIS_MODULE`](chassis-module.md)（DPU モジュール管理状態）
- CONFIG_DB: [`DEVICE_METADATA`](device-metadata.md)（`subtype: SmartSwitch` 設定）

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-smart-switch.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-smart-switch.yang>
