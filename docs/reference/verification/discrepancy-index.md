---
title: HLD と実装の乖離 一覧（discrepancy-index）
description: "HLD と実装の乖離 一覧（discrepancy-index） — このページは、verification: discrepancy-found が付いた全ページを自動収集して並べたものです。meta/scripts/gen_discrepancy_index.py で生成されます。"
verification: meta
last_verified: 2026-05-11
---

# HLD と実装の乖離 一覧（discrepancy-index）

このページは、`verification: discrepancy-found` が付いた全ページを自動収集して並べたものです。`meta/scripts/gen_discrepancy_index.py` で生成されます。

SONiC コミュニティ master の HLD には、(1) 設計提案のみで実装が取り込まれなかったもの、(2) 取り込まれた後に別設計へ置き換えられたもの、(3) 部分的に取り込まれて HLD の記述と乖離しているもの、が混在しています。本プロジェクトでは該当ページに `verification: discrepancy-found` を付け、frontmatter `monitor:` で次のように分類しています。

- `not_implemented`: HLD 提案が現行 master に取り込まれていない
- `evolved_beyond_hld`: 取り込まれたが HLD 記述と乖離した形で進化／置換された

全 **102** ページ。

## area 別件数

| area | 件数 |
|------|-----:|
| `acl-qos` | 6 |
| `architecture` | 25 |
| `internals` | 6 |
| `management` | 16 |
| `overlay` | 1 |
| `platform` | 12 |
| `reference` | 1 |
| `routing` | 8 |
| `switching` | 8 |
| `system` | 19 |

## monitor タグ別件数

| monitor | 件数 |
|---------|-----:|
| `deprecated`（deprecated） | 3 |
| `evolved_beyond_hld`（HLD と乖離した形で実装/進化） | 29 |
| `not_implemented`（未実装） | 11 |
| `partially_implemented`（partially_implemented） | 59 |

## エントリ一覧（area 別）

### acl-qos

- [DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース）](../../acl-qos/dhcp-dos-mitigation-in-sonic.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05 時点で `.cache/sonic-sources/` を裏取りした結果、本機能は **データ層 + CLI のみ取り込み済み、肝心の TC 投入経路が未実装** な部分実装状態。

- [ポートの動的 add / del（zero-port 起動と post-init 操作）](../../acl-qos/enhancements-to-add-or-del-ports-dynamically.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05 時点の `.cache/sonic-sources/` master を裏取り。

- [動的ポート add/del 内部実装（portsyncd / portsorch / mgrd 群と race condition）](../../acl-qos/enhancements-to-add-or-del-ports-dynamically-internals.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [動的ポート add/del 制限事項と HLD との乖離（ref counter 未取り込み・race 残存）](../../acl-qos/enhancements-to-add-or-del-ports-dynamically-limitations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05 時点の `.cache/sonic-sources/` master を裏取り。

- [動的ポート add/del 概念（zero-port 起動と post-init モデル）](../../acl-qos/enhancements-to-add-or-del-ports-dynamically-concepts.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [動的ポート add/del 設定と運用（zero-port 起動・安全削除手順）](../../acl-qos/enhancements-to-add-or-del-ports-dynamically-operations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

### architecture

- [DIP=SIP PTF 検証 内部実装（パケット仕様 / パラメータ）](../../architecture/dip-sip-ptf-validation-high-level-design-internals.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [DIP=SIP PTF 検証 制限事項と HLD-実装乖離（pytest 移行）](../../architecture/dip-sip-ptf-validation-high-level-design-limitations.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05 時点でテスト実体は **PTF スタンドアロンから pytest 配下へ移行済み** で、HLD の記述（ansible + ptftests）はファイル配置レベルで古い。

- [DIP=SIP PTF 検証 概念（テストの目的とトポロジ）](../../architecture/dip-sip-ptf-validation-high-level-design-concepts.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [DIP=SIP PTF 検証 運用（ファイル構成 / 前処理 / 実行）](../../architecture/dip-sip-ptf-validation-high-level-design-operations.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [DIP=SIP PTF 検証テスト](../../architecture/dip-sip-ptf-validation-high-level-design.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05 時点でテスト実体は **PTF スタンドアロンから pytest 配下へ移行済み** で、HLD の記述（ansible + ptftests）はファイル配置レベルで古い。

- [Debug Framework（コンポーネント dump 登録 / assert 拡張）](../../architecture/debug-framework-in-sonic.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05 時点で本 framework は **master に取り込まれておらず、HLD のみ**（2019-07 v0.3 から 6 年以上停滞）。

- [Error Handling Framework 内部実装（OrchAgent producer / ErrorListener / ASIC_DB](../../architecture/error-handling-framework-in-sonic-internals.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [Error Handling Framework 制限事項と HLD との乖離（コア機構未実装 / CRM 代替）](../../architecture/error-handling-framework-in-sonic-limitations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [Error Handling Framework 概念（ERROR_DB / SWSS_RC / 報告のみの責務）](../../architecture/error-handling-framework-in-sonic-concepts.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [Error Handling Framework 設定・運用（show / clear error-database / ERROR_DB スキーマ）](../../architecture/error-handling-framework-in-sonic-operations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05 時点で本 framework は **エラーコード enum だけが先行採用され、ERROR_DB / ErrorListener / CLI は丸ごと未実装** な部分採用状態。

- [SAG（Static Anycast Gateway）for SONiC](../../architecture/sag-high-level-design-for-sonic.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05 時点で **SAG コード / [YANG](../../reference/glossary.md#term-yang) / CLI は community master に取り込まれておらず、HLD 提案段階**。

- [SSD ヘルスチェック 内部実装（API 仕様 / ssdmond）](../../architecture/ssdhealth-design-internals.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [SSD ヘルスチェック 制限事項と HLD-実装乖離](../../architecture/ssdhealth-design-limitations.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD の二段プラグイン構造（`SsdBase` / `SsdUtil`）と CLI（`show platform ssdhealth`）は概ね素直に取り込まれているが、HLD で Open Question として残されていた **常時監視デーモン `ssdmond` は現状実装が見当たらない**。さらに、HLD で示された `sonic_ssd/ssd_base.py` の配置は master では `sonic_storage/` 配下に再構成され、独立スクリプト `ssdhealth` も `ssdutil` Python パッケージに置き換わっている。

- [SSD ヘルスチェック 概念（SsdBase / SsdUtil 二段プラグイン）](../../architecture/ssdhealth-design-concepts.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [SSD ヘルスチェック 運用（CLI / 表示モード）](../../architecture/ssdhealth-design-operations.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [SSD ヘルスチェック（show platform ssdhealth + ssdutil プラグイン）](../../architecture/ssdhealth-design.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD の二段プラグイン構造（`SsdBase` / `SsdUtil`）と CLI（`show platform ssdhealth`）は概ね素直に取り込まれているが、HLD で Open Question として残されていた **常時監視デーモン `ssdmond` は現状実装が見当たらない**。

- [SmartSwitch HA HAMgrD CONFIG/APP/STATE_DB スキーマ（設定経路）](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-operations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  `sonic-swss-common/common/schema.h` で HA Set / HA Scope / Global Config の APP / CFG / STATE 系テーブルは取り込み済（L180-182, L391, L454 付近）。一方で `DASH_HA_DPU_STATE` / `DASH_HA_VDPU_STATE` / `VDPU_TABLE` は **未定義**。さらに **`hamgrd` バイナリは community master に存在しない** ため、本ページのスキーマに書き込んでも consumer が居ない状態（schema 層のみ先行採用された一部のみの部分実装）。詳細は [smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md](smartswi…

- [SmartSwitch HA HAMgrD 内部実装（actor workflow / DPU-Driven 詳細）](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  本ページに記述した actor workflow / DPU-Driven シーケンスは **HLD v0.1 を元にした将来仕様の参考**。schema 層（HA Set / HA Scope の APP/CFG/STATE table 名）は一部のみ取り込み済の部分実装状態である一方、`hamgrd` バイナリ・actor framework・swbus・`DASH_HA_DPU_STATE` / `VDPU_TABLE` の schema は community master に未取り込みで、Switch-Driven mode は HLD 上 TBD のまま。実コードでの裏取り結果と回避策は [smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md](smartswitch-high-ava…

- [SmartSwitch HA HAMgrD 制限事項と実装乖離](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [SmartSwitch HA HAMgrD 概念（actor model と vDPU 抽象）](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  schema 層（HA Set / HA Scope の APP/CFG/STATE table 名）は一部のみ先行採用済み（部分実装）。一方で `hamgrd` バイナリは community master に未取り込み（`grep -ri hamgrd .cache/sonic-sources/sonic-swss/` でコメントのみヒット）。actor framework / vDPU 抽象 / swbus も実装されていない。本ページの概念記述は HLD v0.1 (2025-02) を元にした **将来仕様の参考** であり、現行 community master で「動かす」ことは不可能。詳細は [smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md](smartswitch-high…

- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05 時点で **schema 層（HA Set / HA Scope の table 名）は先行採用済みだが、hamgrd バイナリ・actor framework・swbus・VDPU / DPU_STATE は未取り込み**。HLD の半分弱までが master に入っている部分実装状態。

- [sFlow（hsflowd / sflowmgrd / SAI sample-packet）](../../architecture/sflow-high-level-design.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05 時点で本機能の **全体取り込みは完了している** が、HLD 文書中の「sample_rate の既定値テーブル」だけが実装と不一致である。

- [ビルドプロファイル（rules/profiles/*.mk）](../../architecture/build-profiles.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05 時点で本機能は **HLD は提案されたが master にコードが入っていない**、純粋な未実装状態である。

- [ポート不正パケットドロップ設計（Interface MIB / L3 カウンタ拡張）](../../architecture/port-illegal-packets-drop-design.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。本ページは HLD 主体で書かれており、HLD 記載なしのドロップ理由（implementation 推測部分）に「未確認」と本文中で明示している。実装側の確定は裏取り課題。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

### internals

- [L3 Scaling と Performance 強化 内部実装（RouteOrch bulk / fpmsyncd / sairedis / show](../../internals/l3-scaling-and-performance-enhancements-internals.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [L3 Scaling と Performance 強化 制限事項と HLD との乖離（gc_thresh / CoPP / partial 取り込み）](../../internals/l3-scaling-and-performance-enhancements-limitations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [L3 Scaling と Performance 強化 概念（スケール目標 / 性能目標 / 3 系統の改善）](../../internals/l3-scaling-and-performance-enhancements-concepts.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [L3 Scaling と Performance 強化 設定・運用（sysctl / COPP_TABLE / show arp）](../../internals/l3-scaling-and-performance-enhancements-operations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show](../../internals/l3-scaling-and-performance-enhancements.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。

- [ZMQ ProducerStateTable / ConsumerStateTable 設計](../../internals/zmq-producer-consumer-state-table-design.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。select イベントループのバックプレッシャ挙動など、HLD で詳細が省略されている部分を本文で「要確認」と明示している。実装側の確定は裏取り課題。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

### management

- [AAA Improvements（PAM / NSS / D-Bus / RBAC 多重ロール）](../../management/aaa-improvements.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  本ページは設計討議文書（rev 0.4）であり、提案全体（多重ロール / NSS lookaside / RADIUS 1 回ログイン / sudo+PAM 統合 / console 判定の D-Bus 化）が現行 `sonic-buildimage` master の `hostcfgd` / PAM 設定テンプレートに **全面採用されていない**。q52-az triage で discrepancy-found に降格。個別項目の採否は `src/sonic-host-services` 配下のコードと `/etc/pam.d/` テンプレートを直接確認してください。

- [Console Switch（serial hub の reverse SSH 集約）](../../management/sonic-console-switch.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  per-page queue で既出の通り、HLD 1.1 の中核実装は部分的のみ。再確認した結果:

- [P4RT アプリケーション（PINS の gRPC サービス、port 9559）](../../management/p4rt-application-hld.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  実コード裏取りで判明した HLD との差分（verified at: 2026-05-09）:

- [Portable Console Device 設計（USB ベンダー console デバイスの抽象化）](../../management/portable-console-device-design.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD が掲げる「USB 接続のポータブル console-switch デバイス」を制御するための実装は、CLI / YANG / [CONFIG_DB](../../reference/glossary.md#term-config_db) スキーマのいずれにも入っていない。

- [Redis Client Manager（RCM: connection pool / transactional client）](../../management/redis-client-manager-rcm-hld.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。RCM 4 関数の現行 master 取り込み、counter 統合状況を本文で「未確認」と明示している。実装側の裏取りは継続課題。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [SONiC Application Extension 開発・移植ガイド](../../management/sonic-application-extension-guide.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。HLD は Initial Proposal で、フィールド名・CLI が現行 master と一致するかは本文で「要確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP](../../management/sonic-nos-configuration-methods.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  本ページは入口を 10 種類列挙する **概観文書** であり、個々の入口の細かい挙動・優先度・互換性については現行 master と細部で乖離が残っている可能性がある（q52-az triage で discrepancy-found に降格）。実コマンドの正確な動作は対応する個別 HLD（`generic_config_updater`、`sonic-cfggen`、`bgpcfgd` 等）と `sonic-utilities/config/main.py` の最新コードで確認してください。

- [SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）](../../management/sonic-yang-model-guidelines.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。本ガイドラインで前提とされる SONiC YANG 拡張のうち、**`sonic-buildimage` 側の yang-models と `sonic-mgmt-common` 側で取り込み状況が分裂している**点が最大の罠。

- [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](../../management/smart-switch-gnmi-feedback-design-omit-in-toc.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  HLD が要件として掲げる以下の構成要素を現行 master の `sonic-gnmi` に確認できなかった。

- [TACACS+ passkey 暗号化（key_encrypt + master key /etc/cipher_pass）](../../management/tacacs-passkey-encryption.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。

- [gNMI Master Arbitration（election ID と SetRequest 拡張）](../../management/gnmi-master-arbitration-hld.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  実コード裏取りで判明した HLD との差分（verified at: 2026-05-09, sonic-gnmi @ `eb635b7679b260c3fd0786a6d0734fc8e82c9a22`）:

- [gNSI 内部実装（Certz / Authz / Pathz / Credentialz handler と host service）](../../management/gnsi-hld-internals.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [gNSI 制限事項と HLD との乖離（Credentialz 未配線・フラグ名差異）](../../management/gnsi-hld-limitations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  実コード裏取りで判明した HLD との差分（verified at: 2026-05-09, sonic-gnmi @ `eb635b76`）。HLD の 4 サービス（Authz / Certz / Pathz / Credentialz）のうち 3 つは取り込み済みで、Credentialz のみ未取り込みという **一部のみの部分実装** 状態:

- [gNSI 概念（4 サービスと Rotate モデル）](../../management/gnsi-hld-concepts.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [gNSI 設定と運用（gNMI フラグ / YANG / 運用イメージ）](../../management/gnsi-hld-operations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [gNSI（Certz / Authz / Pathz / Credentialz）の Rotate モデル](../../management/gnsi-hld.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  実コード裏取りで判明した HLD との差分（verified at: 2026-05-09, sonic-gnmi @ `eb635b76`）。HLD の 4 サービス（Authz / Certz / Pathz / Credentialz）のうち 3 つは取り込み済みで、Credentialz のみ未取り込みという **一部のみの部分実装** 状態:

### overlay

- [トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避）](../../overlay/dscp-remapping-for-tunnel-traffic.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  verified at: 2026-05-09。

### platform

- [FEC FLR 内部実装（port_flr.lua / FlexCounterOrch / SAI counter mapping）](../../platform/fec-flr-support-in-sonic-internals.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [FEC FLR 制限事項と HLD との乖離（CLI 未取り込み / ハードコード値）](../../platform/fec-flr-support-in-sonic-limitations.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [FEC FLR 概念（FLR / CER / interleaving / observed vs predicted）](../../platform/fec-flr-support-in-sonic-concepts.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [FEC FLR 設定・運用（counterpoll / show interfaces counters fec-stats / portstat -f）](../../platform/fec-flr-support-in-sonic-operations.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [FEC FLR（Frame Loss Ratio）算出と予測（port_flr.lua / counterpoll port flr-interval-factor）](../../platform/fec-flr-support-in-sonic.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。本機能の **コアロジック (port_flr.lua) と CLI 表示 (portstat) は取り込み済み**だが、**[HLD](../../reference/glossary.md#term-hld) で示唆された動的設定 CLI（`counterpoll port flr-interval-factor`）は未実装**であり、poll 周期は lua スクリプト内のハードコード値に固定されている。

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
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD と実装には次の乖離がある:

- [VoQ Chassis での Everflow ミラー（recycle port 経由の rewrite）](../../platform/everflow-support-on-voq-chassis.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。公式 HLD（2020-12 Rev 1）のみを根拠としており、現行 master の VoQ 拡張・SAI 実装・recycle port セットアップは本文で「未確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [拡張 LPO デバッグレジスタ（VMA / OMA per-lane モニタを Redis に公開）](../../platform/enhanced-lpo-debug-registers-hld.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  `sonic-platform-common` を grep した結果、本 HLD が前提とする `CmisEnhancedLpoApi` / `CmisEnhancedLpoCodes` / `CmisEnhancedLpoMemMap` クラス、`xcvr_api_factory.py` での Arista 系 vendor 分岐、Page 01h Byte 195 = 0x4C の enhanced LPO 検出ロジック、`LPOTxHostInputVMA*` / `LPORxInputOMA*` フィールドのいずれも HEAD に取り込まれていない（`grep -rn "CmisEnhancedLpoApi\|LPOTxHostInputVMA\|enhanced_lpo" .cache/sonic-sources/sonic-platform-common/` でヒット 0）。…

- [液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント）](../../platform/liquid-cooling-leakage-detection-in-sonic.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD と実装には次の乖離がある:

### reference

- [config muxcable サブコマンド](../../reference/cli/config-muxcable.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。`--namespace` 引数サポートの有無は CLI コマンド間で混在しており、本文で「要確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は [HLD](../../reference/glossary.md#term-hld) と実装の差分が未特定であることを示し、後続の裏取り対象。

### routing

- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](../../routing/bgp-route-install-error-handling.md)  
  monitor: `deprecated` / last_verified: `2026-05-09`
  
  2026-05-09 時点の現行 master を裏取り。**本 HLD は採用されず、後発の BGP Suppress FIB Pending に置き換えられている**。

- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../../routing/bfd-hw-offload-for-bgp-session.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05-09 時点の現行 master を裏取り。HLD と実装には次の乖離がある:

- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](../../routing/evpn-vxlan-multihoming.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05-10 時点の現行 master を裏取り。**EVPN Multihoming 機能は SONiC メインリポジトリには取り込まれていない**。

- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../../routing/evpn-vxlan-hld.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`

- [Local ARS（Adaptive Routing & Switching の local 完結版）](../../routing/local-ars-hld.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  2026-05-10 時点の現行 master を裏取り。**Local ARS は HLD 提案のみで SONiC SWSS / utilities / yang への取り込みは未完了**。

- [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](../../routing/bgp-setup-for-voq-chassis.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。新規 FRR コマンドの SONiC 同梱 FRR への取り込み状況は本文で「要追跡」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [bgpcfgd の dynamic BGP peer 動的変更（update.conf.j2 / delete.conf.j2）](../../routing/bgpcfgd-dynamic-peer-modification-support.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。HLD は 2025-07 Rev 1.0 で master 取り込み状況は本文で「要追跡」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md)  
  monitor: `evolved_beyond_hld`（HLD と乖離した形で実装/進化） / last_verified: `2026-05-11`
  
  `sonic-swss/fpmsyncd/routesync.cpp` と `sonic-swss/fpmsyncd/routesync.h` を確認。HLD のコア部分は master に取り込み済み:

### switching

- [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](../../switching/layer-2-forwarding-enhancements.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  実コード裏取りで判明（verified at: 2026-05-09）:

- [Switchport モードと VLAN CLI 拡張 — HLD と実装の乖離](../../switching/switch-port-modes-and-vlan-cli-discrepancy.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [Switchport モードと VLAN CLI 拡張 — 内部実装](../../switching/switch-port-modes-and-vlan-cli-internals.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [Switchport モードと VLAN CLI 拡張 — 概念](../../switching/switch-port-modes-and-vlan-cli-concepts.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [Switchport モードと VLAN CLI 拡張 — 設定と運用](../../switching/switch-port-modes-and-vlan-cli-operations.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`

- [Switchport モード（access / trunk / routed）と VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  2026-05-11 時点の現行 master を裏取り。

- [Wake-on-LAN（wol CLI と SonicWolService gNOI）](../../switching/wake-on-lan-in-sonic.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-09`
  
  2026-05-11 時点の現行 master を裏取り。CLI 本体は完備だが gNOI 経路は未統合で、HLD 全体としては一部のみ取り込まれた部分実装状態。

- [リンクイベントダンピング（AIED アルゴリズムと SyncD intercept）](../../switching/link-event-damping-hld.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-09`
  
  2026-05-11 時点の現行 master を裏取り。

### system

- [Event-Driven TechSupport / Coredump 管理（auto-techsupport / rate-limit / quota）](../../system/event-driven-techsupport-invocation-coredump-mgmt.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。coredump_gen_handler / techsupport_cleanup の現行 master 取り込み、rate-limit と quota 既定値は本文で「未確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [Management Framework 経由の show techsupport（REST/gNMI/IETF since 形式）](../../system/show-techsupport.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  q52-az triage で discrepancy-found に降格。RPC 経路と tarball 採取本体は HLD どおりだが、HLD が前提とする `--since` の IETF YANG date-time 厳密パースや、Management Framework フロント側のエラーマッピング（partial failure / timeout 表現）が現行 master のコードと細部で齟齬があるため、自動化からの呼び出しでは `sonic-utilities/scripts/generate_dump` の戻り値とログを直接確認してください。

- [Multi-ASIC warm reboot（namespace 横断の協調 shutdown / boot）](../../system/multi-asic-warm-reboot.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。各 namespace の swss / syncd の協調 shutdown 順序が現行スクリプトでどうなっているかは本文で「未確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [SONiC BMC Platform Management & Monitoring（pmon ↔ BMC 連携）](../../system/sonic-bmc-platform-management-monitoring.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。BMC 経由 pmon の現行 master 実装、Redfish / IPMI トランスポート差は本文で「未確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [SONiC Container Hardening（capability / read-only / privileged 削減）](../../system/sonic-container-hardening.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  q52-az triage で discrepancy-found に降格。HLD が示す「全 docker を non-privileged 化し最小 capability で動かす」終着点に対し、現行 master では一部 docker のみがテンプレ化を完了しており、残りの docker は依然 `--privileged` または広い cap-add で起動する。各 docker の実際の起動オプションは `sonic-buildimage/dockers/<name>/Dockerfile` と `start.sh` / `supervisord.conf` を直接確認してください。

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

- [Transceiver / DOM Sensor Monitoring（xcvrd / TRANSCEIVER_*）](../../system/transceiver-and-sensor-monitoring-hld.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。xcvrd の現行構造、TRANSCEIVER_* テーブルの現行スキーマ（CMIS 拡張による多数フィールド追加）、polling interval 60s の妥当性は本文で「未確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [Warmboot Manager（shutdown orchestration / reconciliation 統一）](../../system/warmboot-manager-hld.md)  
  monitor: `not_implemented`（未実装） / last_verified: `2026-05-11`
  
  per-page queue で既出の通り提案 HLD は未採用。再走査でも:

- [config-setup サービス（first-boot config 生成 / 版間 migration）](../../system/sonic-configuration-setup-service.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。HLD は 2019-07 Rev 0.2 で停滞。`config-setup` の実際の責務分担は本文で「要確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [kdump（kexec ベース kernel crash dump / makedumpfile）](../../system/kdump.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。HLD は 2019-12 v0.4。kdump-tools 後続バージョン差分・kernel バージョン更新の影響は本文で「未確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../../system/sonic-libsairedis-api-idempotence-support.md)  
  monitor: `deprecated` / last_verified: `2026-05-11`
  
  2026-05-11 時点の現行 master を裏取り。

- [storagemond（SSD / eMMC の health 監視）](../../system/sonic-storage-monitoring-daemon-design.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。storagemond の現行 master 実装、CLI 名・テーブル名の正確な値は本文で「未確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [クリティカルリソースモニタリング (CRM) 要件](../../system/critical-resource-monitoring.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-13`
  
  - 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。新規テーブル名は HLD で明示されておらず、実装側で追加されている可能性が高い旨を本文で「未確認」と明示している。 - 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

- [ローカルユーザパスワード init 時リセット（long reset button + reset-local-users-passwords.service）](../../system/reset-local-users-passwords-during-init-hld.md)  
  monitor: `partially_implemented` / last_verified: `2026-05-11`
  
  per-page queue で既出の通り、[HLD](../../reference/glossary.md#term-hld) が定義する専用機構は未取り込み。`.cache/sonic-sources/` 全体を再走査した結果:

## 監査基準の取り扱い

本ページ群（`verification: discrepancy-found` のページ）は、「機能としては完結していなくても、代わりに HLD と実装の差分を整理して読み手に渡す」ことを目的としています。品質監査 (`meta/quality-audit-*.md`) における **軸 6 (完結性)** は、本ページ群では「乖離説明の整理度」（monitor タグ妥当性 / 「実装との乖離」セクションの構造化 / 裏取り evidence / 読み手への next-action）に読み替えて評価します。詳細は `meta/templates/SCHEMA.md` の 「`discrepancy-found` ページの軸 6 評価基準」セクション、および `meta/quality-audit-guide.md` を参照してください。
