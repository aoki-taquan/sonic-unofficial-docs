---
title: Reboot / Upgrade の発展トピック
description: Reboot / Upgrade の発展トピック — warm / fast / cold reboot の基本パスを押さえた後は、収束時間を縮める「express
  reboot」、multi-ASIC / chassis 級の同期、in-service upgrade との組合せが論点になる。
area: topics
verification: meta
last_verified: 2026-05-11
sources:
- docs/system/sonic-warm-reboot.md
- docs/system/fast-reboot-flow-improvements-hld.md
- docs/system/sonic-express-reboot-hld-spec.md
- docs/system/system-wide-warmboot.md
- docs/system/multi-asic-warm-reboot.md
related:
  cli:
  - config bgp
  - show bgp
  - show bfd
  config_db:
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_AGGREGATE_ADDRESS
  - BGP_PEER_GROUP
  - BGP_NEIGHBOR_AF
  - BGP_NEIGHBOR
  yang:
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
  - sonic-bgp-aggregate-address
  - sonic-bgp-sentinel
---

# Reboot / Upgrade の発展トピック

warm / fast / cold reboot の基本パスを押さえた後は、収束時間を縮める「express reboot」、multi-[ASIC](../../reference/glossary.md#term-asic) / chassis 級の同期、in-service upgrade との組合せが論点になる。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [architecture](architecture.md) と、area HLD の [sonic-warm-reboot](../../system/sonic-warm-reboot.md), [fast-reboot-flow-improvements-hld](../../system/fast-reboot-flow-improvements-hld.md), [sonic-express-reboot-hld-spec](../../system/sonic-express-reboot-hld-spec.md) で完結する。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `warm-reboot` / `fast-reboot` / `reboot` 系コマンド、[reference/config_db/WARM_RESTART](../../reference/config-db/index.md) に集約されている。
- **本ページ**は、基本 reboot を押さえた読者に対し、express reboot, chassis 級同期, gNOI 経由 upgrade などの発展領域だけを扱う。

## 発展トピック

- **Express reboot**: warm reboot のさらに先にある「ASIC を温存したまま OS だけ swap する」設計。`fast-reboot-flow-improvements` と `express-reboot` [HLD](../../reference/glossary.md#term-hld) を組み合わせて、[SAI](../../reference/glossary.md#term-sai) 状態の export / import と [syncd](../../reference/glossary.md#term-syncd) の handover を最小ダウンタイムで行う。
- **System-wide warm reboot**: 単一 [SONiC](../../reference/glossary.md#term-sonic) instance ではなく、複数 ASIC / chassis 全体を 1 回の手順で warm reboot する。`multi-asic-warm-reboot` と組み合わせて line card 順序や Supervisor のロールを設計する。
- **[gNOI](../../reference/glossary.md#term-gnoi) 駆動 upgrade**: `gnoi.os.Install` / `Activate` で controller から SONiC イメージを投入し、warm/fast reboot を制御 plane から発火。手動 ssh 不要化と監査ログ統合が利点。
- **graceful drain & restore**: reboot 前に [BGP](../../reference/glossary.md#term-bgp) / [BFD](../../reference/glossary.md#term-bfd) を drain し、[ECMP](../../reference/glossary.md#term-ecmp) から外れた状態で reboot する手順。`config bgp shutdown all` / `reliable-tsa` と組合せて切替の transient を避ける。
- **Warm reboot 中の orch 状態**: warm-restart 対応 daemon (bgpd, [swssconfig](../../reference/glossary.md#term-swssconfig), syncd, [teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd), lldpd 等) の `WARM_RESTART_TABLE` ステートマシン。reconciliation timeout の管理が要点。
- **2-stage reboot**: kernel kexec → SONiC 初期化 → 経路収束、を時系列で計測し、各 stage の wall clock を切り分けると改善ポイントが見える。

## Express reboot の内部設計

Express reboot は warm reboot の延長で、SAI 状態と data plane を保持したまま control plane だけ swap する。鍵となるのは (1) `syncd` の SAI object handle dump と新 image の `syncd` での再 attach、(2) `orchagent` の internal cache を `APPL_STATE_DB` 経由でリビルド、(3) `bgpd` の GR/LLGR による経路再学習を上位 plane 側でブロックしない、という 3 つの同期点。期待ダウンタイムは < 1 秒 (data plane forward 停止時間) であり、warm reboot (数秒〜十数秒) より大幅に短い。

実装の依存は [ASIC SDK](../../reference/glossary.md#term-asic-sdk) 側の `sai_switch_attribute_t::SAI_SWITCH_ATTR_FAST_API_ENABLE` と、SDK が持つ shared memory hand-off API。これに対応していない platform では express reboot は不可。

## graceful drain & TSA 連携

reboot 前に BGP / BFD を drain する手順は `reliable-tsa` (Traffic Shift Away) HLD で形式化されている。`config bgp shutdown all` だけでは ECMP から外れるまでに peer 側の hold timer 切れを待つため、`graceful-shutdown` community (RFC 8326) を付与して即時 deprefer させる流れが推奨される。drain 後の reboot で transient を最小化できる。

逆に reboot 後の `reliable-tso` (Traffic Shift Over) は、forwarding が確立してから順に peer に announce 再開する。SONiC では `BGP_DEVICE_GLOBAL.tsa_enabled` を切り替えるだけで template 経由で route-map 適用される設計。

## 既知の制約と回避方法

- **Warm reboot 中の経路 stale**: BGP graceful restart が機能しないと FIB が古いまま残り、収束後にループや誤転送が起こる。[FRR](../../reference/glossary.md#term-frr) 側 GR / LLGR 設定と peer 側互換を必ず確認する。
- **Fast reboot で counter リセット**: fast reboot は ASIC reset を伴うため、`COUNTERS_DB` の累積値が 0 に戻る。telemetry collector 側で counter rollover として誤検出する事例がある。
- **Express reboot の platform 依存**: SAI capability に依存し、対応 ASIC が限られる。実機サポート状況を `sonic-platform` 配下の sai profile / platform docs と照合する。
- **[Multi-ASIC](../../reference/glossary.md#term-multi-asic) reboot の順序**: Supervisor → Line card の順を間違えると Chassis DB の整合が崩れる。`config chassis modules shutdown` / `startup` の順序を厳守する。

## 将来計画 / ロードマップ

- Express reboot の community 対応拡大と SAI attribute 標準化が継続テーマ。
- gNOI / gNSI 経由の upgrade orchestration が enterprise 運用で標準化方向。手動手順の自動化と監査トレースの統合が論点。
- Smart switch / [DASH](../../reference/glossary.md#term-dash) 構成 ([13](../13-dash-smartswitch/index.md)) では [DPU](../../reference/glossary.md#term-dpu) 側の独立した reboot 経路が追加され、[NPU](../../reference/glossary.md#term-npu) と DPU の協調 reboot の設計が future work。

## 関連 RFC / 仕様書

- [RFC 4724](https://datatracker.ietf.org/doc/html/rfc4724) — BGP [Graceful Restart](../../reference/glossary.md#term-graceful-restart)
- [RFC 9494](https://datatracker.ietf.org/doc/html/rfc9494) — Long-Lived Graceful Restart (LLGR)
- [RFC 5882](https://datatracker.ietf.org/doc/html/rfc5882) — BFD Generic Application
- [RFC 8071](https://datatracker.ietf.org/doc/html/rfc8071) — NETCONF Call Home (集中管理参考)
- [gNOI OS service spec](https://github.com/openconfig/gnoi/blob/main/os/os.proto)

## upstream 開発の最新動向

- `sonic-buildimage` で `fast-reboot` / `warm-reboot` script の logging / status report 改善 PR が継続。stage ごとの elapsed time 出力で運用デバッグが容易になる。
- `sonic-swss` の orch 群で warm restart reconciliation のタイムアウトと race condition 修正 PR が定期的に入る。
- DASH / [SmartSwitch](../../reference/glossary.md#term-smartswitch) 関連で DPU 独立 reboot のサポート議論が進行中。NPU 側 reboot との同期がどこまで required かは scenario ごとに分岐。

## トラブルシュート観点

- warm reboot 後に経路が一部欠落するときは、`WARM_RESTART_TABLE|<daemon>` の `state` が `reconciled` まで到達したかを確認する。`bgp` daemon が `restored` 止まりだと FRR の GR 受信側で遅延しているサイン。
- syncd handover で失敗する場合、`/var/log/syslog` の `syncd: brcm_sai`/`mlnx_sai` 等 SAI vendor log と、`syncd.sh` の elapsed time を点検する。`config save` 前 / 後の `CONFIG_DB.json` 差分も復旧時に役立つ。
- gNOI Install/Activate の失敗時は `sonic-installer list` で image slot を確認し、必要なら `sonic-installer set-default <prev>` で前 image に戻して `reboot`。

## 検証パスとラボ要件

- VS lab で warm reboot を再現するときは、`docker exec swss supervisorctl restart all` ではなく `sonic-installer` 経由の本物 warm reboot path を `pretest_warm_reboot.sh` で実行する。[orchagent](../../reference/glossary.md#term-orchagent) reconciliation 動作が VS でも観察可能。
- chassis 級は `sonic-mgmt` の `chassis_reboot` test suite が CHASSIS_APP_DB の `module_state` 遷移を assertion している。

## 関連ページ (追補)

- [Independent DPU upgrade](../../system/independent-dpu-upgrade.md)
- [Reboot cause information via telemetry agent](../../system/reboot-cause-information-via-telemetry-agent.md)
- [Reboot support blocking mode](../../system/reboot-support-blockingmode-in-sonic.md)
- [Secure upgrade](../../system/secure-upgrade.md)
- [Smart switch reboot HLD](../../system/smart-switch-reboot-high-level-design.md)
- [SONiC Debian upgrade cadence](../../system/sonic-debian-upgrade-cadence.md)
- [What are the development phases and scope for warm reboot](../../system/what-are-the-development-phases-and-scope-for-warm-reboot.md)
- [Multi-ASIC warm reboot](../../system/multi-asic-warm-reboot.md)
- [System-wide warm boot](../../system/system-wide-warmboot.md)
- [SONiC express reboot HLD spec](../../system/sonic-express-reboot-hld-spec.md)
- [Fast reboot flow improvements HLD](../../system/fast-reboot-flow-improvements-hld.md)
- [SONiC warm reboot](../../system/sonic-warm-reboot.md)
- [12 Multi-ASIC / VOQ: chassis 級 reboot 順序](../12-multi-asic-voq/index.md)
- [10 gNMI / OpenConfig: gNOI OS service との連携](../10-gnmi-openconfig/index.md)
- [13 DASH / SmartSwitch: DPU 独立 reboot との同期](../13-dash-smartswitch/index.md)
- [02 BGP: graceful restart / LLGR と warm reboot の整合](../02-bgp/index.md)
- [15 Security / AAA: secure upgrade と signed image](../15-security-aaa/index.md)

## 関連ページ

- [SONiC warm reboot](../../system/sonic-warm-reboot.md)
- [Fast reboot flow improvements](../../system/fast-reboot-flow-improvements-hld.md)
- [Express reboot HLD](../../system/sonic-express-reboot-hld-spec.md)
- [System-wide warm boot](../../system/system-wide-warmboot.md)
- [Multi-ASIC warm reboot](../../system/multi-asic-warm-reboot.md)
- [12 Multi-ASIC / VOQ](../12-multi-asic-voq/index.md)

<!-- glossary-links-injected: 5c9b3765d470 -->
