---
title: DPU / ENI / VDPU / REMOTE_DPU テーブル
description: "CONFIG_DB の DPU・ENI・VDPU・REMOTE_DPU テーブル — SmartSwitch の DPU (Data Processing Unit) と ENI (Elastic Network Interface) の転送情報を定義し、DashEniFwdOrch が ACL ルールへ変換する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/dash/dashenifwdorch.h
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/dash/dashenifwdorch.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: tests/mock_tests/dashenifwdorch_ut.cpp
    ref: HEAD
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-config-engine/smartswitch_config.py
    ref: HEAD
  - repo: sonic-net/SONiC
    path: doc/smart-switch/high-availability/eni-based-forwarding.md
    ref: HEAD
related:
  config_db:
    - DPU
    - REMOTE_DPU
    - VDPU
    - ENI
    - DPUS
    - VIP_TABLE
  cli: []
  yang: []
---

# DPU / ENI / VDPU / REMOTE_DPU テーブル

## 概要

SmartSwitch において NPU から DPU (Data Processing Unit) へのパケット転送を実現する 5 テーブル群。ENI (Elastic Network Interface) Based Forwarding アーキテクチャの構成情報を保持し、`DashEniFwdOrch` が読み出して ACL ルール (`ENI:*`) へ変換する。

- **`DPU`**: ローカル DPU (同一 SmartSwitch 内) のエンドポイント情報
- **`REMOTE_DPU`**: リモート DPU (クラスタ内他 SmartSwitch) のエンドポイント情報
- **`VDPU`**: 仮想 DPU。複数の DPU/REMOTE_DPU をグループ化する抽象レイヤ
- **`ENI`**: DASH_ENI_FORWARD_TABLE 経由で HaMgrd が書き込む ENI-VDPU マッピング (APPL_DB)
- **`DPUS`**: SmartSwitch プラットフォーム定義 (platform.json から config-engine が投入)

!!! warning "YANG 未定義"
    これらのテーブルはすべて YANG モジュールで未定義。スキーマの正本は `sonic-swss/orchagent/dash/dashenifwdorch.h` (フィールド定数定義) と `dashenifwdorch.cpp` (parse ロジック)。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB_DPU[("CONFIG_DB<br/>DPU / REMOTE_DPU / VDPU")]
  APPL_ENI[("APPL_DB<br/>DASH_ENI_FORWARD_TABLE")]
  HaMgrd["HaMgrd"]
  Orch["DashEniFwdOrch<br/>(orchagent)"]
  ACL[("APPL_DB<br/>ACL_RULE_TABLE")]
  SAI["SAI / ASIC"]

  HaMgrd --> APPL_ENI
  CDB_DPU --> Orch
  APPL_ENI --> Orch
  Orch --> ACL --> SAI
```

!!! note "凡例"
    `DPU` / `REMOTE_DPU` / `VDPU` はシステム起動時に一度読み出され `DpuRegistry` に格納される。`DASH_ENI_FORWARD_TABLE` は HaMgrd がリアルタイムに更新し、DashEniFwdOrch が ACL ルールへ変換する。
<!-- /cdb-mermaid -->

## テーブル構造

### DPU テーブル

ローカル DPU (同一 SmartSwitch カード内の DPU) のエンドポイント情報。

```text
DPU|<dpu_name>
```

`<dpu_name>`: 任意の DPU 識別名 (例: `dpu0`, `local_dpu`)

| フィールド | 型 | 必須 | 説明 |
|----------|----|------|------|
| `pa_ipv4` | IPv4 アドレス (string) | **必須** | DPU の Physical Address (PA)。ローカル NextHop として使用 |
| `pa_ipv6` | IPv6 アドレス (string) | 省略可 | DPU の PA IPv6 アドレス |
| `state` | enum string | 省略可 | `"up"` または `"down"`。`"down"` の場合は DpuRegistry へ登録されない |

`state` フィールドが `"down"` の DPU は `processDpuTable()` でスキップされる。それ以外 (未指定・`"up"`) は `dpu_type_t::LOCAL` として登録される。

### REMOTE_DPU テーブル

リモート DPU (クラスタ内他 SmartSwitch の DPU) のエンドポイント情報。

```text
REMOTE_DPU|<dpu_name>
```

| フィールド | 型 | 必須 | 説明 |
|----------|----|------|------|
| `pa_ipv4` | IPv4 アドレス (string) | **必須** | リモート DPU の PA。VxLAN トンネルの内部 NH として使用 |
| `pa_ipv6` | IPv6 アドレス (string) | 省略可 | リモート DPU の PA IPv6 アドレス |
| `npu_ipv4` | IPv4 アドレス (string) | **必須** | リモート SmartSwitch の NPU IP。VxLAN トンネルの宛先 (outer IP) |
| `npu_ipv6` | IPv6 アドレス (string) | 省略可 | リモート SmartSwitch の NPU IPv6 アドレス |

REMOTE_DPU は `dpu_type_t::CLUSTER` として登録される。必須フィールド (`pa_ipv4`, `npu_ipv4`) が欠けると `Request::parse()` が例外を投げてスキップされる。

### VDPU テーブル

Virtual DPU。DPU または REMOTE_DPU をグループ化し、ENI に対して VDPU ID 単位で primary/secondary を指定できる抽象レイヤ。

```text
VDPU|<vdpu_name>
```

| フィールド | 型 | 必須 | 説明 |
|----------|----|------|------|
| `main_dpu_ids` | コンマ区切り string | **必須** | この VDPU が束ねる DPU 名のリスト (例: `"dpu0,dpu1"`) |

VDPU は `DPU` / `REMOTE_DPU` テーブルを populate した後に処理される。`main_dpu_ids` に含まれる名前が `dpus_name_map_` に存在しない場合は警告ログを出力してスキップ。

### ENI (DASH_ENI_FORWARD_TABLE)

ENI-to-VDPU マッピング。CONFIG_DB テーブルではなく APPL_DB の `DASH_ENI_FORWARD_TABLE` として管理される。HaMgrd が書き込み、`DashEniFwdOrch` が購読して ACL ルールへ変換する。

```text
DASH_ENI_FORWARD_TABLE|<vnet_name>:<mac_address>
```

| フィールド | 型 | 必須 | 説明 |
|----------|----|------|------|
| `vdpu_ids` | コンマ区切り string | **必須** | ENI に関連する VDPU 名のリスト (例: `"vdpu0,vdpu1"`) |
| `primary_vdpu` | string | **必須** | プライマリ VDPU 名。ACL ルールの redirect 先となる DPU を決定 |

### DPUS テーブル

SmartSwitch プラットフォーム定義。`platform.json` から `sonic-config-engine/smartswitch_config.py` が CONFIG_DB へ投入する。

```text
DPUS|<dpu_name>
```

| フィールド | 型 | 必須 | 説明 |
|----------|----|------|------|
| `midplane_interface` | string | **必須** | DPU の midplane インタフェース名 (例: `"dpu0"`)。DHCP サーバが DHCP ポート割り当てに使用 |

## 関連動作: DashEniFwdOrch の ACL 変換

`DashEniFwdOrch` は lazy init でシステム起動後に一度だけ `DpuRegistry::populate()` を呼び出し、`DPU` / `REMOTE_DPU` / `VDPU` を読み込む。その後、`DASH_ENI_FORWARD_TABLE` エントリが届くたびに以下の ACL ルールを生成する。

| ケース | ACL ルールキー | Redirect 先 | Tunnel Termination |
|--------|-------------|-------------|-------------------|
| `primary_vdpu` が LOCAL DPU | `ENI:<vnet>_<MAC>` | ローカル PA_V4 (隣接解決後の OID) | あり (`<MAC>_TERM`) |
| `primary_vdpu` が CLUSTER DPU | `ENI:<vnet>_<MAC>` | `<NPU_V4>@<tunnel>,<VNI>` | なし (T1 非ホスト ENI) |

優先度は BASE_PRIORITY = 9996、Tunnel Termination ルールは +1 = 9997。

## 購読者

- `DashEniFwdOrch` (`sonic-swss/orchagent/dash/dashenifwdorch.cpp`): `DASH_ENI_FORWARD_TABLE` を購読。起動時に `DPU` / `REMOTE_DPU` / `VDPU` を読み込み `DpuRegistry` を構築。ACL ルールを `APPL_DB:ACL_RULE_TABLE` へ書き込む
- `dhcpservd` (`sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py`): `DPUS` テーブルの `midplane_interface` を DHCP サーバのポート割り当てに使用

## 関連 CONFIG_DB / CLI

- 関連 CONFIG_DB: [`DASH_ACL_*`](dash-acl.md)

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| `DPU.state == "down"` | `processDpuTable()` でスキップ。DpuRegistry に登録されない |
| `DPU.pa_ipv4` 未指定 | `Request::parse()` が例外 → `SWSS_LOG_ERROR("Failed to parse key")` |
| `REMOTE_DPU.pa_ipv4` または `npu_ipv4` 未指定 | 同上 |
| `VDPU.main_dpu_ids` に未知 DPU 名を含む | `SWSS_LOG_WARN("Invalid DPU ID")` でその DPU のみスキップ |
| `VDPU.main_dpu_ids` に `state=down` DPU | down DPU は `dpus_name_map_` に未登録のためスキップ |
| LOCAL NH が未解決 (Neighbor Down) | ACL ルール未インストール。Neighbor Up 通知受信後に再試行 |
| ENI の両 VDPU がリモート | Tunnel Termination ルールなし (T1 非ホスト ENI) |
<!-- /cdb-exceptions -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `DPU.state` (enum string)

| 値 | DpuRegistry への登録 | dpu_type | evidence |
|----|---------------------|----------|---------|
| 未指定 | 登録される (`LOCAL`) | `LOCAL` | `dashenifwdorch.cpp:241-253` |
| `"up"` | 登録される (`LOCAL`) | `LOCAL` | `dashenifwdorch.cpp:244-253` |
| `"down"` | スキップ (登録なし) | — | `dashenifwdorch.cpp:244-253` |

### `primary_vdpu` 解決ロジック

| primary_vdpu の dpu_type | Redirect 先 | Tunnel Term | evidence |
|--------------------------|------------|------------|---------|
| `LOCAL` | `pa_ipv4` (Neighbor oid) | あり | `dashenifwdorch.h:LocalEniNH` |
| `CLUSTER` | `npu_ipv4@tunnel,vni` | なし (ただし 両端 LOCAL の場合はあり) | `dashenifwdorch.h:RemoteEniNH` |
<!-- /value-behavior -->

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`DASH_ACL_*`](dash-acl.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-swss/orchagent/dash/dashenifwdorch.h` (L62-89 テーブル名・フィールド名定数、L129-156 request_description). <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/dash/dashenifwdorch.h>

[^2]: `sonic-swss/orchagent/dash/dashenifwdorch.cpp` (L212-347 `DpuRegistry::populate()`, `processDpuTable()`, `processRemoteDpuTable()`, `processVdpuTable()`). <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/dash/dashenifwdorch.cpp>

[^3]: `sonic-net/SONiC/doc/smart-switch/high-availability/eni-based-forwarding.md`. <https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/high-availability/eni-based-forwarding.md>

<!-- ops-hint -->
## 運用ヒント

### 典型設定例 (SmartSwitch HA 構成)

```json
{
    "DPU": {
        "local_dpu0": {
            "pa_ipv4": "10.0.0.1",
            "state": "up"
        }
    },
    "REMOTE_DPU": {
        "remote_dpu0": {
            "pa_ipv4": "10.0.0.2",
            "npu_ipv4": "20.0.0.2"
        }
    },
    "VDPU": {
        "vdpu0": {
            "main_dpu_ids": "local_dpu0"
        },
        "vdpu1": {
            "main_dpu_ids": "remote_dpu0"
        }
    }
}
```

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'DPU|*'
sonic-db-cli CONFIG_DB hgetall 'DPU|dpu0'
sonic-db-cli CONFIG_DB keys 'REMOTE_DPU|*'
sonic-db-cli CONFIG_DB keys 'VDPU|*'
sonic-db-cli CONFIG_DB keys 'DPUS|*'
# ENI forward table は APPL_DB
sonic-db-cli APPL_DB keys 'DASH_ENI_FORWARD_TABLE:*'
```
<!-- /ops-hint -->

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

YANG schema が存在しないため、すべてのデフォルトはコード (`dashenifwdorch.h` / `dashenifwdorch.cpp`) のフィールド定数定義と `request_description_t` の必須指定から由来する。

### DPU テーブル

| フィールド | コード由来デフォルト | 必須区分 | fallback 源 | 備考 |
|-----------|-------------------|---------|------------|------|
| `pa_ipv4` | なし | **必須** | `dpu_table_desc` の mandatory フィールド — `dashenifwdorch.h:136` | 欠如時は parse 例外 |
| `pa_ipv6` | なし | 省略可 | フィールド定数 `PA_V6` — `dashenifwdorch.h:78` | オプション。未指定時は DpuData に格納されない |
| `state` | 未指定 = `"up"` 扱い (省略可) | 省略可 | `processDpuTable()` の state チェック — `dashenifwdorch.cpp:243-253` | `"down"` のみ明示的に除外。それ以外はすべて登録 |

### REMOTE_DPU テーブル

| フィールド | コード由来デフォルト | 必須区分 | fallback 源 | 備考 |
|-----------|-------------------|---------|------------|------|
| `pa_ipv4` | なし | **必須** | `remote_dpu_table_desc` mandatory — `dashenifwdorch.h:147` | 欠如時は parse 例外 |
| `npu_ipv4` | なし | **必須** | `remote_dpu_table_desc` mandatory — `dashenifwdorch.h:147` | 欠如時は parse 例外 |
| `pa_ipv6` | なし | 省略可 | フィールド定数 `PA_V6` — `dashenifwdorch.h:78` | オプション |
| `npu_ipv6` | なし | 省略可 | フィールド定数 `NPU_V6` — `dashenifwdorch.h:79` | オプション |

### VDPU テーブル

| フィールド | コード由来デフォルト | 必須区分 | fallback 源 | 備考 |
|-----------|-------------------|---------|------------|------|
| `main_dpu_ids` | なし | **必須** | `vdpu_table_desc` mandatory — `dashenifwdorch.h:155` | コンマ区切り DPU 名リスト |

### ENI (DASH_ENI_FORWARD_TABLE — APPL_DB)

| フィールド | コード由来デフォルト | 必須区分 | fallback 源 | 備考 |
|-----------|-------------------|---------|------------|------|
| `vdpu_ids` | なし | **必須** | `eni_dash_fwd_desc` optional (ただし空時は ACL 未生成) — `dashenifwdorch.h:86` | コンマ区切り VDPU 名リスト |
| `primary_vdpu` | なし | **必須** | `eni_dash_fwd_desc` mandatory — `dashenifwdorch.h:89` | primary の VDPU が ACL redirect 先を決定 |

### DPUS テーブル

| フィールド | コード由来デフォルト | 必須区分 | fallback 源 | 備考 |
|-----------|-------------------|---------|------------|------|
| `midplane_interface` | なし | **必須** | `config_samples.py:100` で `KeyError` 回避なし | 欠如時 `dhcpservd` が DHCP ポート生成をスキップ |

### 補足

- `DPU` テーブルに対応する YANG schema は現時点 (2026-05) で sonic-buildimage の yang-models に存在しない。すべての制約はコードレベルで実施される。
- `state` フィールドのデフォルト: YANG 定義がないため、コードレベルでは「`"down"` 以外はすべて有効」という形。実質的に未指定 = `"up"` 扱い。
- `DpuRegistry::populate()` はシステム起動時に一度のみ呼ばれる (`lazyInit()`); 実行中の DPU テーブル変更は動的に反映されない。
<!-- /defaults -->
