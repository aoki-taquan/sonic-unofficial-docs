# DASH_ENI_TABLE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: APP_DB `DASH_ENI_TABLE` (ZMQ 経由で CONFIG_DB 相当の役割)

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashorch.cpp` (`DashOrch::addEniObject`, `setEniAdminState`)
- `sonic-swss/orchagent/dash/dashorch.h` (EniEntry / EniTable 定義)
- `SONiC/doc/dash/dash-sonic-hld.md` (§3.2.3 ENI)
- `sonic-swss/tests/dash/dash_configs.py` (テスト設定)

---

## フィールド別 暗黙デフォルト

### `admin_state`

**コード由来デフォルト**: `STATE_DISABLED` (protobuf enum 0 値)

```cpp
// dashorch.cpp:543
bool eni_enable = entry.metadata.admin_state() == dash::eni::State::STATE_ENABLED;
// dashorch.cpp:634
eni_attr.value.booldata = (entry.metadata.admin_state() == dash::eni::State::STATE_ENABLED);
```

`admin_state` は proto3 のフィールドで、未設定の場合 enum デフォルト (`0 = STATE_DISABLED`) になる。
SAI 属性 `SAI_ENI_ATTR_ADMIN_STATE` は `false` (disabled) として渡される。

HLD 記述: "Enabled after all configurations are applied" — コントローラが明示的に `STATE_ENABLED` を送るまで disabled が意図的デフォルト。

---

### `mode`

**コード由来デフォルト**: `SAI_DASH_ENI_MODE_VM` (vm_mode)

```cpp
// dashorch.cpp:724-734
if (entry.metadata.has_eni_mode()) {
    auto it = eniModeMap.find(entry.metadata.eni_mode());
    eni_attr.id = SAI_ENI_ATTR_DASH_ENI_MODE;
    if (it != eniModeMap.end())
    {
        eni_attr.value.u32 = it->second;
    } else {
        // Default to VM mode if not specified
        eni_attr.value.u32 = SAI_DASH_ENI_MODE_VM;
        SWSS_LOG_ERROR("Invalid ENI mode %s for ENI %s, defaulting to VM mode", ...);
    }
    eni_attrs.push_back(eni_attr);
}
```

`has_eni_mode()` が false (フィールド未設定) の場合、`SAI_ENI_ATTR_DASH_ENI_MODE` を attrs に追加しない。
HLD 記述: `Default is 'vm_mode'` (dash-sonic-hld.md:406)。
eniModeMap で未知の mode 値が来た場合のエラー時 fallback も `SAI_DASH_ENI_MODE_VM`。

---

### `pl_underlay_sip` / `pl_sip_encoding`

**コード由来デフォルト**: 設定なし (OPTIONAL、SAI 属性を push しない)

```cpp
// dashorch.cpp:649-664
if (entry.metadata.has_pl_underlay_sip())
{
    eni_attr.id = SAI_ENI_ATTR_PL_UNDERLAY_SIP;
    to_sai(entry.metadata.pl_underlay_sip(), eni_attr.value.ipaddr);
    eni_attrs.push_back(eni_attr);
}

if (entry.metadata.has_pl_sip_encoding())
{
    eni_attr.id = SAI_ENI_ATTR_PL_SIP;
    ...
    eni_attr.id = SAI_ENI_ATTR_PL_SIP_MASK;
    ...
}
```

`has_*()` パターン: proto3 oneof / optional フィールド未設定の場合は SAI 属性未設定のまま。Private Link 機能が不要な ENI ではこれらを省略できる。

---

### `v4_meter_policy_id` / `v6_meter_policy_id`

**コード由来デフォルト**: 設定なし (OPTIONAL、SAI 属性を push しない)

```cpp
// dashorch.cpp:585-588
const string &v4_meter_policy  = entry.metadata.has_v4_meter_policy_id() ?
                                 entry.metadata.v4_meter_policy_id() : "";
const string &v6_meter_policy  = entry.metadata.has_v6_meter_policy_id() ?
                                 entry.metadata.v6_meter_policy_id() : "";
```

未設定時は空文字列 → `if (!v4_meter_policy.empty())` ブロックをスキップ → SAI 属性なし。
メータリング不使用 ENI では省略可。

---

### `qos`

**コード由来デフォルト**: 設定なし (QoS プロファイル名が空 or 未登録の場合は QoS attrs をスキップ)

```cpp
// dashorch.cpp:617-631
bool has_qos = qos_entries_.find(entry.metadata.qos()) != qos_entries_.end();
if (has_qos)
{
    eni_attr.id = SAI_ENI_ATTR_PPS;
    ...
    eni_attr.id = SAI_ENI_ATTR_CPS;
    ...
    eni_attr.id = SAI_ENI_ATTR_FLOWS;
    ...
}
```

`qos` フィールドが空文字列または未登録プロファイル名の場合、PPS / CPS / FLOWS を SAI に設定しない。
SAI デフォルト (実装依存) が使用される。

---

### `trusted_vnis_list`

**コード由来デフォルト**: 空リスト (エントリなし)

```cpp
// dashorch.cpp:868-878
if (!entry.metadata.trusted_vnis_list().empty())
{
    bool all_trusted_vnis_added = addEniTrustedVnis(eni, entry);
    ...
}
```

`trusted_vnis_list` が空の場合は `addEniTrustedVnis` を呼ばない。
Trusted VNI エントリは作成されない。

---

### `disable_fast_path_icmp_flow_redirection`

**コード由来デフォルト**: 未確認 (dashorch.cpp に明示的な処理コードなし)

HLD には OPTIONAL フィールドとして記載 (dash-sonic-hld.md:389)。
sonic-swss の現行コード (`dashorch.cpp`) に `disable_fast_path_icmp_flow_redirection` の処理が見当たらない。
SAI 層での処理が想定されているか、または未実装の可能性がある。
**discrepancy**: HLD 記載あり、orchagent 実装なし。

---

### `underlay_ip` (SAI: SAI_ENI_ATTR_VM_UNDERLAY_DIP)

**コード由来デフォルト**: 必須フィールド (デフォルトなし)

```cpp
// dashorch.cpp:637-642
eni_attr.id = SAI_ENI_ATTR_VM_UNDERLAY_DIP;
if (!to_sai(entry.metadata.underlay_ip(), eni_attr.value.ipaddr))
{
    return false;
}
eni_attrs.push_back(eni_attr);
```

`to_sai` 失敗 (不正な IP アドレス) の場合 `addEniObject` が false を返してリトライ。
必須フィールド — デフォルト値なし。

---

### `vnet` (SAI: SAI_ENI_ATTR_VNET_ID)

**コード由来デフォルト**: 必須フィールド (デフォルトなし)

```cpp
// dashorch.cpp:613-615
eni_attr.id = SAI_ENI_ATTR_VNET_ID;
eni_attr.value.oid = gVnetNameToId[entry.metadata.vnet()];
eni_attrs.push_back(eni_attr);
```

VNET 未登録 → `addEniObject` が retry を返す (dashorch.cpp:572-576)。

---

### `mac_address`

**コード由来デフォルト**: 必須フィールド (ENI ether address map entry のキー)

```cpp
// dashorch.cpp:777
memcpy(eni_ether_address_map_entry.address, entry.metadata.mac_address().c_str(), sizeof(sai_mac_t));
```

MAC アドレスは ENI ether address map entry の lookup key として使用。必須。

---

## 要約表

| フィールド | 必須/任意 | コード由来デフォルト | fallback 源 |
|-----------|---------|-------------------|------------|
| `mac_address` | 必須 | なし | ENI ether address map key — dashorch.cpp:777 |
| `vnet` | 必須 | なし | 未登録時 retry — dashorch.cpp:572 |
| `underlay_ip` | 必須 | なし | to_sai 失敗時 return false — dashorch.cpp:638 |
| `admin_state` | 任意 | `STATE_DISABLED` (proto3 enum 0) | `STATE_ENABLED` と明示比較 — dashorch.cpp:634 |
| `mode` | 任意 | `SAI_DASH_ENI_MODE_VM` (vm_mode) | has_eni_mode() false 時は SAI 未設定; 不正値 fallback も VM — dashorch.cpp:724-734 |
| `qos` | 任意 | なし (SAI 未設定) | qos_entries_ lookup miss → PPS/CPS/FLOWS スキップ — dashorch.cpp:617 |
| `pl_underlay_sip` | 任意 | なし (SAI 未設定) | has_pl_underlay_sip() false → スキップ — dashorch.cpp:649 |
| `pl_sip_encoding` | 任意 | なし (SAI 未設定) | has_pl_sip_encoding() false → スキップ — dashorch.cpp:656 |
| `v4_meter_policy_id` | 任意 | なし (SAI 未設定) | has_v4_meter_policy_id() false → 空文字列 — dashorch.cpp:585 |
| `v6_meter_policy_id` | 任意 | なし (SAI 未設定) | has_v6_meter_policy_id() false → 空文字列 — dashorch.cpp:587 |
| `trusted_vnis_list` | 任意 | 空リスト | リスト空の場合 addEniTrustedVnis() 呼ばず — dashorch.cpp:868 |
| `disable_fast_path_icmp_flow_redirection` | 任意 | 不明 (orchagent 実装なし) | HLD 記載あり、dashorch.cpp に処理コード未確認 |

---

## discrepancy 記録

| フィールド | 状況 |
|-----------|------|
| `disable_fast_path_icmp_flow_redirection` | HLD の DASH_ENI_TABLE スキーマ (dash-sonic-hld.md:389) に記載あるが、sonic-swss orchagent/dash/dashorch.cpp に処理実装が見当たらない |

---

## 証拠リンク

- `sonic-swss/orchagent/dash/dashorch.cpp:566-768` — `addEniObject()` 全体 (SAI 属性組み立て)
- `sonic-swss/orchagent/dash/dashorch.cpp:539-564` — `setEniAdminState()`
- `sonic-swss/orchagent/dash/dashorch.cpp:841-881` — `addEni()` (trusted VNIs 処理)
- `SONiC/doc/dash/dash-sonic-hld.md:378-408` — DASH_ENI_TABLE スキーマ定義
- `sonic-swss/tests/dash/dash_configs.py:104-123` — ENI_CONFIG テスト設定 (STATE_ENABLED を明示)
