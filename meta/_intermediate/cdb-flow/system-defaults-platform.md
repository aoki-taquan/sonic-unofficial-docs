# SYSTEM_DEFAULTS — Phase H (platform-diff) 調査証跡

## 調査対象

- `sonic-buildimage/files/build_templates/init_cfg.json.j2` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage/src/sonic-config-engine/config_samples.py` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-swss/orchagent/muxorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/aclorch.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 差異 1: mux_tunnel_egress_acl の初期値 (init_cfg.json.j2)

`init_cfg.json.j2` L191-195 に Jinja2 分岐が存在する:

```jinja2
{%- if include_mux == "y" %}
    "mux_tunnel_egress_acl": {
{%- if sonic_asic_platform == "mellanox" %}
        "status": "enabled"
{% else %}
        "status": "disabled"
{% endif %}
    }
{% endif %}
```

- **Mellanox (sonic_asic_platform == "mellanox")**: `status: "enabled"` — Dual-ToR ACL を egress で適用
- **その他 (Broadcom 等)**: `status: "disabled"` — ingress ACL (`IngressTableDrop`) を適用
- **非 Dual-ToR (include_mux == "n")**: エントリ自体が生成されない

`muxorch.cpp:1390` は `value != "enabled"` を `is_ingress_acl_` に使うため:
- Mellanox: `is_ingress_acl_ = false` → `EgressTableDrop` テーブルを使用
- Broadcom 等: `is_ingress_acl_ = true` → `MUX_ACL_TABLE_NAME` (`IngressTableDrop`) テーブルを使用
- エントリ不在 (kvm / 非 Dual-ToR): `value == ""` → `is_ingress_acl_ = true` (ingress フォールバック)

## 差異 2: polaris エントリ (Pensando hwsku 限定)

`config_samples.py` L179-184:

```python
if "pensando" in data['DEVICE_METADATA']['localhost']['hwsku'].lower():
    data['SYSTEM_DEFAULTS'] = {
        "polaris": {
            "status": "enabled"
        }
    }
```

Pensando hwsku（`hwsku` 文字列に `"pensando"` が含まれる）のとき、SmartSwitch DPU サンプル設定で `SYSTEM_DEFAULTS.polaris.status = "enabled"` が強制注入される。その直後に `software_bfd` も上書き追記される。他プラットフォームでは `polaris` エントリは生成されない。

## 差異 3: software_bfd エントリ (SmartSwitch DPU 限定)

`config_samples.py` L186-188:

```python
data["SYSTEM_DEFAULTS"]["software_bfd"] = {
    "status": "enabled"
}
```

SmartSwitch DPU (`SmartSwitchDPU` switch type) 向けサンプル設定でのみ `software_bfd: enabled` が自動注入される。一般の Broadcom / Mellanox プラットフォームではこのエントリは通常存在しない（minigraph.py は生成しない）。

## 差異 4: tunnel_qos_remap エントリ (デバイス種別 + 冗長化タイプ依存)

`minigraph.py` L2202-2215:

```python
# Enable tunnel_qos_remap if downstream_redundancy_types(T1) or redundancy_type(T0) = Gemini/Libra
enable_tunnel_qos_map = False
if platform and 'kvm' in platform:
    enable_tunnel_qos_map = False
elif results['DEVICE_METADATA']['localhost']['type'].lower() == 'leafrouter' and \
        ('gemini' in str(downstream_redundancy_types).lower() or 'libra' in str(downstream_redundancy_types).lower()):
    enable_tunnel_qos_map = True
elif results['DEVICE_METADATA']['localhost']['type'].lower() == 'torrouter' and \
        ('gemini' in str(redundancy_type).lower() or 'libra' in str(redundancy_type).lower()):
    enable_tunnel_qos_map = True

if enable_tunnel_qos_map:
    system_defaults['tunnel_qos_remap'] = {"status": "enabled"}
```

- **KVM プラットフォーム**: 常に `disabled`（強制除外）
- **LeafRouter + Gemini/Libra 冗長構成 (T1)**: `enabled`
- **ToRRouter + Gemini/Libra 冗長構成 (T0)**: `enabled`
- **その他デバイス種別・非 Gemini/Libra**: エントリ生成なし (不在 = disabled 扱い)

## まとめ表

| 機能キー | Mellanox | Broadcom | KVM/VS | Pensando/SmartSwitch DPU | 条件 |
|---------|---------|---------|--------|--------------------------|------|
| `mux_tunnel_egress_acl` | `enabled` | `disabled` | (include_mux次第) | (include_mux次第) | Dual-ToR ビルドの場合のみ |
| `tunnel_qos_remap` | Gemini/Libra 時 enabled | Gemini/Libra 時 enabled | 常に不在 | — | デバイス種別と冗長タイプに依存 |
| `software_bfd` | 不在 (通常) | 不在 (通常) | 不在 | `enabled` (強制注入) | SmartSwitch DPU のみ |
| `polaris` | 不在 | 不在 | 不在 | `enabled` (hwsku に "pensando" 含む時) | Pensando hwsku のみ |
