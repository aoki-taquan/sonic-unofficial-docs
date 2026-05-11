---
title: HLD と実装の乖離 一覧（discrepancy-index）
description: "HLD と実装の乖離 一覧（discrepancy-index） — このページは、verification: discrepancy-found が付いた全ページを自動収集して並べたものです。meta/scripts/gen_discrepancy_index.py で生成されます。"
verification: meta
last_verified: 2026-05-11
---

# HLD と実装の乖離 一覧（discrepancy-index）

このページは、`verification: discrepancy-found` が付いた全ページを自動収集して並べたものです。`meta/scripts/gen_discrepancy_index.py` で生成されます。

SONiC コミュニティ master の [HLD](../../reference/glossary.md#term-hld) には、(1) 設計提案のみで実装が取り込まれなかったもの、(2) 取り込まれた後に別設計へ置き換えられたもの、(3) 部分的に取り込まれて HLD の記述と乖離しているもの、が混在しています。本プロジェクトでは該当ページに `verification: discrepancy-found` を付け、frontmatter `monitor:` で次のように分類しています。

- `not_implemented`: HLD 提案が現行 master に取り込まれていない
- `evolved_beyond_hld`: 取り込まれたが HLD 記述と乖離した形で進化／置換された

全 **46** ページ。

## area 別件数

| area | 件数 |
|------|-----:|
| `acl-qos` | 2 |
| `architecture` | 8 |
| `internals` | 1 |
| `management` | 8 |
| `overlay` | 1 |
| `platform` | 7 |
| `routing` | 6 |
| `switching` | 4 |
| `system` | 9 |

## monitor タグ別件数

| monitor | 件数 |
|---------|-----:|
| `deprecated`（deprecated） | 3 |
| `evolved_beyond_hld`（HLD と乖離した形で実装/進化） | 20 |
| `not_implemented`（未実装） | 14 |
| `partially_implemented`（partially_implemented） | 9 |

## エントリ一覧（area 別）

### acl-qos

- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../../acl-qos/dhcp-dos-mitigation-in-sonic.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05 時点で `.cache/sonic-sources/` を裏取りした結果、本機能は **データ層 + CLI のみ取り込み済み、肝心の TC 投入経路が未実装** な部分実装状態。

- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../../acl-qos/enhancements-to-add-or-del-ports-dynamically.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05 時点の `.cache/sonic-sources/` master を裏取り。

### architecture

- [DIP=SIP PTF 検証テスト](../../architecture/dip-sip-ptf-validation-high-level-design.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05 時点でテスト実体は **PTF スタンドアロンから pytest 配下へ移行済み** で、HLD の記述（ansible + ptftests）はファイル配置レベルで古い。

- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../../architecture/debug-framework-in-sonic.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05 時点で本 framework は **master に取り込まれておらず、HLD のみ**（2019-07 v0.3 から 6 年以上停滞）。

- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05 時点で本 framework は **エラーコード enum だけが先行採用され、ERROR_DB / ErrorListener / CLI は丸ごと未実装** な部分採用状態。

- [SAG（Static Anycast Gateway）for SONiC](../../architecture/sag-high-level-design-for-sonic.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05 時点で **SAG コード / [YANG](../../reference/glossary.md#term-yang) / CLI は community master に取り込まれておらず、HLD 提案段階**。

- [SSD ヘルスチェック（show platform ssdhealth + ssdutil プラグイン）](../../architecture/ssdhealth-design.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD の二段プラグイン構造（`SsdBase` / `SsdUtil`）と CLI（`show platform ssdhealth`）は概ね素直に取り込まれているが、HLD で Open Question として残されていた **常時監視デーモン `ssdmond` は現状実装が見当たらない**。

- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05 時点で **schema 層（HA Set / HA Scope の table 名）は先行採用済みだが、hamgrd バイナリ・actor framework・swbus・VDPU / DPU_STATE は未取り込み**。HLD の半分弱までが master に入っている部分実装状態。

- [sFlow（hsflowd / sflowmgrd / SAI sample-packet）](../../architecture/sflow-high-level-design.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-10`
  
  2026-05 時点で本機能の **全体取り込みは完了している** が、HLD 文書中の「sample_rate の既定値テーブル」だけが実装と不一致である。

- [ビルドプロファイル（rules/profiles/*.mk）](../../architecture/build-profiles.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05 時点で本機能は **HLD は提案されたが master にコードが入っていない**、純粋な未実装状態である。

### internals

- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show arp）](../../internals/l3-scaling-and-performance-enhancements.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。

### management

- [Console Switch（serial hub の reverse SSH 集約）](../../management/sonic-console-switch.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  per-page queue で既出の通り、HLD 1.1 の中核実装は部分的のみ。再確認した結果:

- [P4RT アプリケーション（PINS の gRPC サービス、port 9559）](../../management/p4rt-application-hld.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  実コード裏取りで判明した HLD との差分（verified at: 2026-05-09）:

- [Portable Console Device 設計（USB ベンダー console デバイスの抽象化）](../../management/portable-console-device-design.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD が掲げる「USB 接続のポータブル console-switch デバイス」を制御するための実装は、CLI / YANG / [CONFIG_DB](../../reference/glossary.md#term-config_db) スキーマのいずれにも入っていない。

- [SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）](../../management/sonic-yang-model-guidelines.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。本ガイドラインで前提とされる SONiC YANG 拡張のうち、**`sonic-buildimage` 側の yang-models と `sonic-mgmt-common` 側で取り込み状況が分裂している**点が最大の罠。

- [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](../../management/smart-switch-gnmi-feedback-design-omit-in-toc.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  HLD が要件として掲げる以下の構成要素を現行 master の `sonic-gnmi` に確認できなかった。

- [TACACS+ passkey 暗号化（key_encrypt + master key /etc/cipher_pass）](../../management/tacacs-passkey-encryption.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。

- [gNMI Master Arbitration（election ID と SetRequest 拡張）](../../management/gnmi-master-arbitration-hld.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  実コード裏取りで判明した HLD との差分（verified at: 2026-05-09, sonic-gnmi @ `eb635b7679b260c3fd0786a6d0734fc8e82c9a22`）:

- [gNSI（Certz / Authz / Pathz / Credentialz）の Rotate モデル](../../management/gnsi-hld.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  実コード裏取りで判明した HLD との差分（verified at: 2026-05-09, sonic-gnmi @ `eb635b76`）:

### overlay

- [トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避）](../../overlay/dscp-remapping-for-tunnel-traffic.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  verified at: 2026-05-09。

### platform

- [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](../../platform/fec-flr-support-in-sonic.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。本機能の **コアロジック (port_flr.lua) と CLI 表示 (portstat) は取り込み済み**だが、**HLD で示唆された動的設定 CLI（`counterpoll port flr-interval-factor`）は未実装**であり、poll 周期は lua スクリプト内のハードコード値に固定されている。

- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../../platform/hld-for-handling-sai-failures.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD と実装には次の乖離がある:

- [SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP）](../../platform/dump-on-sai-failure.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  **読者への影響**:

- [SONiC ポート命名規則の変更案（et[sX]pY[abcd]）](../../platform/sonic-port-naming-convention-change.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD の提案 4 stage は **いずれも採用されていない**。

- [Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）](../../platform/smartswitch-dpu-graceful-shutdown.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD と実装には次の乖離がある:

- [拡張 LPO デバッグレジスタ（VMA / OMA per-lane モニタを Redis に公開）](../../platform/enhanced-lpo-debug-registers-hld.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  `sonic-platform-common` を grep した結果、本 HLD が前提とする `CmisEnhancedLpoApi` / `CmisEnhancedLpoCodes` / `CmisEnhancedLpoMemMap` クラス、`xcvr_api_factory.py` での Arista 系 vendor 分岐、Page 01h Byte 195 = 0x4C の enhanced LPO 検出ロジック、`LPOTxHostInputVMA*` / `LPORxInputOMA*` フィールドのいずれも HEAD に取り込まれていない（`grep -rn "CmisEnhancedLpoApi\|LPOTxHostInputVMA\|enhanced_lpo" .cache/sonic-sources/sonic-platform-common/` でヒット 0）。…

- [液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント）](../../platform/liquid-cooling-leakage-detection-in-sonic.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD と実装には次の乖離がある:

### routing

- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](../../routing/bgp-route-install-error-handling.md)  
  monitor: `deprecated` / last_verified: `2026-05-09`
  
  2026-05-09 時点の現行 master を裏取り。**本 HLD は採用されず、後発の [BGP](../../reference/glossary.md#term-bgp) Suppress FIB Pending に置き換えられている**。

- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../../routing/bfd-hw-offload-for-bgp-session.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD と実装には次の乖離がある:

- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](../../routing/evpn-vxlan-multihoming.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-10`
  
  2026-05-10 時点の現行 master を裏取り。**[EVPN](../../reference/glossary.md#term-evpn) Multihoming 機能は SONiC メインリポジトリには取り込まれていない**。

- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../../routing/evpn-vxlan-hld.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-10`

- [Local ARS（Adaptive Routing & Switching の local 完結版）](../../routing/local-ars-hld.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-10`
  
  2026-05-10 時点の現行 master を裏取り。**Local ARS は HLD 提案のみで SONiC SWSS / utilities / yang への取り込みは未完了**。

- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  `sonic-swss/fpmsyncd/routesync.cpp` と `sonic-swss/fpmsyncd/routesync.h` を確認。HLD のコア部分は master に取り込み済み:

### switching

- [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](../../switching/layer-2-forwarding-enhancements.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-09`
  
  実コード裏取りで判明（verified at: 2026-05-09）:

- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05-11 時点の現行 master を裏取り。

- [Wake-on-LAN（wol CLI と SonicWolService gNOI）](../../switching/wake-on-lan-in-sonic.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-09`
  
  2026-05-11 時点の現行 master を裏取り。

- [リンクイベントダンピング（AIED アルゴリズムと SyncD intercept）](../../switching/link-event-damping-hld.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-09`
  
  2026-05-11 時点の現行 master を裏取り。

### system

- [SONiC FIPS 140-3 デプロイ（FIPS table と /etc/fips/fips_enabled）](../../system/sonic-fips-deployment.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-09`
  
  CONFIG_DB の `FIPS|global` 表記は HLD どおりで問題なし。

- [SONiC NTP client（chrony / NTP_SERVER / mgmt VRF）](../../system/sonic-network-time-protocol-ntp-client-configuration.md)  
  monitor: `deprecated` / last_verified: `2026-05-11`
  
  2026-05-11 時点の現行 master を裏取り。

- [SONiC Secure Boot（shim/grub/vmlinuz/KO の chain of trust）](../../system/hld-secure-boot.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-10`
  
  2026-05-11 時点の現行 master を裏取り。

- [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](../../system/swss-docker-warm-restart-code-reference.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-11 時点の現行 master を裏取り。

- [SysLogger 拡張（runtime log level + LOGGER.require_manual_refresh + SIGHUP）](../../system/sonic-python-logger-enhancement.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-09`
  
  2026-05-11 時点の現行 master を裏取り。

- [TWAMP Light（Session-Sender / Session-Reflector）](../../system/twamp-light-hld.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  **読者への影響**:

- [Warmboot Manager（shutdown orchestration / reconciliation 統一）](../../system/warmboot-manager-hld.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  per-page queue で既出の通り提案 HLD は未採用。再走査でも:

- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../../system/sonic-libsairedis-api-idempotence-support.md)  
  monitor: `deprecated` / last_verified: `2026-05-09`
  
  2026-05-11 時点の現行 master を裏取り。

- [ローカルユーザパスワード init 時リセット（long reset button + reset-local-users-passwords.service）](../../system/reset-local-users-passwords-during-init-hld.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  per-page queue で既出の通り、HLD が定義する専用機構は未取り込み。`.cache/sonic-sources/` 全体を再走査した結果:

## 監査基準の取り扱い

本ページ群（`verification: discrepancy-found` のページ）は、「機能としては完結していなくても、代わりに HLD と実装の差分を整理して読み手に渡す」ことを目的としています。品質監査 (`meta/quality-audit-*.md`) における **軸 6 (完結性)** は、本ページ群では「乖離説明の整理度」（monitor タグ妥当性 / 「実装との乖離」セクションの構造化 / 裏取り evidence / 読み手への next-action）に読み替えて評価します。詳細は `meta/templates/SCHEMA.md` の 「`discrepancy-found` ページの軸 6 評価基準」セクション、および `meta/quality-audit-guide.md` を参照してください。

<!-- glossary-links-injected: 2c50e311bc81 -->
