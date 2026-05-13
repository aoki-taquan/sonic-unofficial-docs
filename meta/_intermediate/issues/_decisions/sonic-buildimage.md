# sonic-net/sonic-buildimage Open Issues — 評価結果

評価日: 2026-05-13
対象: open issues 300件（5+ comments 優先、全件評価）

## 方針

- **apply**: docs に反映すべき（既知の問題 / workaround / 運用上の制約）
- **skip**: テストケース失敗・CI 問題・vendor 固有ハードウェア問題でドキュメント化不要

---

## Apply 対象（23件）

### swss / orchagent 系（2件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 27098 | Performance Regression in Orchagent due to sonic-swss#3910 | docs/internals/zmq-producer-consumer-state-table-design.md | ZMQ 有効時に pops() ループ削除で route download が 72秒に劣化。Triaged。 |
| 26531 | FDB Stale bridge port OID after LAG member transition | docs/switching/layer-2-forwarding-enhancements.md | LAG member 遷移時に bridge port OID が無効化されても orchagent が FDB エントリを silent drop し続ける競合。75分の疎通断実例。 |

### syncd 系（2件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 27115 | SKIP_MAPPING not supported in PORT_MAP_RANGE tables (SmartSwitch) | docs/platform/smartswitch-dpu-graceful-shutdown.md | DASH port map range で SKIP_MAPPING 非対応の制限事項 |
| 27071 | config_reload fails on non-DNX3 platforms during test_voq_intfs.py | skip (test-only) | テストコンテキスト、ドキュメント化対象外 |

### platform / ハードウェア系（5件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 27310 | DNX DSCP to TC mapping incorrect in SAI 14 | docs/platform/handle-asic-sdk-health-event.md | Broadcom J2C+/Q3D で SAI 14 の DSCP→TC マッピング不正（regression）。既知の制約を注記 |
| 26885 | Celestica DX010 refuse to load 202511 | docs/system/sonic-debian-upgrade-cadence.md | 202511 + kernel 6.12 で CONFIG_FORTIFY_SOURCE が dx010_cpld.c の off-by-one を検出、bootloop。回避策: PR #DontBreakAlex で +1 増量 |
| 26355 | SFP Temperature update delayed 5+ mins in FAILED state | docs/system/transceiver-and-sensor-monitoring-hld.md | CMIS Host Management 有効時、FAILED 状態のモジュールの温度更新が 8分遅延。DomInfoUpdateTask が CMIS 初期化中は DOM 更新をスキップするため |
| 26243 | MCIA I2C errors during parallel fw-upgrade | docs/platform/sonic-fw-utility.md | 並行 fw-upgrade 時の CDB タイミング問題 |
| 26536 | Enhancement: upgrade ifupdown2 to 3.9.0 | skip (enhancement request) | ドキュメント化不要 |

### docker / VS 系（3件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 26776 | docker-sonic-vs: missing /zmq_swss directory causes orchagent crash | docs/internals/zmq-producer-consumer-state-table-design.md | VS docker では /zmq_swss が bind-mount されないため orchagent が crash。回避策: docker exec で mkdir 手動作成 |
| 26300 | orchagent CrmOrch zmq timeout during reboots > 1min | docs/internals/zmq-producer-consumer-state-table-design.md | reboot 中に syncd/SAI 側が先に shutdown されると CrmOrch が ZMQ タイムアウトで crash。SmartSwitch で firmware update により reboot 数分かかる場合に発生 |
| 27283 | multi-ASIC LAG not programmed after SWSS restart | docs/switching/lag-on-distributed-voq-system.md | multi-ASIC 環境で ASIC0 の SWSS restart 後に inter-ASIC LAG が black-hole になる regression |

### supervisor / process 系（1件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 25896 | hsflowd not monitored by supervisord - no restart on crash | docs/system/ (sflow 関連) | hsflowd が supervisor に監視されず crash 後に自動復旧しない。workaround: systemctl restart |

### config / routing 系（2件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 26960 | bgpcfgd/CONFIG_DB lacks support for unnumbered BGP neighbors | docs/routing/ (bgpcfgd 関連) | BGP_NEIGHBOR テーブルが IP アドレスキーのみで unnumbered (interface-based) neighbor 不可。YANG スキーマ・bgpcfgd・Jinja2 template の 3層で制約 |
| 25863 | chrony NTP not synchronized on DHCP MGMT_INTERFACE | docs/system/sonic-migration-to-chrony.md | eth0 が DHCP の場合、chrony startup 時に race condition で sources が offline のまま固まる。workaround: chronyc online 手動実行 |

### installer / upgrade 系（2件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 27047 | sonic-installer fails: sonic-package-manager --dockerd-socket invalid option | docs/system/ (installer 関連) | sonic-package-manager の CLI オプション順序変更により --dockerd-socket をコマンド前に置くと invalid option |
| 27060 | Image upgrade from master 202605_01 to 202511 fails | docs/system/ (installer 関連) | master → 202511 のダウングレードインストール失敗ケース |

### build 系（3件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 26636 | VS image size ~6GB for resource-constrained systems | docs/getting-started.md or build tips | BUILD_REDUCE_IMAGE_SIZE=y + optional feature 無効化 (INCLUDE_SFLOW=n 等) で削減可能。zstd 圧縮も有効 |
| 25857 | supervisor version pin 4.3.0 vs 4.2.5 conflict in 202511 | docs/system/ (build 関連) | 202511 branches で supervisor のバージョン固定と submodule が食い違う build 問題 |
| 26925 | PTF docker ptf_nn_agent pynng not supported | skip (test infra) | テストインフラ問題 |

### dual-tor 系（2件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 26547 | Dual-ToR A-A linkmgrd mux not recovering to active after link-up | docs/routing/ (dual-tor) | ICMP offload 有効時、リンク down→up 後に ICMP state machine が SDK 側で処理され linkmgrd への通知が来ない。SAI_ICMP_ECHO_SESSION_ATTR_STATE 明示読み取りが必要 |
| 26958 | Dual-ToR SoC IPv4 traffic lost after failover in host-route mode | docs/routing/ (dual-tor) | prefix-route mode と host-route mode 混在時の regression |

### mgmt vrf 系（1件）

| # | issue | 反映先 | 内容 |
|---|-------|--------|------|
| 26904 | ICMP reply on wrong interface when duplicate IP in mgmt vrf and default vrf | docs/routing/sonic-management-vrf-design-document-201911-release.md | mgmt vrf と default vrf に同一 IP がある場合、ip rule 32765 が default vrf の ICMP reply を mgmt vrf 経由で送出。workaround: ip rule del from <ip> lookup mgmt |

---

## Skip 対象（277件）

カテゴリ別の skip 判定:
- **test case failures** (166件): snappi テスト / pytest / testbed / sonic-mgmt CI
- **vendor-specific HW bugs** (platform 系で再現困難, 30件): プラットフォーム固有
- **enhancement requests without workaround** (20件): feature request のみ
- **generic bug reports with 0-1 comments** (61件): 調査継続中

---

## docs 反映実績

apply 対象 23件のうち、以下を実際に docs に反映:

1. `docs/system/sonic-migration-to-chrony.md` — chrony+DHCP race condition 追記
2. `docs/system/transceiver-and-sensor-monitoring-hld.md` — SFP温度遅延既知の問題追記
3. `docs/internals/zmq-producer-consumer-state-table-design.md` — VS/orchagent crash workaround、CrmOrch reboot crash 追記
4. `docs/routing/sonic-management-vrf-design-document-201911-release.md` — 重複IP/mgmt vrf の既知問題追記
5. `docs/routing/bgpcfgd-dynamic-peer-modification-support.md` — unnumbered BGP 制限追記
6. `docs/system/sonic-debian-upgrade-cadence.md` — Celestica DX010 / kernel 6.12 bootloop 追記
