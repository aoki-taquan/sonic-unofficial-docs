---
title: gNMI / OpenConfig の発展トピック
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
---

# gNMI / OpenConfig の発展トピック

gNMI / gNOI / Translib / Transformer の基本パスを押さえた後は、telemetry の規模拡張、認証境界 (gNSI)、新しい RPC への対応が次の論点になる。

## 発展トピック

- **gNMI dial-out (publish to collector)**: 通常の gNMI Subscribe は server-driven だが、規模が増えると collector 側で多数の subscription を維持するコストが高い。dial-out では target 側から collector に push する構成で、scale 上有利。`telemetry` docker と外部 collector の組合せが議題。
- **OpenConfig wildcard subscribe**: `/interfaces/interface[name=*]/state/counters` のような wildcard query で per-port stream を一括取得する用途。Sample interval と server CPU 負荷のトレードオフがある。
- **gNOI による OS upgrade**: `gnoi.os.Install` / `Activate` で SONiC イメージを集中投入する運用。warm/fast reboot との組み合わせで in-service upgrade を実現する。
- **gNSI による証明書 / authz の管理**: `gnsi.certz` / `gnsi.authz` で gNMI の TLS 証明書と RBAC ポリシーを動的に更新する。controller 側で証明書ローテーションを行うと SONiC 側はサービス停止なしで更新できる。
- **Transformer の自前 callback 追加**: 既存 OpenConfig path に対応する CONFIG_DB が無いとき、Go callback (transformer/xfmr) を書いて変換ルールを足す。プラグイン的に拡張できる。
- **SAI Redis streaming (低レベル)**: gNMI 経由ではなく、`COUNTERS_DB` を直接 streaming する場合の挙動。debug 用途で `redis-cli psubscribe` でリアルタイム counter を見る。

## 既知の制約と回避方法

- **subscription scale limit**: target あたりの concurrent stream 数には実用上の上限があり、過剰登録で telemetry docker が CPU 100% になる例がある。collector を複数にして load を分割する。
- **OpenConfig path と SONiC schema のミスマッチ**: SONiC 固有機能 (Dual-ToR mux、warm-reboot state) は OpenConfig path に対応が無く、`sonic-mgmt-common` の vendor-augmented YANG で表現される。
- **gNMI Set の atomicity**: 単一 SetRequest 内の複数 update は SONiC 側で完全 atomic とは限らない。CONFIG_DB の partial commit で transient 状態が見える可能性。
- **証明書回転中の reconnect**: controller が証明書を更新した後、client 側 dial を一度切る必要がある場合がある。gNSI による hot swap が対応していれば回避可能。

## 将来計画 / ロードマップ

- gNxI suite (gNMI / gNOI / gNSI / gRIBI) は OpenConfig コミュニティで継続拡張中。SONiC 側は `sonic-gnmi` の依存ライブラリ更新で取り込む。
- gRIBI を経由した RIB 直接注入が議論されており、controller 側で経路を直接 push する用途で SDN ベース fabric の管理が変わる可能性。
- OpenConfig の network-instance / VRF モデルの SONiC 対応は段階的で、未対応 path には vendor augment が並走する。

## 関連 RFC / 仕様書

- [RFC 6020](https://datatracker.ietf.org/doc/html/rfc6020) / [RFC 7950](https://datatracker.ietf.org/doc/html/rfc7950) — YANG 1.0 / 1.1
- [RFC 8040](https://datatracker.ietf.org/doc/html/rfc8040) — RESTCONF
- [RFC 6241](https://datatracker.ietf.org/doc/html/rfc6241) — NETCONF (gNMI と比較)
- [gNMI Specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)
- [gNOI / gNSI / gRIBI](https://github.com/openconfig)
- [OpenConfig models](https://github.com/openconfig/public)

## upstream 開発の最新動向

- `sonic-gnmi` repo で gNSI authz と certz 取り込み、TLS 認証経路のリファクタが継続。
- `sonic-mgmt-common` (Translib / Transformer) で OpenConfig path カバレッジ拡張 PR が頻繁。Routing / BGP / VRF / QoS の path 追加が主軸。
- Telemetry docker の memory footprint 改善と subscription scale 上限緩和の PR が継続。collector 側 (gnmic、gnxi) も community 主導でツール成熟が進む。

## 関連ページ

- [09 Telemetry / SNMP](../09-telemetry-snmp/index.md)
- [11 Reboot / Upgrade](../11-reboot/index.md) — gNOI OS upgrade と組み合わせる前提
- [15 Security / AAA](../15-security-aaa/index.md) — gNSI authz / certz の境界
