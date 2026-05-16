# DPU / ENI / VDPU / REMOTE_DPU フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: CONFIG_DB `DPU`, `REMOTE_DPU`, `VDPU`, `DPUS`, APPL_DB `ENI` (DASH_ENI_FORWARD_TABLE)

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashenifwdorch.h` (フィールド定数・request_description)
- `sonic-swss/orchagent/dash/dashenifwdorch.cpp` (processDpuTable / processRemoteDpuTable / processVdpuTable)
- `sonic-swss/tests/mock_tests/dashenifwdorch_ut.cpp` (テストデータによるフィールド確認)
- `sonic-buildimage/src/sonic-config-engine/smartswitch_config.py` (DPUS / DPU テーブルの初期投入)
- `sonic-net/SONiC/doc/smart-switch/high-availability/eni-based-forwarding.md` (HLD)

---

## grep エントリポイント

```
grep -n "DPU_TABLE\|REMOTE_DPU_TABLE\|VDPU_TABLE\|ENI\|DPU_IDS\|PA_V4\|NPU_V4\|STATE\|midplane" \
  sonic-swss/orchagent/dash/dashenifwdorch.h
```

主要定数 (dashenifwdorch.h L62-81):
- `DPU_TABLE = "DPU"`
- `REMOTE_DPU_TABLE = "REMOTE_DPU"`
- `VDPU_TABLE = "VDPU"`
- `VDPU_IDS = "vdpu_ids"` (ENI テーブルフィールド)
- `PRIMARY = "primary_vdpu"` (ENI テーブルフィールド)
- `STATE = "state"`
- `PA_V4 = "pa_ipv4"`
- `PA_V6 = "pa_ipv6"`
- `NPU_V4 = "npu_ipv4"`
- `NPU_V6 = "npu_ipv6"`
- `DPU_IDS = "main_dpu_ids"` (VDPU テーブルフィールド)

---

## フィールド別 暗黙デフォルト

### DPU テーブル

#### `pa_ipv4`

**必須**

```cpp
// dashenifwdorch.h:129-137
const request_description_t dpu_table_desc = {
    { REQ_T_STRING },
    {
        { DashEniFwd::STATE,    REQ_T_STRING },
        { DashEniFwd::PA_V4,    REQ_T_IP },
        { DashEniFwd::PA_V6,    REQ_T_IP },
    },
    { DashEniFwd::STATE, DashEniFwd::PA_V4 }  // mandatory フィールド
};
```

mandatory リストに `PA_V4` が含まれる → 欠如時は `Request::parse()` が例外を投げ `SWSS_LOG_ERROR("Failed to parse key")` が出力される。

#### `state`

**デフォルト: 未指定 = "up" 扱い (省略可)**

```cpp
// dashenifwdorch.cpp:243-253
auto itr_state = updates.find(DashEniFwd::STATE);
if (itr_state != updates.end())
{
    auto state_val = dpu_request_.getAttrString(DashEniFwd::STATE);
    if (state_val == "down")
    {
        SWSS_LOG_INFO("Skipping LOCAL DPU %s as its state is down", key.c_str());
        continue;
    }
}
// state が未指定、または "up" の場合はここに到達して DpuData として登録
```

`"down"` のみ明示的にスキップ。未指定 / それ以外の値はすべて LOCAL として登録。

#### `pa_ipv6`

**デフォルト: なし (省略可)**

フィールド定数として定義されているが (`dashenifwdorch.h:78`)、`dpu_table_desc` の mandatory リストには含まれない。`DpuData` 構造体にも IPv6 フィールドはない (IPv4 のみ格納)。

---

### REMOTE_DPU テーブル

#### `pa_ipv4`, `npu_ipv4`

**両フィールドとも必須**

```cpp
// dashenifwdorch.h:139-148
const request_description_t remote_dpu_table_desc = {
    { REQ_T_STRING },
    {
        { DashEniFwd::PA_V4,    REQ_T_IP },
        { DashEniFwd::PA_V6,    REQ_T_IP },
        { DashEniFwd::NPU_V4,   REQ_T_IP },
        { DashEniFwd::NPU_V6,   REQ_T_IP },
    },
    { DashEniFwd::PA_V4, DashEniFwd::NPU_V4 }  // mandatory
};
```

`pa_ipv4` と `npu_ipv4` が mandatory。欠如時は parse 例外。

#### `pa_ipv6`, `npu_ipv6`

**省略可**

`remote_dpu_table_desc` に定義されているが mandatory リストに含まれない。`DpuData` 構造体にも IPv6 フィールドなし。

---

### VDPU テーブル

#### `main_dpu_ids`

**必須**

```cpp
// dashenifwdorch.h:150-156
const request_description_t vdpu_table_desc = {
    { REQ_T_STRING },
    {
        { DashEniFwd::DPU_IDS,   REQ_T_STRING_LIST },
    },
    { DashEniFwd::DPU_IDS }  // mandatory
};
```

コンマ区切り DPU 名のリスト。未知 DPU 名は `SWSS_LOG_WARN` でスキップ。

---

### ENI (DASH_ENI_FORWARD_TABLE — APPL_DB)

#### `vdpu_ids`

**実質必須 (省略時 ACL 未生成)**

```cpp
// dashenifwdorch.h:83-90
const request_description_t eni_dash_fwd_desc = {
    { REQ_T_STRING, REQ_T_MAC_ADDRESS },
    {
        { DashEniFwd::VDPU_IDS,   REQ_T_STRING_LIST },
        { DashEniFwd::PRIMARY,    REQ_T_STRING },
    },
    { DashEniFwd::PRIMARY }  // mandatory は PRIMARY のみ
};
```

`vdpu_ids` は optional 定義だが、空の場合は ACL ルール生成に使用する VDPU リストが空になりルール未生成。

#### `primary_vdpu`

**必須**

mandatory リストに含まれる。ACL redirect 先の VDPU を指定。欠如時は parse 例外。

---

### DPUS テーブル

#### `midplane_interface`

**必須 (コード的に KeyError 保護なし)**

```python
# sonic-buildimage/src/sonic-config-engine/config_samples.py:100
midplane_interface = ss_config['DPUS'][dpu_name]['midplane_interface']
```

例外補足なし。欠如時 `KeyError` が発生し処理が中断される。`dhcpservd/dhcp_cfggen.py:119` でも同様に直接アクセス。

---

## 結論

| テーブル | フィールド | デフォルト | 区分 |
|---------|----------|-----------|------|
| DPU | `pa_ipv4` | なし | 必須 |
| DPU | `pa_ipv6` | なし | 省略可 |
| DPU | `state` | 未指定 = "up" 扱い | 省略可 |
| REMOTE_DPU | `pa_ipv4` | なし | 必須 |
| REMOTE_DPU | `npu_ipv4` | なし | 必須 |
| REMOTE_DPU | `pa_ipv6` | なし | 省略可 |
| REMOTE_DPU | `npu_ipv6` | なし | 省略可 |
| VDPU | `main_dpu_ids` | なし | 必須 |
| ENI | `primary_vdpu` | なし | 必須 |
| ENI | `vdpu_ids` | なし | 実質必須 (省略時 ACL 未生成) |
| DPUS | `midplane_interface` | なし | 必須 |

YANG schema 非存在のため、すべての constraint はコードレベルのみ。
