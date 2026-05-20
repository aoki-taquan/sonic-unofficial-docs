---
title: 発展トピック
description: 発展トピック — この章のメインは NAT / DHCP ですが、付帯する管理系サービスとして time / DNS / TWAMP /
  terminal server を同じ章でまとめて読みます。OS daemon と CONFIG_DB のテンプレート生成パスを共通言語にすると、各機能が並列に見えてきます。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/system/sonic-network-time-protocol-ntp-client-configuration.md
- docs/system/sonic-migration-to-chrony.md
- docs/system/static-dns-configuration.md
- docs/reference/config-db/ntp-global.md
- docs/reference/config-db/ntp-server.md
- docs/reference/yang/sonic-ntp.md
- docs/reference/yang/sonic-dns.md
- docs/system/twamp-light-hld.md
- docs/architecture/1-udev-rules-design-for-terminal-server.md
related:
  cli:
  - show nat
  - config nat
  - config vrf
  - config qos
  config_db:
  - NAT
  - VRF
  - STATIC_NAT
  - STATIC_NAPT
  - NAT_POOL
  - NAT_BINDINGS
  - NAT_GLOBAL
  yang:
  - sonic-ntp
  - sonic-dns
  - sonic-nat
  - sonic-vrf
---

# 発展トピック

この章のメインは [NAT](../../reference/glossary.md#term-nat) / DHCP ですが、付帯する管理系サービスとして time / DNS / TWAMP / terminal server を同じ章でまとめて読みます。OS daemon と [CONFIG_DB](../../reference/glossary.md#term-config_db) のテンプレート生成パスを共通言語にすると、各機能が並列に見えてきます。

## NTP / chrony 移行

[SONiC](../../reference/glossary.md#term-sonic) は長らく `ntpd`（後に NTPsec）を使っていましたが、master では `chrony` への移行が完了しています。背景は次の通りです。

- `ntpd` は long jump を完全には抑止できず、1 時間ずれていると 12 分以内に step してしまう。データプレーンへの副作用懸念から step は避けたい。
- slew 中は kernel time discipline が disable され、HW RTC が更新されず reboot で巻き戻る。
- port 123 を listen し続ける必要があり、interface 追加削除への追従が面倒。
- たまに NTP packet を送らなくなる不安定動作。

chrony は client 専門（slew 専念）、kernel time discipline を維持、必要時のみソケットを開く、という設計でこれらを解決します。`NTP|global` の `vrf` フィールドと `NTP_SERVER|<ip>` の組合せから `chrony.conf` を生成します。詳細は [chrony 移行ページ](../../system/sonic-migration-to-chrony.md) と [NTP client 設定ページ](../../system/sonic-network-time-protocol-ntp-client-configuration.md) を参照してください。

CONFIG_DB / [YANG](../../reference/glossary.md#term-yang) リファレンスは次の通りです。

- [NTP_GLOBAL CONFIG_DB](../../reference/config-db/ntp-global.md)
- [NTP_SERVER CONFIG_DB](../../reference/config-db/ntp-server.md)
- [sonic-ntp YANG](../../reference/yang/sonic-ntp.md)

CLI は `chronyc sources` / `chronyc tracking` で同期状況を見ます。`show ntp` も後方互換として使えますが、内部は chrony です。management [VRF](../../reference/glossary.md#term-vrf) を使う構成では `NTP|global` の `vrf: mgmt` を必ず付けます。

## 静的 DNS

`DNS_NAMESERVER` テーブルから `resolv-config.service` が `/etc/resolv.conf` を生成し、host と各 container に展開します。`config dns nameserver add <ip>` で書き込み、`show dns nameserver` で確認します。`update-containers` スクリプトが各 container の resolv.conf も更新する点が特徴で、container ごとに名前解決の挙動が変わらないよう設計されています。詳細は [static DNS ページ](../../system/static-dns-configuration.md) と [sonic-dns YANG](../../reference/yang/sonic-dns.md) を参照してください。

## TWAMP Light

TWAMP Light（RFC 5357）は data plane の双方向 latency / jitter / packet loss 測定プロトコルで、control connection を持たない軽量プロトコルです。SONiC では [ASIC](../../reference/glossary.md#term-asic) offload（`SAI_TWAMP_*` 系 API）を想定した [HLD](../../reference/glossary.md#term-hld) があり、`CFG_TWAMP_SESSION_TABLE` で Session-Sender / Reflector を定義する設計になっています。ただし community master では [SAI](../../reference/glossary.md#term-sai) 拡張 / orch / CLI が未取り込みで、HLD-only ステータスです。実機検証時はまずベンダー SDK 側の TWAMP サポートを確認してください。詳細は [TWAMP Light HLD ページ](../../system/twamp-light-hld.md) を参照してください。

[QoS](../../reference/glossary.md#term-qos) / Observability 寄りの機能ですが、「control 接続を持たない軽量サービス」という性格上、本章の発展トピックとして置きます。

## Terminal server（udev rules）

ターミナルサーバ機能を持つ装置はフロントパネルに複数シリアルポートを持ち、内部で USB hub + USB-to-UART チップ（例: cp210x）経由で `/dev/ttyUSB<N>` に枚挙されます。デフォルトの枚挙順は単一ポート故障で詰まるため、SONiC は udev rules で物理ポート番号と symlink 名（`/dev/Mytty-<N>` 等）を固定する設計を採用しています。haliburton platform で `50-ttyUSB-C0.rules` として実装されています。詳細は [udev rules ページ](../../architecture/1-udev-rules-design-for-terminal-server.md) を参照してください。

terminal server は SONiC を「ネットワーク装置」ではなく「コンソールサーバ装置」として使う場合の周辺機能ですが、管理サービス層という共通点で本章に含めました。

## 関連ページ

- [chrony 移行](../../system/sonic-migration-to-chrony.md)
- [SONiC NTP client](../../system/sonic-network-time-protocol-ntp-client-configuration.md)
- [静的 DNS 設定](../../system/static-dns-configuration.md)
- [NTP_GLOBAL CONFIG_DB](../../reference/config-db/ntp-global.md)
- [NTP_SERVER CONFIG_DB](../../reference/config-db/ntp-server.md)
- [sonic-ntp YANG](../../reference/yang/sonic-ntp.md)
- [sonic-dns YANG](../../reference/yang/sonic-dns.md)
- [TWAMP Light HLD](../../system/twamp-light-hld.md)
- [terminal server udev rules](../../architecture/1-udev-rules-design-for-terminal-server.md)

## 発展トピック

- **NAT64 / DNS64**: IPv6 専用 host から IPv4 to の通信を NAT64 + DNS64 で橋渡しする。SONiC NAT は主に IPv4 NAT に焦点が当たっており、NAT64 は ASIC capability と SAI 対応が前提。
- **DHCPv4 / v6 server (in-box)**: 通常は relay 用途だが、lab / mgmt 用途で in-box DHCP server を動かす構成が議論される (`dnsmasq` ベース)。
- **NTP 精度向上 (PTP との比較)**: 1ms 級の同期が必要なら PTP (IEEE 1588) を使うが、SONiC PTP は HLD 段階の機能が多い。chrony で得られる精度の限界を理解しておく。
- **DHCP server identifier override**: 複数 DHCP relay 装置で同じ subnet を扱うとき、server identifier override (RFC 5107) を使って応答の経路を制御する。
- **TWAMP Light の SAI offload**: control 接続なし双方向遅延測定を ASIC で実行する。SONiC への取り込みは段階的。

## 既知の制約と回避方法

- **NAT セッション [TCAM](../../reference/glossary.md#term-tcam) 上限**: NAT セッション数は ASIC TCAM に依存する。`SAI_OBJECT_TYPE_NAT_ENTRY` の capacity を `sai capability` で確認し、aging timer で session 数を制御する。
- **DHCP DoS 緩和との競合**: 章 07 の DHCP DoS 緩和と DHCP relay の rate-limit が二重にかかると、正規 DHCP も落ちる。レイヤを 1 つに揃える。
- **chrony の VRF bind**: mgmt VRF を使う場合、chrony 設定の `bindaddress` / `bindacqaddress` を mgmt 側に固定しないと data plane に漏れる。
- **resolv.conf の container 同期遅延**: `update-containers` 実行が遅れると container 内で古い DNS server が残る。手動 restart の手順を運用 runbook に残す。

## 将来計画 / ロードマップ

- TWAMP Light の community master 取り込み（SAI 拡張と orch / CLI）が future work。
- NAT64 / DNS64 の正式サポート議論が断続的にある。
- DHCP relay の YANG モデル整備と Option 79 / Option 82 の細分化拡張。

## 関連 RFC / 仕索書

- [RFC 5357](https://datatracker.ietf.org/doc/html/rfc5357) — TWAMP / TWAMP-Light
- [RFC 8186](https://datatracker.ietf.org/doc/html/rfc8186) — TWAMP-Light Reflector roles
- [RFC 5107](https://datatracker.ietf.org/doc/html/rfc5107) — DHCP Server Identifier Override
- [RFC 3022](https://datatracker.ietf.org/doc/html/rfc3022) — Traditional NAT
- [RFC 6146](https://datatracker.ietf.org/doc/html/rfc6146) / [RFC 6147](https://datatracker.ietf.org/doc/html/rfc6147) — NAT64 / DNS64
- [RFC 5905](https://datatracker.ietf.org/doc/html/rfc5905) — NTPv4
- [IEEE 1588-2008](https://standards.ieee.org/ieee/1588/4355/) — PTP

## upstream 開発の最新動向

- `sonic-buildimage` の chrony 移行関連 PR は完了側に入り、test plan 拡充と timezone まわりの細部修正が継続。
- NAT 関連は `natorch` / `natsyncd` で aging / counter / scale 改善 PR が散発的に入る。
- TWAMP Light は HLD のみで community PR は限定的。SAI extension の議論待ちが続く状況。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [internals](internals.md) と、関連 HLD の [NAT in SONiC](../../architecture/nat-in-sonic.md), [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md), [chrony 移行](../../system/sonic-migration-to-chrony.md), [静的 DNS 設定](../../system/static-dns-configuration.md) で完結する。`natorch` / `natsyncd` の [APPL_DB](../../reference/glossary.md#term-appl_db) ↔ [ASIC_DB](../../reference/glossary.md#term-asic_db) 経路、DHCP relay の Option 82/79 制御は internals で扱う。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `config nat` / `show nat` / `config dhcp_relay` / `show dhcp_relay` / `config ntp` 系、`NAT`, `STATIC_NAT`, `DHCP_RELAY`, `DNS_NAMESERVER`, `NTP_SERVER` の [CONFIG_DB スキーマ](../../reference/config-db/index.md) に集約。
- **本ページ** は NAT64/DNS64、TWAMP Light、PTP / chrony 切替、resolv.conf container 同期、DHCP DoS 緩和との競合など、章境界をまたぐ発展領域だけを扱う。

## トラブルシュート観点

- NAT セッションが超過しているときは、`show nat translations count` で current/max を確認し、`config nat add timeout` で aging を短縮する。`SAI_STATUS_INSUFFICIENT_RESOURCES` が [syncd](../../reference/glossary.md#term-syncd) ログに出る場合は TCAM 物理上限到達。
- DHCP relay で `discover` が forward されない場合、`show dhcp_relay ipv4 helper` で helper IP の到達性、[VLAN](../../reference/glossary.md#term-vlan) 上の broadcast bind、Option 82 の `link-selection` が relay/server で一致しているかを点検する。
- chrony が NTP sync しないときは、`chronyc tracking` / `chronyc sources -v` で Stratum / reach、`chronyc activity` で source 数を確認。mgmt VRF 配下では `bindaddress` の固定が必須。

## 検証パスとラボ要件

- NAT scale 検証は `pktgen` で per-src/per-dst NAT を 100k〜1M セッション規模で生成し、`show nat statistics` の hit/miss と aging 後の解放速度を計測する。target は 1M セッションで session install < 30 秒、release < 60 秒。
- DHCP relay の Option 82/79 検証は `dhcpgen` などで client → relay → server を流し、Wireshark で sub-option (circuit-id / remote-id / Option 79 link-layer addr) を点検する。
- chrony 切替後の時刻同期は、reboot → cold start → `chronyc tracking` で Stratum 到達と offset (target < 10ms) を確認する。

## 関連ページ (追補)

- [NAT in SONiC](../../architecture/nat-in-sonic.md)
- [DHCPv4 Relay Agent](../../architecture/dhcpv4-relay-agent.md)
- [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md)
- [SONiC migration to chrony](../../system/sonic-migration-to-chrony.md)
- [Static DNS configuration](../../system/static-dns-configuration.md)
- [TWAMP Light HLD](../../system/twamp-light-hld.md)
- [05 Dual-ToR: DHCPv6 loopback source mode](../05-dual-tor/index.md)
- [07 ACL / CoPP / Mirror: DHCP DoS 緩和との境界](../07-acl-copp-mirror/index.md)
- [15 Security / AAA: mgmt VRF と service bind](../15-security-aaa/index.md)

<!-- glossary-links-injected: ec18b66e3507 -->
