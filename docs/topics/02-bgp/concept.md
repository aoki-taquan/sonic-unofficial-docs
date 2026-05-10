---
title: 概要
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 概要

SONiC の BGP は、FRR が経路プロトコルを処理し、SONiC daemon が設定入力と ASIC 反映を受け持つ構成で理解すると迷いにくい。BGP neighbor を設定したいときは CONFIG_DB/CLI/YANG から入る。一方で、学習された route が forwarding 可能になるまでには bgpd、zebra、fpmsyncd、orchagent、syncd、SAI/ASIC が関わる。

## まず責務を分ける

| 層 | 主な責務 | 代表コンポーネント |
| --- | --- | --- |
| 設定入力 | CLI、gNMI/REST、CONFIG_DB の受付 | sonic-utilities、Management Framework |
| FRR 設定反映 | CONFIG_DB 差分を FRR 設定へ変換 | bgpcfgd、frrcfgd |
| BGP 制御 | neighbor、policy、best path、RIB | bgpd |
| 経路配布 | FRR RIB から SONiC への FPM 出力 | zebra、dplane_fpm_sonic |
| SONiC 転送面反映 | APPL_DB から ASIC_DB/SAI へ | fpmsyncd、orchagent、syncd |

従来の中心は `bgpcfgd` で、Jinja template と一部の動的反映により FRR 設定を作る。OpenConfig BGP を Management Framework から扱う構成では `frrcfgd` が CONFIG_DB の差分から FRR vty コマンドを生成する。`frrcfgd` と `bgpcfgd` は同時に動かす前提ではなく、`DEVICE_METADATA.localhost.frr_mgmt_framework_config` で切り替える設計である。詳しくは [FRR-BGP Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) を参照する。

## router-id はどこで決まるか

BGP router-id は、明示設定がない場合に既存ロジックで決まる。明示したい場合は `DEVICE_METADATA.localhost.bgp_router_id` を使う設計がある。これは FRR 側だけの設定ではなく、SONiC の起動時設定生成に関わるため、どの値が最終的に FRR に入るかを確認する必要がある。詳細は [BGP router-id を明示的に設定する](../../routing/bgp-router-id-explicitly-configured.md) にまとまっている。

## FRR upgrade は何に影響するか

FRR upgrade は単なるパッケージ更新ではない。SONiC では FRR fork、patch、docker image、起動テンプレート、FPM plugin、Management Framework との接点が絡む。BGP 機能を読むときは、HLD が前提にする FRR version と現在の SONiC 実装が一致するかを確認する必要がある。upgrade 手順と patch 管理の観点は [SONiC における FRR upgrade](../../routing/detailed-steps-to-upgrade-frr-in-sonic.md) を参照する。

## この章での読み方

BGP の設定問題は [設定](setup.md) へ進む。経路が ASIC に入らない、あるいは advertise が遅れる問題は [アーキテクチャ](architecture.md) と [運用](operations.md) を先に読む。大量経路、障害収束、FIB pending、dynamic peer のように実装差分が大きい機能は [内部実装](internals.md) で比較する。

## 関連ページ

- [BGP router-id を明示的に設定する](../../routing/bgp-router-id-explicitly-configured.md)
- [FRR-BGP Unified Mgmt Framework](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md)
- [SONiC における FRR upgrade](../../routing/detailed-steps-to-upgrade-frr-in-sonic.md)
