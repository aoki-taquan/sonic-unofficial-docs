# TUNNEL_DECAP_TERM_TABLE — プラットフォーム差調査

Task F Phase H: `TUNNEL_DECAP_TERM_TABLE` (APPL_DB) 処理におけるプラットフォーム/構成差を `tunneldecaporch.cpp`・`tunnelmgr.cpp`・`ipinip.json.j2` から精読した結果。

## 結論サマリ

APPL_DB の `TUNNEL_DECAP_TERM_TABLE` エントリを **処理する側** (`tunneldecaporch`) にはプラットフォーム差なし。プラットフォーム差は **書き込み側** (`ipinip.json.j2` テンプレート) で発生し、`switch_type`・ASIC ベンダー・デバイスタイプ・ロールアドレス数の組み合わせによって生成エントリ数・親トンネルの `dscp_mode` が変わる。

---

## 1. DPU (`switch_type == "dpu"`)

`ipinip.json.j2` L1: `switch_type == "dpu"` のとき JSON 全体が `[]` を返す。

- TUNNEL_DECAP_TABLE も TUNNEL_DECAP_TERM_TABLE も **一切生成されない**。
- DPU 筐体では IP-in-IP デカップ機能自体を使用しない設計。

## 2. BackEnd デバイスタイプ（`storage_device` 未設定時）

`ipinip.json.j2` L67-76:

```jinja
{%- set backend_device_types = ['BackEndToRRouter', 'BackEndLeafRouter', 'BackEndSpineRouter'] -%}
{% if 'type' in DEVICE_METADATA['localhost'] and
      DEVICE_METADATA['localhost']['type'] in backend_device_types and
      'storage_device' not in DEVICE_METADATA['localhost'] %}
{% set ipv4_addresses = [] %}
{% set ipv6_addresses = [] %}
...
{% endif %}
```

- Backend ロールかつ `storage_device` メタデータが存在しない場合、すべてのアドレスリストを空にリセットする。
- 結果として TUNNEL_DECAP_TERM_TABLE エントリが **一切生成されない**（parent の TUNNEL_DECAP_TABLE も同様）。
- `storage_device` を持つ BackEnd デバイス（Azure StorageFront 等）はこの制限対象外。

## 3. 大規模トポロジ（ルーティングインターフェース > 128 個）

`ipinip.json.j2` L79-83:

```jinja
{# SAI report tunnel TABLE_FULL for large topo. Only generating for VLAN and loopback if over 128 routed interfaces.#}
{% if ipv4_addresses|length + ipv6_addresses|length > 128 %}
{%- set ipv4_addresses = ipv4_loopback_addresses + ipv4_vlan_addresses %}
{%- set ipv6_addresses = ipv6_loopback_addresses + ipv6_vlan_addresses %}
{% endif %}
```

- ルーティングインターフェース（Loopback + VLAN + Port + PortChannel）の合計が **128 超** のとき、term エントリの生成対象を **Loopback + VLAN アドレスのみ**に限定する。
- 根拠: SAI 実装が `SAI_ERR_TABLE_FULL` を返す可能性があるため（コメント中に明記）。
- 小規模トポロジではすべての routed interface アドレスに対して P2MP term が生成される。

## 4. ASIC ベンダー別: 親トンネルの dscp_mode

`ipinip.json.j2` L97-108（例: IPINIP_SUBNET）:

```jinja
{% if is_broadcom %}
{% if is_broadcom_t1 %}
    "dscp_mode":"pipe",
{% else %}
    "dscp_mode":"uniform",
{% endif %}
{% else %}
    "dscp_mode":"pipe",
{% if azure_qos_exists %}
    "decap_dscp_to_tc_map":"AZURE",
{% endif %}
{% endif %}
```

| ベンダー / ロール | dscp_mode | decap_dscp_to_tc_map |
|---|---|---|
| Broadcom + LeafRouter (T1) | `pipe` | なし |
| Broadcom + 非 T1 (ToR, Spine 等) | `uniform` | なし |
| 非 Broadcom + AZURE QoS マップ存在 | `pipe` | `AZURE` |
| 非 Broadcom + AZURE QoS マップなし | `pipe` | なし |

TUNNEL_DECAP_TABLE エントリの `dscp_mode` が異なるが、**TUNNEL_DECAP_TERM_TABLE 自体のフィールド（`term_type`・`src_ip`・`subnet_type`）に差分はない**。orchagent の `doDecapTunnelTermTask()` 処理ロジックにも分岐なし。

## 5. IPv4 / IPv6 アドレスファミリー混在チェック (tunneldecaporch)

`tunneldecaporch.cpp` L950-954:

```cpp
if (src_ip.isV4() != dst_ip.isV4())
{
    SWSS_LOG_ERROR("Src IP %s doesn't match IP version of dst IP %s.", ...);
    return false;
}
```

- `P2P` / `MP2MP` term において `src_ip` と `dst_ip` の IP バージョン（v4/v6）が異なる場合、`false` を返して SAI 呼び出しをスキップする。
- これは ASIC 非依存のソフトウェアチェック。すべてのプラットフォームに均等に適用される。

## 6. MuxTunnel0 (Dual-ToR)

`tunneldecaporch.h` L21: `#define MUX_TUNNEL "MuxTunnel0"`

`muxorch.cpp` は `MUX_TUNNEL` をキーとして `TunnelDecapOrch::createNextHopTunnel()` / `getDstIpAddresses()` / `getDscpMode()` を呼び出す。
- Dual-ToR 構成では TUNNEL_DECAP_TERM_TABLE に MuxTunnel0 向け term エントリが追加される。
- term の処理ロジック自体は通常の P2MP/P2P term と同一であり、orchagent 内の MuxTunnel0 固有の分岐は存在しない。

## 7. multi-asic / VOQ chassis

`tunneldecaporch` は `orchagent` コンテナ内で asic-namespace ごとに独立して動作する。各 namespace の orchagent が自身の APPL_DB を購読し、対応する ASIC の SAI に書き込む。テーブル処理ロジックに asic-namespace 固有の分岐はない。

## まとめ

| プラットフォーム差 | 影響対象 | TERM テーブルへの直接影響 |
|---|---|---|
| `switch_type == "dpu"` | テンプレート生成 | **TERM エントリなし** |
| BackEnd デバイスタイプ（storage_device なし） | テンプレート生成 | **TERM エントリなし** |
| ルーティングIF > 128 | テンプレート生成 | **生成アドレス数を Loopback + VLAN に制限** |
| Broadcom T1 vs 非 T1 vs 非 Broadcom | 親 TUNNEL の dscp_mode | **TERM フィールドへの影響なし** |
| IPv4/IPv6 混在 (src/dst バージョン不一致) | orchagent バリデーション | SAI 呼び出しをスキップ（全 ASIC 共通） |
| multi-asic / VOQ | orchagent namespace 分離 | 各 ASIC 独立処理（ロジック差なし） |
