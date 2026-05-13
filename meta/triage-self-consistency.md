# verification self-consistency triage

`check_verification_self_consistency.py` で検出された 114 件の suspect を 3 分類した。

| Class | 件数 | 意味 |
|---|---|---|
| A (verbatim) | 25 | HLD 引用として `未実装` `未対応` `TBD` 等が本文に残っているだけ。実 issue ではない。除外候補。 |
| B (legitimate) | 39 | 本文の主張として `要確認` `未確認` 等を肯定的に使っている。`verification` を `partial` 等へ降格すべき。 |
| C (ambiguous) | 50 | 上記いずれにも当てはまらず、人間レビューが必要。 |

分類ルールは `meta/scripts/triage_self_consistency.py` 参照。

## B. legitimate (本文の主張で未確認/未実装) — 39 件

| Path | verification | hits | 例 |
|---|---|---|---|
| `docs/acl-qos/acl-support-in-sonic.md` | code-verified | 未実装×3, 未対応×2 | `未対応`: - ** は  のみ**（IPv6 は当時未対応）。 |
| `docs/acl-qos/configurable-drop-counters-in-sonic.md` | code-verified | 要確認×1 | `要確認`: - **[CRM](../reference/glossary.md#term-crm)**: debug counter のスロット消費は CRM の resource 監視に乗らない（HLD で明記なし、要確認）。 |
| `docs/acl-qos/egress-mirroring-support-and-acl-action-capability-check.md` | code-verified | 未実装×2, TBD×1, 未対応×1 | `TBD`: - system-level test は HLD 上 TBD |
| `docs/architecture/port-illegal-packets-drop-design.md` | code-verified | 未確認×1 | `未確認`: HLD には記載なし。実装側で  等が関連すると推測されるが未確認。 |
| `docs/internals/zmq-producer-consumer-state-table-design.md` | code-verified | 要確認×1 | `要確認`: - **select イベントループ**:  /  のバックプレッシャ挙動は要確認 |
| `docs/management/aaa-improvements.md` | code-verified | 要確認×1 | `要確認`: 本 HLD は 2020 年 Martin Bélanger（Rev 0.4）の **設計討議文書**。AAA / PAM / NSS の本質的問題提起と提案で、現行 master が本提案を全面採用しているかは要確認。。 |
| `docs/management/gnoi-hld-for-file-and-factory-reset-apis.md` | code-verified | 要確認×1, 未対応×3 | `要確認`: > 注: 「 以外を消させない」を **string match** で守るのは脆く見える。実装側で  系の traversal が抜けないか要確認（ で  リジェクトは UT 済）。 |
| `docs/management/redis-client-manager-rcm-hld.md` | code-verified | 未確認×1 | `未確認`: 上の RCM 4 関数（ /  /  / ）の現行 master 取り込み、 への counter 統合は未確認。 |
| `docs/management/sonic-application-extension-guide.md` | code-verified | 要確認×1 | `要確認`: - HLD 自体が Initial Proposal で、フィールド名や CLI が現行 master と一致するかは要確認。 |
| `docs/management/sonic-nos-configuration-methods.md` | code-verified | 要確認×1 | `要確認`: -  の checkpoint / rollback 実装の取り込みは要確認 |
| `docs/overlay/active-active-dual-tor.md` | code-verified | TBD×2 | `TBD`: に active-active 専用の state machine 一式 (、) が存在し、 は （）で active-active 系処理を分岐する。新規 APP_DB / STATE_DB テーブル（ /  /  / ）は  に登録済み。 も  の  に追加済み。warm reboot 対応は HLD 上 T... |
| `docs/overlay/active-standby-dual-tor-internals.md` | code-verified | TBD×1 | `TBD`: 3. **Directed Broadcast**: HW フラッディングで standby port を含めた挙動が単一 ToR と異なる（HLD では TBD） |
| `docs/overlay/active-standby-dual-tor-limitations.md` | code-verified | TBD×1 | `TBD`: - directed broadcast は HLD 上 TBD |
| `docs/overlay/active-standby-dual-tor.md` | code-verified | TBD×2 | `TBD`: 3. **Directed Broadcast**: HW フラッディングで standby port を含めた挙動が単一 ToR と異なる（HLD では TBD） |
| `docs/overlay/dash-sonic-kvm.md` | code-verified | TBD×3, 未対応×1 | `TBD`: HLD §「DPU SONiC KVM image with dataplane will be released at the next stage」「5.2 DPU+VPP NPU testbed (TBD)」のとおり、データプレーン同梱イメージ・VPP NPU testbed は TBD。 |
| `docs/overlay/vxlan-sonic-limitations.md` | code-verified | TBD×1 | `TBD`: -  と  の協調実装（HLD で TBD だった部分） |
| `docs/platform/everflow-support-on-voq-chassis.md` | code-verified | TBD×2, 未確認×1 | `未確認`: 本ページは公式 HLD（Rev 1, 2020-12）のみを根拠に書かれている。 /  の VoQ 拡張、SYSTEM_PORT 対応の SAI 実装、recycle port のセットアップは未確認。HLD は 2020 年で 3 年以上経過しており、Option 1 / Option 2 のどちらが採用された... |
| `docs/reference/cli/config-muxcable.md` | code-verified | 要確認×1 | `要確認`: -  指定をサポートするコマンドと、しないコマンドが混在する。CLI 引数の  と  全件ループ実装の有無を要確認。 |
| `docs/routing/bfd-hw-offload.md` | code-verified | 未実装×2, 要確認×1, 未対応×1 | `要確認`: 実際のキー名（ か  か）は HLD 表記揺れがあり、現行 swss 実装側で要確認。 |
| `docs/routing/bgp-prefix-independent-convergence-architecture-document.md` | code-verified | 未確認×1, 未対応×1 | `未確認`: で  /  /  と  フラグによる hierarchical NHG 制御が確認できた。 側の **FAST/SLOW DOWNLOAD** という用語は実装に存在せず、 で  経由の **warm-restart timer** 区別として実装されている。SAI vendor 側の hitless updat... |
| `docs/routing/bgp-setup-for-voq-chassis.md` | code-verified | 要追跡×1 | `要追跡`: - **新規 FRR コマンド**  の SONiC 同梱 FRR への取り込み状況は要追跡 |
| `docs/routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md` | code-verified | 要確認×1 | `要確認`: - **fpmsyncd NextHop Group 拡張**: 同じ  を共有するため、両機能の有効化状態が干渉しないか要確認 |
| `docs/routing/bgpcfgd-dynamic-peer-modification-support.md` | code-verified | 要追跡×1 | `要追跡`: - HLD は 2025-07 Rev 1.0。master 取り込み状況は要追跡 |
| `docs/routing/srv6-vpn-hld.md` | code-verified | 未対応×2 | `未対応`: - **SAI 側で SRv6 VPN 拡張がプラットフォームでサポート** されている必要がある（未対応プラットフォームでは動かない） |
| `docs/routing/static-ip-route-configuration.md` | code-verified | 未対応×1 | `未対応`: - （未対応フィールドや拡張用） |
| `docs/switching/lag-on-distributed-voq-system.md` | code-verified | 未対応×3 | `未対応`: - supervisor / global redis-server の warm boot なし restart は **全 ASIC SONiC が exit**（pizza box 同等。graceful restart 未対応） |
| `docs/switching/mclag-enhancements.md` | code-verified | 未対応×2 | `未対応`: - ICCP は **2 台ピアまで**（3-way 以上は未対応） |
| `docs/system/critical-resource-monitoring.md` | code-verified | 未確認×2 | `未確認`: 要件 HLD 上はテーブル名が明示されていない。実装側で  テーブルが追加されている可能性が高いが、本ページでは未確認のため空配列とする。実装裏取り（ 昇格）時に追記する想定。 |
| `docs/system/event-driven-techsupport-invocation-coredump-mgmt.md` | code-verified | 未確認×1 | `未確認`: coredump_gen_handler / techsupport_cleanup の現行 master 取り込み、rate-limit と quota 既定値は未確認。 |
| `docs/system/kdump.md` | code-verified | 未確認×1 | `未確認`: - HLD は 2019-12 v0.4。kdump-tools 後続バージョンの差分・kernel バージョン更新の影響は未確認 |
| `docs/system/multi-asic-warm-reboot.md` | code-verified | 未確認×1 | `未確認`: 各 namespace の swss / syncd の協調 shutdown 順序が現行スクリプトでどうなっているかは未確認。 |
| `docs/system/process-and-docker-stats-availability-via-telemetry-agent.md` | code-verified | 未確認×1 | `未確認`: - HLD は 2019 年で実装が現行 master にどこまで残っているかは未確認（高優先で裏取り対象） → 2026-05-09 裏取り済み。実装は  リポジトリ側 () に移管されているが、テーブル名・フィールド・top-1024・2 分周期は HLD 記載通り。 |
| `docs/system/show-techsupport.md` | code-verified | 要確認×1 | `要確認`: - HLD は 2019-10 Rev 0.1 で 6 年以上停滞。Management Framework 自身の進化（特に gNMI / OpenConfig 化）と整合しているかは要確認 |
| `docs/system/sonic-bmc-platform-management-monitoring.md` | code-verified | 未確認×1 | `未確認`: BMC 経由 pmon の現行 master 実装、Redfish / IPMI トランスポート差は未確認。 |
| `docs/system/sonic-configuration-setup-service.md` | code-verified | 要確認×1 | `要確認`: - HLD は **2019-07 / Rev 0.2** で停滞。 との実際の責務分担は実装側で要確認 |
| `docs/system/sonic-container-hardening.md` | code-verified | 未確認×1, 未対応×1 | `未確認`: 各 docker の現行 supervisor / docker_image_ctl テンプレートでの cap-drop / read-only 適用状況は未確認。 |
| `docs/system/sonic-storage-monitoring-daemon-design.md` | code-verified | 未確認×1 | `未確認`: storagemond の現行 master 実装、CLI 名・テーブル名の正確な値は未確認（ 系の既存実装と類似）。 |
| `docs/system/sonic-telemetry-in-dial-out-mode.md` | code-verified | TBD×1, 未確認×1 | `TBD`: - 性能 / スケールテストは TBD |
| `docs/system/transceiver-and-sensor-monitoring-hld.md` | code-verified | 未確認×1 | `未確認`: の現行構造、 /  /  テーブルの現行スキーマ（CMIS 拡張で多数フィールド追加）、polling interval 60s の妥当性は未確認。 |

## C. ambiguous — 50 件

| Path | verification | hits | 例 |
|---|---|---|---|
| `docs/acl-qos/acl-in-sonic.md` | code-verified | 未対応×1 | `未対応`: - **type ごとの match / action 制約**:  /  /  /  /  /  /  で利用できる match field と action は異なる。ベンダー SAI 実装によっては HLD で許される組み合わせの一部が未対応。 |
| `docs/acl-qos/copp-neighbor-miss-trap-and-enhancements.md` | code-verified | 未実装×1 | `未実装`: -  の対応は **ベンダー依存**。未実装 ASIC では |
| `docs/acl-qos/dash-acl-tags.md` | code-verified | 未対応×1 | `未対応`: - **warm / fast reboot 未サポート**（[DPU](../reference/glossary.md#term-dpu) SONiC 自体が未対応） |
| `docs/acl-qos/everflow-test-plan.md` | code-verified | 未取り込み×1 | `未取り込み`: テストプラン本体は  側の Ansible / PTF テストスクリプトに対する仕様だが、被テストの mirror 機能 ( 制御パス: src/dst IP / DSCP / TTL / GRE type / next-hop / queue / status) は  L15-L24 ほか 1611 行に渡って... |
| `docs/acl-qos/port-buffer-drop-counters-in-sonic.md` | code-verified | 未取り込み×1 | `未取り込み`: -  行が出ない: [sonic-utilities](../reference/glossary.md#term-sonic-utilities) が未取り込み。 を redis で確認 |
| `docs/acl-qos/reclaim-reserved-buffer-sequence-flow.md` | code-verified | 未対応×1 | `未対応`: - ASIC が **PG / queue 削除サポート** すれば「remove で 0 化」、未対応なら「zero profile で 0 化」と二段階フォールバック |
| `docs/acl-qos/sonic-port-mirroring-hld.md` | code-verified | 未対応×3 | `未対応`: - Capability Discovery: ASIC ごとに対応モード/属性を STATE_DB に公開し、未対応モードの設定試行を早期に弾く。 |
| `docs/acl-qos/watermark-counters-in-sonic.md` | code-verified | 未対応×1 | `未対応`: - 値がいつもゼロ: SAI / ASIC が  未対応か  未開始。 ログと FC group 設定を確認 |
| `docs/acl-qos/wred-and-ecn-statistics.md` | code-verified | 未対応×1 | `未対応`: -  で値が出ない →  を確認。全  なら SAI 未対応 |
| `docs/architecture/build-system-improvements.md` | code-verified | 未取り込み×1 | `未取り込み`: HLD は Debian Stretch 時代の文書だが、 の  /  /  マクロは現存。BuildKit は  フラグとしては未取り込みで、CI /  で  を直接設定する形になっている ( ではむしろ  既定)。 個別の指定は現行  には残っておらず、 の汎用機構に統合されている。dh  関連は debia... |
| `docs/architecture/dhcpv6-relay-agent.md` | code-verified | 未対応×2 | `未対応`: - Option 79 は default on だが server 側未対応で互換性問題を起こすケースあり |
| `docs/architecture/smart-switch-database-design.md` | code-verified | 未実装×1 | `未実装`: - DPU 数取得は platform API 未実装で  直読み（Open Items） |
| `docs/architecture/sonic-bulk-counter-design.md` | code-verified | 未対応×1 | `未対応`: - vendor SAI が bulk 未対応の object type は従来通り |
| `docs/architecture/sonic-generic-hash.md` | code-verified | 未対応×2 | `未対応`: - ASIC の  capability に依存、未対応プラットフォームでは意味のあるバリデーション不可 |
| `docs/architecture/sonic-ip-interface-loopback-action.md` | code-verified | 未対応×1 | `未対応`: - SAI 側未対応: ベンダー SAI 実装で  をサポートしていないと  が失敗する。 の SWSS / SAI ログを確認。 |
| `docs/architecture/sonic-policy-based-hashing.md` | code-verified | 未対応×1 | `未対応`: - inner 5-tuple は IPv4 / IPv6 限定。NVGRE / VxLAN 以外の encap には未対応 schema |
| `docs/architecture/sonic-port-auto-fec-design.md` | code-verified | 未対応×3 | `未対応`: -  未対応 SAI では operational FEC を出せない |
| `docs/architecture/sonic-port-auto-negotiation-design.md` | code-verified | 未対応×2 | `未対応`: 1. 未対応属性へのアクセスは **error 返却で済ませる**（crash 禁止） |
| `docs/management/gnoi-hld-for-system-apis.md` | code-verified | 未対応×1 | `未対応`: - platform で **未対応の method** が指定された |
| `docs/management/packetio.md` | code-verified | 未実装×1 | `未実装`: - メタデータ ifindex が 0 → kernel driver の metadata 抽出未実装の可能性 |
| `docs/overlay/nvgre-tunnel-in-sonic.md` | code-verified | 未対応×1 | `未対応`: - SAI バージョン: 1.9 未満ベンダーは未対応。 の SAI バージョン確認。 |
| `docs/platform/1-sonic-on-multi-asic-platforms.md` | code-verified | 未対応×1 | `未対応`: - **multi-asic 対応の [sonic-utilities](../reference/glossary.md#term-sonic-utilities)** が必要。 未対応コマンドは ASIC 横断で正しく動かない |
| `docs/platform/automatic-module-provisioning-for-chassis.md` | code-verified | 未実装×1 | `未実装`: -  未実装のベンダーでは新 status 値を使わない（既存の / で運用） |
| `docs/platform/global-platform-specific-psuutil-class-instance.md` | code-verified | 未実装×1 | `未実装`: - 抽象メソッドはデフォルトで  を投げる「未実装 OK」設計で、ベース拡張で既存実装を壊さない |
| `docs/platform/sai-api-version-check.md` | code-verified | 未実装×1, 未対応×1 | `未実装`: -  未定義エラー: ベンダー libsai が古く、本 API 未実装。ベンダーに更新を要求する。 |
| `docs/platform/sfputil-add-the-ability-to-read-write-any-byte-from-eerpom-both-by-page-and-offset.md` | code-verified | 未実装×1, 未対応×1 | `未対応`: - vendor 未対応 () は明示的にハンドル |
| `docs/platform/sonic-fast-link-up.md` | code-verified | 未対応×3 | `未対応`: - プラットフォーム未対応時はどうなる（拒否？ no-op？） |
| `docs/platform/sonic-fw-utility.md` | code-verified | 未実装×1 | `未実装`: - **platform plugin が必要**: plugin 未実装の component は  から触れない |
| `docs/platform/sonic-port-fec-ber.md` | code-verified | 未実装×1, 未対応×1 | `未対応`: - 空欄 → SAI カウンタ未対応か、speed/lanes が lookup 外 |
| `docs/platform/sonictpidsettinghld1.md` | code-verified | 未対応×1 | `未対応`: - ベンダ SAI が  /  未対応 → 機能無効 |
| `docs/platform/voq-sonic.md` | code-verified | 未対応×1 | `未対応`: - **single-asic 前提機能との非互換**: 一部の機能（[VLAN](../reference/glossary.md#term-vlan)、特定 [ACL](../reference/glossary.md#term-acl)）は VoQ 上で挙動差・未対応あり |
| `docs/reference/config-db/buffer-pool.md` | code-verified | 未対応×1 | `未対応`: -  を ASIC 未対応のまま使うと [PFC](../../reference/glossary.md#term-pfc) で head-of-line を起こす。 プラットフォームでは 。 |
| `docs/reference/config-db/debug-counter.md` | code-verified | 未対応×1 | `未対応`: - プラットフォーム SAI が未対応の reason を指定すると CrmOrch がエラーを出してカウンタが作られない。 |
| `docs/reference/config-db/portchannel.md` | code-verified | 未対応×1 | `未対応`: -  を未設定で対向が LACP 未対応だと [PortChannel](../../reference/glossary.md#term-portchannel) が永遠に down。 |
| `docs/reference/config-db/prefix-set.md` | code-verified | 未実装×1 | `未実装`: -  と実プレフィクスの family の整合チェックは TODO コメントで未実装 |
| `docs/reference/runbooks/gnmi-subscribe-disconnect.md` | code-verified | 未対応×1 | `未対応`: 5. **path syntax 不正で server が close する**: 一部 yang model が未対応で internal error 返却 |
| `docs/reference/runbooks/sai-failure.md` | runbook-verified | 未対応×1 | `未対応`: 2. **[SAI](../../reference/glossary.md#term-sai) 属性の未対応**: SDK バージョンが古く、[orchagent](../../reference/glossary.md#term-orchagent) が新属性を打って失敗 |
| `docs/reference/runbooks/warm-reboot-failure.md` | runbook-verified | 未対応×1 | `未対応`: 2. **[BGP](../../reference/glossary.md#term-bgp) graceful restart の対向側未対応 / capability 未交換**: GR helper として動作するために対向 peer も GR 対応が必要 |
| `docs/routing/dhcp-relay-for-ipv6-hld.md` | code-verified | 未対応×1 | `未対応`: -  の  に v6 が出ない: CLI または  側が当該機能未対応の可能性。実装確認は裏取り課題。 |
| `docs/routing/mpls-tc-to-tc-map.md` | code-verified | 未実装×1 | `未実装`: - SAI 側で qos_map 作成失敗: SAI / sairedis 側のサポートは前提だが、ベンダ SAI が  を未実装の場合は降ろせない。 のログを確認。 |
| `docs/routing/sonic-management-vrf-design-document-201911-release.md` | code-verified | 未対応×1 | `未対応`: - non-default VRF からの DNS / NTP / TACACS+ 利用は各サービスが VRF-aware に再実装される必要があり、サービスにより未対応のものがある。 |
| `docs/routing/sonic-route-flow-counter-design.md` | code-verified | 未対応×2 | `未対応`: - ASIC Generic Counter 必須。未対応 platform は CLI で判別可能 |
| `docs/routing/sonic-usid.md` | code-verified | 未対応×1 | `未対応`: -  /  を SET したのに ASIC に入らない場合、まず  のログで behavior マップヒットを確認。SAI から  が返ってきている場合は ASIC ベンダーの SAI 実装が UN/UA 未対応の可能性 |
| `docs/switching/sonic-bum-storm-control.md` | code-verified | 未対応×1 | `未対応`: - 値の上書きが反映されない → ベンダ SAI が  未対応の場合は再作成が必要。SWSS/SAI ログ確認 |
| `docs/switching/sonic-ip-lag-incremental-update.md` | code-verified | 未対応×1 | `未対応`: - conflicting configuration は未対応（前項） |
| `docs/system/critical-resource-monitoring-in-sonic.md` | code-verified | 未対応×1 | `未対応`: - **[SAI](../reference/glossary.md#term-sai) 側 availability API が必要**。vendor 未対応 resource は値が出ない |
| `docs/system/dataplane-telemetry-in-sonic.md` | code-verified | 未対応×1 | `未対応`: - v0.2 と古いため、新しい INT / IFA 系の上書き仕様には未対応の可能性 |
| `docs/system/dump-sfp-eeprom-page-data-in-show-techsupport-command.md` | code-verified | 未実装×1 | `未実装`: - techsupport に EEPROM が含まれない →  を手動実行してエラーメッセージを確認。platform API 未実装の可能性。 |
| `docs/system/persistent-log-level-hld.md` | code-verified | 未対応×1 | `未対応`: -  の出力に出てこないコンポーネント: そのコンポーネントが Logger シングルトン経由でない、または listener thread が未対応。HLD 列挙コンポーネント以外は本機能の対象外。 |
| `docs/system/smart-switch-reboot-high-level-design.md` | code-verified | 未対応×1 | `未対応`: - **fastboot**: SmartSwitch では未対応 |

## A. verbatim (HLD 引用) — 25 件

| Path | verification | hits | 例 |
|---|---|---|---|
| `docs/acl-qos/acl-ingress-egress-test-plan.md` | code-verified | 未確認×1 | `未確認`: 既存 [ACL](../reference/glossary.md#term-acl) テストは ingress 側のみ・FORWARD 偏重・カウンタ未確認・ルール衝突（RULE_12/13 が RULE_1 にマッチして hit しない）等の問題があった[^1]。本テストプランは以下を目的とする[^1]: |
| `docs/acl-qos/egress-outer-dscp-change-table.md` | code-verified | 未対応×1 | `未対応`: - **[SAI](../reference/glossary.md#term-sai) metadata 属性が必須**[^1]。未対応 platform では作成不可 |
| `docs/acl-qos/support-a-new-acl-table-type-that-combines-l3-acl-and-l3v6-acl-tables.md` | code-verified | 未実装×1 | `未実装`: - ACL テーブル間の優先順位付けは未実装。1 ポートに複数 ACL テーブルが bind され action が衝突した場合の勝者は未定義。Phase 2 で  priority 設定で対処予定[^1] |
| `docs/architecture/sonic-port-link-training-design.md` | code-verified | 未対応×1 | `未対応`: ベンダ SAI 要件: 未対応属性アクセスはエラー返却で swss/[syncd](../reference/glossary.md#term-syncd) を crash させない、デフォルトは disabled[^1]。 |
| `docs/architecture/steps-to-bring-up-sonic-vs.md` | code-verified | 要確認×1 | `要確認`: - ** 等のフラグ**: HLD は古い Debian 名を列挙しているが、現行 master ではフラグ集合が変わっている可能性がある。 の  /  を要確認[^1]。 |
| `docs/internals/aggregate-voq-counters-in-sonic.md` | code-verified | 未対応×1 | `未対応`: clear 系は **未対応**（後述の制限事項）[^1]。 |
| `docs/internals/support-redis-databases-in-multiple-namespaces.md` | code-verified | 未対応×1 | `未対応`: **他 NS への TCP 接続は未対応**。Unix socket 経由のみ[^1]。 |
| `docs/management/ipv4-port-based-dhcp-server-in-sonic.md` | code-verified | 未対応×1 | `未対応`: - 現状 **relay された DHCP request への応答は未対応**（option 82 を持って戻ってきたパケット処理は将来）[^1] |
| `docs/management/p4rt-read-cache-hld.md` | code-verified | 未対応×3 | `未対応`: P4RT App は現時点で warm boot 未対応だが、対応する際は **既存の Redis 読み出し経路を再利用してキャッシュを事前充填** する設計を HLD は提示している[^1]。 |
| `docs/overlay/vxlan-sonic.md` | code-verified | 未対応×1 | `未対応`: - Warm restart 未対応[^1] |
| `docs/platform/1-6t-support-in-sonic.md` | code-verified | 未確認×1 | `未確認`: - **HW がまだ存在しない**ことを前提に書かれた spec 先行 HLD。実 HW での挙動は未確認[^1] |
| `docs/platform/icmp-hardware-offload.md` | code-verified | 未対応×1 | `未対応`: はハードウェアサポートを起動時にチェックし、未対応プラットフォームでは **software モードへフォールバック** する[^1]。 を設定しても、capability が無ければ実質 software のままになる。 |
| `docs/platform/platform-capability-file-enhancement.md` | code-verified | 未対応×1 | `未対応`: の **既定値は **[^1]。すなわち capability セクションが書かれていない / 一部欠落している場合は **「制御可能」前提で動く** 後方互換動作になる。新フィールド未対応のプラットフォームでもクラッシュしない設計。 |
| `docs/platform/query-stats-capability-new-sai-api-indroduction.md` | code-verified | 未対応×1 | `未対応`: ベンダ SAI が  を返した場合は **既存の per-ID 取得方式にフォールバック** する。これにより SAI 未対応ベンダでも互換性を維持する[^1]。 |
| `docs/platform/single-asic-voq-fixed-system-sonic.md` | code-verified | 未実装×1 | `未実装`: - **HLD は 2025-08 の比較的新しい改訂**: 改修は進行中の可能性が高く、master との差分の方向は「未実装かもしれない」が中心[^1]。 |
| `docs/platform/sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md` | code-verified | 未確認×1 | `未確認`: - HLD 検証は Broadcom NPU でのみ。他 vendor は未確認[^1] |
| `docs/reference/cli/config-dhcp-relay.md` | code-verified | 未対応×1 | `未対応`: [^2]:  (同 plugin L16-L20)。 の  を見て、未対応なら  系コマンドはエラー終了する。 |
| `docs/reference/cli/show-flowcnt.md` | code-verified | 未対応×1 | `未対応`: はプラットフォームサポートが必要で、未対応プラットフォームでは  で即終了する[^2]。 |
| `docs/routing/prefix-based-mux-neighbors.md` | code-verified | TBD×2 | `TBD`: - **Warm reboot 対応は TBD**: [HLD](../reference/glossary.md#term-hld) は warm reboot サポートを「TBD」と明記しており未確定[^1]。 |
| `docs/routing/routing-and-next-hop-table-enhancement.md` | code-verified | 未対応×1 | `未対応`: - **Warm upgrade 未対応**: 既存アプリは本機能を使わないため対象外。将来採用アプリ時に別 enhancement で対応想定[^1] |
| `docs/routing/sonic-vrf-support-design-spec-draft.md` | code-verified | 未対応×1 | `未対応`: - **VRF level の admin up/down 非対応** / **Fallback lookup（RFC 4364）未対応**[^1] |
| `docs/routing/virtual-router-redundancy-protocol-adaptation-hld.md` | code-verified | 要確認×1 | `要確認`: は **VRRP container**（FRR 系 daemon 同居）または **[BGP](../reference/glossary.md#term-bgp) container** 同居の設計が選択肢[^1]。最終案は Rev 0.2 で固まる傾向、実装側で要確認。 |
| `docs/system/platform-monitor-requirement-for-chassis-subsystem.md` | code-verified | 未実装×1 | `未実装`: -  で LINECARD1 等のままになる: 要件 #21 の hostname 反映が未実装の可能性[^1]。 |
| `docs/system/sonic-openssl-fips-140-3-hld.md` | code-verified | 未対応×1 | `未対応`: Golang stdlib  は FIPS に未対応。Google の  branch は **BoringSSL に切り替えるが BoringSSL は Google 内利用前提** で一般公開されない。RedHat が ** ベースで OpenSSL に向ける patch** を公開しているため、SONiC ... |
| `docs/system/sonic-snmp-table-schema-proposal.md` | code-verified | 未実装×1 | `未実装`: -  は HLD 時点で未実装（コードでは未使用、Read-only のみ有効）と明記されている[^1]。 |

