# SUBNET_DECAP — ハードコード定数 (Phase E)

## 調査対象

- `sonic-swss/orchagent/tunneldecaporch.cpp`
- `sonic-swss/orchagent/tunneldecaporch.h`
- `sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2`

## 検出された定数

### OVERLAY_RIF_DEFAULT_MTU (tunneldecaporch.cpp:14)

```c
#define OVERLAY_RIF_DEFAULT_MTU 9100
```

decap トンネルのオーバーレイ RIF (Router Interface) 作成時にハードコードで設定される MTU 値。
CONFIG_DB の `SUBNET_DECAP` テーブルから変更不可（tunneldecaporch.cpp:749-750）。

### トンネル名ハードコード (tunneldecaporch.h:97-103)

```cpp
SubnetDecapConfig subnetDecapConfig = {
    false,
    "",
    "",
    "IPINIP_SUBNET",
    "IPINIP_SUBNET_V6"
};
```

- `tunnel`: `"IPINIP_SUBNET"` — IPv4 subnet decap に使用するトンネルオブジェクト名
- `tunnel_v6`: `"IPINIP_SUBNET_V6"` — IPv6 subnet decap に使用するトンネルオブジェクト名

これらの名前は CONFIG_DB の `SUBNET_DECAP` フィールドでは変更不可。`ipinip.json.j2` が同名でトンネルオブジェクトを生成するため、名前が一致しなければ decap term が永続的に `unhandledDecapTerms` に残留する。

### ipinip.json.j2 によるハードコードトンネルパラメータ

`ipinip.json.j2` が生成する `TUNNEL_DECAP_TABLE:IPINIP_SUBNET` / `IPINIP_SUBNET_V6` エントリには以下のハードコード値が含まれる（CONFIG_DB の `SUBNET_DECAP` から変更不可）:

| パラメータ | 値 | 条件 |
|-----------|-----|------|
| `dscp_mode` | `"pipe"` | Broadcom 以外、または Broadcom 非 T1 ToR で AZURE DSCP map なし |
| `dscp_mode` | `"uniform"` | Broadcom T1 ToR (`DEVICE_METADATA.localhost.type` が `"ToRRouter"` かつ `ASIC_VENDOR == "broadcom"`) |
| `ecn_mode` | `"copy_from_outer"` | 全プラットフォーム固定 |
| `ttl_mode` | `"pipe"` | 全プラットフォーム固定 |

`ecn_mode` と `ttl_mode` は全プラットフォームで固定であり、CONFIG_DB 側からの変更手段がない。

### MUX_TUNNEL 定数 (tunneldecaporch.h:21)

```c
#define MUX_TUNNEL "MuxTunnel0"
```

DualToR の Mux トンネル名。SUBNET_DECAP とは直接関係しないが、TunnelDecapOrch が同一クラス内で管理するため参照される。CONFIG_DB から変更不可。

## CONFIG_DB 経由で変更可能な値（参考）

以下は `TUNNEL_DECAP_TABLE` フィールドとして APP_DB 経由で変更可能だが、`SUBNET_DECAP` テーブルフィールドには存在しない:

- `dscp_mode`: `uniform` / `pipe`（TUNNEL_DECAP_TABLE の update で変更可能だが、`ipinip.json.j2` のビルド時値が初期値）
- `ecn_mode`: `copy_from_outer` / `standard`（SAI create-only のため、作成後の変更は `SWSS_LOG_WARN` でスキップされる; tunneldecaporch.cpp:179）
- `encap_ecn_mode`: `standard` のみ対応（tunneldecaporch.cpp:187-189）
- `ttl_mode`: `uniform` / `pipe`（TUNNEL_DECAP_TABLE 更新で変更可能）

## Evidence

- `sonic-swss` `orchagent/tunneldecaporch.cpp:14,749-750`
- `sonic-swss` `orchagent/tunneldecaporch.h:21,97-103`
- `sonic-buildimage` `dockers/docker-orchagent/ipinip.json.j2:95-210`
