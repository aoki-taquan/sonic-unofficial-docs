---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/management/packetio.md
  - docs/management/send-to-ingress-hld.md
  - docs/management/p4rt-read-cache-hld.md
---

# 運用

PINS の運用で確認したいのは「コントローラの Write は ASIC に届いているか」「PacketIO / Send to Ingress の経路は活きているか」「Read が遅いときキャッシュは効いているか」の 3 点です。それぞれ確認順を整理します。

## Write が ASIC に届いているかの確認

P4Orch は同期書き込みなので、コントローラの RPC レスポンスがそのまま成否を表します。レスポンスが OK にも関わらず ASIC に効いていないと感じる場合は、APPL_STATE_DB の対応エントリを直接見ます。

1. `redis-cli -n 0 KEYS "P4RT_TABLE:*"` で APPL_DB 側に書き込みが残っているか確認
2. `redis-cli -n 14 KEYS "..."` で APPL_STATE_DB に成否が返っているか確認
3. `redis-cli -n 1 KEYS "ASIC_STATE:*"` で実 SAI オブジェクトの存在を確認

詳細な責務分担は [P4Orch HLD](../../internals/p4-orchagent.md) と [P4RT App HLD](../../management/p4rt-application-hld.md) を参照してください。

## CPU packet path の確認

PacketIO Receive は generic netlink + CoPP trap group が両方そろわないと届きません。次の順で確認します。

1. CoPP の対象 trap group が `genetlink_name` / `genetlink_mcgrp_name` を持っているか（既定では `queue2_group1`）
2. SAI hostif が `SAI_HOSTIF_TABLE_ENTRY_CHANNEL_TYPE_GENETLINK` で作られているか（`copporch.cpp` の `createGenetlinkHostIf()` 経路）
3. p4rt-app プロセスが generic netlink family `psample` を受信しているか
4. controller が install した punt flow に match する trap が発火しているか（CoPP の counter / `aclshow` で確認）

ベンダ側 kernel の `genl_packet` filter 実装が無い ASIC では、HLD が想定する PacketIO は動きません。詳細は [PacketIO HLD](../../management/packetio.md) を参照してください。

## Send to Ingress の使い分け

Send to Ingress は **ASIC の ingress pipeline にパケットを再注入する** モードで、次の場面で使い分けます。

- **使う**: controller が宛先を決め切れず、ECMP / WCMP を ASIC に判定させたい。あるいはテスト用途で「CPU 起点で ingress に入れたパケットの ASIC ルーティングを観察したい」。
- **使わない**: 送信先 port がすでに決まっている。この場合は Direct transmit（対応 netdev のソケット）で十分。

ホスト側で `ip link show send_to_ingress` が出るか、`PortsOrch::addSendToIngressHostIf()` が呼ばれたかが入口になります。詳細は [Send to Ingress HLD](../../management/send-to-ingress-hld.md) を参照してください。

## Read が遅いときの確認

Read の遅さは AppDb への `HGETALL` 大量発行が支配的でした。entity_cache_（旧 table_entry_cache_）が効いていれば 16,000 フローでも約 40ms に収まる想定です。

- p4rt-app のログで Read 時間が 1 秒オーダーで残っていれば、キャッシュが回避されている経路を疑う
- Write 中の整合不一致は `P4RuntimeImpl::VerifyState()` が `VerifyP4rtTableWithCacheEntities` で検出する
- warm boot 時の事前充填は `warm_boot_state_adapter_` がフレームワーク化済み

詳細は [Read キャッシュ HLD](../../management/p4rt-read-cache-hld.md) を参照してください。
