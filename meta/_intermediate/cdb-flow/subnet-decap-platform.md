# subnet-decap — Phase H platform 調査メモ

## 調査対象

`SUBNET_DECAP` テーブルとそれを消費する `TunnelDecapOrch` / `ipinip.json.j2` における
プラットフォーム固有の差異を特定する。

## 主要ソース

- `sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2`
- `sonic-swss/orchagent/tunneldecaporch.cpp`

## 1. DPU デバイス — SUBNET_DECAP 設定が生成されない

`ipinip.json.j2:1-2`:

```jinja2
{% if DEVICE_METADATA['localhost']['switch_type'] == "dpu" %}
[]
{% else %}
...
{% endif %}
```

`switch_type == "dpu"` の場合、テンプレートは空リスト `[]` を出力する。
すなわち `SUBNET_DECAP` を含む **すべての TUNNEL_DECAP_TABLE / TUNNEL_DECAP_TERM_TABLE エントリが生成されない**。
DPU 環境でのサブネットデカプセルはこのテンプレートではなく別の設定経路で行われる（または機能しない）。

## 2. dscp_mode の Broadcom / 非 Broadcom 分岐

`ipinip.json.j2` の `is_broadcom` / `is_broadcom_t1` 判定:

```jinja2
{% set is_broadcom = false %}
{% if ASIC_VENDOR is defined and "broadcom" in ASIC_VENDOR|lower %}
  {% set is_broadcom = true %}
{% endif %}

{% set is_broadcom_t1 = false %}
{% if is_broadcom and 'LeafRouter' in DEVICE_METADATA['localhost']['type'] %}
    {% set is_broadcom_t1 = true %}
{% endif %}
```

生成される `dscp_mode` の違い:

| ASIC / デバイスタイプ | `dscp_mode` | 追加属性 |
|----------------------|-------------|---------|
| Broadcom T1 (`LeafRouter`) | `"pipe"` | なし |
| Broadcom 非 T1 | `"uniform"` | なし |
| 非 Broadcom（AZURE QoS マップあり） | `"pipe"` | `"decap_dscp_to_tc_map":"AZURE"` |
| 非 Broadcom（AZURE QoS マップなし） | `"pipe"` | なし |

`ecn_mode: "copy_from_outer"` / `ttl_mode: "pipe"` は全プラットフォームで共通。

## 3. BackEnd デバイスタイプ — トンネルエントリが生成されない

```jinja2
{%- set backend_device_types = ['BackEndToRRouter', 'BackEndLeafRouter', 'BackEndSpineRouter'] -%}
{% if 'type' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['type'] in backend_device_types
    and 'storage_device' not in DEVICE_METADATA['localhost'] %}
{% set ipv4_addresses = [] %}
...
{% endif %}
```

`BackEndToRRouter` / `BackEndLeafRouter` / `BackEndSpineRouter` かつ `storage_device` メタデータがない場合、
すべてのアドレスリストがクリアされ、TUNNEL_DECAP_TERM_TABLE エントリが生成されない（テーブル自体は空になる）。
`storage_device` メタデータがある BackEnd デバイスは通常の生成パスへ進む。

## 4. 大規模トポロジー (>128 routed interfaces) — ロードバランシング制限

```jinja2
{# SAI report tunnel TABLE_FULL for large topo.
   Only generating for VLAN and loopback if over 128 routed interfaces. #}
{% if ipv4_addresses|length + ipv6_addresses|length > 128 %}
{%- set ipv4_addresses = ipv4_loopback_addresses + ipv4_vlan_addresses %}
{%- set ipv6_addresses = ipv6_loopback_addresses + ipv6_vlan_addresses %}
{% endif %}
```

ルーティングインタフェース総数（IPv4 + IPv6）が 128 超の場合、ASIC の SAI `TABLE_FULL` エラー回避のため、
Loopback および VLAN インタフェースのアドレスのみを使用してトンネルデカプセルエントリを生成する。
通常の物理・ポートチャネルインタフェースのプレフィクスはこの条件では除外される。

## 5. SAI MP2MP / P2MP 対応

`tunneldecaporch.cpp:886,930-936`:
- `subnet_type: vlan` / `subnet_type: vip` を持つエントリは `MP2MP` タイプとして SAI に登録される
- `P2MP` は宛先 IP ごとの単一マッチ（通常の IP-in-IP デカプセル）
- `MP2MP` はサブネット単位のデカプセル（`SUBNET_DECAP` 機能コア）

ASIC が `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_MP2MP` を未実装の場合、
`sai_tunnel_api->create_tunnel_term_table_entry()` がエラーを返し、
`addDecapTunnelTermEntry` が `false` を返す。
この場合エントリは `unhandledTerms` キューに残り、後続のポーリングで再試行される。

## 6. FrontEnd / BackEnd ロールによるループバックアドレス選択

```jinja2
{% if DEVICE_METADATA['localhost']['sub_role'] == 'FrontEnd'
   or DEVICE_METADATA['localhost']['sub_role'] == 'BackEnd' %}
{% set loopback_intf_names = ['Loopback0', 'Loopback4096'] %}
{% else %}
{% set loopback_intf_names = ['Loopback0', 'Loopback2', 'Loopback3'] %}
{% endif %}
```

`sub_role` が `FrontEnd` または `BackEnd` の場合、ループバックは `Loopback0` / `Loopback4096` のみを使用。
それ以外（通常デバイス）は `Loopback0` / `Loopback2` / `Loopback3` を使用。
これはデカプセルトンネルのソース IP レンジに影響する。

## まとめ

| 条件 | 挙動 |
|------|------|
| `switch_type == "dpu"` | TUNNEL_DECAP 設定一切生成なし |
| Broadcom T1 (`LeafRouter`) | `dscp_mode: pipe` |
| Broadcom 非 T1 | `dscp_mode: uniform` |
| 非 Broadcom + AZURE QoS | `dscp_mode: pipe` + `decap_dscp_to_tc_map: AZURE` |
| BackEnd（storage_device なし） | TUNNEL_DECAP_TERM_TABLE エントリなし |
| routed interfaces > 128 | LoopbackAddress + VLANアドレスのみ使用 |
| FrontEnd / BackEnd sub_role | Loopback0 / Loopback4096 のみ |
| その他 sub_role | Loopback0 / Loopback2 / Loopback3 |
| SAI MP2MP 非対応 ASIC | サブネットデカプセルエントリ登録失敗 → unhandledTerms 再試行 |
