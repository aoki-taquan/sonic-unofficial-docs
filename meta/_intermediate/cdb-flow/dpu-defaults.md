# DPU フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `DPU`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-smart-switch.yang` (YANG定義)
- `sonic-buildimage/src/sonic-config-engine/smartswitch_config.py` (設定生成)
- `sonic-buildimage/src/sonic-yang-models/doc/Configuration.md` (公式説明)
- `sonic-swss/orchagent/dash/dashenifwdorch.h` (orchagent 読み込み側)
- `sonic-host-services/scripts/caclmgrd` (swbus_port 処理)
- `sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go` (gnmi_port fallback)
- `sonic-buildimage/dockers/docker-telemetry-watchdog/watchdog/src/main.rs` (gnmi_port fallback)
- `sonic-buildimage/src/sonic-yang-models/tests/files/sample_config_db.json` (実例値)

---

## テーブル概要

`DPU` テーブルは SmartSwitch プラットフォームの物理 DPU (Data Processing Unit) 情報を保持する。
エントリは `platform.json` から `sonic-config-engine/smartswitch_config.py` 経由で CONFIG_DB に書き込まれる。
YANG model (`sonic-smart-switch.yang`) にはいずれのフィールドにも `default` 文が存在しない — すべて
プラットフォーム固有の設定値であり、コードレベルの暗黙デフォルトは **読み取り側** のコードにのみ存在する。

---

## フィールド別 暗黙デフォルト

### `state` (admin state)

**YANG default**: なし (`type stypes:admin_status` — 値は `"up"` / `"down"`)  
**コード由来デフォルト**: なし (必須フィールドとして扱われる)  
**dpu_table_desc** (`dashenifwdorch.h:136`): `state` は mandatory フィールドとして `required_attributes` に含まれる。
DB にエントリが存在しない場合、orchagent は request を reject する。

---

### `local_port`

**YANG default**: なし (`type stypes:interface_name`)  
**コード由来デフォルト**: なし  
参照のみ — `dashenifwdorch` はこのフィールドを直接参照しない。プラットフォーム固有の port 名を格納する。

---

### `vip_ipv4` / `vip_ipv6`

**YANG default**: なし (`type inet:ipv4-address` / `inet:ipv6-address`)  
**コード由来デフォルト**: なし  
minigraph 由来の VIP アドレス。`EniFwdCtxBase::getVip()` がこれを参照して VIP Prefix を決定する。

---

### `pa_ipv4` / `pa_ipv6`

**YANG default**: なし  
**コード由来デフォルト**: なし  
`dashenifwdorch.h:133` の `dpu_table_desc` で mandatory (`PA_V4` は required_attributes 指定):

```cpp
// dashenifwdorch.h:132-136
const request_description_t dpu_table_desc = {
    { REQ_T_STRING },
    { { DashEniFwd::STATE, REQ_T_STRING }, { DashEniFwd::PA_V4, REQ_T_IP }, { DashEniFwd::PA_V6, REQ_T_IP } },
    { DashEniFwd::STATE, DashEniFwd::PA_V4 }   // ← required
};
```

`pa_ipv4` が欠如している場合、orchagent は当該 DPU エントリを処理しない。

---

### `midplane_ipv4`

**YANG default**: なし (`type inet:ipv4-address`; 2025-08-18 revision で追加)  
**コード由来デフォルト**: なし  
`169.254.0.0/16` レンジ (link-local) の midplane アドレスが使われる例が多いが、
コード側に強制はない。`container_checker` スクリプトが `DPUS` テーブルの `midplane_interface` を参照して
ヘルスチェックに使うが、`DPU.midplane_ipv4` は直接参照しない。

---

### `dpu_id`

**YANG default**: なし (`type string { pattern [0-7]; }` — 0〜7 の単一文字)  
**コード由来デフォルト**: なし  
minigraph 由来の DPU ID。`dpu_id` は YANG パターンで `[0-7]` (0 から 7 の 1 桁のみ) に制限される。

---

### `vdpu_id`

**YANG default**: なし (`type string { length 1..255; }`)  
**コード由来デフォルト**: なし  
minigraph 由来の VDPU GUID。`VDPU` テーブルの `vdpu_id` への論理参照。

---

### `gnmi_port`

**YANG default**: なし (`type inet:port-number`)  
**コード由来デフォルト (読み取り側)**: `50052`

```go
// sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go:18-100
DefaultGNMIPort = "50052"
gnmiPort, ok := configFields["gnmi_port"]
if !ok || gnmiPort == "" {
    gnmiPort = DefaultGNMIPort   // ← フィールド欠如時は "50052" にフォールバック
}
```

reboot_smartswitch_helper スクリプトも `sonic-db-cli CONFIG_DB hget "$k" gnmi_port` で読み取る。
test mock データ (`dashenifwdorch_ut.cpp:71`) では `"50051"` を使用。
sample_config_db.json では `"50052"` を使用。HLD 記載値は `50051`。

**実装上の注意**: `gnmi_port` フィールドが CONFIG_DB に存在しない場合、
sonic-gnmi proxy は `50052` にフォールバックし、さらに `8080` / `50052` を順次試行する。
DPU gNMI サービスが listenする port と一致させる必要がある。

---

### `orchagent_zmq_port`

**YANG default**: なし (`type inet:port-number`)  
**コード由来デフォルト**: なし (ただし HLD 記載の典型値は `5555`)  

sample_config_db.json の例では `"50"` を使用しているが、これはテスト用の値。
HLD (`smart-switch-ha-detailed-design.md:338`) の記載値は `5555`。
読み取り側コードでフォールバック値を設定している実装は確認されなかった。

---

### `swbus_port`

**YANG default**: なし (`type inet:port-number`)  
**コード由来デフォルト**: なし (ただし Convention: `23606 + dpu_id`)

HLD の説明: 「Must be 23606 + dpu_id」(Configuration.md:3476)。
`caclmgrd` (`sonic-host-services/scripts/caclmgrd:1096-1100`) は `swbus_port` を読み取り、
iptables ルールを生成する。`swbus_port` が欠如している場合は DPU configuration を無視する:

```python
# caclmgrd:1096-1100
if (fv[0] == "swbus_port"):
    new_port = fv[1]
    break
if not new_port:
    self.log_info("Received DPU configuration without swbus_port. Ignore it.")
    return
```

Convention として `dpu_id=0` → `23606`、`dpu_id=1` → `23607`。
sample_config_db.json では両 DPU とも `"23607"` (テスト用)。

---

## 要約表

| フィールド | YANG default | コード由来デフォルト | 必須 | 備考 |
|-----------|-------------|-------------------|------|------|
| `state` | なし | なし | 実質必須 | `dpu_table_desc` required_attributes |
| `local_port` | なし | なし | 推奨 | プラットフォーム固有 |
| `vip_ipv4` | なし | なし | 任意 | minigraph 由来 |
| `vip_ipv6` | なし | なし | 任意 | minigraph 由来 |
| `pa_ipv4` | なし | なし | 実質必須 | `dpu_table_desc` required_attributes |
| `pa_ipv6` | なし | なし | 任意 | IPv6 不使用時は省略可 |
| `midplane_ipv4` | なし | なし | 任意 | 2025-08-18 追加フィールド |
| `dpu_id` | なし | なし | 推奨 | pattern `[0-7]` (0–7 の 1 桁) |
| `vdpu_id` | なし | なし | 任意 | VDPU テーブルへの論理参照 |
| `gnmi_port` | なし | `"50052"` (sonic-gnmi proxy fallback) | 推奨 | 欠如時 proxy は 50052 試行 |
| `orchagent_zmq_port` | なし | なし (HLD 典型値 `5555`) | 推奨 | ZMQ orchagent との通信ポート |
| `swbus_port` | なし | なし (Convention: `23606 + dpu_id`) | 推奨 | 欠如時 caclmgrd が DPU config を無視 |

---

## 証拠リンク

- `sonic-smart-switch.yang` — DPU container 定義 (YANG default 文なし)
- `sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go:18-100` — `DefaultGNMIPort = "50052"` fallback
- `sonic-swss/orchagent/dash/dashenifwdorch.h:129-136` — `dpu_table_desc` required_attributes
- `sonic-host-services/scripts/caclmgrd:1096-1100` — `swbus_port` 欠如時の無視ロジック
- `SONiC/doc/smart-switch/high-availability/smart-switch-ha-detailed-design.md:337-339` — 典型値 (gnmi_port=50051, orchagent_zmq_port=5555, swbus_port=23606)
- `sonic-buildimage/src/sonic-yang-models/tests/files/sample_config_db.json:3041-3068` — 実例値 (gnmi_port=50052, orchagent_zmq_port=50, swbus_port=23607)
- `sonic-buildimage/src/sonic-yang-models/doc/Configuration.md:3476` — swbus_port convention (`23606 + dpu_id`)
