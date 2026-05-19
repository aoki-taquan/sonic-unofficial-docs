# subnet-decap — Phase H: プラットフォーム差

## 調査対象ソース

- `sonic-net/sonic-buildimage` — `dockers/docker-orchagent/ipinip.json.j2` (全行)
- `sonic-net/sonic-swss` — `orchagent/tunneldecaporch.cpp` (全行, 1576 行)
- `orchagent/tunneldecaporch.h` — SubnetDecapConfig 構造体

## 調査サマリ

`tunneldecaporch.cpp` 自体にはプラットフォーム固有の分岐 (`gMySwitchType`, `BRCM_PLATFORM_SUBSTRING`, VOQ, multi-asic namespace 等) が **存在しない**。  
プラットフォーム差は **ビルド時テンプレート `ipinip.json.j2`** に集中する。

## 差異 1: switch_type == "dpu" — 全設定スキップ

`ipinip.json.j2:1-3`

```jinja
{% if DEVICE_METADATA['localhost']['switch_type'] == "dpu" %}
[]
{% else %}
```

SmartSwitch の DPU ノードでは `switch_type = "dpu"` が設定される。この場合 `ipinip.json.j2` は空配列 `[]` を返し、`TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` が一切 APP_DB に投入されない。
その結果 `TunnelDecapOrch` は起動しても tunnel オブジェクトを受け取れず、`SUBNET_DECAP` テーブルに `status=enable` を書いても実質的に decap は動作しない。

| switch_type | 結果 |
|---|---|
| `"dpu"` | APP_DB への投入なし → SUBNET_DECAP は実質無効 |
| その他 (`""` / `"voq"` / `"fabric"` 等) | 通常 template 処理を継続 |

## 差異 2: BackEnd デバイス種別 — IP アドレスリストを空にしてトンネル term を抑止

`ipinip.json.j2:68-76`

```jinja
{%- set backend_device_types = ['BackEndToRRouter', 'BackEndLeafRouter', 'BackEndSpineRouter'] -%}
{% if 'type' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['type'] in backend_device_types
   and 'storage_device' not in DEVICE_METADATA['localhost'] %}
{% set ipv4_addresses = [] %}
{% set ipv6_addresses = [] %}
...
{% endif %}
```

`BackEndToRRouter` / `BackEndLeafRouter` / `BackEndSpineRouter` で `storage_device` フィールドが無い場合、すべての IP アドレスリストがクリアされる。ループバック / VLAN 由来のトンネル term が一切生成されなくなる。`subnet_decap.enable = true` であっても `TUNNEL_DECAP_TABLE:IPINIP_SUBNET` は生成されず、BackEnd ノードで SUBNET_DECAP は機能しない。

**例外**: `storage_device` フィールドが `DEVICE_METADATA.localhost` に存在する BackEnd デバイス（iSCSI storage leaf 等）はこのクリアが行われず、通常通り decap term が生成される。

| type | storage_device | IPINIP_SUBNET 生成 |
|---|---|---|
| `BackEndToRRouter` | なし | **生成されない** |
| `BackEndToRRouter` | あり | 生成される |
| `ToRRouter` / `LeafRouter` 等 | どちらでも | 生成される |

## 差異 3: Broadcom T1 (LeafRouter) vs その他 — dscp_mode 差

`ipinip.json.j2:5-14, 97-108`

```jinja
{% set is_broadcom = false %}
{% if ASIC_VENDOR is defined and "broadcom" in ASIC_VENDOR|lower %}
  {% set is_broadcom = true %}
{% endif %}
{% set is_broadcom_t1 = false %}
{% if is_broadcom and 'LeafRouter' in DEVICE_METADATA['localhost']['type'] %}
    {% set is_broadcom_t1 = true %}
{% endif %}
```

| プラットフォーム | `dscp_mode` (`IPINIP_SUBNET` / `IPINIP_SUBNET_V6`) |
|---|---|
| Broadcom + type に `"LeafRouter"` を含む (T1 ToR 相当) | `"pipe"` |
| Broadcom + type に `"LeafRouter"` を含まない | `"uniform"` |
| 非 Broadcom (Mellanox / Barefoot / Cisco 等) | `"pipe"` |

この差は `IPINIP_SUBNET` / `IPINIP_SUBNET_V6` / `IPINIP_TUNNEL` / `IPINIP_V6_TUNNEL` の全トンネルオブジェクトに共通して適用される。`ecn_mode = "copy_from_outer"` / `ttl_mode = "pipe"` は全プラットフォーム共通固定。

`dscp_mode` の APP_DB への注入はビルド時 1 回のみ。`tunneldecaporch.cpp:179` により `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` はトンネル作成後に変更不可 (create-only) と同様に、`dscp_mode` に対応する SAI 属性もトンネルオブジェクト作成後は変更されない（orchagent は SET_COMMAND 受信時 `"pipe"` / `"uniform"` 等の属性を `sai_tunnel_api` で試みるが、既存トンネル再設定は実質的に再作成が必要）。

## 差異 4: DSCP_TO_TC_MAP.AZURE が存在する場合の decap_dscp_to_tc_map 注入

`ipinip.json.j2:86-107`

```jinja
{% set azure_qos_exists = false %}
{% if DSCP_TO_TC_MAP is defined and DSCP_TO_TC_MAP.AZURE is defined %}
{% set azure_qos_exists = true %}
{% endif %}
```

非 Broadcom プラットフォームで `DSCP_TO_TC_MAP.AZURE` が CONFIG_DB に存在する場合のみ、`TUNNEL_DECAP_TABLE:IPINIP_SUBNET` に `"decap_dscp_to_tc_map": "AZURE"` フィールドが追加される。Broadcom プラットフォームではこの分岐に入らない（`is_broadcom = true` のブランチでは `azure_qos_exists` を参照しない）。

| ASIC ベンダ | DSCP_TO_TC_MAP.AZURE の有無 | decap_dscp_to_tc_map 注入 |
|---|---|---|
| Broadcom (T1) | どちらでも | なし |
| Broadcom (非 T1) | どちらでも | なし |
| 非 Broadcom | あり | `"AZURE"` |
| 非 Broadcom | なし | なし |

## 差異 5: sub_role == FrontEnd / BackEnd — LoopbackIntf セット差

`ipinip.json.j2:22-26`

```jinja
{% if DEVICE_METADATA['localhost']['sub_role'] == 'FrontEnd' or DEVICE_METADATA['localhost']['sub_role'] == 'BackEnd' %}
{% set loopback_intf_names = ['Loopback0', 'Loopback4096'] %}
{% else %}
{% set loopback_intf_names = ['Loopback0', 'Loopback2', 'Loopback3'] %}
{% endif %}
```

Multi-ASIC T2 chassis (`sub_role=FrontEnd`/`BackEnd`) では `Loopback4096` を LoopbackIntf として参照し、`Loopback2` / `Loopback3` を無視する。これにより `IPINIP_SUBNET` / `IPINIP_TUNNEL` トンネル term の inner dst IP 候補が変わる。  
`sub_role` が未設定のシングル ASIC デバイスは `Loopback0` / `Loopback2` / `Loopback3` を参照。

## 差異 6: ルート数 > 128 によるトンネル term 数削減

`ipinip.json.j2:80-83`

```jinja
{% if ipv4_addresses|length + ipv6_addresses|length > 128 %}
{%- set ipv4_addresses = ipv4_loopback_addresses + ipv4_vlan_addresses %}
...
{% endif %}
```

合算 IPv4 + IPv6 アドレス数が 128 を超える大規模トポロジ（インターフェース多数の ToR / BGP ピア多数ファブリック）では、INTERFACE / PORTCHANNEL_INTERFACE 由来の term を除外し、Loopback / VLAN 由来のみに制限する。これは SAI `TABLE_FULL` 回避のためのハードコード閾値。`tunneldecaporch.cpp` 実行時には影響しない（APP_DB に届く term 数が減るのみ）。

## tunneldecaporch.cpp 自体のプラットフォーム差

`tunneldecaporch.cpp` 全行を走査した結果、以下の点が確認された:

- `gMySwitchType` / `VOQ` / `BRCM_PLATFORM_SUBSTRING` / `MLNX_PLATFORM_SUBSTRING` 等のプラットフォーム分岐: **ゼロ件**
- `SAI_STATUS_NOT_IMPLEMENTED` / `SAI_STATUS_NOT_SUPPORTED` 処理: `ecn_mode` (`L179`) と `encap_ecn_mode` (`L195`) の create-only スキップのみ。これらは全プラットフォーム共通の create-only 回避
- multi-asic namespace: `TunnelDecapOrch` は単一プロセス内で動作し、namespace 切替なし

すべてのプラットフォーム差は **ビルド時 `ipinip.json.j2`** に閉じている。

## スキャン証跡

- `ipinip.json.j2` 全行 (228 行) 精読
- `tunneldecaporch.cpp` 1576 行 をキーワード検索 (`switch_type`, `broadcom`, `voq`, `VOQ`, `SAI_STATUS_NOT`, `multi_asic`, `DualToR`) → 全件ゼロまたは namespace 等 C++ 標準使用のみ
