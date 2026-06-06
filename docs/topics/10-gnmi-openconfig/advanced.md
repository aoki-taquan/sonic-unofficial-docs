---
title: gNMI / OpenConfig の発展トピック
description: gNMI / OpenConfig の発展トピック — gNMI / gNOI / Translib / Transformer
  の基本パスを押さえた後は、telemetry の規模拡張、認証境界 (gNSI)、新しい RPC への対応が次の論点になる。
area: topics
verification: meta
last_verified: 2026-06-06
sources:
- repo: sonic-net/sonic-gnmi
  path: dialout/dialout_client/dialout_client.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnsi_certz.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-gnmi
  path: gnmi_server/gnsi_authz.go
  ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
- repo: sonic-net/sonic-mgmt-common
  path: translib/transformer/xlate.go
  ref: f71cf829883c36963455cf4d90fe16dae35f0b80
- repo: sonic-net/sonic-mgmt-common
  path: translib/transformer/xfmr_interface.go
  ref: f71cf829883c36963455cf4d90fe16dae35f0b80
related:
  cli: []
  config_db:
  - GNMI
  - TELEMETRY
  - TELEMETRY_CLIENT
  yang: []
  _no_related_cli: true
  _no_related_yang: true
---

# gNMI / OpenConfig の発展トピック

[gNMI](../../reference/glossary.md#term-gnmi) / [gNOI](../../reference/glossary.md#term-gnoi) / Translib / Transformer の基本パスを押さえた後は、telemetry の規模拡張、認証境界 (gNSI)、新しい RPC への対応が次の論点になる。

## 発展トピック

- **gNMI dial-out (publish to collector)**: 通常の gNMI Subscribe は server-driven だが、規模が増えると collector 側で多数の subscription を維持するコストが高い。dial-out では target 側から collector に push する構成で、scale 上有利。`telemetry` docker と外部 collector の組合せが議題。
- **OpenConfig wildcard subscribe**: `/interfaces/interface[name=*]/state/counters` のような wildcard query で per-port stream を一括取得する用途。Sample interval と server CPU 負荷のトレードオフがある。
- **gNOI による OS upgrade**: `gnoi.os.Install` / `Activate` で [SONiC](../../reference/glossary.md#term-sonic) イメージを集中投入する運用。warm/fast reboot との組み合わせで in-service upgrade を実現する。
- **gNSI による証明書 / authz の管理**: `gnsi.certz` / `gnsi.authz` で gNMI の TLS 証明書と RBAC ポリシーを動的に更新する。controller 側で証明書ローテーションを行うと SONiC 側はサービス停止なしで更新できる。
- **Transformer の自前 callback 追加**: 既存 OpenConfig path に対応する [CONFIG_DB](../../reference/glossary.md#term-config_db) が無いとき、Go callback (transformer/xfmr) を書いて変換ルールを足す。プラグイン的に拡張できる。
- **[SAI](../../reference/glossary.md#term-sai) [Redis](../../reference/glossary.md#term-redis) streaming (低レベル)**: gNMI 経由ではなく、`COUNTERS_DB` を直接 streaming する場合の挙動。debug 用途で `redis-cli psubscribe` でリアルタイム counter を見る。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [architecture](architecture.md) と、area [HLD](../../reference/glossary.md#term-hld) の [sonic-gnmi-server-interface-design](../../management/sonic-gnmi-server-interface-design.md), [model-based-replace-delete-in-mgmt-framework-transformer](../../management/model-based-replace-delete-in-mgmt-framework-transformer.md), [openconfig-support-for-ethernet-interfaces](../../management/openconfig-support-for-ethernet-interfaces.md) に集約されている。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `show gnmi` / `config gnmi` 系、[reference/config_db/TELEMETRY](../../reference/config-db/index.md) と、area HLD [gnmi-usage](../../management/gnmi-usage.md) に集約されている。
- **本ページ** では、上の基本パスを踏まえた上での「規模拡張」「認証境界」「新 RPC への追従」という運用観点の発展トピックだけを扱う。

## dial-out と scale 設計の詳細

gNMI dial-out (publish to collector) は server-driven Subscribe の補完で、target 側が active TCP connection を保ち、自分から push する。collector 側で session 数を減らせるため、数千台の fabric では運用負荷が下がる。SONiC では `sonic-gnmi` リポジトリの `dialout/dialout_client` パッケージ (`package telemetry_dialout`) が CONFIG_DB (`db 4`) の `TELEMETRY_CLIENT` テーブルから `Global` / `DestinationGroup_<name>` / `Subscription_<name>` の 3 種キーを読み取り、destination ごとに goroutine を立てる。`Global` キーには `src_ip` / `retry_interval` / `encoding` (`JSON_IETF` / `ASCII` / `BYTES` / `PROTO`) / `unidirectional` が、`Subscription_<name>` には `path_target` (`COUNTERS_DB` 等) と `paths` (`COUNTERS/Ethernet*` 等) が入る<!-- evidence: sonic-net/sonic-gnmi dialout/dialout_client/dialout_client.go L410-L434 (TELEMETRY_CLIENT スキーマコメント) -->。collector 側 (`gnmic`, `gnxi`) の prometheus exporter と組み合わせると metrics pipeline が完成する。

OpenConfig wildcard subscribe は `/interfaces/interface[name=*]/state/counters` のような path で per-port stream を一括取得するが、sample interval を 1s で全 port 投入すると server CPU が 100% に達する例がある。対策は (1) `STREAM` モードを `SAMPLE` に絞る、(2) heartbeat interval を 30s 以上に広げる、(3) collector を分割して target を pin する、の 3 通り。

## gNOI / gNSI の運用境界

gNOI OS の `Install` / `Activate` / `Verify` は SONiC の `sonic-installer` を内側で呼ぶ。`Install` は image を `/host/image-<ver>/` に展開、`Activate` は `next-boot` を切り替える。warm/fast reboot と組み合わせるなら、`Activate` 直後に gNOI System.Reboot を `WARM` mode で呼ぶ。失敗した場合の rollback は `Activate` で前 image を指定するだけで再起動を要するため、運用 runbook 側で plan B を持つ。

gNSI `certz` は TLS 証明書を hot-swap する RPC で、`gnmi-server` が listen socket を rebuild せずに新 cert を採用する。controller 側で短命証明書を回転させる構成が想定されている<!-- evidence: sonic-net/sonic-gnmi gnmi_server/gnsi_certz.go (gNSI certz サーバ実装) -->。`authz` は RBAC ポリシー (gRPC method × role × user) を JSON で push する RPC で、`gnmi_server/gnsi_authz.go` がメタデータ (`testdata/gnsi/authz_meta.json` 等) と組み合わせて検証する<!-- evidence: sonic-net/sonic-gnmi gnmi_server/gnsi_authz.go + testdata/gnsi/authz_meta.json -->。`pathz` は path 単位のアクセス制御で、SONiC では `pathz_authorizer/` package として個別 directory が存在するが本稿執筆時点では限定的な実装。

## Transformer 拡張と native YANG

OpenConfig path の SONiC 未対応領域に対しては、`sonic-mgmt-common` (Translib / Transformer) に Go callback (xfmr) を追加することで CONFIG_DB マッピングを足せる。`translib/transformer/` 配下の各 `xfmr_*.go` が `init()` で `XlateFuncBind(name, fn)` に callback を register する流れで<!-- evidence: sonic-net/sonic-mgmt-common translib/transformer/xlate.go L43 (func XlateFuncBind) + xfmr_showtech.go L30 / xfmr_testxfmr_callbacks.go (利用例) -->、`PreXfmrFunc` / `PostXfmrFunc` / `TableXfmrFunc` / `ValueXfmrFunc` などの型に応じて key / field / table / subtree / pre / post の callback を埋める<!-- evidence: sonic-net/sonic-mgmt-common translib/transformer/xfmr_interface.go L199-L262 (Xfmr 関数型定義) -->。vendor augmented YANG は `sonic-mgmt-common/models/yang/` 配下に置かれ、OpenConfig deviation よりも自由度が高い。

## 既知の制約と回避方法

- **subscription scale limit**: target あたりの concurrent stream 数には実用上の上限があり、過剰登録で telemetry docker が CPU 100% になる例がある。collector を複数にして load を分割する。
- **OpenConfig path と SONiC schema のミスマッチ**: SONiC 固有機能 (Dual-ToR mux、warm-reboot state) は OpenConfig path に対応が無く、`sonic-mgmt-common` の vendor-augmented [YANG](../../reference/glossary.md#term-yang) で表現される。
- **gNMI Set の atomicity**: 単一 SetRequest 内の複数 update は SONiC 側で完全 atomic とは限らない。CONFIG_DB の partial commit で transient 状態が見える可能性。`replace` 操作は `model-based-replace-delete-in-mgmt-framework-transformer` の HLD 通り、サブツリー単位での差し替えになり、[orchagent](../../reference/glossary.md#term-orchagent) 側で transient な flap を観察することがある。
- **証明書回転中の reconnect**: controller が証明書を更新した後、client 側 dial を一度切る必要がある場合がある。gNSI による hot swap が対応していれば回避可能。
- **master arbitration**: 複数 controller が同時に Set を出すと last-writer-wins になるため、`gnmi-master-arbitration` の `MasterArbitration` 拡張を有効化して election token を交換する。

## 将来計画 / ロードマップ

- gNxI suite (gNMI / gNOI / gNSI / gRIBI) は OpenConfig コミュニティで継続拡張中。SONiC 側は `sonic-gnmi` の依存ライブラリ更新で取り込む。
- gRIBI を経由した RIB 直接注入が議論されており、controller 側で経路を直接 push する用途で SDN ベース fabric の管理が変わる可能性。SONiC では `gribi-server` の prototype が議論段階。
- OpenConfig の network-instance / [VRF](../../reference/glossary.md#term-vrf) モデルの SONiC 対応は段階的で、未対応 path には vendor augment が並走する。
- `save-on-set` (Set 直後に CONFIG_DB を `config_db.json` へ persist) は long-running deployment では default ON が望ましいが、scale 時の I/O コストがあり opt-in 設計が継続。

## 関連 RFC / 仕様書

- [RFC 6020](https://datatracker.ietf.org/doc/html/rfc6020) / [RFC 7950](https://datatracker.ietf.org/doc/html/rfc7950) — YANG 1.0 / 1.1
- [RFC 8040](https://datatracker.ietf.org/doc/html/rfc8040) — RESTCONF
- [RFC 6241](https://datatracker.ietf.org/doc/html/rfc6241) — NETCONF (gNMI と比較)
- [gNMI Specification](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)
- [gNOI / gNSI / gRIBI](https://github.com/openconfig)
- [OpenConfig models](https://github.com/openconfig/public)

## upstream 開発の最新動向

- `sonic-gnmi` repo で gNSI authz と certz 取り込み、TLS 認証経路のリファクタが継続。
- `sonic-mgmt-common` (Translib / Transformer) で OpenConfig path カバレッジ拡張 PR が頻繁。Routing / [BGP](../../reference/glossary.md#term-bgp) / VRF / [QoS](../../reference/glossary.md#term-qos) の path 追加が主軸。
- Telemetry docker の memory footprint 改善と subscription scale 上限緩和の PR が継続。collector 側 (gnmic、gnxi) も community 主導でツール成熟が進む。
- [SmartSwitch](../../reference/glossary.md#term-smartswitch) 向け gNMI feedback design (`smart-switch-gnmi-feedback-design`) が [DPU](../../reference/glossary.md#term-dpu) 側 telemetry を含めて議論中。

## 関連ページ

- [09 Telemetry / SNMP](../09-telemetry-snmp/index.md)
- [11 Reboot / Upgrade](../11-reboot/index.md) — gNOI OS upgrade と組み合わせる前提
- [15 Security / AAA](../15-security-aaa/index.md) — gNSI authz / certz の境界

<!-- glossary-links-injected: 8ba32e5aa69d -->
