# 横断カテゴリ提案レポート

## 前提

- 対象ページ数: 455 (`find docs -name "*.md" -not -name "index.md" | xargs grep -l "title:"` 相当)
- 抽出材料: path から得た area / slug、frontmatter の `title`、その他 frontmatter キー値。本文は使っていない。
- 抽出は機械的なキーワード一致で、カテゴリ間の重複を許容する。
- 各カテゴリの表示は最大 20 件。

## 抽出ルール

- DASH 関連: `\bdash\b`
- SmartSwitch 関連: `smartswitch`, `smart[-_ ]switch`
- Dual-ToR 関連: `dual[-_ ]?tor`, `dualtor`, `active[-_ ]active`, `active[-_ ]standby`, `muxcable`, `mux[-_ ]cable`, `\bmux\b`, `linkmgrd`, `y[-_ ]?cable`, `ycable`
- Warm-Reboot / Fast-Reboot 関連: `warm[-_ ]?reboot`, `warm[-_ ]?restart`, `fast[-_ ]?reboot`, `fastboot`, `kexec`
- Multi-ASIC / VOQ chassis 関連: `multi[-_ ]?asic`, `voq`, `chassis`, `fabric`, `line[-_ ]?card`, `supervisor`, `namespace`
- BGP / EVPN 関連: `\bbgp\b`, `evpn`, `vxlan`, `vnet`, `\bbmp\b`, `route[-_ ]?map`, `prefix[-_ ]?(list|set)`
- SAI 拡張属性追加系: `\bsai\b.*(attr|attribute|capability|extension|api|post|version|failure|failures)`, `(attr|attribute|capability|extension|api|post|version|failure|failures).*\bsai\b`, `sai_[a-z0-9_]+_attr`, `sai[-_ ]api`
- MIB / SNMP 関連: `\bmib\b`, `\bsnmp\b`
- gNMI / gNOI / OpenConfig 関連: `gnmi`, `gnoi`, `openconfig`, `open[-_ ]config`, `\byang\b`
- Container / Build system 関連: `container`, `\bdocker\b`, `\bbuild\b`, `image`, `\bmake\b`, `debian`, `bullseye`, `bookworm`, `sonic-buildimage`
- その他: 上記カテゴリのどれにも一致しなかったページ。

## 候補カテゴリ別ページ

### DASH 関連 (3 pages)

- `docs/acl-qos/dash-acl-tags.md` - DASH ACL タグ（DASH_PREFIX_TAG_TABLE と DASH_ACL_RULE_TABLE 拡張） (area: `acl-qos`, slug: `dash-acl-tags`)
- `docs/overlay/dash-sonic-kvm.md` - DASH SONiC KVM（BMv2 ベース仮想 DPU） (area: `overlay`, slug: `dash-sonic-kvm`)
- `docs/overlay/sonic-dash-hld.md` - SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観 (area: `overlay`, slug: `sonic-dash-hld`)

### SmartSwitch 関連 (10 pages)

- `docs/architecture/smart-switch-database-design.md` - Smart Switch のデータベース構成（NPU 上の DPU overlay DB） (area: `architecture`, slug: `smart-switch-database-design`)
- `docs/architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md` - SmartSwitch HA - DPU-Scope-DPU-Driven 構成 (area: `architecture`, slug: `smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup`)
- `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md` - SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携） (area: `architecture`, slug: `smartswitch-high-availability-manager-daemon-hamgrd-design`)
- `docs/management/smart-switch-gnmi-feedback-design-omit-in-toc.md` - SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id） (area: `management`, slug: `smart-switch-gnmi-feedback-design-omit-in-toc`)
- `docs/overlay/smartswitch-eni-based-forwarding.md` - SmartSwitch ENI Based Forwarding（DashEniFwdOrch / ENI_REDIRECT ACL） (area: `overlay`, slug: `smartswitch-eni-based-forwarding`)
- `docs/platform/smartswitch-dpu-graceful-shutdown.md` - Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT） (area: `platform`, slug: `smartswitch-dpu-graceful-shutdown`)
- `docs/platform/smartswitch-pmon-high-level-design.md` - SmartSwitch PMON（NPU 側 pmon と DPU 連携の境界） (area: `platform`, slug: `smartswitch-pmon-high-level-design`)
- `docs/system/independent-dpu-upgrade.md` - Smart Switch: DPU 独立アップグレード（gNOI 経路） (area: `system`, slug: `independent-dpu-upgrade`)
- `docs/system/smart-switch-ip-address-assignment.md` - Smart Switch DPU IP アドレス割当（midplane bridge / DHCP server） (area: `system`, slug: `smart-switch-ip-address-assignment`)
- `docs/system/smart-switch-reboot-high-level-design.md` - SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot） (area: `system`, slug: `smart-switch-reboot-high-level-design`)

### Dual-ToR 関連 (12 pages)

- `docs/architecture/dhcpv6-relay-agent.md` - DHCPv6 Relay Agent（Option 79 / dual ToR loopback） (area: `architecture`, slug: `dhcpv6-relay-agent`)
- `docs/management/design-doc.md` - gRPC client（active-active DualToR / ycabled ↔ SoC 連携） (area: `management`, slug: `design-doc`)
- `docs/overlay/active-active-dual-tor.md` - Active-Active Dual ToR（gRPC ベース cable control + prefix-based neighbor） (area: `overlay`, slug: `active-active-dual-tor`)
- `docs/overlay/active-standby-dual-tor.md` - Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel） (area: `overlay`, slug: `active-standby-dual-tor`)
- `docs/overlay/dscp-remapping-for-tunnel-traffic.md` - トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避） (area: `overlay`, slug: `dscp-remapping-for-tunnel-traffic`)
- `docs/platform/icmp-hardware-offload.md` - ICMP Hardware Offload（DualToR link prober の NPU 化） (area: `platform`, slug: `icmp-hardware-offload`)
- `docs/reference/cli/config-muxcable.md` - config muxcable サブコマンド (area: `reference`, slug: `config-muxcable`)
- `docs/reference/cli/show-muxcable.md` - show muxcable サブコマンド (area: `reference`, slug: `show-muxcable`)
- `docs/reference/config-db/mux-cable.md` - MUX_CABLE テーブル (area: `reference`, slug: `mux-cable`)
- `docs/routing/default-route.md` - linkmgrd のデフォルトルート連動（DualToR mux 制御） (area: `routing`, slug: `default-route`)
- `docs/routing/multiple-nexthop-route-hld.md` - dual-tor mux 跨ぎの multi-nexthop route ループ回避（MuxOrch::updateRoute） (area: `routing`, slug: `multiple-nexthop-route-hld`)
- `docs/routing/prefix-based-mux-neighbors.md` - プレフィックスルート方式の Mux ネイバ（Dual-ToR の状態遷移最適化） (area: `routing`, slug: `prefix-based-mux-neighbors`)

### Warm-Reboot / Fast-Reboot 関連 (12 pages)

- `docs/reference/cli/reboot-fast-warm.md` - reboot / fast-reboot / warm-reboot コマンド (area: `reference`, slug: `reboot-fast-warm`)
- `docs/routing/vrf-feature-ansible-test-plan-omit-in-toc.md` - VRF Ansible テストプラン（T0 上で BGP/ACL/loopback/warm-reboot 含む E2E 検証） (area: `routing`, slug: `vrf-feature-ansible-test-plan-omit-in-toc`)
- `docs/switching/increasing-lacp-pdu-timeout-during-warm-reboot.md` - Warm-reboot 中の LACP retry count 拡張（LACP version 0xf1 / 新規 TLV） (area: `switching`, slug: `increasing-lacp-pdu-timeout-during-warm-reboot`)
- `docs/switching/view-switching-in-producerstatetable.md` - ProducerStateTable の view switching（warm reboot 用の差分適用） (area: `switching`, slug: `view-switching-in-producerstatetable`)
- `docs/system/fast-reboot-flow-improvements-hld.md` - Fast-reboot Flow Improvements（finalizer / reconciliation） (area: `system`, slug: `fast-reboot-flow-improvements-hld`)
- `docs/system/kdump.md` - kdump（kexec ベース kernel crash dump / makedumpfile） (area: `system`, slug: `kdump`)
- `docs/system/multi-asic-warm-reboot.md` - Multi-ASIC warm reboot（namespace 横断の協調 shutdown / boot） (area: `system`, slug: `multi-asic-warm-reboot`)
- `docs/system/sonic-libsairedis-api-idempotence-support.md` - libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止） (area: `system`, slug: `sonic-libsairedis-api-idempotence-support`)
- `docs/system/sonic-swss-docker-warm-restart.md` - SWSS docker warm restart（state restore / consistency / sync up） (area: `system`, slug: `sonic-swss-docker-warm-restart`)
- `docs/system/sonic-warm-reboot.md` - SONiC Warm Reboot（要件・順序・docker 別 warm restart） (area: `system`, slug: `sonic-warm-reboot`)
- `docs/system/swss-docker-warm-restart-code-reference.md` - SWSS docker の Warm Restart 実装メモ（開発時リファレンス） (area: `system`, slug: `swss-docker-warm-restart-code-reference`)
- `docs/system/what-are-the-development-phases-and-scope-for-warm-reboot.md` - Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison） (area: `system`, slug: `what-are-the-development-phases-and-scope-for-warm-reboot`)

### Multi-ASIC / VOQ chassis 関連 (20 pages)

- `docs/acl-qos/distributed-forwarding-in-a-virtual-output-queue-voq-architecture.md` - VoQ アーキテクチャの分散転送（FSI/SSI と Chassis DB / redis_chassis） (area: `acl-qos`, slug: `distributed-forwarding-in-a-virtual-output-queue-voq-architecture`)
- `docs/internals/aggregate-voq-counters-in-sonic.md` - VOQ カウンタ集約（chassis supervisor からの aggregate 表示） (area: `internals`, slug: `aggregate-voq-counters-in-sonic`)
- `docs/internals/support-redis-databases-in-multiple-namespaces.md` - Multi-ASIC 名前空間の Redis（database_global.json と SonicDBConfig） (area: `internals`, slug: `support-redis-databases-in-multiple-namespaces`)
- `docs/platform/1-sonic-on-multi-asic-platforms.md` - SONiC on Multi-ASIC platforms（namespace / per-asic Redis / sonic-net） (area: `platform`, slug: `1-sonic-on-multi-asic-platforms`)
- `docs/platform/automatic-module-provisioning-for-chassis.md` - Chassis Line Card 自動プロビジョニング（sonic-provisiond / provision_module） (area: `platform`, slug: `automatic-module-provisioning-for-chassis`)
- `docs/platform/db-design-for-multi-asic-scenarios.md` - multi-ASIC 用 Golden Config 単一 JSON フォーマット（localhost / asic0 / asic1 ...） (area: `platform`, slug: `db-design-for-multi-asic-scenarios`)
- `docs/platform/everflow-support-on-voq-chassis.md` - VoQ Chassis での Everflow ミラー（recycle port 経由の rewrite） (area: `platform`, slug: `everflow-support-on-voq-chassis`)
- `docs/platform/fabric-port-support-on-sonic.md` - VOQ シャーシの Fabric ポート（fabric ASIC 管理 / link monitoring） (area: `platform`, slug: `fabric-port-support-on-sonic`)
- `docs/platform/global-platform-specific-psuutil-class-instance.md` - 新 Platform API（sonic_platform / Chassis / PSU/Fan/Sfp の Python クラス階層） (area: `platform`, slug: `global-platform-specific-psuutil-class-instance`)
- `docs/platform/multi-asic-single-json-configuration-design.md` - Multi-ASIC Single JSON Configuration（Golden Config に namespace layer） (area: `platform`, slug: `multi-asic-single-json-configuration-design`)
- `docs/platform/recirculation-port-support-on-voq-chassis.md` - VOQ シャシでの recirculation port サポート（Inb / Rec ポートロール） (area: `platform`, slug: `recirculation-port-support-on-voq-chassis`)
- `docs/platform/single-asic-voq-fixed-system-sonic.md` - 単一 ASIC VoQ 固定システム（chassisdb.conf による is_voq_chassis 分岐） (area: `platform`, slug: `single-asic-voq-fixed-system-sonic`)
- `docs/platform/voq-sonic.md` - VoQ SONiC（distributed VoQ chassis / system-port / fabric） (area: `platform`, slug: `voq-sonic`)
- `docs/routing/bgp-setup-for-voq-chassis.md` - VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax） (area: `routing`, slug: `bgp-setup-for-voq-chassis`)
- `docs/routing/reliable-tsa.md` - Reliable TSA（VoQ Chassis 全体での TSA を CHASSIS_APP_DB で同期） (area: `routing`, slug: `reliable-tsa`)
- `docs/switching/lag-on-distributed-voq-system.md` - 分散 VOQ シャシでの LAG（SYSTEM_LAG_TABLE と system_lag_id） (area: `switching`, slug: `lag-on-distributed-voq-system`)
- `docs/system/multi-asic-warm-reboot.md` - Multi-ASIC warm reboot（namespace 横断の協調 shutdown / boot） (area: `system`, slug: `multi-asic-warm-reboot`)
- `docs/system/platform-monitor-design-for-multi-asic-platforms.md` - PMON の Multi-ASIC 対応（global DB と per-ASIC namespace の役割分担） (area: `system`, slug: `platform-monitor-design-for-multi-asic-platforms`)
- `docs/system/platform-monitor-requirement-for-chassis-subsystem.md` - シャーシサブシステムにおける Platform Monitor 要件（Mandatory + Future） (area: `system`, slug: `platform-monitor-requirement-for-chassis-subsystem`)
- `docs/system/sonic-entity-mib-and-entity-sensor-mib-extension.md` - Entity MIB / Entity Sensor MIB 拡張（chassis 階層化と sensor / fan / PSU 追加） (area: `system`, slug: `sonic-entity-mib-and-entity-sensor-mib-extension`)

### BGP / EVPN 関連 (41 pages)

- `docs/architecture/sonic-policy-based-hashing.md` - Policy Based Hashing（PBH: NVGRE / VxLAN inner 5-tuple） (area: `architecture`, slug: `sonic-policy-based-hashing`)
- `docs/overlay/vnet-local-endpoint-forwarding.md` - VNET の Local Endpoint Forwarding（DPU 直結 nexthop の最適化） (area: `overlay`, slug: `vnet-local-endpoint-forwarding`)
- `docs/overlay/vxlan-sonic.md` - VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper） (area: `overlay`, slug: `vxlan-sonic`)
- `docs/reference/cli/config-bgp.md` - config bgp サブコマンド (area: `reference`, slug: `config-bgp`)
- `docs/reference/cli/config-vxlan.md` - config vxlan サブコマンド (area: `reference`, slug: `config-vxlan`)
- `docs/reference/cli/show-bgp.md` - show bgp / show ip bgp / show ipv6 bgp サブコマンド (area: `reference`, slug: `show-bgp`)
- `docs/reference/cli/show-route-map.md` - show route-map コマンド (area: `reference`, slug: `show-route-map`)
- `docs/reference/config-db/bgp-aggregate-address.md` - BGP_AGGREGATE_ADDRESS テーブル (area: `reference`, slug: `bgp-aggregate-address`)
- `docs/reference/config-db/bgp-device-global.md` - BGP_DEVICE_GLOBAL テーブル (area: `reference`, slug: `bgp-device-global`)
- `docs/reference/config-db/bgp-globals.md` - BGP_GLOBALS テーブル (area: `reference`, slug: `bgp-globals`)
- `docs/reference/config-db/bgp-neighbor-af.md` - BGP_NEIGHBOR_AF テーブル (area: `reference`, slug: `bgp-neighbor-af`)
- `docs/reference/config-db/bgp-neighbor.md` - BGP_NEIGHBOR テーブル (area: `reference`, slug: `bgp-neighbor`)
- `docs/reference/config-db/bgp-peer-group-af.md` - BGP_PEER_GROUP_AF テーブル (area: `reference`, slug: `bgp-peer-group-af`)
- `docs/reference/config-db/bgp-peer-group.md` - BGP_PEER_GROUP テーブル (area: `reference`, slug: `bgp-peer-group`)
- `docs/reference/config-db/prefix-list.md` - PREFIX_LIST テーブル (BGP) (area: `reference`, slug: `prefix-list`)
- `docs/reference/config-db/prefix-set.md` - PREFIX_SET テーブル (area: `reference`, slug: `prefix-set`)
- `docs/reference/config-db/route-map.md` - ROUTE_MAP テーブル (area: `reference`, slug: `route-map`)
- `docs/reference/config-db/vxlan-tunnel-map.md` - VXLAN_TUNNEL_MAP テーブル (area: `reference`, slug: `vxlan-tunnel-map`)
- `docs/reference/config-db/vxlan-tunnel.md` - VXLAN_TUNNEL テーブル (area: `reference`, slug: `vxlan-tunnel`)
- `docs/reference/yang/sonic-bgp-global.md` - sonic-bgp-global YANG (area: `reference`, slug: `sonic-bgp-global`)
- ... and 21 more

### SAI 拡張属性追加系 (9 pages)

- `docs/acl-qos/egress-mirroring-support-and-acl-action-capability-check.md` - ACL の egress mirror 対応と SAI ベース action capability 問い合わせ (area: `acl-qos`, slug: `egress-mirroring-support-and-acl-action-capability-check`)
- `docs/architecture/port-profile-init-hld.md` - Port Profile Init（SAI bulk port API による fast-boot 高速化） (area: `architecture`, slug: `port-profile-init-hld`)
- `docs/architecture/sonic-port-auto-fec-design.md` - Port Auto FEC（SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE / FEC=auto） (area: `architecture`, slug: `sonic-port-auto-fec-design`)
- `docs/platform/dump-on-sai-failure.md` - SAI 失敗時の dump 取得（syncd_dump.sh / SAI_REDIS_NOTIFY_SYNCD_INVOKE_DUMP） (area: `platform`, slug: `dump-on-sai-failure`)
- `docs/platform/hld-for-handling-sai-failures.md` - SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB） (area: `platform`, slug: `hld-for-handling-sai-failures`)
- `docs/platform/query-stats-capability-new-sai-api-indroduction.md` - sai_query_stats_capability による Counter Capability 一括取得 (area: `platform`, slug: `query-stats-capability-new-sai-api-indroduction`)
- `docs/platform/sai-api-version-check.md` - SAI API バージョン整合チェック（sai_query_api_version + ビルド時検査） (area: `platform`, slug: `sai-api-version-check`)
- `docs/switching/sonic-sai-post-support-for-macsec.md` - FIPS 向け MACsec SAI POST（FIPS_MACSEC_POST_TABLE） (area: `switching`, slug: `sonic-sai-post-support-for-macsec`)
- `docs/system/generic-sai-extension-critical-resource-monitoring-crm.md` - Generic SAI Extension テーブルの CRM（CRM_EXT_TABLE） (area: `system`, slug: `generic-sai-extension-critical-resource-monitoring-crm`)

### MIB / SNMP 関連 (8 pages)

- `docs/architecture/port-illegal-packets-drop-design.md` - ポート不正パケットドロップ設計（Interface MIB / L3 カウンタ拡張） (area: `architecture`, slug: `port-illegal-packets-drop-design`)
- `docs/reference/cli/config-snmp.md` - config snmp / snmpagentaddress / snmptrap サブコマンド (area: `reference`, slug: `config-snmp`)
- `docs/switching/sonic-basic-l2-mode-test-plan.md` - SONiC Basic L2 モードテストプラン（FDB / VLAN / SNMP の最小機能検証） (area: `switching`, slug: `sonic-basic-l2-mode-test-plan`)
- `docs/system/snmp-migration-from-snmp-yml-to-configdb.md` - SNMP 設定の snmp.yml → CONFIG_DB 移行 (area: `system`, slug: `snmp-migration-from-snmp-yml-to-configdb`)
- `docs/system/snmp-transceiver-monitoring-testbed-test-plan.md` - SNMP Transceiver Monitoring テストプラン（Entity MIB / Entity Sensor MIB） (area: `system`, slug: `snmp-transceiver-monitoring-testbed-test-plan`)
- `docs/system/sonic-entity-mib-and-entity-sensor-mib-extension.md` - Entity MIB / Entity Sensor MIB 拡張（chassis 階層化と sensor / fan / PSU 追加） (area: `system`, slug: `sonic-entity-mib-and-entity-sensor-mib-extension`)
- `docs/system/sonic-snmp-changes-to-support-ipv6.md` - SNMP IPv6 応答の SRC IP 不整合と SNMP_AGENT_ADDRESS_CONFIG による回避 (area: `system`, slug: `sonic-snmp-changes-to-support-ipv6`)
- `docs/system/sonic-snmp-table-schema-proposal.md` - SNMP TABLE スキーマ提案（SNMP / SNMP_COMMUNITY / SNMP_USER） (area: `system`, slug: `sonic-snmp-table-schema-proposal`)

### gNMI / gNOI / OpenConfig 関連 (57 pages)

- `docs/management/gnmi-master-arbitration-hld.md` - gNMI Master Arbitration（election ID と SetRequest 拡張） (area: `management`, slug: `gnmi-master-arbitration-hld`)
- `docs/management/gnmi-usage.md` - gNMI クライアントツールの使い方（gnmi_get / gnmi_set / gnmi_cli） (area: `management`, slug: `gnmi-usage`)
- `docs/management/gnoi-hld-for-file-and-factory-reset-apis.md` - gNOI File.Remove と FactoryReset.Start（gNMI/UMF + DBUS host service） (area: `management`, slug: `gnoi-hld-for-file-and-factory-reset-apis`)
- `docs/management/gnoi-hld-for-healthz-api.md` - gNOI Healthz API（Get / Acknowledge / Artifact + DBUS host service） (area: `management`, slug: `gnoi-hld-for-healthz-api`)
- `docs/management/gnoi-hld-for-os-apis.md` - gNOI OS API（Install / Activate / Verify と sonic-installer 連携） (area: `management`, slug: `gnoi-hld-for-os-apis`)
- `docs/management/gnoi-hld-for-system-apis.md` - gNOI System Reboot / RebootStatus / CancelReboot（reboot method と sanity check） (area: `management`, slug: `gnoi-hld-for-system-apis`)
- `docs/management/json-patch-ordering-using-yang-models.md` - JSON Patch ordering（YANG 制約に従う apply-patch のステップ分割） (area: `management`, slug: `json-patch-ordering-using-yang-models`)
- `docs/management/openconfig-support-for-ethernet-interfaces.md` - OpenConfig Interfaces YANG（Ethernet 設定の REST/gNMI 対応と sonic-mgmt-common transformer） (area: `management`, slug: `openconfig-support-for-ethernet-interfaces`)
- `docs/management/save-on-set-hld.md` - gNMI Save-On-Set（Set ごとの ConfigDB 永続化） (area: `management`, slug: `save-on-set-hld`)
- `docs/management/smart-switch-gnmi-feedback-design-omit-in-toc.md` - SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id） (area: `management`, slug: `smart-switch-gnmi-feedback-design-omit-in-toc`)
- `docs/management/sonic-cli-auto-generation-tool.md` - SONiC CLI 自動生成ツール（YANG → click plugin 自動生成） (area: `management`, slug: `sonic-cli-auto-generation-tool`)
- `docs/management/sonic-config-update-validation-via-yang.md` - YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ） (area: `management`, slug: `sonic-config-update-validation-via-yang`)
- `docs/management/sonic-gnmi-server-interface-design.md` - SONiC gNMI Server インタフェース設計（CONFIG_DB / SONiC YANG / Generic Config Updater 連携） (area: `management`, slug: `sonic-gnmi-server-interface-design`)
- `docs/management/sonic-management-framework.md` - SONiC Management Framework（REST / gNMI / Translib / Transformer） (area: `management`, slug: `sonic-management-framework`)
- `docs/management/sonic-nos-configuration-methods.md` - SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP / vtysh / redis / apply-patch） (area: `management`, slug: `sonic-nos-configuration-methods`)
- `docs/management/sonic-yang-model-guidelines.md` - SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang） (area: `management`, slug: `sonic-yang-model-guidelines`)
- `docs/platform/liquid-cooling-leakage-detection-in-sonic.md` - 液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント） (area: `platform`, slug: `liquid-cooling-leakage-detection-in-sonic`)
- `docs/platform/smartswitch-dpu-graceful-shutdown.md` - Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT） (area: `platform`, slug: `smartswitch-dpu-graceful-shutdown`)
- `docs/reference/yang/sonic-bgp-global.md` - sonic-bgp-global YANG (area: `reference`, slug: `sonic-bgp-global`)
- `docs/reference/yang/sonic-bgp-neighbor.md` - sonic-bgp-neighbor YANG (area: `reference`, slug: `sonic-bgp-neighbor`)
- ... and 37 more

### Container / Build system 関連 (14 pages)

- `docs/architecture/build-profiles.md` - ビルドプロファイル（rules/profiles/*.mk） (area: `architecture`, slug: `build-profiles`)
- `docs/architecture/build-system-improvements.md` - ビルド時間最適化（Dockerfile レイヤ削減 / BuildKit / 並列 dh / sairedis 分離） (area: `architecture`, slug: `build-system-improvements`)
- `docs/architecture/rfs-split-build-improvements-hld.md` - RFS Split build（build_debian.sh の 2 段化と squashfs 中間配備） (area: `architecture`, slug: `rfs-split-build-improvements-hld`)
- `docs/platform/sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md` - NPU MDIO アクセスと gbsyncd 単一 docker 化 (area: `platform`, slug: `sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld`)
- `docs/routing/dhcp-relay-for-ipv6-hld.md` - DHCPv6 リレー（dhcp-relay docker 内の dhcrelay -6 プロセス） (area: `routing`, slug: `dhcp-relay-for-ipv6-hld`)
- `docs/system/process-and-docker-stats-availability-via-telemetry-agent.md` - Process / Docker stats のテレメトリ公開（PROCESS_STATS / DOCKER_STATS） (area: `system`, slug: `process-and-docker-stats-availability-via-telemetry-agent`)
- `docs/system/secure-upgrade.md` - Secure Upgrade（image 署名検証 / SECURE_UPGRADE_MODE） (area: `system`, slug: `secure-upgrade`)
- `docs/system/sonic-container-hardening.md` - SONiC Container Hardening（capability / read-only / privileged 削減） (area: `system`, slug: `sonic-container-hardening`)
- `docs/system/sonic-debian-upgrade-cadence.md` - SONiC Debian アップグレード方針（base / container / 廃止 cadence） (area: `system`, slug: `sonic-debian-upgrade-cadence`)
- `docs/system/sonic-os-sonic-docker-images-versioning.md` - SONiC OS と Docker イメージのセマンティックバージョニング (area: `system`, slug: `sonic-os-sonic-docker-images-versioning`)
- `docs/system/sonic-swss-docker-warm-restart.md` - SWSS docker warm restart（state restore / consistency / sync up） (area: `system`, slug: `sonic-swss-docker-warm-restart`)
- `docs/system/sonic-syslog-message-rate-limit-configuration-per-container.md` - syslog rate limit のコンテナ単位設定（SYSLOG_CONFIG / SYSLOG_CONFIG_FEATURE） (area: `system`, slug: `sonic-syslog-message-rate-limit-configuration-per-container`)
- `docs/system/sonic-warm-reboot.md` - SONiC Warm Reboot（要件・順序・docker 別 warm restart） (area: `system`, slug: `sonic-warm-reboot`)
- `docs/system/swss-docker-warm-restart-code-reference.md` - SWSS docker の Warm Restart 実装メモ（開発時リファレンス） (area: `system`, slug: `swss-docker-warm-restart-code-reference`)

### その他 (286 pages)

- `docs/acl-qos/acl-flex-counters-support.md` - ACL カウンタの flex counter 化（ACL_COUNTER + COUNTERS_ACL_COUNTER_RULE_MAP） (area: `acl-qos`, slug: `acl-flex-counters-support`)
- `docs/acl-qos/acl-in-sonic.md` - ACL in SONiC（テーブル型 / マッチ・アクション / SWSS パイプライン） (area: `acl-qos`, slug: `acl-in-sonic`)
- `docs/acl-qos/acl-ingress-egress-test-plan.md` - ACL Ingress / Egress テストプラン（DATAINGRESS / DATAEGRESS テーブル） (area: `acl-qos`, slug: `acl-ingress-egress-test-plan`)
- `docs/acl-qos/acl-support-in-sonic.md` - ACL の基本設計（ACL_TABLE / ACL_RULE スキーマ） (area: `acl-qos`, slug: `acl-support-in-sonic`)
- `docs/acl-qos/acl-user-defined-table-type-support.md` - ACL ユーザ定義テーブルタイプ（ACL_TABLE_TYPE と AclTableType） (area: `acl-qos`, slug: `acl-user-defined-table-type-support`)
- `docs/acl-qos/align-watermark-flow-with-port-configuration-hld.md` - flexcounter の queue/PG map 生成と watermark 有効化の整合 (area: `acl-qos`, slug: `align-watermark-flow-with-port-configuration-hld`)
- `docs/acl-qos/asymmetric-pfc-test-plan.md` - Asymmetric PFC テストプラン（PTF + sonic-mgmt fixtures） (area: `acl-qos`, slug: `asymmetric-pfc-test-plan`)
- `docs/acl-qos/configurable-drop-counters-in-sonic.md` - 設定可能な Drop Counter（DEBUG_COUNTER と SAI debug counter） (area: `acl-qos`, slug: `configurable-drop-counters-in-sonic`)
- `docs/acl-qos/copp-manager-redesign-test-plan.md` - CoPP Manager 再設計テストプラン（feature テーブル整合性 + always_enabled） (area: `acl-qos`, slug: `copp-manager-redesign-test-plan`)
- `docs/acl-qos/copp-neighbor-miss-trap-and-enhancements.md` - CoPP Neighbor Miss trap と enum capability query（show copp configuration） (area: `acl-qos`, slug: `copp-neighbor-miss-trap-and-enhancements`)
- `docs/acl-qos/dhcp-dos-mitigation-in-sonic.md` - DHCP DoS 緩和（ポート単位 DHCP レート制限・Linux TC ベース） (area: `acl-qos`, slug: `dhcp-dos-mitigation-in-sonic`)
- `docs/acl-qos/dynamically-headroom-calculation.md` - Dynamic Headroom Calculation（buffer_model = dynamic） (area: `acl-qos`, slug: `dynamically-headroom-calculation`)
- `docs/acl-qos/egress-outer-dscp-change-table.md` - Egress Outer DSCP 書換 ACL（UNDERLAY_SET_DSCP / METADATA + EGR_SET_DSCP） (area: `acl-qos`, slug: `egress-outer-dscp-change-table`)
- `docs/acl-qos/enhancements-on-show-acl-commands.md` - show acl 強化（STATE_DB.ACL_TABLE_TABLE / ACL_RULE_TABLE の status） (area: `acl-qos`, slug: `enhancements-on-show-acl-commands`)
- `docs/acl-qos/enhancements-to-add-or-del-ports-dynamically.md` - ポートの動的 add / del（zero-port 起動と post-init 操作） (area: `acl-qos`, slug: `enhancements-to-add-or-del-ports-dynamically`)
- `docs/acl-qos/everflow-test-plan.md` - Everflow テストプラン（ingress + egress mirror、LAG / ECMP / IPv6） (area: `acl-qos`, slug: `everflow-test-plan`)
- `docs/acl-qos/pfc-historical-statistics.md` - PFC 履歴統計（PFCWD lua スクリプトによる estimate と --history CLI） (area: `acl-qos`, slug: `pfc-historical-statistics`)
- `docs/acl-qos/port-access-control-in-sonic.md` - Port Access Control（PAC: 802.1x / MAB / RADIUS） (area: `acl-qos`, slug: `port-access-control-in-sonic`)
- `docs/acl-qos/port-buffer-drop-counters-in-sonic.md` - ポートバッファドロップカウンタ（PORT_BUFFER_DROP FC group） (area: `acl-qos`, slug: `port-buffer-drop-counters-in-sonic`)
- `docs/acl-qos/reclaim-reserved-buffer-sequence-flow.md` - 未使用ポートの予約バッファ回収（reclaim reserved buffer）シーケンス (area: `acl-qos`, slug: `reclaim-reserved-buffer-sequence-flow`)
- ... and 266 more

## 実装案

### 案 A: `docs/categories/<category>.md` を作る

Pros:

- `mkdocs.yml` や既存ページ frontmatter を大きく変えずに始められる。
- カテゴリごとに短い説明、代表的な読み順、関連 area へのリンクを人手で調整できる。
- 現行の area 階層を維持したまま、横断的な入口だけを追加できる。

Cons:

- ページ追加・リネーム時にカテゴリページのリンク更新が必要。
- 1 ページが複数カテゴリに属する場合、手動リンクの重複管理が発生する。
- `mkdocs.yml` または `.pages` の nav 連携方針を別途決める必要がある。

### 案 B: mkdocs-material の Tags プラグインを導入する

Pros:

- frontmatter の `tags` からカテゴリ一覧を自動生成でき、重複カテゴリにも強い。
- ページ単位でタグを持てるため、検索・フィルタ・将来の自動集計に向く。
- 読み手のペルソナタグや機能ファミリータグを同じ仕組みで扱える。

Cons:

- `mkdocs.yml` の plugin 設定変更が必要。
- 全ページまたは対象ページの frontmatter に `tags` を追加する移行作業が必要。
- タグ名の表記揺れを lint する仕組みがないと、長期的に品質が落ちやすい。

### 案 C: `.pages` の `nav` で hidden category として並べる

Pros:

- 既存の `mkdocs-awesome-pages-plugin` 前提なら、局所的な `.pages` 追加でカテゴリ一覧を制御できる。
- area 階層のナビゲーションを崩さず、必要なカテゴリだけを隠しページとして置ける。
- 初期導入では `docs/categories/` と組み合わせやすい。

Cons:

- `.pages` nav は単一の表示順制御が主目的で、タグのような自動分類ではない。
- hidden にすると発見性は検索・リンク元に依存する。
- ページリストの生成・更新は結局手動または別スクリプトになる。

## 推奨案

短期は案 A を推奨する。まず `docs/categories/<category>.md` に人が読める横断入口を作り、今回のような機械抽出結果を初期リストとして使う。本文や frontmatter に触らず始められ、現行 area 階層への影響が小さい。

中期は案 A と案 C の併用がよい。`docs/categories/` を通常 nav に出すか hidden にするかは、トップページからの導線を見て決める。

長期は案 B に移行する価値がある。ただし導入時は `tags` の正規化ルール、許可タグ一覧、CI でのタグ検証を一緒に入れるべき。ページ数が 455 件あるため、Tags プラグインだけ先に入れても分類品質は安定しない。
