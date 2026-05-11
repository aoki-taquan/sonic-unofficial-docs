---
title: 発展トピック
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
---

# 発展トピック

この章のメインは NAT / DHCP ですが、付帯する管理系サービスとして time / DNS / TWAMP / terminal server を同じ章でまとめて読みます。OS daemon と CONFIG_DB のテンプレート生成パスを共通言語にすると、各機能が並列に見えてきます。

## NTP / chrony 移行

SONiC は長らく `ntpd`（後に NTPsec）を使っていましたが、master では `chrony` への移行が完了しています。背景は次の通りです。

- `ntpd` は long jump を完全には抑止できず、1 時間ずれていると 12 分以内に step してしまう。データプレーンへの副作用懸念から step は避けたい。
- slew 中は kernel time discipline が disable され、HW RTC が更新されず reboot で巻き戻る。
- port 123 を listen し続ける必要があり、interface 追加削除への追従が面倒。
- たまに NTP packet を送らなくなる不安定動作。

chrony は client 専門（slew 専念）、kernel time discipline を維持、必要時のみソケットを開く、という設計でこれらを解決します。`NTP|global` の `vrf` フィールドと `NTP_SERVER|<ip>` の組合せから `chrony.conf` を生成します。詳細は [chrony 移行ページ](../../system/sonic-migration-to-chrony.md) と [NTP client 設定ページ](../../system/sonic-network-time-protocol-ntp-client-configuration.md) を参照してください。

CONFIG_DB / YANG リファレンスは次の通りです。

- [NTP_GLOBAL CONFIG_DB](../../reference/config-db/ntp-global.md)
- [NTP_SERVER CONFIG_DB](../../reference/config-db/ntp-server.md)
- [sonic-ntp YANG](../../reference/yang/sonic-ntp.md)

CLI は `chronyc sources` / `chronyc tracking` で同期状況を見ます。`show ntp` も後方互換として使えますが、内部は chrony です。management VRF を使う構成では `NTP|global` の `vrf: mgmt` を必ず付けます。

## 静的 DNS

`DNS_NAMESERVER` テーブルから `resolv-config.service` が `/etc/resolv.conf` を生成し、host と各 container に展開します。`config dns nameserver add <ip>` で書き込み、`show dns nameserver` で確認します。`update-containers` スクリプトが各 container の resolv.conf も更新する点が特徴で、container ごとに名前解決の挙動が変わらないよう設計されています。詳細は [static DNS ページ](../../system/static-dns-configuration.md) と [sonic-dns YANG](../../reference/yang/sonic-dns.md) を参照してください。

## TWAMP Light

TWAMP Light（RFC 5357）は data plane の双方向 latency / jitter / packet loss 測定プロトコルで、control connection を持たない軽量プロトコルです。SONiC では ASIC offload（`SAI_TWAMP_*` 系 API）を想定した HLD があり、`CFG_TWAMP_SESSION_TABLE` で Session-Sender / Reflector を定義する設計になっています。ただし community master では SAI 拡張 / orch / CLI が未取り込みで、HLD-only ステータスです。実機検証時はまずベンダー SDK 側の TWAMP サポートを確認してください。詳細は [TWAMP Light HLD ページ](../../system/twamp-light-hld.md) を参照してください。

QoS / Observability 寄りの機能ですが、「control 接続を持たない軽量サービス」という性格上、本章の発展トピックとして置きます。

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
