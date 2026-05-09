---
title: Weighted ECMP（WCMP / BGP link-bandwidth ext community）
area: routing
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/wcmp/wcmp-design.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - BGP_DEVICE_GLOBAL
  cli:
    - config bgp device-global wcmp
    - show bgp device-global
  yang: []
---

!!! info "裏取りステータス: code-verified"
    `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py` で `wcmp_template = ... bgpd/wcmp/bgpd.wcmp.conf.j2`、`wcmp_enabled` キー処理、`configure_wcmp(data)` を master で確認。`docker-fpm-frr/frr/bgpd/wcmp/` テンプレートディレクトリも存在。

# Weighted ECMP（WCMP / BGP link-bandwidth ext community）

## 概要

各 ToR-Spine リンクが部分故障した際、ECMP は **生存 link の容量差を反映できない** ため均等分散して輻輳を起こす。**Weighted ECMP (WCMP, W-ECMP, UCMP)** は **BGP link bandwidth 拡張コミュニティ** で各 path の利用可能帯域を運び、FRR / Zebra が 1〜255 に正規化した weight で NHG member を作る[^1]。SONiC 側 SWSS / SAI は既に NHG member weight をサポートしているので、本 HLD は **FRR を WCMP モードで動かすための CLI / CONFIG_DB / templates** の整備が中心。L3 用途を **In scope**、EVPN Type-5 は **Out of scope**。

## 動作仕様

### Dataflow

```mermaid
flowchart LR
  TOR[ToR (server側)<br/>route-map wcmp-map<br/>set extcommunity bandwidth num-multipaths] -- BGP advertise --> SP[Spine]
  SP --> RTOR[Remote ToR]
  RTOR -. link 故障 .- SP
  SP -- updated bandwidth --> ZEBRA[FRR / Zebra]
  ZEBRA --> NHG[NHG member weights<br/>(normalized 1-255)]
  NHG --> FPM[fpmsyncd]
  FPM --> RO[Route OA / orchagent]
  RO --> SD[syncd]
  SD --> SAI[SAI: NHG member weight]
```

- 入口 ToR（anycast / ECMP server 側）が `route-map wcmp-map permit 100` で `set extcommunity bandwidth num-multipaths` を付与[^1]
- 受信 BGP は default 動作で **link bandwidth ext community を weight に変換**。一部 path が community 不持ちなら **通常 ECMP に fallback**
- Zebra が NHG を再計算 → fpmsyncd → orchagent (Route OA) → SAI

### FRR 設定 (L3)

```
route-map wcmp-map permit 100
  set extcommunity bandwidth num-multipaths
exit
router bgp 65100
  ...
  address-family ipv4 unicast
    neighbor SPINE route-map wcmp-map out
    neighbor SPINE activate
  exit-address-family
end
```

### FRR 設定 (EVPN Type-5、L2VPN evpn)

```
address-family l2vpn evpn
  advertise ipv4 unicast route-map wcmp-map
  neighbor SPINE activate
exit-address-family
```

EVPN は `docker_routing_config_mode` が `split` / `split-unified` のときのみ有効[^1]。

### CONFIG_DB

```
BGP_DEVICE_GLOBAL|STATE:
  wcmp_enabled = "true" | "false"
```

initial config（`init_cfg.json.j2`）で **default `false`**[^1]。

### Configuration daemon

`DeviceGlobalCfgMgr` クラスに `set_wcmp` API を追加。CONFIG_DB の `BGP_DEVICE_GLOBAL|STATE` 変更を受けて jinja2 template `bgpd.wcmp.conf.j2`（`sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/wcmp/`）を反映する[^1]:

```jinja
! template: bgpd/wcmp/bgpd.wcmp.conf.j2
{%- if wcmp_enabled == 'true' %}
  set extcommunity bandwidth num-multipaths
{%- else %}
  no set extcommunity bandwidth
{%- endif %}
! end of template
```

**SWSS OA は変更不要**: NHG member weight は既存仕様で通る[^1]（[WCMP SWSS HLD #738]）。

[WCMP SWSS HLD #738]: https://github.com/sonic-net/SONiC/pull/738

### CLI

```
config bgp device-global wcmp <enabled|disabled>
show bgp device-global [-j|--json]
```

```
$ show bgp device-global
TSA        WCMP
---------  --------
Disabled   Enabled
```

### Weight の正規化

- 各 NHG 内で `bw / total_bw` 比を **1..255** に正規化[^1]
- すべて 0 / 同一値の場合は通常 ECMP と等価
- multipath の一部に bandwidth コミュニティが無い場合は **全体 ECMP fallback**

<!-- evidence:
source: sonic-net/SONiC/doc/wcmp/wcmp-design.md#L211-L223 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  FRR converts the incoming BGP link bandwidth extended community values into proportionated weight
  among the ecmp members in such a way that the cumulative value of individual weights is normalized to 255
  ... NH weights on routes are reported to fpmsyncd and further via Redis DB to Route OA
reasoning: 1-255 正規化と fpmsyncd 経由で SAI に下る経路の根拠。
-->

## Warm / Fast boot

- CONFIG_DB の `wcmp_enabled` を再読込して FRR を再起動 / reload する想定
- 詳細は本 HLD では別途扱われていない[^1]

## 制限事項

- **EVPN Type-5 は scope 外**（本 HLD では将来）
- 一部 multipath が link-bandwidth コミュニティを持たないと ECMP fallback
- normalize の精度は 8bit (1-255) 内なので極端な比は表現できない
- ASIC によっては NHG member weight の resource 制約あり（HLD には未明記、SWSS HLD 側参照）

## 干渉する機能

- **BGP PIC**: NHG を共有
- **EVPN over L2VPN**: 将来 scope の Type-5
- **`local-ars-hld`** 等の他 multipath 系: weight 計算ロジックは独立
- **fpmsyncd / Route OA**: 既存 NHG member weight の経路を流用

## 引用元

[^1]: `sonic-net/SONiC` `doc/wcmp/wcmp-design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- DeviceGlobalCfgMgr.set_wcmp の sonic-buildimage / sonic-bgpcfgd 取り込み確認
- bgpd.wcmp.conf.j2 (docker-fpm-frr/frr/bgpd/wcmp) の存在確認
- BGP_DEVICE_GLOBAL|STATE wcmp_enabled の sonic-yang-models 反映確認
- init_cfg.json.j2 デフォルト wcmp_enabled=false 確認
- FRR 側の link-bandwidth ext community → NHG weight 1-255 正規化動作の検証
- show bgp device-global / config bgp device-global wcmp の sonic-utilities 取り込み確認
-->
