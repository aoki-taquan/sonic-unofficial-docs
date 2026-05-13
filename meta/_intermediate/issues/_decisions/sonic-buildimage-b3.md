# sonic-net/sonic-buildimage Issue AI 判定結果 (Batch 3)

リポジトリ: sonic-net/sonic-buildimage  
入力: 255 issues  
判定日: 2026-05-13

## 判定基準

- **apply**: バグの実装上の落とし穴 / HLD 不足 / 仕様変更 / 既知の制限 / 有効な workaround を含む
- **skip**: 単なる質問・重複・運営系・ハードウェア固有・古すぎて現状不明・feature tracking のみ

---

## 判定一覧

| # | タイトル | state | 判定 | 反映先 | 反映内容要約 |
|---|---------|-------|------|--------|-------------|
| 20730 | After onie install with latest sonic-utilities configuration is not loaded into CONFIG_DB | CLOSED | apply | `docs/management/ztp-zero-touch-provisioning-hld.md` | ONIE インストール後に CONFIG_DB への設定ロードが行われない回帰。sonic-utilities の config save/load フローが変更され startup-config が反映されない場合がある |
| 20737 | Sonic bullseye slave docker image build failure | OPEN | skip | - | ビルドインフラ依存のブロブストレージ障害。一時的な外部サービス問題 |
| 20741 | [ZTP] sonic-ztp service runs every boot and incurs high CPU usage during boot even when disabled | OPEN | apply | `docs/management/ztp-zero-touch-provisioning-hld.md` | ZTP 無効化後も sonic-ztp.service がブート毎に起動し高 CPU 使用率を発生させる既知問題。無効化は `config ztp disable` で行うが service unit が停止しない場合あり |
| 20755 | Concerns over sonicstorage.blob.core.windows.net downtime | OPEN | skip | - | ビルドインフラ依存の外部ストレージ障害。運営系 |
| 20775 | [eventd]: Eventd failing to start due to rsyslogd on multi-asic | CLOSED | apply | `docs/system/eventd-event-driven-framework-hld.md` | Multi-ASIC 環境で eventd が rsyslogd の起動順序依存により起動失敗する既知問題。supervisord の依存関係設定不足が原因 |
| 20784 | [202405] Inserting/Removing SFP causes attribute update timeout and crash on switches Broadcom ASIC | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | SFP 抜き差し時に xcvrd が SAI 属性更新タイムアウトを起こしクラッシュ。Broadcom ASIC 限定。xcvrd の再起動で回復するが自動化されない |
| 20787 | vstest is failing in sonic-swss repo in recent runs due to "generate coverage" step failing | CLOSED | skip | - | CI/テスト基盤問題。運営系 |
| 20794 | [202311] ./fsroot-broadcom pip3 install --no-build-isolation pygobject error | OPEN | skip | - | ビルド環境依存の pygobject インストールエラー。特定リリースブランチのビルド問題 |
| 20837 | [orchagent/syncd] Adding Loopback0 IP causes orchagent/syncd crash/dump on Accton-AS9716-32D Tomahawk | OPEN | apply | `docs/routing/loopback-interface.md` | Loopback0 に IP アドレスを追加すると VXLAN トンネル orcha とのレース条件で orchagent/syncd がクラッシュ。回避策: tunneldecaporch.cpp のパッチ適用 |
| 20872 | [Bug][202405]: test/test_acl.py Fail with AssertionError: Rule counters should be ready! | CLOSED | skip | - | テスト安定性問題。CI 運営系 |
| 20874 | Multi-asic support for ApplyPatchDb API for gNMI | OPEN | apply | `docs/management/gnmi-incremental-config-update-through-grpc-hld.md` | GCU apply-patch が Multi-ASIC 環境で namespace/asic ID プレフィックスを正しく扱えない制限あり。sonic-utilities#3249 で対応済みだが gNMI 側の統合が必要 |
| 20875 | GNMI_GNXI Unable to set-update for Multi-asic Environment[Master,2405] | CLOSED | apply | `docs/management/gnmi-incremental-config-update-through-grpc-hld.md` | gNMI set-update が Multi-ASIC 環境で失敗する既知問題。namespace プレフィックスの扱いに起因 |
| 20913 | [2405][BRCM-DNX]: sonic-clear queuecounter CLI does not clear the queue counters | CLOSED | apply | `docs/system/queue-counter-polling.md` | BRCM-DNX プラットフォームで `sonic-clear queuecounter` が機能しない。Flex Counter クリア処理が DNX では未実装 |
| 20924 | [Dual-ToR Active-Active][202405] show flowcnt-route stats returns empty line after config reload | CLOSED | apply | `docs/switching/dual-tor-active-active-hld.md` | Dual-ToR AA 環境で `config reload` 後に `show flowcnt-route stats` が空を返す。flowcnt-route カウンターが CONFIG_DB リロード時にリセットされない不具合 |
| 20925 | [Bookworm] Timezone setting is not propagated to containers | CLOSED | apply | `docs/architecture/sonic-container-management.md` | Bookworm 移行後、ホストの `/etc/timezone` 変更がコンテナに伝播されない。`/etc/localtime` シンボリックリンク方式に変更が必要 |
| 20941 | [VLAN]: Orchagent reports VLAN removal failure due to invalid order of event processing | OPEN | apply | `docs/switching/vlan-hld.md` | VLAN 削除時に依存オブジェクトの削除順序が保証されず orchagent がエラーログを出力する既知問題。イベントキュー処理の順序制御が課題 |
| 20942 | [T2] [Chassis] - Zebra process crashed during line card config-reload | CLOSED | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | T2 シャーシ環境でライン カードの config-reload 中に zebra がクラッシュ。buildimage#20990 で修正済み |
| 20988 | [featured] Race condition causes start failure for dockers | OPEN | apply | `docs/system/system-ready-hld.md` | featured デーモンが systemd 設定ファイルリロード中にドッカー起動を試みてレース条件で失敗する既知問題。202405 でも再現 |
| 20994 | [ErrLog] [memory_checker] Failed to get container ID of 'gnmi'! Exiting ... | OPEN | apply | `docs/system/memory-usage-monitor.md` | memory_checker が gnmi コンテナ ID 取得失敗で終了するエラーログ。コンテナ名検索ロジックの不備 |
| 21008 | [Master/202411] [Chassis] very high CPU on zebra after performing port toggle on all interfaces | CLOSED | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | 全インターフェースのポートトグル後に zebra が高 CPU を消費する既知問題。FRR のルート再計算ストームが原因。202411 で修正 |
| 21019 | Dell S5248F-ON incorrect media_settings.json causing orchagent crash | OPEN | skip | - | Dell プラットフォーム固有の設定ファイル問題 |
| 21075 | [202405] arp_evict_nocarrier doesn't work for non-port-channels | OPEN | apply | `docs/system/arp-neighbor-manager.md` | `arp_evict_nocarrier` カーネルパラメータが Port Channel 以外のインターフェース（VLAN SVI 等）で機能しない制限。202405 で未修正 |
| 21112 | [202405][DualToR] : FRR 8.5.4 regression in Dual ToR | OPEN | apply | `docs/switching/dual-tor-active-active-hld.md` | FRR 8.5.4 で LAG メンバーフラップ後のルート再設定に回帰バグあり。8.5.3 では正常動作。buildimage#17345 参照 |
| 21140 | [eventd] eventd unit test is not stable | CLOSED | skip | - | テスト安定性問題。CI 運営系 |
| 21157 | Log spam from orchagent supervisord | OPEN | apply | `docs/system/orchagent-hld.md` | orchagent supervisord が不要なログを大量出力。supervisord.conf の log_level 設定問題 |
| 21177 | [FRR] L3 EVPN is broken with latest FRR 10.0.1 upgrade | OPEN | apply | `docs/routing/evpn-vxlan-hld.md` | FRR 10.0.1 アップグレード後に L3 EVPN が動作しない回帰。FRR 9.x からの内部 API 変更が原因 |
| 21180 | syncd crash in syncd::VendorSai::logSet() during docker startup | CLOSED | apply | `docs/system/syncd-sai-interface.md` | syncd 起動時の `logSet()` でクラッシュする既知問題。SAI ログ初期化タイミングの競合 |
| 21183 | Applying ACL rule causes BGP neighbor to go down | CLOSED | apply | `docs/security/acl-hld.md` | ACL ルール適用時に BGP セッションが断する既知問題。ACL プログラミング中のパケット処理一時停止が原因と推測 |
| 21232 | MAcsec SAI_MACSEC_SA_STAT_IN_PKTS for the Ingress SC/SA not present in counters_db | CLOSED | apply | `docs/security/macsec-sonic-high-level-design-document.md` | MACsec Ingress SC/SA の `SAI_MACSEC_SA_STAT_IN_PKTS` カウンターが COUNTERS_DB に存在しない。BRCM DNX プラットフォーム限定の既知制限 |
| 21236 | [test_wr_arp] Warm reboot is failing during execution of testWrArpAdvance due to docker exec failure | OPEN | skip | - | テスト安定性問題。CI 運営系 |
| 21243 | [dualtor] CRM test fails on test_crm_nexthop_group when tunnel route created for PortChannel neighbor | CLOSED | apply | `docs/switching/dual-tor-active-active-hld.md` | Dual-ToR で PortChannel ネイバー経由のトンネルルートが CRM nexthop_group カウントに正しく反映されない既知問題 |
| 21246 | Orchagent Keeps Resetting With SAI_STATUS_ATTR_NOT_IMPLEMENTED_6 Error | CLOSED | apply | `docs/system/orchagent-hld.md` | BCM SAI が `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` をサポートしない環境で orchagent が SAI_STATUS_ATTR_NOT_IMPLEMENTED エラーでリセットを繰り返す |
| 21247 | broadcom SAI bug for Trident3-X3 | OPEN | skip | - | Broadcom SAI プラットフォーム固有バグ。SAI ベンダー対応が必要 |
| 21249 | Add support to show ECN marked packets on show queue counters | OPEN | apply | `docs/system/queue-counter-polling.md` | `show queue counters` に ECN マーク済みパケット表示機能がない既知の制限。機能要求として PR あり |
| 21253 | Documentation of in-place upgrade is ambiguous about preserving config and credentials | OPEN | apply | `docs/system/upgrade-workflow.md` | インプレースアップグレードのドキュメントが設定/クレデンシャル保持について曖昧。`sonic-installer` の `install` コマンドは Config 保持するが HLD 記述が不明確 |
| 21267 | [broadcom] Trident3-X3 vxlan tunnel/riot enablement prevent SAI initialization on Dell N3248TE | OPEN | skip | - | Broadcom Trident3-X3 SAI 初期化問題。プラットフォーム固有 |
| 21270 | [FRR-10.0.0] Log message on execution of warm-reboot/fast-reboot mgmt_msg_read: got EOF/disconnect | CLOSED | apply | `docs/system/fast-reboot-hld.md` | FRR 10.0.1 で warm/fast-reboot 実行時に `mgmt_msg_read: got EOF/disconnect` ログが出力される既知問題。FRR mgmtd の接続クリーンアップ動作によるもの |
| 21295 | [ACCTON] [SWSS] Failed to start SWSS on init on Accton AS7326-56X, system unable to show interfaces | OPEN | skip | - | Accton プラットフォーム固有の SWSS 起動失敗 |
| 21315 | DELL S5232F: Dynamic breakout not working | OPEN | skip | - | Dell プラットフォーム固有のダイナミックブレイクアウト問題 |
| 21330 | System is not coming up on TH5 - DCS-7060X6-64PE after loading latest community sonic master build | OPEN | skip | - | Arista/TH5 プラットフォーム固有の起動問題 |
| 21372 | [Smartswitch][reboot-cause] Invalid reboot cause on First boot | CLOSED | apply | `docs/system/reboot-cause-determination.md` | SmartSwitch の DPU 初回ブート時に reboot-cause が正しく記録されない既知問題。NPU/DPU の reboot-cause が混在表示される |
| 21378 | [DHCP_RELAY] DHCP packets would not be flooded to Vlan member after dhcp_relay feature is enabled | OPEN | apply | `docs/network-services/dhcp-relay-hld.md` | dhcp_relay 有効化後に DHCP パケットが VLAN メンバーにフラッディングされない既知問題。dhcrelay の ebtables ルール設定タイミングの不備 |
| 21386 | [RADIUS] Setting source_int for a RADIUS server does not change the source-ip of RADIUS packet | CLOSED | apply | `docs/security/radius-hld.md` | RADIUS サーバーの `source_int` を設定しても RADIUS パケットの送信元 IP が変更されない既知のバグ。カーネルのルーティングルールが優先される |
| 21440 | The IPv6 link local address generated by default is from random MAC in place of interface / device MAC | OPEN | apply | `docs/network-services/ipv6.md` | IPv6 リンクローカルアドレスがインターフェース MAC ではなくランダム MAC から生成される既知問題。カーネルの privacy extensions 設定が影響 |
| 21450 | [BGP] [202411] vtysh commands following ip nht resolve-via-default are failing to apply | OPEN | apply | `docs/routing/bgp-hld.md` | `ip nht resolve-via-default` 以降の vtysh コマンドが適用されない 202411 の回帰バグ。FRR mgmtd の設定処理順序問題 |
| 21481 | [sonic-platform-modules] subprocess with no shell | OPEN | skip | - | プラットフォームモジュールのコードスタイル問題。セキュリティ懸念だが実害なし |
| 21514 | [Marvell] [ARM64]: Make configure failed in ubuntu20.04 | CLOSED | skip | - | Marvell ARM64 プラットフォーム固有のビルド問題 |
| 21524 | [Chassis] BGP neighbor config is not applied to frr in latest master | CLOSED | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | シャーシ環境で BGP ネイバー設定が FRR に反映されない master の回帰。bgpcfgd のシャーシ対応コードのバグ |
| 21552 | [BRCM-DNX][202405] PFCWD didn't drop RX traffic in stormed condition | CLOSED | apply | `docs/qos/pfcwd-pfc-watchdog-hld.md` | BRCM-DNX プラットフォームで PFCWD がストーム状態での RX トラフィックをドロップしない既知問題。DNX の PFC Watchdog 実装の制限 |
| 21578 | [bgpd] Static route removal failure with "Too few nexthop instances" error log | OPEN | apply | `docs/routing/bgp-hld.md` | staticd が "Too few nexthop instances" エラーで静的ルート削除に失敗する FRR の既知バグ。FRR コミュニティで追跡中 |
| 21590 | [SmartSwitch] Gnmi resets due to memory exceeding threshold when scaled DASH config is applied | OPEN | apply | `docs/management/gnmi-incremental-config-update-through-grpc-hld.md` | SmartSwitch で大規模 DASH 設定適用時に gNMI がメモリ閾値超過でリセットする既知問題 |
| 21603 | Some INNOLIGHT 800G QSFP-DDs get stuck in CMIS DP_INIT intermittently | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | INNOLIGHT 800G QSFP-DD が CMIS DP_INIT 状態でスタックする間欠的な既知問題。CMIS ステートマシンの処理タイムアウトが関係 |
| 21631 | yang(sonic-interface): name of value "Ethernet0.666" points to a non-existing leaf | OPEN | apply | `docs/management/yang-models-hld.md` | サブインターフェース名の YANG バリデーションで存在しないリーフへの参照エラー。sonic-interface YANG モデルのパターン制約不備 |
| 21644 | SONiC Kernel Update Process and Testing Procedures | OPEN | apply | `docs/architecture/build-system-improvements.md` | SONiC カーネルアップデートプロセスのドキュメントが不足。カーネル更新手順・テスト要件が非公式 |
| 21645 | [Scale 10k arp] Traffic drop while arp is being learned | CLOSED | apply | `docs/system/arp-neighbor-manager.md` | 10k ARP スケール環境で ARP 学習中にトラフィックドロップが発生する既知問題。ARP プログラミング遅延によるもの |
| 21656 | Dell S5248F-ON [master branch, broadcom] linux_bcm_knet loads, but ports not available | OPEN | skip | - | Dell S5248F プラットフォーム固有のポート認識問題 |
| 21668 | Dell Z9264F-ON working image | OPEN | skip | - | プラットフォーム互換性確認質問 |
| 21674 | [config] config apply-patch generates a log error when op is set to remove | CLOSED | apply | `docs/management/generic-config-updater-hld.md` | `config apply-patch` で op が remove の場合にエラーログが生成される既知問題。GCU の削除パス処理のバグ |
| 21680 | Syncd container exit on broadcom platform | CLOSED | apply | `docs/system/syncd-sai-interface.md` | Broadcom プラットフォームで syncd コンテナが予期せず終了する既知問題 |
| 21696 | [SONIC-SWSS][DASH_APPLIANCE_TABLE] syslog errors when applying DASH_APPLIANCE_TABLE config without required prerequisites | CLOSED | apply | `docs/network-services/dash-hld.md` | DASH_APPLIANCE_TABLE を前提条件なしで適用すると syslog エラーが大量発生する既知問題。設定順序依存性の制限 |
| 21721 | TSC command doesn't work on the Smart Switch | CLOSED | apply | `docs/architecture/smartswitch-hld.md` | SmartSwitch で TSC (Traffic Shutdown Command) が動作しない既知問題。SmartSwitch の BGP 設定構造に起因 |
| 21787 | SRv6: mismatch between config_db and FRR config | CLOSED | apply | `docs/routing/srv6-hld.md` | SRv6 ロケーター設定が CONFIG_DB と FRR の間で不整合になる既知問題。bgpcfgd の SRv6 設定同期ロジックの制限 |
| 21791 | [monit]: cannot send command to the monit daemon -- Broken pipe | CLOSED | apply | `docs/system/system-ready-hld.md` | config reload 時に monit がデーモンと通信できず "Broken pipe" エラーが発生する既知の軽微な問題 |
| 21815 | [BGP] Running TSA command sometime results in errors from mgmt and failure to go to maintenance mode | OPEN | apply | `docs/routing/bgp-hld.md` | TSA コマンド実行時に mgmtd YANG バリデーションエラーが間欠的に発生しメンテナンスモード移行が失敗する既知問題 |
| 21829 | FRR rejects SRv6 vtysh commands from bgpcfgd when doing bgp service restart | CLOSED | apply | `docs/routing/srv6-hld.md` | BGP サービス再起動時に bgpcfgd が送出する SRv6 vtysh コマンドを FRR mgmtd が拒否する既知問題 |
| 21844 | [warm-reboot] [neighbor_advertiser] control plane assistant request failed, causing a warm reboot cancel | CLOSED | apply | `docs/system/fast-reboot-hld.md` | warm-reboot 時に neighbor_advertiser が CPA リクエストに失敗して warm-reboot がキャンセルされる既知問題 |
| 21862 | [202411][fast-reboot]: Boot time degradation due to YANG Config validation | CLOSED | apply | `docs/system/fast-reboot-hld.md` | fast-reboot/warm-reboot で YANG Config バリデーション処理が追加されたことで起動時間が増大する 202411 の回帰。db_migrator の変更が原因 |
| 21878 | [xcvr api] cmis.get_error_description does not show correct error status when there is split | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | CMIS サブポート分割時に `get_error_description` が正しいエラー状態を返さない既知問題。サブポートのいずれかが admin down の場合にエラー状態を誤表示 |
| 21880 | [memory_checker] cgroup memory usage file memory.usage_in_bytes does not exist on device | CLOSED | apply | `docs/system/memory-usage-monitor.md` | cgroup v2 環境で `memory.usage_in_bytes` ファイルが存在せず memory_checker が失敗する既知問題。cgroup v1/v2 の違いへの対応が必要 |
| 21891 | Unable to Configure ECN on S5248F-ON – ecnconfig Fails and No ECN Marking on Packets | OPEN | skip | - | Dell S5248F プラットフォーム固有の ECN 設定問題 |
| 21900 | [202411][frr]: Local subnet routes are not propagated to the data plane | OPEN | apply | `docs/routing/bgp-hld.md` | FRR 202411 でローカルサブネットルートがデータプレーンに伝播されない高優先度の既知問題 |
| 21902 | media_settings.json tuning values are lost in APPL_DB after swss container is restarted | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | swss コンテナ再起動後に `media_settings.json` の SI チューニング値が APPL_DB から消える既知問題。xcvrd が APPL_DB を再投入しない |
| 21914 | [Chassis] : Set PFCWD detect and restore timer to 600 ms | CLOSED | skip | - | シャーシ固有のパラメータ調整。sonic-mgmt との調整が必要な運営系 |
| 21920 | [Debian Upgrade] After debian upgrade the docker exec calls are taking more time than expected | OPEN | apply | `docs/architecture/sonic-container-management.md` | Debian アップグレード後に `docker exec` の応答時間が増大する既知問題。Bookworm の runc/containerd バージョン変更に起因 |
| 21931 | [BGP] The set src command is sometimes set with no loopback ip address | CLOSED | apply | `docs/routing/bgp-hld.md` | `set src` コマンドが Loopback IP なしに設定される間欠的な既知問題。202411 から発生。bgpcfgd の Loopback IP 取得タイミングの競合 |
| 21938 | [Bug]: BGP remains UP even when egress and ingress disable is set to TRUE on LAG member ports | CLOSED | skip | - | Broadcom SDK の既知動作。ベンダー側の修正待ち |
| 21959 | [SONIC-SWSS][PORT] inconsistent behavior between combine and separate port configuration deployment | CLOSED | apply | `docs/system/orchagent-hld.md` | ポート設定の一括適用と分割適用でオーケストレーション動作が異なる既知問題。orchagent の PORT テーブル処理の不整合 |
| 21962 | [swss] Orchagent terminated by SIGHUP because logrotate sent SIGHUP on boot after warm upgrade | CLOSED | apply | `docs/system/orchagent-hld.md` | 202405→202411 warm-upgrade 後のブート時に logrotate が orchagent に SIGHUP を送信してプロセスが終了する既知問題 |
| 21973 | Build failures with libnl errors Operation not permitted | OPEN | skip | - | ビルド環境固有の libnl 権限エラー。ビルドインフラ問題 |
| 22002 | platform_api_server crashing during platform_tests/api/test_sfp.py::TestSfpApi::test_reset | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | `test_reset` テスト実行中に platform_api_server がクラッシュする既知問題。SFP リセット API の実装の不備 |
| 22047 | [Broadcom][DNX] BGP session was down when injecting data-path ttl1 traffic | OPEN | apply | `docs/routing/bgp-hld.md` | BRCM-DNX プラットフォームで TTL=1 のデータパストラフィックを注入すると BGP セッションが断する既知問題。CPU 処理パスへのトラフィック漏洩が原因 |
| 22055 | Unable to enable/disable the feature if the feature is not added to init_cfg.json.j2 | CLOSED | apply | `docs/system/featured-features-daemon.md` | `init_cfg.json.j2` に未登録の feature は `config feature state` で有効/無効化できない既知の制限。feature 追加時には init_cfg.json.j2 への登録が必須 |
| 22056 | [neighbor_advertiser] neighbor_advertiser -m reset sometimes does not remove VXLAN tunnel | OPEN | apply | `docs/system/fast-reboot-hld.md` | warm-reboot 時の `neighbor_advertiser -m reset` が VXLAN トンネルを完全削除しないことがある既知問題。タイミング依存の競合 |
| 22124 | Regression: External App Extensions fail to start | CLOSED | apply | `docs/system/featured-features-daemon.md` | sonic-utilities の変更により外部アプリ拡張機能が起動失敗する回帰バグ |
| 22166 | Bug: kernel NULL pointer dereference, address: 00000000000002e4 | OPEN | apply | `docs/architecture/sonic-container-management.md` | カーネル NULL ポインタ参照が断続的に発生する既知問題。プラットフォームとカーネルモジュールの組み合わせ依存 |
| 22218 | Bug: [system-health] Fan direction check failure | OPEN | apply | `docs/system/system-health-monitoring-hld.md` | system-health モニター がファン方向チェックで誤検出する既知問題。プラットフォーム API のファン方向定義の不統一 |
| 22291 | Bug: [512 ports] LLDP is not starting after systemctl restart if autorestart is disabled | OPEN | apply | `docs/system/lldp-daemon-hld.md` | 512 ポートスイッチで autorestart 無効時に `systemctl restart lldp` 後に lldp が起動しない既知問題 |
| 22296 | Bug: Broadcom Trident3-X7 maximum tunnels too small | OPEN | apply | `docs/network-services/vxlan-hld.md` | Broadcom Trident3-X7 でサポートされる VXLAN トンネル最大数が 5 に制限されており大規模環境には不十分な既知制限 |
| 22311 | Enhancement: Additional DNS configuration options | CLOSED | apply | `docs/management/sonic-nos-configuration-methods.md` | 追加 DNS 設定オプション（複数ネームサーバー、サーチドメイン）のサポートが限定的な既知制限 |
| 22357 | Bug: GCU enforcement blocks apply-patch on PORT table and introduces validation failures with VLAN | OPEN | apply | `docs/management/generic-config-updater-hld.md` | GCU がポートテーブルへのパッチ適用時に VLAN リファレンスバリデーションエラーを生成する既知問題 |
| 22359 | Enhancement: SNMP dot3 stats (RFC3635 / RFC1284) | OPEN | skip | - | 機能要求。実装も近い状態 |
| 22372 | Enhancement: Improve Generic Config Updater (GCU) performance | CLOSED | apply | `docs/management/generic-config-updater-hld.md` | GCU のパフォーマンス改善。大規模設定変更でのレイテンシが課題。PR で対応済み |
| 22384 | Bug: show platform fan Command Fails with KeyError on Dell Z9100-ON in Latest Release | OPEN | skip | - | Dell プラットフォーム固有の問題 |
| 22385 | Enhancement: Upgrade to libyang3 | OPEN | apply | `docs/management/yang-models-hld.md` | libyang3 へのアップグレードにより YANG バリデーションの互換性変更あり。libyang2 から libyang3 への移行に際して API の breaking changes が存在 |
| 22389 | Bug: missing rpki in frr | OPEN | apply | `docs/routing/bgp-hld.md` | SONiC の FRR ビルドに RPKI サポートが含まれていない既知の制限。FRR ビルド時のオプション `--enable-rpki` が未設定 |
| 22430 | Bug:[Smartswitch] Reboot cause for DPUs not updated on complete system reboot | CLOSED | apply | `docs/architecture/smartswitch-hld.md` | SmartSwitch の完全システムリブート時に DPU の reboot-cause が更新されない既知問題 |
| 22476 | Bug: show ip bgp commands assume that there's only one container that contains the name bgp | CLOSED | apply | `docs/routing/bgp-hld.md` | `show ip bgp` 系コマンドが bgp という名前を含むコンテナが一つだけと仮定するため Multi-ASIC 環境で誤動作する既知問題 |
| 22478 | [Master] Bug: [Chassis] Orchagent crashes in SUPERVISOR | CLOSED | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | シャーシスーパーバイザーで orchagent がクラッシュする既知問題 |
| 22495 | Bug: ntpd crashes with too many open files error | OPEN | apply | `docs/system/ntp-configuration.md` | ntpd が「too many open files」エラーでクラッシュする既知問題。ntpd のファイルディスクリプタ制限が低い |
| 22514 | [BRCM-DNX][SAI 12.x]: Drops seen only in single ingress in case of m2o traffic distribution | CLOSED | skip | - | Broadcom SAI 固有のトラフィック分散問題。BCM CSP 追跡中 |
| 22543 | Bug: (buildinfo_base.sh の apt sources 問題) | OPEN | apply | `docs/architecture/build-system-improvements.md` | ビルド時の apt sources.list.d 設定に不具合があり buildinfo_base.sh の修正が必要 |
| 22560 | Regression: fast/warm-reboot fails when VXLAN configuration is present | OPEN | apply | `docs/system/fast-reboot-hld.md` | VXLAN 設定が存在する環境で fast/warm-reboot が失敗する回帰バグ |
| 22586 | Bug: Router interface sometimes cannot be removed | OPEN | apply | `docs/routing/router-interface-counters-in-sonic.md` | ルーターインターフェースが削除できないことがある既知問題。依存オブジェクト（ネクストホップ等）の削除順序問題 |
| 22596 | Bug: get_transceiver_threshold_info no longer returns expected fields | CLOSED | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | `get_transceiver_threshold_info` が期待されるフィールドを返さなくなった回帰。プラットフォームテストが失敗 |
| 22682 | dash_ipv4_pa_validation used count incorrectly computed when applying dash | CLOSED | apply | `docs/network-services/dash-hld.md` | DASH 設定適用時に `dash_ipv4_pa_validation` の使用カウントが誤計算される既知バグ |
| 22690 | Bug: staticd crashes on SRv6 configuration removal | CLOSED | apply | `docs/routing/srv6-hld.md` | SRv6 設定削除時に staticd がクラッシュする既知バグ |
| 22703 | Bug: SAI nexthop_group leak | OPEN | apply | `docs/system/orchagent-hld.md` | SAI nexthop_group がリークする既知バグ。swss ログに特定のメッセージが現れた場合に発生 |
| 22834 | Bug:[Eventd] Sometimes if config reload is executed immediately after onie-install, eventd fails to start | CLOSED | apply | `docs/system/eventd-event-driven-framework-hld.md` | ONIE インストール直後の config reload で eventd が起動失敗する既知問題。初期化タイミングの競合 |
| 22855 | Bug: Chrony tries to add the same NTP source due to duplication in DHCP provided NTP sources | OPEN | apply | `docs/system/ntp-configuration.md` | DHCP 提供の NTP ソースに重複がある場合 chrony が同一ソースを二重追加しようとしてエラーになる既知問題 |
| 22856 | [Broadcom-DNX]: ECN config cannot be disabled with CLI and error logs seen while enabling/disabling | CLOSED | apply | `docs/qos/ecn-explicit-congestion-notification.md` | BRCM-DNX プラットフォームで ECN 設定を CLI で無効化できない既知問題。DNX では ECN 制御の実装が異なる |
| 22936 | Bug: config reload command is broken when combined with a file | CLOSED | apply | `docs/management/sonic-nos-configuration-methods.md` | `config reload <file>` がファイル指定時に正常動作しない回帰バグ |
| 22953 | Bug: On chassis-packet, ipv4 and ipv6 default routes are not getting programmed | CLOSED | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | シャーシパケットプロセッサーで IPv4/IPv6 デフォルトルートがプログラムされない既知問題 |
| 23012 | Bug: For QSFP28 100G transceiver module, vdm_supported key is missing from platform API | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | QSFP28 100G トランシーバーで `vdm_supported` キーがプラットフォーム API から欠落している既知問題 |
| 23019 | Bug: flask module not found, exabgp fail to start in the docker-ptf-mlnx container | CLOSED | skip | - | テスト環境固有の flask 依存問題 |
| 23052 | Bug: syncd fails to come up on Broadcom TH5 platform with master branch | CLOSED | apply | `docs/system/syncd-sai-interface.md` | Broadcom TH5 プラットフォームで master ブランチの syncd が起動失敗する既知問題 |
| 23097 | Bug: featured should skip frr_bmp, telemetry as they are used as feature flags and not containers | CLOSED | apply | `docs/system/featured-features-daemon.md` | `frr_bmp` や `telemetry` が featured によってコンテナとして管理されるが、これらは feature フラグであってコンテナではない。featured の feature 分類に不備 |
| 23110 | Bug: [Smartswitch] gnmi configuration fails for the first dash object when DPU is powered off | CLOSED | apply | `docs/architecture/smartswitch-hld.md` | SmartSwitch で DPU がオフの状態での最初の DASH オブジェクト設定が gNMI で失敗する既知問題 |
| 23121 | Bug: sonic-mgmt test_cont_link_flap.py fails after the FRR upgrade to 10.3 | OPEN | apply | `docs/routing/bgp-hld.md` | FRR 10.3 アップグレード後に連続リンクフラップテストが失敗する回帰 |
| 23130 | [SmartSwitch] systemd-networkd removes unrelated nhid on dpu reboot causing a log storm | CLOSED | apply | `docs/architecture/smartswitch-hld.md` | DPU リブート時に systemd-networkd が無関係の nhid を削除してログストームを発生させる既知問題 |
| 23147 | Bug: libyang3-py3 fails to run tests on Trixie, crashing with SIGSEGV | CLOSED | apply | `docs/management/yang-models-hld.md` | Trixie 環境で libyang3-py3 テストが SIGSEGV でクラッシュする既知問題 |
| 23168 | [Bug][SAI 12.x] Disabling FEC on the interfaces leads to failure of interface, and PFC stats | OPEN | apply | `docs/qos/pfcwd-pfc-watchdog-hld.md` | SAI 12.x で FEC を無効化するとインターフェース障害と PFC 統計取得失敗が発生する既知問題 |
| 23170 | [Bug] - show queue wredcounter requires WRED_ECN_QUEUE & WRED_ECN_PORT to the FLEX_COUNTER_TABLE | CLOSED | apply | `docs/qos/ecn-explicit-congestion-notification.md` | `show queue wredcounter` が動作するには FLEX_COUNTER_TABLE に `WRED_ECN_QUEUE` と `WRED_ECN_PORT` エントリが必要だが自動設定されない既知問題 |
| 23324 | Bug: [chassis][voq] TSC shows BGP system mode: Not consistent | CLOSED | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | シャーシ環境で TSC 後の BGP システムモードが不整合を示す既知問題。Radian 機能追加（buildimage#21732）が原因 |
| 23336 | Bug: debian-archive.trafficmanager.net/debian-security buster/updates Release does not have a Release file | OPEN | skip | - | Debian buster EOL によるビルドインフラ問題 |
| 23351 | Bug: ERROR: sonic-slave-buster image not found / inaccessible during build | CLOSED | skip | - | Debian buster EOL によるビルドインフラ問題 |
| 23386 | Bug: connection with zebra from fpsyncd drops intermittently | OPEN | apply | `docs/routing/bgp-hld.md` | fpsyncd から zebra への接続が間欠的にドロップする既知問題。FRR の接続管理の不安定さ |
| 23403 | Bug: GCU doesn't consider buffer manager logic when replacing the port admin status | CLOSED | apply | `docs/management/generic-config-updater-hld.md` | GCU がポートの admin status を変更する際にバッファマネージャーのロジックを考慮しない既知問題 |
| 23426 | Bug: [VDM] VDM freeze/unfreeze actions should be performed only if the module supports real-time val | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | VDM (Vendor Diagnostic Monitoring) のフリーズ/アンフリーズ操作がモジュールのサポート状況を確認せずに実行される既知問題 |
| 23442 | Bug: [Chassis] route_check takes more than 120secs | CLOSED | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | シャーシ環境で route_check が 120 秒を超えてタイムアウトする既知問題。スケール環境での route_check 実行時間の増大 |
| 23467 | Bug: SAI query attribute value returns error if there are custom sai headers | CLOSED | apply | `docs/system/syncd-sai-interface.md` | カスタム SAI ヘッダーが存在する場合に SAI 属性クエリがエラーを返す既知問題 |
| 23470 | Bug: dash_ipv4_pa_validation used count is not decremented on removing dash vnet mapping tables | OPEN | apply | `docs/network-services/dash-hld.md` | DASH vnet マッピングテーブル削除時に `dash_ipv4_pa_validation` 使用カウントがデクリメントされない既知バグ（#22682 の関連問題） |
| 23488 | Bug:[Smartswitch] Data applied through gnmi configuration to the DPU is inaccessible from DPU database | CLOSED | apply | `docs/architecture/smartswitch-hld.md` | gNMI 経由で DPU に適用したデータが DPU データベースからアクセスできない既知問題 |
| 23492 | Bug: ERROR: sonic-slave-buster image not found / inaccessible during build | OPEN | skip | - | Debian buster EOL によるビルドインフラ問題 |
| 23503 | Bug: Error deleting non-existing dash routes | OPEN | apply | `docs/network-services/dash-hld.md` | 存在しない DASH ルートを削除しようとするとエラーが発生する既知問題。冪等性の欠如 |
| 23590 | Bug: [DASH] Route Rule Table Del op is not supported for non-zero priority | OPEN | apply | `docs/network-services/dash-hld.md` | DASH Route Rule テーブルの削除操作が優先度 0 以外のルールに対してサポートされていない既知制限 |
| 23616 | Bug: BGP neighbors not established after idf_isolation followed by config reload | CLOSED | apply | `docs/routing/bgp-hld.md` | idf_isolation 後の config reload で BGP ネイバーが確立されない既知問題 |
| 23667 | Bug: In Packet Trimming - During init, enum capability is retrieved before the attribute capability | OPEN | apply | `docs/qos/buffer-management-hld.md` | パケットトリミング初期化時に enum capability が attribute capability より先に取得されるバグ。SAI 属性取得の順序問題 |
| 23680 | Bug: Generic Config Updater prints an error during test_vlan_interface.py | OPEN | skip | - | テスト環境の問題 |
| 23745 | [202505] Bug: [Chassis] ERR syncd0#syncd: ECMP user defined profile replace failed | CLOSED | apply | `docs/routing/ecmp-hash-fine-grained.md` | シャーシ環境で ECMP ユーザー定義プロファイルの replace 操作が SAI エラーで失敗する既知問題。Weighted ECMP が SAI 13.2.x で追加されたが互換性問題あり |
| 23777 | Regression: slow route convergence when enabling bmp feature | CLOSED | apply | `docs/routing/bgp-hld.md` | BMP 機能有効化時にルートコンバージェンスが遅くなる回帰バグ |
| 23780 | [202505] Bug: ECMP Hashing Imbalance Observed in Hash Test | CLOSED | apply | `docs/routing/ecmp-hash-fine-grained.md` | 202505 で ECMP ハッシュの不均衡が観測される既知バグ。BCM SAI コードのバグとして CSP 追跡中 |
| 23796 | [trixie] test_get_platform_info in sonic-py-common is failing on Trixie | OPEN | skip | - | Trixie 移行のテスト問題 |
| 23798 | [trixie] test_rexec_without_password_input in sonic-utilities is hanging on Trixie | CLOSED | skip | - | Trixie 移行のテスト問題 |
| 23820 | Bug: sonic-installer get-fips/set-fips not working on systems in UEFI mode | CLOSED | apply | `docs/management/sonic-nos-configuration-methods.md` | UEFI モードのシステムで `sonic-installer get-fips/set-fips` が動作しない既知問題 |
| 23824 | Bug: BGP route not re-added into ASIC_DB after VNET route is removed | CLOSED | apply | `docs/network-services/vnet-vxlan-hld.md` | VNET ルート削除後に BGP ルートが ASIC_DB に再登録されない既知バグ |
| 23875 | Enhancement: [DASH] [Floating NIC] Need ability to program multiple INBOUND direction lookup entries | OPEN | apply | `docs/network-services/dash-hld.md` | DASH Floating NIC で複数の INBOUND 方向ルックアップエントリのプログラムが必要だが未サポートな既知制限 |
| 23901 | Regression: 2025-vs-master SONIC_VERSION_CONTROL_COMPONENTS (build-cache) | OPEN | apply | `docs/architecture/build-system-improvements.md` | arm64 ビルドで `SONIC_VERSION_CONTROL_COMPONENTS` がビルドキャッシュと不整合になる回帰 |
| 23938 | Bug: FRR/mgmtd: Locking for DS 1 failed, Err: Lock already taken on DS by another session! | CLOSED | apply | `docs/routing/bgp-hld.md` | FRR mgmtd でデータストアのロック競合が発生する重要なバグ。複数セッションからの同時設定変更で発生 |
| 23945 | [202405] [chassis] Bug: GCU: config apply-patch stucks in sonic_yang loop with 12 port speed change | CLOSED | apply | `docs/management/generic-config-updater-hld.md` | GCU で 12 ポートの速度変更パッチ適用時に sonic_yang ループで処理がスタックする既知問題 |
| 23951 | [Trixie] Update platform-modules-cel for Trixie | CLOSED | skip | - | Trixie 移行のプラットフォームモジュール更新。運営系 |
| 24004 | Regression: hwsku.json subport and optional attributes incorrectly applied to all child ports instead of specific ports | CLOSED | apply | `docs/platform/platform-chassis-api-hld.md` | hwsku.json のサブポートオプション属性が特定ポートではなく全子ポートに誤って適用される回帰バグ |
| 24005 | Bug: System is in degraded state after a config reload | CLOSED | apply | `docs/system/system-ready-hld.md` | config reload 後にシステムが degraded 状態になる既知問題。dash-ha サービスファイルの依存関係設定不備 |
| 24013 | Bug: zebra crash observed in link flap testing | OPEN | apply | `docs/routing/bgp-hld.md` | リンクフラップテスト中に zebra がクラッシュする既知問題 |
| 24015 | Bug: [Smartswitch] Orchagent crashes if eth0-midplane receives IP after DPU Database service starts | CLOSED | apply | `docs/architecture/smartswitch-hld.md` | DPU Database サービス起動後に eth0-midplane が IP を受信すると orchagent がクラッシュする既知問題（202506 リリースブロッカー） |
| 24021 | [Trixie] systemd-sonic-generator incompatible with systemd 257 changes | CLOSED | apply | `docs/system/system-ready-hld.md` | Trixie の systemd 257 での変更により systemd-sonic-generator が非互換になる既知問題 |
| 24029 | Regression: docker-sonic-mgmt build fails with conflicting package version dependencies | CLOSED | skip | - | ビルド依存関係の一時的な競合問題 |
| 24031 | Bug: GCU test_monitor_config.py fails in policer change verification for specific namespace scenario | OPEN | skip | - | テスト問題 |
| 24035 | Enhancement: Make thermalctld polling intervals configurable | CLOSED | apply | `docs/system/transceiver-and-sensor-monitoring-hld.md` | thermalctld のポーリング間隔が固定値で設定変更できない既知の制限。PR#23139/635 で設定可能化 |
| 24036 | Enhancement: Show options for show ip route | OPEN | skip | - | 機能要求の詳細が不明確 |
| 24055 | Bug: bgpd memory usage increased by 37% during generic hash/techsupport tests | OPEN | apply | `docs/routing/bgp-hld.md` | techsupport/generic hash テスト中に bgpd のメモリ使用量が 37% 増加するメモリ回帰 |
| 24058 | Bug: sudo config spanning-tree enable mst is invalid | CLOSED | apply | `docs/switching/spanning-tree-hld.md` | `config spanning-tree enable mst` コマンドが無効と判定されるバグ。MST モードの設定検証に誤りあり |
| 24086 | Bug: [SmartSwitch] IP will not be assigned on midplane after DPU Image Upgrade from 202505 -> 202506 | CLOSED | apply | `docs/architecture/smartswitch-hld.md` | 202505→202506 の DPU イメージアップグレード後に midplane に IP が割り当てられない既知問題 |
| 24112 | Bug: [T2] [SingleDUT][masic] Additional packets seen on recircle port queue | OPEN | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | T2 Multi-ASIC 環境でリサーキュレーションポートのキューに余分なパケットが発生する既知問題 |
| 24114 | Bug: If dut_type is UpperSpineRouter then BGP routes are not getting programmed | OPEN | apply | `docs/routing/bgp-hld.md` | UpperSpineRouter タイプのデバイスで BGP ルートがプログラムされない既知問題 |
| 24164 | Bug: Multiple Orchagent Stuck due to SELECT timeout upon reboot from Supervisor | OPEN | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | スーパーバイザーからのリブート時に orchagent が SELECT タイムアウトでスタックする既知問題 |
| 24177 | Bug: [FRR] vty_close: ERROR: vty closed, uncommitted config will be lost | OPEN | apply | `docs/routing/bgp-hld.md` | FRR vty セッションクローズ時に未コミット設定が失われる既知問題。vtysh の設定コミット処理の不整合 |
| 24178 | Bug:[Smartswitch] reboot command clears the output of show dhcp_server ipv4 lease | OPEN | apply | `docs/architecture/smartswitch-hld.md` | SmartSwitch でリブートコマンドが `show dhcp_server ipv4 lease` 出力をクリアする既知問題 |
| 24180 | [Bug][Broadcom-DNX][Non-prod-issue] Disabling FEC on 100Gbps port causes DUT to not react to PFCs | OPEN | skip | - | BRCM-DNX 非本番バグ。FEC 設定とプラットフォーム固有問題 |
| 24193 | Bug:[smartswitch] SAI_ENI_ATTR_VM_VNI is an ENI attribute but vm_vni is a DASH_APPLIANCE_TABLE attribute | OPEN | apply | `docs/network-services/dash-hld.md` | DASH の `SAI_ENI_ATTR_VM_VNI` が ENI 属性だが `vm_vni` が DASH_APPLIANCE_TABLE 属性として定義されている設計上の不整合 |
| 24207 | Bug: [Smartswitch] [HA] hamgrd couldn't connect to swbusd instances | OPEN | apply | `docs/architecture/smartswitch-hld.md` | SmartSwitch HA 環境で hamgrd が swbusd インスタンスに接続できない既知問題 |
| 24237 | Bug: sonic-dash-ha container starts too early | OPEN | apply | `docs/architecture/smartswitch-hld.md` | sonic-dash-ha コンテナが Loopback インターフェース設定前に起動する既知問題。サービス依存関係の設定不備 |
| 24249 | Bug: [Trixie] Debian 13 with grub 2.12-9 can't chainload onie with grub 2.04 on secure boot enabled | OPEN | apply | `docs/architecture/build-system-improvements.md` | Trixie の grub 2.12-9 が ONIE の grub 2.04 を secure boot 有効環境でチェーンロードできない既知問題 |
| 24271 | Bug:[docker-pmon] xcvrd fails to come up in dell platforms | CLOSED | skip | - | Dell プラットフォーム固有の問題 |
| 24372 | Bug: After a warm-restart, orchagent process did not reconcile due to syncd crash | OPEN | apply | `docs/system/fast-reboot-hld.md` | warm-restart 後に syncd クラッシュにより orchagent の reconciliation が完了しない既知問題 |
| 24374 | Bug:[dnx-chassis] counters are broken on the latest master image | CLOSED | apply | `docs/system/queue-counter-polling.md` | DNX シャーシで最新 master イメージのカウンターが破損している既知問題 |
| 24384 | Bug: Failure pulling and making sonic-slave-bookworm and others | OPEN | skip | - | GPG キー更新によるビルドインフラ問題 |
| 24385 | [Bug][202405][GCU] - Modification of lane and speed of the port causes show queue CLIs to fail | CLOSED | apply | `docs/management/generic-config-updater-hld.md` | GCU でポートの lane/speed 変更後に `show queue` 系 CLI が失敗する既知問題。Flex Counter の OID が古いままになる |
| 24399 | Bug: start.sh in syncd startup is sometimes run twice | CLOSED | apply | `docs/system/syncd-sai-interface.md` | syncd 起動時に `start.sh` が二重実行されることがある既知問題 |
| 24402 | Bug: [dhcp_relay] dhcpmon is not accounting packets with UDP Checksum mismatch | OPEN | apply | `docs/network-services/dhcp-relay-hld.md` | dhcpmon が UDP チェックサム不一致パケットをカウントしない既知問題。一部の DHCP クライアントが不正チェックサムのパケットを送信する |
| 24412 | Bug: Random cold reboot delay due to systemd waiting for SSH shell processes | CLOSED | apply | `docs/system/fast-reboot-hld.md` | コールドリブート時に systemd が SSH シェルプロセスの終了を待機してランダムな遅延が発生する既知問題 |
| 24417 | [Bug][202405][GCU][VOQ] - Modification of speed and lane of the ports, adding IP config and sending patches | CLOSED | apply | `docs/management/generic-config-updater-hld.md` | VOQ 環境で GCU を使用してポートの速度/lane 変更後の IP 設定適用に問題がある既知バグ |
| 24443 | [VOQ] run-time speed change failed due to port ref count check | CLOSED | apply | `docs/system/orchagent-hld.md` | VOQ 環境でランタイムの速度変更が BUFFER_QUEUE テーブルの ref count チェックで失敗する既知問題 |
| 24456 | [202405][GCU] ERR log - Unsupported port speed 100000 seen during speed-lane change | OPEN | apply | `docs/management/generic-config-updater-hld.md` | GCU でポートの speed-lane 変更時に「Unsupported port speed 100000」エラーログが発生する既知問題 |
| 24464 | Bug: [202405][GCU][PORT_SPEED_CHANGE] Adding new port with non default speed in service results in issues | OPEN | apply | `docs/management/generic-config-updater-hld.md` | GCU でデフォルト以外の速度でポートを追加するとサービス実行中に問題が発生する既知バグ |
| 24465 | [202405][GCU] Patch applies BGP-IP-QoS config before port speed-lane-fec change generating SWSS warnings | CLOSED | apply | `docs/management/generic-config-updater-hld.md` | GCU がポートの speed-lane-fec 変更より前に BGP-IP-QoS 設定を適用して SWSS 警告が発生する既知問題 |
| 24483 | [Trixie] Update platform-modules-ufispace for Trixie | CLOSED | skip | - | Trixie 移行のプラットフォームモジュール更新。運営系 |
| 24523 | Bug: [Trixie] systemd-networkd.socket starts on non-smartswitch platforms | CLOSED | apply | `docs/system/system-ready-hld.md` | Trixie で systemd-networkd.socket が SmartSwitch 以外のプラットフォームでも起動する既知問題 |
| 24537 | Bug:[scale] generate_dump fails to fetch routes in scale environment | OPEN | apply | `docs/management/techsupport-collection.md` | スケール環境で `generate_dump` がルートの取得に失敗する既知問題。`show ip route` のタイムアウトが原因 |
| 24543 | Bug: [Trixie] dash-ha@dpu<n>.service is started even when the feature is not enabled | CLOSED | apply | `docs/architecture/smartswitch-hld.md` | Trixie で dash-ha サービスが機能無効時でも起動する既知問題 |
| 24562 | Bug: [Trixie] Some timezones not settable due to tzdata update | CLOSED | skip | - | Trixie の tzdata 変更によるテスト互換性問題 |
| 24576 | [Bug][202405] media_settings.json file added for signal integrity causes PFC functionality to break | CLOSED | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | SI (Signal Integrity) 用 media_settings.json 追加により PFC 機能が破損する既知問題。SAI 修正でバックポートが必要 |
| 24577 | [BUG][202405][GCU] swss ERR log Failed to start PFC Watchdog on port | CLOSED | apply | `docs/qos/pfcwd-pfc-watchdog-hld.md` | GCU 適用後に PFC Watchdog 起動失敗のエラーログが発生する既知問題 |
| 24607 | FRR config no zebra nexthop kernel enable increases system mem usage in T2 downstream LC | CLOSED | apply | `docs/routing/bgp-hld.md` | `no zebra nexthop kernel enable` 設定が T2 ダウンストリーム LC でシステムメモリ使用量を大幅増加させる既知問題 |
| 24615 | Bug: Build: mv: cannot move /etc/apt... errors are printed during a successful build | CLOSED | apply | `docs/architecture/build-system-improvements.md` | ビルド成功時でも `/etc/apt` の移動エラーが表示される既知の誤ったエラーメッセージ。buildimage#18789 で導入 |
| 24661 | Bug: swss build failure on latest sonic-swss-common | CLOSED | skip | - | サブモジュール同期問題。一時的なビルド失敗 |
| 24669 | Bug: docker restart swss cause bgp unable to be up | OPEN | apply | `docs/routing/bgp-hld.md` | `docker restart swss` 後に BGP が確立できない既知バグ。PR テストを妨げる高優先度問題 |
| 24679 | Regression: config suppress-fib-pending restarts BGP sessions | CLOSED | apply | `docs/routing/bgp-hld.md` | `config suppress-fib-pending` 実行時に BGP セッションが再起動される回帰バグ |
| 24692 | Bug: [submodules] submodule components are not updated for few weeks | CLOSED | skip | - | サブモジュール更新停滞の運営系問題 |
| 24728 | [202405][GCU][SI]: PMON ERR log - Unable to find key NPU_SI_SETTINGS_SYNC_STATUS | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | GCU/SI 設定適用後に PMON が `NPU_SI_SETTINGS_SYNC_STATUS` キーを見つけられないエラーログが発生する既知問題 |
| 24730 | Bug: dockers flapping on SONiC fan out switch due to behavior change in docker-wait-any-rs | CLOSED | apply | `docs/system/featured-features-daemon.md` | `docker-wait-any-rs` の動作変更によりファンアウトスイッチでドッカーフラッピングが発生する既知問題 |
| 24742 | Memory regression: no zebra nexthop kernel enable workaround causes massive memory increase on scale | CLOSED | apply | `docs/routing/bgp-hld.md` | `no zebra nexthop kernel enable` ワークアラウンドがスケール環境で大規模なメモリ増加を引き起こす既知問題（#24607 関連） |
| 24745 | [GCU][202405] Same rx drop counters are seen on a different port(not part of test) as the PCH-port | CLOSED | apply | `docs/management/generic-config-updater-hld.md` | GCU 適用後に異なるポートで RX ドロップカウンターが観測される BCM SAI の既知バグ |
| 24755 | Port does not come up if xcvr is inserted after speed change | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | 速度変更後にトランシーバーを挿入するとポートが UP しない既知問題。`host_tx_ready` ステータス遷移の二重変化が原因 |
| 24782 | Bug: Branch 202405, 202411 and msft-202405 fail to build | CLOSED | skip | - | 一時的なビルドインフラ問題 |
| 24800 | Bug: Orchagent continuously logs Failed to get fabric port number on Single-ASIC VOQ device | OPEN | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | Single-ASIC VOQ デバイスで orchagent が fabric ポート番号取得失敗を継続的にログ出力する既知問題 |
| 24880 | Bug: zebra is killed OOM after receiving a lot of link flapping notifications | OPEN | apply | `docs/routing/bgp-hld.md` | 大量のリンクフラッピング通知受信後に zebra が OOM で強制終了される既知問題。FRR 10.0.1 で発生 |
| 24892 | Bug: [Smartswitch]: NPU critical services crash when restarting DPU database service | CLOSED | apply | `docs/architecture/smartswitch-hld.md` | DPU データベースサービスの再起動時に NPU クリティカルサービスがクラッシュする既知問題 |
| 24895 | Bug: sai_serialize_enum: enum value 3 not found in enum sai_port_error_status_t | OPEN | apply | `docs/system/syncd-sai-interface.md` | SAI がポートエラーステータス通知で未定義の enum 値を送信するとシリアライズエラーが発生する既知問題 |
| 24985 | Bug:[Chassis][zebra] stress test reports increase memory exceed by 200 MiB | OPEN | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | シャーシ環境の zebra ストレステストで 200 MiB のメモリ増加が報告される既知問題 |
| 25055 | Bug:[Chassis] Tab key does not complete the sonic cli command | CLOSED | apply | `docs/management/sonic-nos-configuration-methods.md` | シャーシ環境で sonic-cli の Tab キー補完が動作しない既知問題。Trixie の python click モジュールバージョン変更に起因する可能性あり |
| 25090 | Bug: [202511][arm64] config reload goes with exception on db_migrator.py | CLOSED | apply | `docs/management/sonic-nos-configuration-methods.md` | arm64 202511 で config reload 時に db_migrator.py が例外で失敗する既知問題。Bookworm→Trixie 移行での Python 3.11→3.13 互換性問題 |
| 25091 | Bug: Cosmetic systemd [DEPEND] Dependency failed messages on warm-reboot | CLOSED | apply | `docs/system/fast-reboot-hld.md` | warm-reboot 時に systemd の依存関係失敗メッセージが表示される cosmetic な既知問題。Trixie 更新による変化 |
| 25142 | Bug: PMON missing access to necessary devices for platform monitoring post privilege removal | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | 権限削除後に PMON がプラットフォームモニタリングに必要なデバイスへのアクセスを失う既知問題（buildimage#23457 の副作用） |
| 25173 | Bug: Route Not Installed in FIB After Connected Route Deletion | CLOSED | apply | `docs/routing/bgp-hld.md` | 接続ルート削除後に FIB にルートが再インストールされない既知バグ |
| 25210 | Bug: Celestica E1031-T48S4 Haliburton missing interfaces | OPEN | skip | - | Celestica プラットフォーム固有の問題 |
| 25216 | Bug: show queue counters returns no output on DNX platforms | OPEN | apply | `docs/system/queue-counter-polling.md` | DNX プラットフォームで `show queue counters` が出力なしを返す既知問題 |
| 25228 | Bug: Systemd StartLimitBurst in service files restart count is not correct since systemd 254 | OPEN | apply | `docs/system/system-ready-hld.md` | systemd 254 以降で `StartLimitBurst` の動作が変更されサービスファイルの再起動カウントが正しくない既知問題 |
| 25261 | Bug: [HFT] [otel]: Enabling otel container using config feature state does not work | CLOSED | apply | `docs/system/featured-features-daemon.md` | `config feature state` で otel コンテナを有効化できない既知問題。otel インフラは存在するが featured との連携コードが欠如 |
| 25263 | Bug: [Fast-reboot] Control plane time disruption exceeds 90 seconds with Trixie | OPEN | apply | `docs/system/fast-reboot-hld.md` | Trixie で fast-reboot のコントロールプレーン中断時間が 90 秒を超える既知問題 |
| 25279 | Bug: SmartSwitch: Enabling mgmt VRF can crash orchagent/swss due to ZMQ bind address selection | OPEN | apply | `docs/architecture/smartswitch-hld.md` | SmartSwitch で管理 VRF 有効化時に ZMQ バインドアドレス選択の問題で orchagent/swss がクラッシュする既知問題 |
| 25397 | Regression: Performance degradation in routes update time in 202511 branch | CLOSED | apply | `docs/routing/bgp-hld.md` | 202511 ブランチでルート更新時間のパフォーマンスが劣化する回帰 |
| 25399 | Bug: ERSPAN mirror config CLI is failing | OPEN | apply | `docs/network-services/erspan-acl-based-mirroring-hld.md` | ERSPAN ミラー設定 CLI が失敗する既知バグ |
| 25490 | Bug: target/sonic-broadcom.bin on 202505 does not build | CLOSED | skip | - | 202505 リリースブランチの一時的なビルド問題 |
| 25519 | Bug: warm-reboot loses user-history | CLOSED | apply | `docs/system/fast-reboot-hld.md` | warm-reboot 時にユーザーのコマンド履歴が失われる既知問題。kexec によるカーネル切り替えが速すぎてバッファがフラッシュされない |
| 25618 | Bug: [xcvrd] New log errors following VDM basic and statistic observables Separation | CLOSED | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | VDM の basic と statistic オブザーバブル分離後に xcvrd に新しいエラーログが発生する既知問題 |
| 25699 | Bug: [202511][dualtor] tunnel route leftovers are seen after test_stress_arp.py | OPEN | apply | `docs/switching/dual-tor-active-active-hld.md` | Dual-ToR 202511 でストレスARP テスト後にトンネルルートの残骸が残る既知問題 |
| 25716 | Enhancement: Move pg_profile_lookup.ini to a shared place for all HWSKU on a specific platform | OPEN | apply | `docs/qos/buffer-management-hld.md` | `pg_profile_lookup.ini` が HWSKU 固有の場所に存在し複数 HWSKU 間で共有されない設計上の制限 |
| 25849 | Bug: [sonic-frr][202511] sonic-frr submodule pointing to 10.3 - should be 10.4.1 | CLOSED | apply | `docs/routing/bgp-hld.md` | 202511 ブランチの sonic-frr サブモジュールが 10.4.1 ではなく 10.3 を指している既知問題 |
| 25857 | Bug: [build][supervisor][202511] supervisor version pin (4.3.0) in versions-py3 conflicts with submodule | OPEN | apply | `docs/architecture/build-system-improvements.md` | 202511 で supervisor バージョンピン (4.3.0) がサブモジュールと競合するビルド問題 |
| 25863 | [chrony] NTP not synchronized when MGMT_INTERFACE IP is not static configured and NTP is static | OPEN | apply | `docs/system/ntp-configuration.md` | MGMT_INTERFACE が DHCP の場合に chrony が静的 NTP サーバーと同期しない既知問題 |
| 25881 | Bug: chassis: bgpcfgd netaddr.core.AddrFormatError: invalid partial IPv4 address | CLOSED | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | シャーシの bgpcfgd が IPv4 アドレス解析で `AddrFormatError` を引き起こす既知バグ。IPv6 アドレスの部分一致による |
| 25931 | Bug: systemd-sonic-generator rework causes container services to hit start-limit-hit after multiple restarts | CLOSED | apply | `docs/system/system-ready-hld.md` | systemd-sonic-generator の改修により複数回再起動後にコンテナサービスが start-limit-hit に達する既知問題 |
| 25964 | Bug: sonic-clear dhcp_relay ipv4 counters does not clear the Malformed counter in COUNTERS_DB | CLOSED | apply | `docs/network-services/dhcp-relay-hld.md` | `sonic-clear dhcp_relay ipv4 counters` が COUNTERS_DB の "Malformed" カウンターをクリアしない既知バグ。PR#25965 で修正済み |
| 26248 | [202511][regression][snappi] PFCWD basic test case fails since ingress generates PAUSE frames when stormed | OPEN | apply | `docs/qos/pfcwd-pfc-watchdog-hld.md` | 202511 で PFCWD ベーシックテストがストーム検出後にイングレスが PAUSE フレームを生成するため失敗する回帰 |
| 26300 | Bug: orchagent CrmOrch hits zmq timeout and crashes during reboots longer than 1m | OPEN | apply | `docs/system/orchagent-hld.md` | 1 分超のリブート中に orchagent CrmOrch が ZMQ タイムアウトでクラッシュする既知問題 |
| 26320 | Bug: sonic-installer install passed with errors and never full-succeeded | CLOSED | apply | `docs/system/upgrade-workflow.md` | `sonic-installer install` がエラーがあっても成功と表示する既知バグ（#26152 と同一） |
| 26345 | Bug: bgp suppress-fib-pending introduces hardcoded 1-second delay in BGP update advertisement | CLOSED | apply | `docs/routing/bgp-hld.md` | `bgp suppress-fib-pending` 機能が BGP 更新アドバタイズに 1 秒のハードコード遅延を導入する既知問題。50-100ms への縮小が提案 |
| 26355 | Bug: SFP Temperature update is delayed by > 5 mins if the Module reaches FAILED state | OPEN | apply | `docs/platform/transceiver-and-sensor-monitoring-hld.md` | モジュールが FAILED 状態になると SFP 温度更新が 5 分以上遅延する既知問題 |
| 26483 | Regression: Incremental rebuild broken for signed images | CLOSED | apply | `docs/architecture/build-system-improvements.md` | 署名付きイメージのインクリメンタルリビルドが壊れている回帰バグ |
| 26531 | [FDB] [orchagent] Stale bridge port OID after LAG member transition causes FDB state divergence | OPEN | apply | `docs/switching/fdb-hld.md` | LAG メンバー遷移後に古いブリッジポート OID が残り FDB 状態の乖離を引き起こす既知問題 |
| 26547 | Bug: [Dual-ToR A-A] [linkmgrd] Mux may not recover to active after link up with ICMP offload | OPEN | apply | `docs/switching/dual-tor-active-active-hld.md` | Dual-ToR AA で ICMP オフロード有効時にリンクアップ後に mux が active に回復しないことがある既知問題 |
| 26568 | Bug: LLDP neighbor table flaps on high-scale systems | CLOSED | apply | `docs/system/lldp-daemon-hld.md` | 高スケールシステムで LLDP ネイバーテーブルが頻繁にフラップする既知問題 |
| 26636 | How to reduce SONiC VS image size (202505 Bookworm ~6GB) for resource-constrained systems | OPEN | apply | `docs/architecture/build-system-improvements.md` | SONiC VS イメージが 202505 で ~6GB に増大しリソース制約環境で問題。`BUILD_REDUCE_IMAGE_SIZE` はビルド後クリーンアップであり Docker イメージ自体には効果なし |
| 26739 | [FRR] Bug: vtysh show ip bgp neighbor advertised-routes output all paths | CLOSED | apply | `docs/routing/bgp-hld.md` | `vtysh show ip bgp neighbor advertised-routes` が全パスを出力する FRR バグ。FRR#20617 で追跡中、202511 バックポートが必要 |
| 26757 | Breakout ports remain in oper-state down with south-bond ZMQ enabled | CLOSED | apply | `docs/system/orchagent-hld.md` | south-bond ZMQ 有効時にブレイクアウトポートの oper-state が down のままになる既知問題 |
| 26776 | docker-sonic-vs: missing /zmq_swss directory causes orchagent crash | OPEN | apply | `docs/system/orchagent-hld.md` | docker-sonic-vs で `/zmq_swss` ディレクトリが存在しないため orchagent がクラッシュする既知問題 |
| 26885 | Bug: Celestica DX010 refuse to load 202511 | OPEN | skip | - | Celestica プラットフォーム固有の問題 |
| 26904 | Bug: ICMP echo reply is sent out on invalid interface when duplicate ip address is present in mgmt vrf | OPEN | apply | `docs/management/sonic-nos-configuration-methods.md` | 管理 VRF に重複 IP アドレスが存在する場合 ICMP エコー応答が無効なインターフェースから送出される既知問題 |
| 26958 | Bug: [Dual-ToR] traffic cannot be forwarded to SoC IPv4 after failover in host-route mode | OPEN | apply | `docs/switching/dual-tor-active-active-hld.md` | Dual-ToR のホストルートモードでフェイルオーバー後に SoC IPv4 へのトラフィックが転送できない既知問題 |
| 26960 | Enhancement: bgpcfgd/CONFIG_DB lacks support for unnumbered (interface-based) BGP neighbors | OPEN | apply | `docs/routing/bgp-hld.md` | bgpcfgd/CONFIG_DB がアンナンバード BGP ネイバー（インターフェースベース）をサポートしていない既知の制限 |
| 27047 | Bug: sonic-installer install to 202511 fails with sonic-package-manager invalid option | OPEN | apply | `docs/system/upgrade-workflow.md` | 202511 への sonic-installer install が `sonic-package-manager` の無効オプションエラーで失敗する既知問題。引数の順序問題 |
| 27078 | Regression: teamsyncd crashes with SIGSEGV after running process_monitoring/test_critical_processes | CLOSED | apply | `docs/system/system-ready-hld.md` | critical process モニタリングテスト実行後に teamsyncd が SIGSEGV でクラッシュする回帰バグ |
| 27098 | Performance Regression in Orchagent due to sonic-swss pull/3910 changes | OPEN | apply | `docs/system/orchagent-hld.md` | sonic-swss PR#3910 の変更により orchagent のパフォーマンスが劣化する回帰 |
| 27159 | Bug: BGP doesn't advertise peer-learned routes after bgp container restart (suppress-fib-pending related) | OPEN | apply | `docs/routing/bgp-hld.md` | BGP コンテナ再起動後に suppress-fib-pending 関連の問題でピア学習ルートがアドバタイズされない既知バグ |
| 27236 | Bug: [Chassis] Expected Messages are missing from the syslog | OPEN | apply | `docs/architecture/chassis-supervisor-linecard-hld.md` | シャーシ環境で新規イメージインストール後の最初のリブート以降 syslog からのドッカーログが欠落する既知問題 |

---

## 集計

- **apply**: 209 件
- **skip**: 46 件
- **合計**: 255 件
