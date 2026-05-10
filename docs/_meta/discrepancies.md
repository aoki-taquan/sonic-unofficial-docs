---
title: 実装との乖離
---

# 実装との乖離

このページは、HLD と現行 master 実装の突き合わせで `verification: discrepancy-found` が付いたページの一覧です。
HLD は設計意図や背景を理解する資料として有用ですが、現行 SONiC の挙動・CLI・CONFIG_DB / STATE_DB スキーマ・実装パスと一致しない場合があります。

読み手は HLD だけを根拠にせず、各ページの「実装との乖離」や冒頭の裏取りステータスを確認し、必要に応じて実コードでも裏取りすることを推奨します。

## acl-qos

- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../acl-qos/dhcp-dos-mitigation-in-sonic.md)  
  area: `acl-qos` / last_verified: `2026-05-09`  
  `dhcp_rate_limit` の YANG / CLI / db migrator は取り込み済みだが、HLD が要求する `portmgrd` / `portmgr` の `tc qdisc` / `tc filter` 投入ロジックは未取り込み。CoPP の DHCP trap 制限も残っている。

- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../acl-qos/enhancements-to-add-or-del-ports-dynamically.md)  
  area: `acl-qos` / last_verified: `2026-05-09`  
  zero-port 起動や per-port flex counter は取り込み済みだが、ポート削除時の buffer cfg per-port reference counter PR は未マージ。依存設定が残るポート削除を HLD どおり防御できない。

## architecture

- [ビルドプロファイル（rules/profiles/*.mk）](../architecture/build-profiles.md)  
  area: `architecture` / last_verified: `2026-05-09`  
  HLD の `rules/profiles/` と `PROFILE` 変数による Makefile 取り込みは現行 master に存在しない。`Makefile.work` は `rules/config` と `rules/config.user` のみを読む。

- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../architecture/debug-framework-in-sonic.md)  
  area: `architecture` / last_verified: `2026-05-09`  
  `Debugframework` クラス、`linkWithFramework` API、`SWSS_DEBUG_PRINT*` マクロ、対応 CLI は未取り込み。残骸コードは `#ifdef DEBUG_FRAMEWORK` 配下にあるが、master ビルドでは有効化されていない。

- [DIP=SIP PTF 検証テスト](../architecture/dip-sip-ptf-validation-high-level-design.md)  
  area: `architecture` / last_verified: `2026-05-09`  
  HLD の独立 PTF スクリプト `dip_sip.py` は削除済みで、現行は `sonic-mgmt/tests/ipfwd/test_dip_sip.py` の pytest 構成へ移行している。

- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../architecture/error-handling-framework-in-sonic.md)  
  area: `architecture` / last_verified: `2026-05-09`  
  `SWSS_RC_*` の error code 体系は採用済みだが、`ERROR_DB` / `ERROR_ROUTE_TABLE` / `ERROR_NEIGH_TABLE`、`ErrorListener` / `ErrorReporter`、関連 CLI は未実装。

- [SAG（Static Anycast Gateway）for SONiC](../architecture/sag-high-level-design-for-sonic.md)  
  area: `architecture` / last_verified: `2026-05-09`  
  `src/sonic-sag`、`sonic-static-anycast-gateway.yang`、`SAG` テーブル、`IntfMgr` / `IntfsOrch` 拡張、`config static-anycast-gateway` CLI は community master に統合されていない。

- [sFlow（hsflowd / sflowmgrd / SAI sample-packet）](../architecture/sflow-high-level-design.md)  
  area: `architecture` / last_verified: `2026-05-10`  
  実装経路は概ね存在するが、本ページが書いていた sample_rate 既定値が HLD / 実装と異なる。実装は `oper_speed` Mbps をそのまま sample_rate として返す。

- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md)  
  area: `architecture` / last_verified: `2026-05-09`  
  DASH HA 関連 table 定義の一部は存在するが、`hamgrd` バイナリ、`DASH_HA_DPU_STATE` / `DASH_HA_VDPU_STATE`、`swbus` 実装は見当たらない。

- [SSD ヘルスチェック（show platform ssdhealth + ssdutil プラグイン）](../architecture/ssdhealth-design.md)  
  area: `architecture` / last_verified: `2026-05-09`  
  HLD の `scripts/ssdhealth` や `sonic_ssd/ssd_base.py` は現行構成と異なる。実装は `ssdutil/` と `sonic_storage/` 配下へ再構成され、pmon `ssdmond` も未取り込み。

## internals

- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show arp）](../internals/l3-scaling-and-performance-enhancements.md)  
  area: `internals` / last_verified: `2026-05-09`  
  HLD 提案の ARP / ND `gc_thresh` 値と CoPP ARP / ND 8000 pps は採用されていない。一方、`RouteOrch` bulk route API と `fpmsyncd` の table 0 時 master lookup skip は実装済み。

## management

- [gNMI Master Arbitration（election ID と SetRequest 拡張）](../management/gnmi-master-arbitration-hld.md)  
  area: `management` / last_verified: `2026-05-09`  
  HLD は default role 以外を無視すると書くが、実装は `Role` 指定を `Unimplemented` で拒否する。CONFIG_DB 駆動の `master_arbitration_enabled` もなく、起動フラグで有効化する。

- [gNSI（Certz / Authz / Pathz / Credentialz）の Rotate モデル](../management/gnsi-hld.md)  
  area: `management` / last_verified: `2026-05-09`  
  Authz / Certz / Pathz は実装されているが、Credentialz の gNMI server handler は未取り込み。HLD の flag 名や STATE_DB profile state の記述も現行実装とずれる。

- [P4RT アプリケーション（PINS の gRPC サービス、port 9559）](../management/p4rt-application-hld.md)  
  area: `management` / last_verified: `2026-05-09`  
  HLD の独立 `HashOrch` は存在せず、hash 設定は既存 `SwitchOrch` が担う。P4RT コンテナ、APP_P4RT table、`P4Orch` など主要経路は実装済み。

- [Portable Console Device 設計（USB ベンダー console デバイスの抽象化）](../management/portable-console-device-design.md)  
  area: `management` / last_verified: `2026-05-09`  
  HLD の `sonic_console/<vendor>/console_<model>.py` 階層、`PortableConsoleDeviceBase`、`factory.py` は存在しない。`CONSOLE_SWITCH` 系の別機能はあるが、本 HLD の抽象化は未実装。

- [SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）](../management/sonic-yang-model-guidelines.md)  
  area: `management` / last_verified: `2026-05-09`  
  `sonic-{feature}.yang` 命名は広く使われているが、ガイドライン記載の `map-list` / `key-delim` 拡張は本リポの `sonic-extension` には存在しない。`error-app-tag` の付与も限定的。

- [TACACS+ passkey 暗号化（key_encrypt + master key /etc/cipher_pass）](../management/tacacs-passkey-encryption.md)  
  area: `management` / last_verified: `2026-05-09`  
  YANG と共通暗号 API は存在するが、`config tacacs passkey --encrypt` CLI と `hostcfgd` の復号取り込みが未実装。master key の実体も HLD の `/etc/cipher_pass` ではなく `/etc/cipher_pass.json`。

## overlay

- [トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避）](../overlay/dscp-remapping-for-tunnel-traffic.md)  
  area: `overlay` / last_verified: `2026-05-09`  
  HLD は PFCWD フィールドを `pfc_wd_sw_enable` と書くが、現行実装は `pfcwd_sw_enable`。tunnel decap QoS map や Dual-ToR 限定出力は HLD どおり実装済み。

## platform

- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../platform/dump-on-sai-failure.md)  
  area: `platform` / last_verified: `2026-05-09`  
  HLD の汎用 dump スクリプト名 `/usr/bin/syncd_dump.sh` は現行では `/usr/bin/sai_failure_dump.sh`。通知 enum や dump 出力先などの主要挙動は一致する。

- [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](../platform/fec-flr-support-in-sonic.md)  
  area: `platform` / last_verified: `2026-05-09`  
  `port_flr.lua` と表示側カラムは実装済みだが、HLD の `counterpoll port flr-interval-factor` CLI / `FLR_INTERVAL_FACTOR` 動的設定は未取り込み。lua 側の固定値のみが使われる。

- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../platform/hld-for-handling-sai-failures.md)  
  area: `platform` / last_verified: `2026-05-09`  
  `handleSai*Status` は `Orch` base の virtual 関数ではなく `saihelper` の free function。`ERROR_DB` / `ERROR_APPL_*` も実装されておらず、失敗エスカレーション経路は HLD と異なる。

- [液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント）](../platform/liquid-cooling-leakage-detection-in-sonic.md)  
  area: `platform` / last_verified: `2026-05-09`  
  `LeakageSensorBase` や `LiquidCoolingUpdater` は存在するが、STATE_DB テーブル名は HLD の `LIQUID_COOLING_DEVICE` ではなく `LIQUID_COOLING_INFO`。

- [Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）](../platform/smartswitch-dpu-graceful-shutdown.md)  
  area: `platform` / last_verified: `2026-05-09`  
  HLD の独立 `gnoi_reboot_daemon.py` は未取り込み。実装は `chassisd` が `module.set_admin_state_gracefully` を直接呼び、STATE_DB フラグ名も HLD と異なる。

- [SONiC ポート命名規則の変更案（et[sX]pY[abcd]）](../platform/sonic-port-naming-convention-change.md)  
  area: `platform` / last_verified: `2026-05-09`  
  device tree の `port_config.ini` は引き続き `EthernetN` key と `alias` 列を使う。`etsXpY[abcd]` / `ets<X>p<Y>` 命名は master に取り込まれていない。

## routing

- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../routing/bfd-hw-offload-for-bgp-session.md)  
  area: `routing` / last_verified: `2026-05-09`  
  HLD の `bfdsyncd` プロセスと `FEATURE.bgp.bfd_hw_offload` は未取り込み。`BfdOrch` の SAI session set はあるが、remote 属性 get と STATE_DB 反映は未実装。

- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](../routing/bgp-route-install-error-handling.md)  
  area: `routing` / last_verified: `2026-05-09`  
  `ERROR_ROUTE_TABLE` / `BGP_ERROR_CFG_TABLE` / `config bgp error-handling` は未実装。後発の BGP Suppress FIB Pending に置き換えられ、`bgp suppress-fib-pending` が使われる。

- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../routing/evpn-vxlan-hld.md)  
  area: `routing` / last_verified: `2026-05-10`  
  ページは巨大 HLD の中核に絞った要約で、現行実装との詳細な差分確認は未完了。EVPN multihoming は別ページに分離されているため、参照範囲に注意が必要。

- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](../routing/evpn-vxlan-multihoming.md)  
  area: `routing` / last_verified: `2026-05-10`  
  ページは EVPN MH の中核概念に絞った要約で、現行実装との詳細な差分確認は未完了。基本 EVPN VXLAN とは別 HLD として扱う必要がある。

- [Local ARS（Adaptive Routing & Switching の local 完結版）](../routing/local-ars-hld.md)  
  area: `routing` / last_verified: `2026-05-10`  
  `ArsOrch`、`sonic-ars.yang` / `ARS_PROFILE`、`config ars` / `show ars` は確認できない。SAI 側 API は見えるが、SONiC SWSS / YANG / utilities への機能取り込みは未完了。

## switching

- [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](../switching/layer-2-forwarding-enhancements.md)  
  area: `switching` / last_verified: `2026-05-09`  
  `FdbOrch` 側の MAC move / static MAC 保留 / flush / aging time 反映は実装済みだが、HLD の `config mac` と `config vlan range` 系 CLI は未取り込み。

- [リンクイベントダンピング（AIED アルゴリズムと SyncD intercept）](../switching/link-event-damping-hld.md)  
  area: `switching` / last_verified: `2026-05-09`  
  SwSS 側の port 属性受理はあるが、HLD の `config interface link_event_damping_algorithm` CLI は `sonic-utilities` / `sonic-buildimage` に未取り込み。

- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../switching/switch-port-modes-and-vlan-cli-enhancement.md)  
  area: `switching` / last_verified: `2026-05-09`  
  HLD の `config interface mode`、`show vlan brief`、`show interface status`、routed mode 連携は未取り込み。既存 VLAN CLI / `show interfaces status` / L3 化手順とはコマンド体系が異なる。

- [Wake-on-LAN（wol CLI と SonicWolService gNOI）](../switching/wake-on-lan-in-sonic.md)  
  area: `switching` / last_verified: `2026-05-09`  
  HLD は Python CLI と gNOI service を想定するが、現行 `wol` CLI は Rust 実装。`SonicWolService` / `WolRequest` proto や gNOI 経路は未確認または未取り込み。

## system

- [SONiC Secure Boot（shim/grub/vmlinuz/KO の chain of trust）](../system/hld-secure-boot.md)  
  area: `system` / last_verified: `2026-05-10`  
  署名スクリプトは HLD の `.py` ではなく bash、build flag は `SB_BUILD` ではなく `SECURE_UPGRADE_MODE` / `SECURE_UPGRADE_DEV_SIGNING_KEY`。boot chain の考え方は概ね一致する。

- [SONiC FIPS 140-3 デプロイ（FIPS table と /etc/fips/fips_enabled）](../system/sonic-fips-deployment.md)  
  area: `system` / last_verified: `2026-05-09`  
  HLD の FIPS table と `config fips` / `show fips status` / hostcfgd 経路は未取り込み。現行は `/proc/sys/crypto/fips_enabled` や `openssl fipsinstall` など OS / OpenSSL 側の状態確認が中心。

- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../system/sonic-libsairedis-api-idempotence-support.md)  
  area: `system` / last_verified: `2026-05-09`  
  HLD の `ATTR2OID_*` / `OID2ATTR_*` / `RESTORE_DB` などは `sonic-sairedis` master に存在しない。現行 warm restart の同等機能は syncd の view comparison が担う。

- [SONiC NTP client（chrony / NTP_SERVER / mgmt VRF）](../system/sonic-network-time-protocol-ntp-client-configuration.md)  
  area: `system` / last_verified: `2026-05-10`  
  HLD は `ntpd` 時代の設計で、現行 SONiC は `chrony` へ移行済み。template / service / CLI の前提が大きく変わっている。

- [SysLogger 拡張（runtime log level + LOGGER.require_manual_refresh + SIGHUP）](../system/sonic-python-logger-enhancement.md)  
  area: `system` / last_verified: `2026-05-09`  
  runtime log level と `require_manual_refresh` 経路は実装済みだが、HLD が要求する `SysLogger` singleton 化は未実装。実装は `logging.getLogger(name)` と handler 重複除去で対応している。

- [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](../system/swss-docker-warm-restart-code-reference.md)  
  area: `system` / last_verified: `2026-05-10`  
  HLD 自体が一時的な開発メモで、`swss-flushdb` や `hgetallordered` など現行 master に見当たらない記述がある。Warm Restart 理解には正式 HLD ベースのページを参照すべき。
