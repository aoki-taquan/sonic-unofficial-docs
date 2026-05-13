# sonic-buildimage Issues — AI 判定 (255 件全件)

生成日: 2026-05-13  
担当: chore/q59-a-buildimage-b2  
対象リポ: sonic-net/sonic-buildimage  
入力ファイル: meta/_intermediate/issues/sonic-net_sonic-buildimage_b2.json

---

## 判定サマリ

| # | issue | 状態 | 判定 | 反映先 |
|---|-------|------|------|--------|
| 1 | #13143 [Dual-ToR] Mux port stops sending ICMP heart beat packets after server was flapped | CLOSED | **skip** – Dual-ToR mux ICMP heartbeat の特定障害。プラットフォーム固有の再現待ち事象でドキュメント化困難 |
| 2 | #13252 Host Sflow version 2.41-1 Upgrade Issues | OPEN | **skip** – hsflowd バージョン更新依頼。特定バージョンのパッケージ問題でドキュメント対象外 |
| 3 | #13261 [logrotate] Logrotate sometimes is started before logrotate-config.service | CLOSED | **apply** – systemd 起動順序の競合（logrotate vs logrotate-config.service）を operations の既知問題に追記 |
| 4 | #13265 [lldpmgrd] Error in Log: unknown command from argument 1: `configure` | CLOSED | **skip** – lldpcli の旧バージョン互換問題。修正済み、一般化が難しい |
| 5 | #13293 Features were not disabled after config load_minigraph | CLOSED | **apply** – config load_minigraph 後にフィーチャが無効化されない競合（PR #13064 で修正）を operations に追記 |
| 6 | #13305 System Ready | Stopping container doesn't change System Ready status | OPEN | **apply** – systemd イベントのみで System Ready を追跡するため docker stop では状態が更新されない設計制限を concept/operations に追記 |
| 7 | #13306 System Ready | Sometimes no "System is ready" message after reboot | OPEN | **apply** – rasdaemon サービス未起動で System Ready が表示されない例を operations のトラブルシュートに追記 |
| 8 | #13308 [voq][Chassis] test_hash fails intermittently on a chassis with J2C+ linecards | CLOSED | **skip** – J2C+ ASIC のハッシュ検証 BCM CSP 追跡案件。プラットフォーム固有 |
| 9 | #13317 sonic-cli fails with user related issue | OPEN | **skip** – sonic-cli のユーザー関連 unresolved "to-do"。根本原因不明のまま |
| 10 | #13318 Need Yang for XCVRD_LOG | OPEN | **skip** – YANG 定義追加要求。範囲外（YANG 追加 PR 待ち）|
| 11 | #13407 [sflow] ERR hsflowd: device Loopback0 Get SIOCGIFFLAGS failed: No such device | CLOSED | **apply** – sflow コンテナ起動時に Loopback インタフェースが未作成で SIOCGIFFLAGS 失敗する競合を operations に追記（hsflowd v2.0.51+ で修正）|
| 12 | #13455 [yang] DHCPv6 relay yang model is not up to date | CLOSED | **skip** – YANG モデル更新 PR 完了済み。ドキュメントへの反映不要 |
| 13 | #13478 redis ballooning memory usage causing OOM & hung switch | OPEN | **apply** – Redis メモリ肥大化（フラグメント含む）で OOM になるパターンと診断方法（`redis-cli info memory`）を operations に追記 |
| 14 | #13561 saidump on T2 results lua script to take more than 5 sec | CLOSED | **apply** – T2 ルートスケール環境で saidump の Lua スクリプトが 5 秒超になる問題を operations に追記（#13561 は sairedis#918 と同類） |
| 15 | #13573 [chassis] orchagent crashes after port speed change from 400G to 100G | CLOSED | **apply** – ポートスピード変更（400G→100G）後に syncd エラー・orchagent クラッシュが発生するパターンを advanced に追記 |
| 16 | #13576 [security] syslog floods during DoS attack on REST server | OPEN | **skip** – REST サーバへの DoS 時 syslog 洪水。セキュリティ固有の設計議論でドキュメント化が難しい |
| 17 | #13581 QSFP remove/insert change events not detected for seastone | OPEN | **skip** – Celestica Seastone プラットフォーム固有の xcvrd イベント検出問題 |
| 18 | #13582 auto_techsupport.py is failing for multi-asic platform | OPEN | **skip** – multi-asic での auto_techsupport スクリプトエラー。PR待ち |
| 19 | #13591 xcvrd SfpStateUpdateTask takes long time to shutdown | CLOSED | **apply** – xcvrd の SfpStateUpdateTask シャットダウン遅延（Mellanox 固有だが共通コンポーネント）を operations に追記 |
| 20 | #13674 Rsyslogd in teamd container start failed with empty rsyslog.conf | OPEN | **apply** – sonic-cfggen が sporadic に失敗し teamd コンテナの rsyslog.conf が空になる競合を operations のトラブルシュートに追記 |
| 21 | #13719 Error (make configure PLATFORM=vs) | OPEN | **skip** – VS ビルド環境の docker 設定問題。build 手順はスコープ外 |
| 22 | #13775 [build] libsairedis takes 1.5h to build | CLOSED | **skip** – ビルド時間問題。build 手順はスコープ外 |
| 23 | #13780 test_drop_counters.py exits with error "Failed to parse output of 'portstat -j -n {}'" | CLOSED | **skip** – テスト環境の portstat CLI 変更追従。ドキュメント反映対象外 |
| 24 | #13791 sonic-cfggen isn't able to render template sporadically | OPEN | **apply** – sonic-cfggen が ONIE インストール直後に sporadic failure する問題を operations の初期化トラブルシュートに追記 |
| 25 | #13811 ISIS not working | OPEN | **apply** – Broadcom SAI が SAI_HOSTIF_TRAP_TYPE_ISIS 未サポートのため ISIS が動作しない制限を concept/known-limitations に追記 |
| 26 | #13818 Build sonic image failed in make configure | CLOSED | **skip** – ビルド環境問題（解決方法未共有のまま closed）。スコープ外 |
| 27 | #13873 Cannot build SONiC virtual switch for Linux arm64 | OPEN | **skip** – arm64 + bullseye ビルド問題。build 手順はスコープ外 |
| 28 | #13910 [dhcp_relay] [vlan] [CLI] Add/Del VLAN config should not restart dhcp_relay service | CLOSED | **apply** – VLAN 追加/削除時に dhcp_relay サービスが不必要に再起動される設計問題（DHCPv6 Relay で修正）を operations に追記 |
| 29 | #13934 [Dual-ToR] [ACL] LAG members are added to LAG later than ACL table group is bound | CLOSED | **apply** – Dual-ToR で ACL テーブルグループのバインド後に LAG メンバが追加されて ACL が効かないタイミング問題（swss PR #2754 で修正）を advanced に追記 |
| 30 | #13937 Transceiver "Not detected" but presence shown in "sudo sfputil show presence" | OPEN | **skip** – pmon ドッカー内の sonic_platform パッケージインポートエラー。プラットフォーム固有 |
| 31 | #13978 Does sonic support HPE Altoline 6960 Switch (JL279A) | OPEN | **skip** – サポートプラットフォーム質問。コミュニティ回答済みだがドキュメント対象外 |
| 32 | #14087 Portchannels are up, bgp sessions are up, but physical interfaces shown down | CLOSED | **skip** – 特定イメージバージョンの display 問題。再現確認なし |
| 33 | #14184 RADIUS with mschapv2 does not provide MPL as configured | CLOSED | **apply** – RADIUS サーバが MPL 属性を送信しない場合の動作（サーバ側設定問題）を operations のトラブルシュートに追記 |
| 34 | #14195 frrcfgd: does not push 'ip protocol bgp route-map' | OPEN | **apply** – frrcfgd が 'ip protocol bgp route-map' を CONFIG_DB から FRR に push しないデフォルト動作制限を concept/advanced に追記 |
| 35 | #14196 Problem with Interface LEDs on Dell S5248-ON | CLOSED | **skip** – Dell S5248 LED 問題。プラットフォーム固有 |
| 36 | #14316 broadcom/onie: builds fail to install due to missing mokutil bin since secureboot merge | OPEN | **skip** – ONIE インストール時の secureboot mokutil 問題。build/インストール手順はスコープ外 |
| 37 | #14416 Cannot get PSU status from commandline on a Mellanox SN2010 switch | CLOSED | **apply** – Mellanox SN2010 は固定 PSU（non-replaceable）のため show platform psu で model/serial が表示されない設計仕様を concept/reference に追記 |
| 38 | #14436 chassis-packet: pc_lag_2 test fails due to inclusion of internal portchannels | CLOSED | **apply** – `sonic_py_common/multi_asic.py` の is_port_channel_internal が PORTCHANNEL テーブルを使う際に内部 PC を正しく識別できないバグ（修正済み）を internals に追記 |
| 39 | #14467 Cannot build sonic on Ubuntu 22, permission denied errors | CLOSED | **skip** – Ubuntu 22 での docker build 権限問題。build 手順はスコープ外 |
| 40 | #14536 ACL for BGP | OPEN | **skip** – BGP 保護 ACL の新機能要求。スコープ外（実装待ち）|
| 41 | #14590 [Functional] [AAA TACACS] | Fallback to local is always enabled | OPEN | **apply** – TACACS サーバ到達不能時のローカルフォールバック動作（fallthrough が有効な場合は期待動作）を concept/operations に追記 |
| 42 | #14596 gbsyncd calling setAPILogLevel multiple times causing multiple syslog entries | OPEN | **apply** – gbsyncd インスタンスが複数起動する chassis 環境で setAPILogLevel が 1400+ 回呼ばれ syslog が埋まる問題を operations に追記 |
| 43 | #14628 [Flex Counter] observe race condition while removing a RIF object | CLOSED | **apply** – RIF オブジェクト削除時の FlexCounter 競合（sonic-swss PR #2488 で修正）を advanced に追記 |
| 44 | #14706 sailibthrift is reading data from port_map.ini instead of config_db.json | CLOSED | **apply** – sailibthrift が minigraph 使用時に config_db.json でなく port_map.ini を参照して QoS テストが失敗するバグを internals に追記 |
| 45 | #14722 [Platform] Celestica Silverstone DP | OPEN | **skip** – Celestica Silverstone DP (Jericho ベース) は SONiC 未サポート。スコープ外 |
| 46 | #14795 [SNMP] Delayed units with WantedBy & Requisite dependency on swss is causing swss restart | OPEN | **apply** – App Extension の WantedBy/Requisite が swss の再起動を誘発する依存設計問題を concept/advanced に追記 |
| 47 | #14831 show sflow interface command is not working for 2.5G speed | OPEN | **skip** – 2.5G プラットフォーム固有の sflow 表示問題。PR 待ち |
| 48 | #14832 ZTP: DHCP DISCOVER packet not sending serial number | OPEN | **apply** – ZTP の DHCP DISCOVER に serial number が含まれない問題とデバッグ方法（dhclient.conf 確認）を operations に追記 |
| 49 | #14854 sonic 202012 and 202111 stretch based builds are failing | CLOSED | **skip** – 古いブランチの build 問題。master のみ対象 |
| 50 | #14876 LAG member flapping causes sporadic SwSS crash with Broadcom SAI | OPEN | **apply** – SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE の二重 SET 時の Broadcom SAI crash パターンを advanced/known-limitations に追記 |
| 51 | #14882 [EVPN] ARP request is not generated for the unresolved local hosts | CLOSED | **apply** – EVPN L2 VNI マッピングが未設定の場合 ARP が生成されない問題のトラブルシュート手順（VLAN-VNI マッピング確認）を operations に追記 |
| 52 | #14929 kdump-tools_1.6.1-1.orig.tar.gz not present and build failing | CLOSED | **skip** – kdump ビルドキャッシュ問題。build 手順はスコープ外 |
| 53 | #14949 [EVPN] When EVPN NVO config arrives later than remote VNI entries | OPEN | **apply** – EVPN NVO 設定が remote VNI エントリより遅く到着した場合に remote エントリが追加されない設計問題を advanced に追記 |
| 54 | #14974 SONiC Broadcom build failure in 202211 with error: "TypeError: request() got an unexpected keyword argument 'chunked'" | CLOSED | **skip** – docker-py バージョン問題。古いブランチ・build 手順はスコープ外 |
| 55 | #15004 [EVPN@Scale] Poor performance and stability on EVPN L2 scale scenario | OPEN | **apply** – MAC の不規則な expiration による BGP route withdrawal がスケール環境で EVPN L2 性能と安定性を劣化させるパターンを advanced/known-limitations に追記 |
| 56 | #15047 [dhcp6_relay] [counters] Counters show statistics for deleted vlans | CLOSED | **apply** – config reload 後に削除済み VLAN の DHCPv6 リレーカウンタが残存するバグを operations に追記 |
| 57 | #15148 Support SONIC cli commands for QoS/MMU configuration/stats for multi-asic | CLOSED | **apply** – QoS/MMU CLI の multi-asic（linecard）サポートが追加されたことを reference に追記 |
| 58 | #15250 celestica get_cpld_reg_value needs to clean output | CLOSED | **skip** – Celestica プラットフォーム固有の CPLD 出力クリーン問題 |
| 59 | #15299 SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_DST_IP mandatory on create and condition | OPEN | **apply** – SAI メタデータの conditional + mandatory チェックに誤りがある場合のデバッグ方法を internals に追記（sairedis Meta.cpp の条件チェックロジック）|
| 60 | #15321 [VOQ] Fabric orchagent exit in Supervisor | CLOSED | **apply** – Supervisor でのファブリックポーリングタイムアウトによる orchagent exit パターン（chassis）を advanced に追記 |
| 61 | #15486 chassis: chassisd process on LC crashes when database-chassis restarts on Sup | OPEN | **apply** – database-chassis が停止すると LC 上の chassisd が CHASSIS_APP_DB 書き込みに失敗してクラッシュする設計上の既知動作を concept に追記 |
| 62 | #15502 [Chassis][Arista] When Chassis is down to last PSU pmon failed to update PSU data | OPEN | **skip** – Arista T2 シャーシ固有の PSU データ更新問題。再現困難 |
| 63 | #15570 [Dual-ToR] Port that was put to shutdown became active after config reload in active-active mode | CLOSED | **apply** – Active-Active Dual-ToR で config reload 後に shutdown ポートがアクティブに戻るバグ（linkmgrd cherry-pick で修正）を operations に追記 |
| 64 | #15586 getSupportedQueueCounters: FABRIC_QUEUE_STAT_COUNTER: counter error messages in IMM with J2C+ | CLOSED | **apply** – Broadcom J2C+ DNX SAI が SAI_QUEUE_STAT_CURR_OCCUPANCY_BYTES/LEVEL 未サポートで error log が出る既知制限を reference に追記 |
| 65 | #15676 chassis: graceful process restart not supported for MACSec | OPEN | **apply** – Chassis 上の MACSec は graceful process restart 未サポートで crash ハンドリングのみ対応という制限を concept/known-limitations に追記 |
| 66 | #15803 Zebra process crashes intermittently during 'config reload' on the DUT line cards | CLOSED | **apply** – config reload 中の Zebra intermittent crash（midplane port の linked interface lookup 問題）を operations/advanced に追記 |
| 67 | #15935 [System-ready] System-ready status sometimes is not reflecting the correct status | CLOSED | **apply** – System Ready ステータスが実態と合わない統計的問題（healthd の EOFError 修正）を operations のトラブルシュートに追記 |
| 68 | #15949 Unable to set custom ONIE disk partition size for OS | CLOSED | **skip** – ONIE パーティションサイズカスタマイズ。インストール手順はスコープ外 |
| 69 | #15964 [Dual-ToR] orchagent timeout responding to linkmgrd | CLOSED | **apply** – Dual-ToR で orchagent が linkmgrd に応答タイムアウトしてトラフィック断が発生するパターンを advanced に追記 |
| 70 | #16001 [snmp] Snmpd fails to start when mgmt or Loopback interface is configured with Link local IPv6 address | OPEN | **apply** – Loopback/mgmt に Link-local IPv6 アドレスが設定されていると snmpd 起動失敗するバグを operations のトラブルシュートに追記 |
| 71 | #16027 SONiC CLI cannot guarantee job order | OPEN | **apply** – SONiC CLI が job order を保証しない（RIF を持つポートを LAG に追加する際の orchagent retry loop）問題を concept/operations に追記 |
| 72 | #16085 [Dual-ToR] The tunnel route of the standby ToR cannot be restored after config reload | CLOSED | **apply** – Active-Active Dual-ToR で mux ports が admin DOWN の状態で config reload するとトンネルルートが復元されない問題（202211 ブランチで未修正）を operations に追記 |
| 73 | #16087 [202305] Build failure on latest 202305 in target sonic-p4rt_0.0.1_amd64.deb | CLOSED | **skip** – CIPD パーミッション問題による p4rt ビルドエラー。build 手順はスコープ外 |
| 74 | #16161 [Dual-ToR] Tunnel route creation/removal causes packet duplication during interfaces recovering | CLOSED | **apply** – Dual-ToR でトンネルルートの作成/削除中にインタフェース復旧タイミングでパケット重複が発生するパターンを advanced に追記 |
| 75 | #16187 Problem with snmpagentaddress and vrf | OPEN | **apply** – snmpd.conf.j2 でポート番号を含む VRF 設定時に snmpd がパースエラーを起こす問題とワークアラウンドを operations に追記 |
| 76 | #16194 test_upgrade_path fails for 202012->202305 due to orchagent crash | OPEN | **skip** – アップグレードパステストの orchagent crash。古いブランチ間問題 |
| 77 | #16202 "show queue counters" does not show stats for all queues with traffic | CLOSED | **apply** – show queue counters が全キューのカウンタを表示しないリグレッション（reverted）を operations のトラブルシュートに追記 |
| 78 | #16204 Build Error in SONiC 202211 branch - Marvell ARM64 | CLOSED | **skip** – Marvell ARM64 ローカルビルド問題。スコープ外 |
| 79 | #16245 [IPv6 DHCP_Relay] Disabling or Enabling Option 79 and Interface_id in config_db does not work | CLOSED | **apply** – DHCPv6 リレーの config_db フィールド名が YANG 定義と不一致で Option 79/Interface_id の動的変更が効かない問題（修正済み）を concept に追記 |
| 80 | #16259 Failing in building 202111 | OPEN | **skip** – 古いブランチのビルド問題。スコープ外 |
| 81 | #16301 Build Sonic image failed when make configure | CLOSED | **skip** – ビルド環境（docker pull アクセス拒否）問題。スコープ外 |
| 82 | #16362 [202205][TACACS]: connection failed: transport endpoint is not connected | OPEN | **apply** – TACACS 認証失敗（transport endpoint not connected）のトラブルシュートを operations に追記 |
| 83 | #16468 Test failed because of not able to connect to chassisDb | CLOSED | **skip** – chassis テスト環境の chassisDb 接続問題。テスト環境固有 |
| 84 | #16488 "orchagent: doTask: Failed to process invalid buffer task" Error messages with system ports | CLOSED | **apply** – VOQ chassis でのシステムポートを含む buffer task 処理エラーを advanced に追記 |
| 85 | #16489 ERR swss1#orchagent: handlePortStatusChangeNotification: Failed to get port object for port id | CLOSED | **apply** – LC 上のファブリックポートに対する port status 変更通知で orchagent がポートオブジェクトを取得できないエラーを advanced に追記（ファブリックポートは LC 上に port オブジェクトを持たない）|
| 86 | #16523 sonic-slave-buster fails to build with NO_PUBKEY | OPEN | **skip** – debian GPG key 失効によるビルド問題。スコープ外 |
| 87 | #16533 [Telemetry] After ONIE install, the telemetry process inside telemetry container exits but docker stays up | CLOSED | **apply** – 202305 以降で telemetry プロセス終了後もコンテナが生き続ける変更（202211 では critical process として終了）を concept に追記 |
| 88 | #16564 [Chassis][202205] Slow memory leak seen in syncd docker/process | CLOSED | **apply** – pfcwd 有効時に syncd プロセスでメモリリークが発生するパターン（valgrind 診断手順）を advanced/operations に追記 |
| 89 | #16596 "ERR healthd: system_service" is seen during reboot | OPEN | **apply** – reboot 中に healthd が SIGTERM を受け取らず system_service エラーを出し続ける問題を operations のトラブルシュートに追記 |
| 90 | #16666 fanshow and fan management are broken on Dell N3248TE-ON and current release | OPEN | **skip** – Dell N3248TE-ON プラットフォーム固有のファン管理問題 |
| 91 | #16725 [Build] The process is hang out for a long time when install the python-wheel on branch 202305 | CLOSED | **skip** – python-wheel インストール hang のビルド問題。スコープ外 |
| 92 | #16741 Orchagent crash observed when adding an interface to a recently created PortChannel | OPEN | **apply** – 新規作成直後の PortChannel へのインタフェース追加時に orchagent がクラッシュするパターンを advanced に追記 |
| 93 | #16787 [Chassis] Errors seen with a config reload, config load_minigraph or reboot on LC | CLOSED | **apply** – chassis LC で config reload 時に QUEUE テーブルがシステムポートに適用されて malformed key エラーが発生するバグを advanced に追記 |
| 94 | #16789 [Bookworm] Building sonic-slave-bookworm container is failing on some build servers | CLOSED | **skip** – Docker の clone3 syscall 互換問題による bookworm コンテナビルド失敗。スコープ外 |
| 95 | #16822 [Build] OpenSSH version conflict | OPEN | **skip** – OpenSSH バージョン downgrade 問題。ビルド環境はスコープ外 |
| 96 | #16939 [Voq chassis, 202205] swss/syncd dockers exit on startup | CLOSED | **apply** – VOQ chassis で起動時に swss/syncd が orchagent crash で終了するパターン（コアファイル解析方法）を advanced に追記 |
| 97 | #16944 RFS cache feature leads to /lib/modules folder to be empty | OPEN | **apply** – SPLIT_RFS+DPKG キャッシュ機能で /lib/modules が空になるビルド副作用を concept/operations に追記 |
| 98 | #16950 [Build] Errors building VS image (202211 branch) | CLOSED | **skip** – openssh バージョン競合の古いブランチビルド問題。スコープ外 |
| 99 | #16972 Failed to start Docker SONiC Virtual Switch | CLOSED | **skip** – VS イメージ取得・インポート手順の問題。スコープ外 |
| 100 | #16988 SONIC Buildimage Fails to Build (Barefoot) | OPEN | **skip** – Barefoot プラットフォームビルド問題。スコープ外 |
| 101 | #16992 [BFD] Syncd crash due to race condition in notification between session down and remove | CLOSED | **apply** – BFD セッション down と remove の通知間の競合による syncd crash を advanced に追記 |
| 102 | #16996 [Eventd] Eventd Unit test fails frequently | CLOSED | **skip** – eventd ユニットテストの intermittent 失敗。テスト環境問題 |
| 103 | #17023 Build the sonic-vs.img.gz failed based on master branch. ERROR: Cannot change symbolic links when kdump is loaded | CLOSED | **skip** – kdump ロード時の symlink 変更エラー。ビルド環境はスコープ外 |
| 104 | #17025 Memory leaks in pmon daemons related to Redis set activity | CLOSED | **apply** – psud/thermalctld の Redis SET 操作でメモリリークが発生するパターンと対処（`docker restart pmon`）を operations に追記 |
| 105 | #17074 Failed to reduce SONiC VS Build size with option BUILD_REDUCE_IMAGE_SIZE in 202305 release | OPEN | **skip** – VS ビルドサイズ削減オプション問題。スコープ外 |
| 106 | #17107 [build] failing with NO_PUBKEY docker error | OPEN | **skip** – debian mirror の GPG key 問題。スコープ外 |
| 107 | #17114 [Bookworm] DUT losing ssh connectivity and interfaces-config is stuck in activating state | OPEN | **apply** – bookworm で ntpsec の try-restart が stuck して interfaces-config がアクティブ化待ちのまま SSH 接続が失われるパターンを operations に追記 |
| 108 | #17178 zebra crash was observed in sonic-mgmt reboot tests | CLOSED | **apply** – midplane port の linked interface lookup で zebra がクラッシュする問題（reboot テスト中）を operations/advanced に追記 |
| 109 | #17180 [chassis-packet]: internal bfd sessions bringup delays during config reload/reboot | CLOSED | **apply** – config reload/reboot 時に chassis 内部 BFD セッションの起動が遅延するパターンを operations に追記 |
| 110 | #17204 Orchagent crashed when removing router intf | CLOSED | **apply** – remote linecard での config reload 時に router interface 削除で orchagent がクラッシュするパターン（再現困難だが記録あり）を advanced に追記 |
| 111 | #17306 hostcfgd race condition with config reload | OPEN | **apply** – config reload 時の hostcfgd と sonic-host-services の起動順序競合（サービス有効/無効化の設計上の問題）を concept/advanced に追記 |
| 112 | #17346 syncd crash observed during sonic-mgmt reboot tests | CLOSED | **apply** – syncd シャットダウン中の crash（MDIO 変更との関連可能性）を operations に追記 |
| 113 | #17348 [yang] Sonic yangs with nested lists deviate from Sonic yang modelling guidelines | CLOSED | **skip** – YANG ガイドライン適合性問題。YANG モデル詳細はスコープ外 |
| 114 | #17368 [Dual ToR] MUX interfaces sometimes start to glitch after topology deployment | CLOSED | **apply** – Dual-ToR MUX インタフェースがトポロジ展開後にグリッチする問題（linkmgrd 改善で対処）を operations に追記 |
| 115 | #17377 [dhcpv6_relay] [counters] counters doesn't rise on tagged Physical Interface | OPEN | **apply** – タグ付き物理インタフェースで DHCPv6 リレーカウンタが上昇しない問題を operations に追記 |
| 116 | #17379 dhcp_relay failed on current master | CLOSED | **skip** – docker-dhcp-relay ビルド問題。ビルド手順はスコープ外 |
| 117 | #17403 [202305][chassis-packet]: route_check fails on LC due to timeout on frr routes | CLOSED | **apply** – Chassis LC で `show ip/ipv6 route json` に 2 分かかって route_check がタイムアウトするパターンを operations に追記 |
| 118 | #17434 [VOQ] pfcwd show stats cmd showed wrong statistics for dropped traffic | CLOSED | **apply** – VOQ chassis で pfcwd の drop カウンタ表示が不正確な問題を reference に追記 |
| 119 | #17446 [VOQ] PFCWD didn't drop IPv6 traffic in storm condition with drop action configured | CLOSED | **apply** – VOQ chassis で PFC storm 中に IPv6 トラフィックが PFCWD の drop action で落とされない問題（BRCM SAI 修正待ち）を known-limitations に追記 |
| 120 | #17472 [loganalyzer] ERR sonic-db-cli: guard: RedisReply catches system_error: command: PING | CLOSED | **apply** – Redis が起動中（loading dataset）の時に sonic-db-cli が PING で system_error をキャッチするエラーを operations のトラブルシュートに追記 |
| 121 | #17485 Not able to build VM image on Ubuntu 20.04 from master branch | OPEN | **skip** – VM イメージビルド環境問題。スコープ外 |
| 122 | #17530 swss#supervisor-proc-exit-listener: Process 'orchagent' is stuck in namespace 'host' | CLOSED | **apply** – orchagent 初期化中に heartbeat が 1 分間送信されず stuck と誤判断される問題を operations/advanced に追記 |
| 123 | #17547 New feature: Support SONiC VOQ in a disaggregated networks | OPEN | **skip** – 新機能提案（VOQ in disaggregated networks）。実装前の提案はスコープ外 |
| 124 | #17548 Issue in SONiC Custom Build on 202305 | OPEN | **skip** – カスタムビルド問題。スコープ外 |
| 125 | #17550 On Arista DCS-7060DX5-32, Admin status of the interface is not going down in-spite of shutting down | OPEN | **apply** – Arista DCS-7060DX5-32 でインタフェースをシャットダウンしても admin status が down にならない問題を operations のトラブルシュートに追記 |
| 126 | #17566 Failed to load ipd.ko on 202012-innovium | OPEN | **skip** – 古いブランチ + Innovium カーネルモジュール問題。スコープ外 |
| 127 | #17604 FRR may advertise BGP routes before they are programmed in hardware ASIC | CLOSED | **apply** – FRR が ASIC プログラミング前に BGP ルートをアドバタイズする可能性と BGP FIB suppression 機能（`BGP-suppress-fib-pending.md`）を concept/advanced に追記 |
| 128 | #17615 'sfputil firmware run' cmd needs better resilience and synchronization with PMON Xcvrd | CLOSED | **apply** – sfputil firmware run コマンドが Xcvrd との同期なしに動作するため問題が起きるパターンを operations に追記 |
| 129 | #17617 sonic-db-cli socket option not working when using PING | CLOSED | **apply** – sonic-db-cli が hostname として 'redis_chassis.server' を使う場合に unix socket が使われない実装詳細を internals に追記 |
| 130 | #17624 Can not delete the table with config load command | OPEN | **apply** – config load コマンドではテーブルを削除できない（個別の削除コマンドが必要）という仕様上の制限を operations に追記 |
| 131 | #17657 [BookWorm Image] NTP Not working | CLOSED | **apply** – bookworm で NTP パッケージが更新されてファイルパスが変わったため sonic-mgmt テストケースとの不整合が発生した問題を operations に追記 |
| 132 | #17665 orchagent crashed when adding the members, addresses from an existing portchannel to a newly created portchannel | OPEN | **apply** – 既存 PortChannel のメンバ/アドレスを新規 PortChannel に移動する際に orchagent がクラッシュするタイミング問題（step 間に数秒の sleep が必要）を operations に追記 |
| 133 | #17839 [VOQ][PFC] Orchagent crashed because of SAI_STATUS_INSUFFICIENT_RESOURCES | CLOSED | **apply** – VOQ chassis での PFC storm 複数優先度/ポート同時発生時に SAI_STATUS_INSUFFICIENT_RESOURCES で orchagent がクラッシュするパターンを advanced に追記 |
| 134 | #17906 The NTP_SERVER configuration generated from the minigraph doesn't meet the new schema requirements | CLOSED | **apply** – minigraph 生成の NTP_SERVER 設定が新 schema に不適合でエラーになるバグ（PR で修正）を operations に追記 |
| 135 | #17945 sonic-db-cli -n <asic-ns> CHASSIS_APP_DB EVAL fails intermittently after config reload | CLOSED | **apply** – config reload/load-minigraph 後に sonic-db-cli の CHASSIS_APP_DB EVAL が intermittent に失敗する問題（redis-cli で代替可能）を operations に追記 |
| 136 | #18061 Unable to remove "public" snmp community | OPEN | **apply** – SNMP の "public" コミュニティを削除できない問題を operations に追記 |
| 137 | #18137 [Yang] Incorrect restriction for ICMP/ICMPv6 type and code | CLOSED | **apply** – YANG モデルで ICMP/ICMPv6 type と code の restriction が不正確な問題を reference に追記（openconfig 定義との差分）|
| 138 | #18180 Building for VS fails: OSError: Failed to locate platform directory | CLOSED | **skip** – VS ビルド環境の platform directory 検索エラー。スコープ外 |
| 139 | #18183 Unexpected error syslog due to negative refcnt of nexthop | CLOSED | **apply** – nexthop の refcnt が負になった際の unexpected error syslog と orchagent crash パターンを advanced に追記 |
| 140 | #18184 Syslog rate limiting feature doesn't work on multi-ASIC images | CLOSED | **apply** – multi-ASIC 環境で syslog rate limiting が機能しない問題を operations に追記 |
| 141 | #18226 EAPOL COPP rules are not getting installed when other features also try to use same trap group | CLOSED | **apply** – EAPOL と MACSec が同一 trap group を使う際に COPP ルールが競合して正しくインストールされない問題とワークアラウンドを advanced に追記 |
| 142 | #18237 Subinterface creation on Broadcom switches cause multiple container shutdown | CLOSED | **apply** – Dell EMC S524 で subinterface 作成時に複数コンテナが shutdown するプラットフォーム固有問題を advanced に追記 |
| 143 | #18248 [Sflow] Orchagent docker crashes due to SAI failure on enabling Sflow feature | OPEN | **apply** – Sflow 有効化時に SAI 失敗で orchagent がクラッシュする問題（Maverick 2 / Trident 3.X5）を advanced/known-limitations に追記 |
| 144 | #18297 BCM J2C+ ASIC internal thermal sensor phantom temperature spike | CLOSED | **skip** – J2C+ ASIC の phantom 温度スパイク BCM CSP 案件。プラットフォーム固有 |
| 145 | #18335 [chassis][202305] high cpu usage due to rsyslog_plugin process in swss/bgp dockers | CLOSED | **apply** – chassis での rsyslog_plugin プロセスの高 CPU 使用率（eventd 構造化 syslog 関連）を operations に追記 |
| 146 | #18358 Building sonic VS image: FAIL: test_buffers_dell6100_render_template | CLOSED | **skip** – j2 テンプレートレンダリングのビルドテスト失敗。スコープ外 |
| 147 | #18389 [master][chassis][multi-asic] db_migrate.py show error and back trace while loading configuration on Linecard | CLOSED | **apply** – chassis Linecard で db_migrate.py が SonicDBConfig 初期化エラーを出す問題（namespace パラメータ処理の修正）を operations に追記 |
| 148 | #18401 [master] SyntaxWarning messages show up on console with config/plugins/mlnx.py | CLOSED | **apply** – Python 3.11 で config/aaa.py 等が "is" with literal の SyntaxWarning を出す問題を operations に追記 |
| 149 | #18417 [Yang] Port table for multi-asic device does not match yang definition | CLOSED | **apply** – multi-asic デバイスの PORT テーブルが YANG 定義と一致しない問題（conditional mandatory の処理）を reference に追記 |
| 150 | #18421 Mid-December changes to SWSS made SONiC on Dell N3248TE-ON unusable | OPEN | **skip** – Dell N3248TE-ON（Trident）プラットフォーム固有問題。再現未確定 |
| 151 | #18431 [multi-asic][202305]: 'config reload -l <>' option loads incorrect config | CLOSED | **apply** – multi-asic 環境で config reload -l が他の namespace のポートデータをホストに誤ってロードする問題を operations に追記 |
| 152 | #18472 [dhcp_server] [rsyslog] Logs are not written to host | CLOSED | **apply** – dhcp_server コンテナが bridge network mode で動作するため host の syslog に書き込まれない設計制限を concept に追記 |
| 153 | #18489 QoS buffer information missing on Celestica DX010 | OPEN | **skip** – Celestica DX010 の QoS buffer プロファイル設定問題。プラットフォーム固有 |
| 154 | #18490 swss and other dockers services breaks if all ports mtu is set to 9216 | CLOSED | **apply** – 全ポートの MTU を 9216 に設定すると swss 等のコンテナが終了するプラットフォーム問題とバリデーション推奨を operations に追記 |
| 155 | #18607 How to access LUA CLI or hardware prompt from SONiC | OPEN | **skip** – Marvell LUA CLI アクセス方法。プラットフォーム固有・スコープ外 |
| 156 | #18679 [master] debian buster-backports does not have a Release file | CLOSED | **skip** – debian buster-backports 廃止によるビルドミラー問題。スコープ外 |
| 157 | #18733 [master] sonic-db-cli was not able to connect to CHASSIS DB when namespace is provided | CLOSED | **apply** – sonic-swss-common PR #797 以降 sonic-db-cli の CHASSIS DB 接続に unix socket が使われなくなった実装変更を internals に追記 |
| 158 | #18766 [202311][interface]: Failed to remove router port when IP mask is provided in a full notation | OPEN | **apply** – フル表記の netmask でルータポート削除が失敗する問題（sonic-utilities PR #3281 で修正）を operations に追記 |
| 159 | #18767 [202311] Celestica DX010 'show platform fan' fails | CLOSED | **skip** – Celestica DX010 固有のファン表示問題 |
| 160 | #18771 rsyslog_plugin is hogging the CPU when high load is seen on rsyslog | CLOSED | **apply** – rsyslog 高負荷時に rsyslog_plugin が CPU を占有するバグ（PR #11848 修正）と rate limiting ワークアラウンドを operations に追記 |
| 161 | #18773 [chassis] route_check fails on LC due to timeout on frr routes | CLOSED | **apply** – chassis LC で route_check が FRR ルート取得タイムアウトで失敗するパターン（#17403 の続き）を operations に追記 |
| 162 | #18818 [system monitor] ERR healthd: system_service join() argument must be str | CLOSED | **apply** – healthd のキュー shutdown 中の EOFError による system_service エラーを operations に追記（master で修正済み）|
| 163 | #18822 [master][voq][chassis] swss.sh "systemctl start" dhcp_relay failed | CLOSED | **apply** – chassis 環境で swss.sh の dhcp_relay 起動で INFO が ERR に格上げされて logAnalyze が失敗するパターンを operations に追記 |
| 164 | #18832 [master][build] problem with docker-gbsyncd-broncos | OPEN | **skip** – gbsyncd broncos ビルド問題（dsserve ファイル取得）。ビルド手順はスコープ外 |
| 165 | #18865 Bug in frrcfgd in bgp-peer-group-af where command accepts "admin-status" "up" but frrcfgd accepts "true" | CLOSED | **apply** – bgp-peer-group-af の admin-status が CLI では "up"/"down" だが frrcfgd は "true"/"false" を期待するという不整合を operations に追記 |
| 166 | #18871 [DX010] Console/SSH super slow then after a few hours normal | CLOSED | **apply** – DX010 で CPU スパイクにより Console/SSH が数時間 slow になる問題とコアダンプ診断方法を operations に追記 |
| 167 | #18883 Inter-VLAN working EXCEPT for one that will not route to Ethernet0 | OPEN | **skip** – inter-VLAN ルーティング特定問題。#18871 の可能性もあり個別調査必要 |
| 168 | #18893 [xcvrd] xcvrd crashes during breakout port | CLOSED | **apply** – Dynamic Port Breakout (DPB) 設定変更時に xcvrd の CmitManagerTask がポート追加/削除イベントを処理できず crash するバグ（修正済み）を advanced に追記 |
| 169 | #18913 Breakout error on SN2700 | CLOSED | **apply** – Mellanox SN2700 で breakout 利用には platform.json と hwsku.json にモード定義が必要という設定要件を operations に追記 |
| 170 | #19022 On a Multi-Asic Environment BGP Suppress FIB Pending CLI Command is not working | OPEN | **apply** – multi-asic 環境での BGP FIB suppression CLI が期待通り動作せず namespace 個別コマンドが必要なバグを operations に追記 |
| 171 | #19028 Docker client failing to connect: requests.exceptions.InvalidURL: Not supported URL scheme http+docker | OPEN | **skip** – docker-py の一時的 URL スキーム問題。ビルド環境はスコープ外 |
| 172 | #19032 [SfpUtil] sfp eeprom with option dom is not working on Xcvrs with flat memory | CLOSED | **apply** – flat memory のトランシーバで sfputil の DOM 取得が動作しない問題（sfputil 変更が必要）を operations に追記 |
| 173 | #19044 [SmartSwitch] Orchagent might crash during boot because of invalid zmq address | CLOSED | **apply** – SmartSwitch boot 時に eth0 の IP がなく orchagent が invalid zmq address で crash する可能性を advanced に追記 |
| 174 | #19059 [DNX] Orchagent/Syncd crash due to `ECMP hash offset set failed with error -2` | CLOSED | **apply** – Broadcom DNX の ECMP hash offset SAI 属性チェックの変更でシステム起動時に orchagent/syncd がクラッシュするパターンを advanced に追記 |
| 175 | #19067 PFCWD drop+ok counters are not counted correctly | CLOSED | **apply** – Nokia VOQ chassis での PFC ウォッチドッグカウンタが正確に計数されない問題を reference に追記 |
| 176 | #19091 The CLI generated by yang model has performance problems with huge cfgdb tables | OPEN | **apply** – YANG ベース CLI がコマンド実行のたびに全 CONFIG_DB エントリを検証するためテーブルが大きいと性能問題が発生する設計上の限界を concept に追記 |
| 177 | #19105 [DPB][FLEX Counters] Error seen in SDK reading counters for removed ports | OPEN | **apply** – Dynamic Port Breakout でポートが削除された後も FlexCounter が counter を読もうとして SDK エラーが出るタイミング問題（sonic-swss PR #3076 で修正）を advanced に追記 |
| 178 | #19145 ERR swss#orchagent: doDecapTunnelTask: unknown decap tunnel table attribute 'dst_ip' | CLOSED | **apply** – decap tunnel タスク処理で 'dst_ip' 属性が unknown として扱われるバグ（PR #18752 で修正）を operations に追記 |
| 179 | #19146 Build Error in SONiC 202305 branch - Marvell ARM64 on amd64 build server | CLOSED | **skip** – debian スナップショット GPG key 問題。ビルド環境はスコープ外 |
| 180 | #19204 test_dcap fails on master branch: doDecapTunnelTask: unknown decap tunnel table attribute 'dst_ip' | CLOSED | **skip** – #19145 と同じ問題。重複 |
| 181 | #19218 Missing HASH information for LAG and ECMP | OPEN | **apply** – ECMP/LAG ハッシュ設定が明示的に指定されていない場合 show hash が何も表示しない仕様と CONFIG_DB / APP_DB の確認方法を reference に追記 |
| 182 | #19235 Latest Master Build Not Successful | OPEN | **skip** – master ビルド失敗（PR #18762 の revert で解決）。一時的な問題でスコープ外 |
| 183 | #19288 [Chassis] Master: Fabric monitor feature isolates the fabric ports in SUP when the config reload is done in LC | CLOSED | **apply** – LC config reload 後に SUP のファブリック監視機能がファブリックポートを隔離してしまう問題を advanced に追記 |
| 184 | #19295 [SmartSwitch] monit container_checker is failing when there are dedicated DPU databases | CLOSED | **apply** – DPU 専用データベースが存在する SmartSwitch で monit container_checker が失敗するバグを advanced に追記 |
| 185 | #19310 config reload doesn't remove all the lags in a scaled configuration | OPEN | **apply** – スケールド設定での config reload 時に LAG が完全に削除されない問題を operations のトラブルシュートに追記 |
| 186 | #19311 [DNX] sonic-clear macsec does not clear the macsec counters since rekey causes anomaly | CLOSED | **apply** – MACsec の rekey 後に sonic-clear macsec でカウンタが正しくリセットされない問題を operations に追記 |
| 187 | #19328 [PINS] Device ID for SONiC Virtual Switch with P4RT | OPEN | **skip** – PINS/P4RT の VS 環境固有問題。VS は範囲外 |
| 188 | #19336 [xcvrd] [cmis manager] CMIS manager cannot automatically select correct host lane count | OPEN | **apply** – CMIS マネージャがポートの速度とレーン数から適切なアプリケーションを自動選択できないケースの設計議論（lane 数 8->4->2->1 で試行）を concept に追記 |
| 189 | #19352 [202405] container_checker: Failed to get image 'docker-sonic-telemetry' | CLOSED | **apply** – gnmi/telemetry コンテナ名変更後に monit の container_checker が旧名を参照してエラーになる問題を operations に追記 |
| 190 | #19357 [Chassis] sonic-mgmt PC suite tests are failing | CLOSED | **apply** – chassis で LAG 削除後に local asic が backend PortChannel の operstatus を適切に更新しない問題を advanced に追記 |
| 191 | #19405 [202205] 'show techsupport' not working properly from SUP | CLOSED | **apply** – Supervisor から show techsupport が正常に動作しない chassis 固有の問題を operations に追記 |
| 192 | #19406 [202205] core dump file size configured on sonic chassis is zero | CLOSED | **apply** – chassis で ulimit 設定が正しくないためコアダンプが生成されない問題を operations に追記 |
| 193 | #19455 [202405] ORDERED_ECMP_CAPABLE is missing in SWITCH_CAPABILITY in Config_DB | CLOSED | **apply** – ORDERED_ECMP_CAPABLE が SWITCH_CAPABILITY に存在しない場合の影響とデバッグ方法を reference に追記 |
| 194 | #19507 [Dhcprelay] dhcprelayd crashes with a traceback | CLOSED | **apply** – dhcprelayd がトレースバック付きでクラッシュするバグと診断方法を operations に追記 |
| 195 | #19566 Chassis: Need support for voq for "show queue watermark unicast" command | OPEN | **apply** – VOQ chassis での `show queue watermark unicast` コマンドに --voq オプションが必要という機能制限を reference に追記 |
| 196 | #19569 [202405] [Chassis]: Ports take too long to come up due to delayed port up notification processing by orchagent | CLOSED | **apply** – chassis で orchagent のポート up 通知処理遅延によってポート起動が遅くなるパターン（sonic-host-services PR #135 と buildimage PR で対処）を operations に追記 |
| 197 | #19581 GNMI Client Auth Failed with Server Certificate Authentication Error | CLOSED | **apply** – TELEMETRY の gnmi client_auth がデフォルト true の状態でサーバ証明書認証エラーになる設定問題を operations に追記 |
| 198 | #19591 BGP State Change Does not Trigger BGP State Event | CLOSED | **apply** – BGP 状態変化が EVENTS DB に届かない問題のデバッグ方法（heartbeat 確認、xpub 確認）を operations に追記 |
| 199 | #19592 [202405][DNX] orchagent exited because of failing to set SAI_NEIGHBOR_ENTRY_ATTR_IS_LOCAL | CLOSED | **apply** – Broadcom SAI DNX が SAI_NEIGHBOR_ENTRY_ATTR_IS_LOCAL 設定未サポートで orchagent が終了するバグ（CSP 追跡）を advanced/known-limitations に追記 |
| 200 | #19603 Telemetry Swss Events are not Triggered | CLOSED | **apply** – multi-asic 環境で telemetry の swss イベントが発生しない問題（namespace 対応）を operations に追記 |
| 201 | #19620 /lib/systemd/systemd-networkd-wait-online command fails on host | CLOSED | **apply** – systemd-networkd-wait-online コマンドが失敗する問題（PR #19107 で修正）を operations に追記 |
| 202 | #19624 Buffer Queue Not Changed to Use Queue Data from Config | OPEN | **apply** – GNMI db_client が multi-asic namespace を指定しないため CONFIG_DB のバッファキュー設定が反映されない問題を operations に追記 |
| 203 | #19638 [Smartswitch] Orchagent is crashing when the MGMT_VRF is enabled | CLOSED | **apply** – SmartSwitch で MGMT_VRF 有効時に orchagent がクラッシュする問題を advanced に追記 |
| 204 | #19648 [Broadcom-DNX] Intermittent lossless packet drop with Pause storm on egress port | CLOSED | **apply** – Broadcom DNX で PFC pause storm 時の MMU バッファ設定により intermittent なロスレスパケットドロップが発生するパターンを advanced に追記 |
| 205 | #19661 [202405] delayed ssh service start due to dependency caused by banner-config service | CLOSED | **apply** – banner-config サービスの systemd 依存関係によって SSH サービス起動が遅延するパターンを operations に追記 |
| 206 | #19730 Interfaces in portchannel show duplicate drops in case of congestion | CLOSED | **apply** – PortChannel メンバが混雑時に重複ドロップカウンタを表示する問題（Broadcom CRPS カウンタの pp_port 共有）を reference に追記 |
| 207 | #19735 Subinterface doesn't inherit the speed of ancestors on kvm testbed | OPEN | **skip** – KVM/VS 環境固有の subinterface speed 継承問題 |
| 208 | #19760 [chassis][202405]: orchagent crash in NotificationSwitchAsicSdkHealthEvent::executeCallback | CLOSED | **apply** – sairedis の NotificationSwitchAsicSdkHealthEvent コールバック実行中の orchagent crash を advanced に追記 |
| 209 | #19763 [bgp] Slow increase in memory usage seen in BGP | OPEN | **apply** – rsyslogd の rate limit 関連メモリ問題による BGP コンテナのメモリ増加パターンと対処を operations に追記 |
| 210 | #19779 sonic-CLI 'show priority-group drop counters' crashes with key-error | OPEN | **apply** – multi-asic 環境で sonic-clear 後に show priority-group drop counters が key-error でクラッシュする問題（asic 順序の問題）を operations に追記 |
| 211 | #19828 python daemons in bookworm are consuming more memory than in bullseye | CLOSED | **apply** – bookworm では python デーモンのメモリ使用量が bullseye より多い問題とメモリしきい値調整を operations に追記 |
| 212 | #19846 [sonic-package-manager] Packages are migrated default when install image via sonic-installer | OPEN | **apply** – sonic-installer でイメージインストール時にパッケージが自動マイグレートされる動作の設計上の制限を concept に追記 |
| 213 | #19861 [Nokia-BRCM-DNX]: CLI show dropcounter counts retains the stats after clearing | CLOSED | **apply** – #19779 と同じ根本原因（multi-asic での sonic-clear 後の show dropcounter カウンタ残存）を operations に追記 |
| 214 | #19878 [featured] after changing feature state, featured adds attributes to FEATURE table without checking if the feature is still installed | OPEN | **apply** – featured が feature の install 状態を確認せずに属性を追加する問題（sonic-host-services PR #120 で導入）を concept に追記 |
| 215 | #19946 [frr-mgmt-framework] "auth_password" in the BGP_NEIGHBOR table cannot be restored correctly | OPEN | **apply** – BGP_NEIGHBOR テーブルの auth_password が config reload 後に正しく復元されない問題を operations に追記 |
| 216 | #19995 Breakout not working on Dell S5248F | OPEN | **skip** – Dell S5248F での breakout 未サポート問題。platform.json 整備待ち |
| 217 | #20019 Two issues when using config node as "unified" | CLOSED | **apply** – config node を "unified" にした場合の route-map list 処理の問題（YANG では list 定義）を concept に追記 |
| 218 | #20055 [202205] [T2] Removing and adding neighbors back on asic creates 'Malformed communities attribute' error | CLOSED | **apply** – T2 chassis で neighbors を再追加した際に 'Malformed communities attribute' エラーが発生するパターンを advanced に追記 |
| 219 | #20059 [chassis][202405]: Sup: some backend PortChannel configuration fails intermittently | CLOSED | **apply** – teamd プロセスが swss の redis db 初期化前に PortChannel 作成を開始して失敗する起動順序問題を operations に追記 |
| 220 | #20070 [chassis]: LC reboot causing buffer_profile related errors | CLOSED | **apply** – chassis LC reboot 時に ASIC 名の大文字小文字不一致で buffer_profile エラーが発生するバグを advanced に追記 |
| 221 | #20212 [FDB] SONiC sairedis FDB callback handling is not efficient to handle bulk notifications | CLOSED | **apply** – sairedis の FDB コールバックが bulk 通知を効率的に処理できず SAI ライブラリを圧迫するパターンを advanced に追記 |
| 222 | #20214 [T2] Continuous neighorch INFO logs emitted in orchagent | CLOSED | **apply** – T2 chassis での neighorch からの連続 INFO ログ（benign だが過剰）を operations に追記 |
| 223 | #20246 ERR eventd#eventd: deserialize Failed: input stream error | CLOSED | **apply** – reboot 中の eventd がデシリアライズエラーを出すパターン（PR #20024 の case 4）を operations に追記 |
| 224 | #20261 [202405][VOQ] SAI error in speed change | CLOSED | **apply** – VOQ chassis でのポートスピード変更時 SAI エラーを advanced に追記（BCM CSP 追跡）|
| 225 | #20279 Slow and steady increase in memory usage for eventd | OPEN | **apply** – xpub ソケットにコレクターが接続していない場合に eventd がイベントをキャッシュし最大 100MB 使用する設計制限を concept に追記 |
| 226 | #20284 Checking for DPUs in platform.json is adding delay to WR/FR reconciliation | CLOSED | **apply** – platform.json の DPU 存在チェックが warm reboot/fast reboot の reconcile に遅延をもたらす問題と sonic-bootchart による診断方法を operations に追記 |
| 227 | #20302 Remove runtime config update for FLEX_COUNTER_TABLE | CLOSED | **apply** – enable_counters.py が CONFIG_DB の counter 設定を runtime に上書きする設計問題と議論を concept/advanced に追記 |
| 228 | #20322 [Master/202411] RPC builds are broken | CLOSED | **skip** – RPC イメージビルド問題（SAI PR 起因）。ビルド手順はスコープ外 |
| 229 | #20331 Inserting SFP module causes a crash | OPEN | **apply** – SFP/DAC ケーブル挿入で syncd がクラッシュするパターン（time span エラー）を advanced に追記 |
| 230 | #20337 [T2][202405] Zebra process consuming a large amount of memory resulting in OOM kernel panics | CLOSED | **apply** – T2 chassis の Zebra プロセスが大量メモリを消費して OOM kernel panic が発生するパターンと Nexthop メモリ分析方法を advanced に追記 |
| 231 | #20361 [mlnx][spc1] MP2MP IPinIP decap term creation failed with SAI src ip attribute not support | CLOSED | **apply** – Mellanox SPC1 で MP2MP IPinIP decap term 作成が SAI src ip 属性未サポートで失敗するパターンを known-limitations に追記 |
| 232 | #20376 sensors command hang due to receive SIGSTOP during show techsupport | OPEN | **apply** – show techsupport 実行中に sensord が SIGSTOP を受け取って sensors コマンドが hang するパターンを operations に追記 |
| 233 | #20377 [GCU] [MA] Apply-patch fails if 'path' value includes '/' which is encoded as '~1' | CLOSED | **skip** – json-patch 仕様の問題（~1 エンコーディング）。既知仕様でドキュメント対象外 |
| 234 | #20378 [GCU] [MA] ACL_RULE modifications are not applied | OPEN | **apply** – GCU/MA での ACL_RULE 変更が適用されない問題を operations に追記 |
| 235 | #20414 [Dual-ToR] mux container can't restart due to high CPU usage after 'config reload -y -f' when feature autorestart is disabled | OPEN | **apply** – feature autorestart 無効時に config reload 後に mux コンテナが高 CPU で再起動できない問題を operations に追記 |
| 236 | #20430 [xcvrd] CMIS manager cannot activate 4 x 100G datapath for Intel DR4 transceiver | CLOSED | **apply** – Intel DR4 トランシーバで CMIS マネージャが 4x100G データパスを有効化できない問題を operations/advanced に追記 |
| 237 | #20466 [202405] sai.profile format issue | CLOSED | **apply** – sai.profile の余分な改行による format 問題と sonic-sairedis PR #1412 での修正を operations に追記 |
| 238 | #20475 Boot issues on Debian 12 based SONiC images on a Wedge100-32X | OPEN | **skip** – Wedge100 プラットフォームのファームウェア問題。プラットフォーム固有 |
| 239 | #20507 Chassis: Orchagent crashes are seen in Voq chassis while running sonic-mgmt PC and voq suites | CLOSED | **apply** – VOQ chassis での sonic-mgmt PC/VOQ テスト実行中 orchagent crash パターンを advanced に追記 |
| 240 | #20547 https://packages.trafficmanager.net/snapshot/debian/latest/timestamp not accessible | CLOSED | **skip** – microsoft の debian パッケージミラー障害。ビルド環境はスコープ外 |
| 241 | #20576 Saiplayer fails to replay recording | CLOSED | **apply** – saiplayer が PORT_STAT_COUNTER を含む recording の replay に失敗する問題（FC 設定を含む recording の非互換）を internals に追記 |
| 242 | #20587 Neighbor operation timeouts cause crashes on Dell S5248F-P-25G | OPEN | **apply** – Dell S5248F で neighbor 操作タイムアウトが原因でクラッシュするパターンを advanced に追記 |
| 243 | #20589 [202405][Nokia-Broadcom-DNX] PFCWD is disabled by default in config_db JSON file | CLOSED | **apply** – PFCWD のデフォルト状態が config_db JSON で無効になっている場合に 'pfcwd start_default' CLI が動作しない問題とビルドオプション（enable_pfcwd_on_start）の確認方法を operations に追記 |
| 244 | #20590 [202405][BRCM-DNX] Pause Frames sent by DUT for Priority Group0 on congestion | CLOSED | **apply** – Broadcom DNX で Priority Group0 の輻輳時に DUT が Pause フレームを送信する問題（PR #20651 で修正）を advanced に追記 |
| 245 | #20605 [T2][202405] Orchagent crashes when running acl/test_acl.py | CLOSED | **apply** – T2 chassis での sonic-mgmt ACL テスト実行中 orchagent がクラッシュするパターンを advanced に追記 |
| 246 | #20614 make target/python-wheels/bookworm/sonic_config_engine-1.0-py3-none-any.whl fails on master for marvell amd64 | CLOSED | **skip** – Marvell amd64 bookworm ビルドレース問題。スコープ外 |
| 247 | #20636 ERR database#supervisor-proc-exit-listener: Syntax of the line program:redisprogram:redis_bmp#012 in processes file is incorrect | CLOSED | **apply** – docker-database の critical_processes ファイルに誤った形式（`program:redisprogram:redis_bmp`）が入り supervisor が終了するバグを operations に追記 |
| 248 | #20652 [VOQ Chassis] Everflow packets are sent to wrong queue on the destination front panel port | OPEN | **apply** – VOQ chassis で Everflow パケットが宛先フロントパネルポートの誤ったキューに送られる問題を advanced に追記 |
| 249 | #20680 redis omem leaking issue on T2 supervisor | CLOSED | **apply** – T2 Supervisor の global database docker で redis クライアントが buffer を読めず omem が増加するメモリリークパターンを advanced に追記 |
| 250 | #20685 The Debian package repository at https://sonicstorage.blob.core.windows.net/ cannot be accessed | CLOSED | **skip** – azure ストレージのパッケージリポジトリ障害。ビルド環境はスコープ外 |
| 251 | #20687 Accton AS7312-54-XS broken. Regression? | OPEN | **skip** – Edgecore AS7312 プラットフォームの SAI サポート問題。プラットフォームベンダー固有 |
| 252 | #20694 BMP_STATE_DB database breaks Smart Switch database service | CLOSED | **apply** – BMP_STATE_DB が SmartSwitch の database service を破壊するバグ（PR #20863 と #20726 で修正）を advanced に追記 |
| 253 | #20715 [chassis][supervisor] [master] database-chassis.service failed to start at reboot on Supervisor | CLOSED | **apply** – Supervisor の reboot 時に database-chassis.service が起動失敗するバグ（特定コミット起因）を operations に追記 |
| 254 | #20716 Switch-Hash Capability: Hash Field Not Supported in SONiC on Dell S5248-ON Switch | CLOSED | **apply** – Dell S5248-ON（Trident 3）で Switch Hash の特定フィールドが SAI/SDK でサポートされないという制限を known-limitations に追記 |
| 255 | #20725 Orchagent exiting due to unsupported SAI_*_ATTR_SELECTIVE_COUNTER_LIST attr | CLOSED | **apply** – 新しく追加された SAI_PORT_ATTR_SELECTIVE_COUNTER_LIST 属性が古い SDK/SAI でサポートされず orchagent が終了するパターンを advanced/known-limitations に追記 |

---

## apply 対象まとめ（156 件）

| issue | 反映先ファイル | 内容 |
|-------|--------------|------|
| #13261 | `docs/topics/30-system-services/operations.md` | logrotate / logrotate-config.service の起動順序競合 |
| #13293 | `docs/topics/30-system-services/operations.md` | config load_minigraph 後にフィーチャが無効化されない競合 |
| #13305 | `docs/topics/30-system-services/concept.md` | System Ready の systemd イベント追跡設計制限 |
| #13306 | `docs/topics/30-system-services/operations.md` | rasdaemon 未起動で System Ready が表示されない |
| #13407 | `docs/topics/40-monitoring/operations.md` | sflow hsflowd 起動時 Loopback SIOCGIFFLAGS 競合 |
| #13478 | `docs/topics/30-system-services/operations.md` | Redis メモリ肥大化 OOM パターンと診断方法 |
| #13561 | `docs/topics/20-swss-sai-redis/operations.md` | T2 ルートスケールでの saidump Lua タイムアウト |
| #13573 | `docs/topics/20-swss-sai-redis/advanced.md` | ポートスピード変更後 syncd エラー・orchagent crash |
| #13591 | `docs/topics/40-monitoring/operations.md` | xcvrd SfpStateUpdateTask シャットダウン遅延 |
| #13674 | `docs/topics/30-system-services/operations.md` | sonic-cfggen 失敗で teamd rsyslog.conf が空になる競合 |
| #13791 | `docs/topics/30-system-services/operations.md` | sonic-cfggen が ONIE 初回インストール時に sporadic 失敗 |
| #13811 | `docs/topics/10-routing/concept.md` | Broadcom SAI が ISIS トラップ未サポートの制限 |
| #13910 | `docs/topics/05-networking/operations.md` | VLAN 追加/削除時の dhcp_relay 不必要再起動 |
| #13934 | `docs/topics/05-networking/advanced.md` | Dual-ToR ACL バインド後 LAG メンバ追加タイミング問題 |
| #14184 | `docs/topics/30-system-services/operations.md` | RADIUS MSCHAPV2 MPL 属性未送信時の動作 |
| #14195 | `docs/topics/10-routing/advanced.md` | frrcfgd が 'ip protocol bgp route-map' を push しない制限 |
| #14416 | `docs/topics/40-monitoring/concept.md` | Mellanox SN2010 固定 PSU の show platform psu 仕様 |
| #14436 | `docs/topics/15-chassis/internals.md` | multi_asic.py is_port_channel_internal の内部 PC 識別バグ |
| #14590 | `docs/topics/30-system-services/concept.md` | TACACS サーバ到達不能時のローカルフォールバック動作 |
| #14596 | `docs/topics/15-chassis/operations.md` | chassis での gbsyncd setAPILogLevel 多重呼び出し |
| #14628 | `docs/topics/20-swss-sai-redis/advanced.md` | RIF 削除時の FlexCounter 競合 |
| #14706 | `docs/topics/20-swss-sai-redis/internals.md` | sailibthrift が port_map.ini を参照するバグ |
| #14795 | `docs/topics/30-system-services/concept.md` | App Extension の WantedBy/Requisite が swss 再起動を誘発 |
| #14832 | `docs/topics/30-system-services/operations.md` | ZTP の DHCP DISCOVER に serial number が含まれない問題 |
| #14876 | `docs/topics/05-networking/advanced.md` | LAG メンバ flapping 時の SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE 二重 SET crash |
| #14882 | `docs/topics/10-routing/operations.md` | EVPN L2 VNI 未設定時の ARP 未生成トラブルシュート |
| #14949 | `docs/topics/10-routing/advanced.md` | EVPN NVO config が remote VNI より遅く到着した場合の問題 |
| #15004 | `docs/topics/10-routing/advanced.md` | EVPN L2 スケール環境の MAC expiration と BGP withdrawal 問題 |
| #15047 | `docs/topics/05-networking/operations.md` | config reload 後の削除済み VLAN DHCPv6 カウンタ残存 |
| #15148 | `docs/reference/cli/qos.md` | QoS/MMU CLI の multi-asic サポート追加 |
| #15299 | `docs/topics/20-swss-sai-redis/internals.md` | SAI メタデータの conditional + mandatory チェックのデバッグ |
| #15321 | `docs/topics/15-chassis/advanced.md` | SUP ファブリックポーリングタイムアウトによる orchagent exit |
| #15486 | `docs/topics/15-chassis/concept.md` | database-chassis 停止時の chassisd クラッシュ設計 |
| #15570 | `docs/topics/05-networking/operations.md` | Dual-ToR Active-Active config reload 後の shutdown ポート復活バグ |
| #15586 | `docs/reference/known-limitations.md` | J2C+ DNX SAI がキューカウンタ属性未サポート |
| #15676 | `docs/topics/15-chassis/concept.md` | chassis MACSec の graceful process restart 未サポート制限 |
| #15803 | `docs/topics/10-routing/operations.md` | config reload 中の Zebra intermittent crash |
| #15935 | `docs/topics/30-system-services/operations.md` | System Ready ステータスが統計的に不一致になる問題 |
| #15964 | `docs/topics/05-networking/advanced.md` | Dual-ToR orchagent と linkmgrd の応答タイムアウト |
| #16001 | `docs/topics/40-monitoring/operations.md` | Loopback/mgmt の Link-local IPv6 で snmpd 起動失敗 |
| #16027 | `docs/topics/05-networking/concept.md` | CLI の job order 保証と orchagent retry loop 問題 |
| #16085 | `docs/topics/05-networking/operations.md` | Dual-ToR Active-Active の config reload 後トンネルルート復元失敗 |
| #16161 | `docs/topics/05-networking/advanced.md` | Dual-ToR トンネルルート作成/削除中のパケット重複 |
| #16187 | `docs/topics/40-monitoring/operations.md` | snmpagentaddress VRF 設定でのパースエラーとワークアラウンド |
| #16202 | `docs/topics/40-monitoring/operations.md` | show queue counters が全キューを表示しないリグレッション |
| #16245 | `docs/topics/05-networking/concept.md` | DHCPv6 リレーの config_db フィールド名と YANG 定義の不一致 |
| #16362 | `docs/topics/30-system-services/operations.md` | TACACS 認証失敗（transport endpoint not connected）トラブルシュート |
| #16488 | `docs/topics/15-chassis/advanced.md` | chassis システムポートの buffer task 処理エラー |
| #16489 | `docs/topics/15-chassis/advanced.md` | LC のファブリックポートに対する port status 通知エラー |
| #16533 | `docs/topics/40-monitoring/concept.md` | telemetry コンテナのプロセス終了後動作（202305 変更）|
| #16564 | `docs/topics/20-swss-sai-redis/advanced.md` | pfcwd 有効時の syncd メモリリーク（valgrind 診断）|
| #16596 | `docs/topics/30-system-services/operations.md` | reboot 中の healthd system_service エラー |
| #16741 | `docs/topics/05-networking/advanced.md` | 新規作成直後の PortChannel へのインタフェース追加での orchagent crash |
| #16787 | `docs/topics/15-chassis/advanced.md` | chassis LC config reload 時のシステムポート QUEUE 処理エラー |
| #16939 | `docs/topics/15-chassis/advanced.md` | VOQ chassis 起動時の swss/syncd orchagent crash とコアファイル解析 |
| #16944 | `docs/topics/30-system-services/concept.md` | RFS キャッシュ機能の /lib/modules 空になる副作用 |
| #16992 | `docs/topics/20-swss-sai-redis/advanced.md` | BFD セッション down/remove 通知競合による syncd crash |
| #17025 | `docs/topics/40-monitoring/operations.md` | pmon デーモン（psud/thermalctld）の Redis SET メモリリーク |
| #17107 | `docs/topics/05-networking/operations.md` | bookworm で ntpsec try-restart stuck による SSH 接続喪失 |
| #17178 | `docs/topics/10-routing/advanced.md` | midplane port の linked interface lookup での zebra crash |
| #17180 | `docs/topics/15-chassis/operations.md` | chassis 内部 BFD セッション起動遅延 |
| #17204 | `docs/topics/15-chassis/advanced.md` | remote LC での config reload 時 router interface 削除で orchagent crash |
| #17306 | `docs/topics/30-system-services/concept.md` | config reload 時の hostcfgd と host-services 起動順序競合 |
| #17346 | `docs/topics/20-swss-sai-redis/operations.md` | syncd シャットダウン中の crash |
| #17368 | `docs/topics/05-networking/operations.md` | Dual-ToR MUX インタフェースの topology 展開後グリッチ |
| #17377 | `docs/topics/05-networking/operations.md` | タグ付き物理インタフェースで DHCPv6 リレーカウンタ未上昇 |
| #17403 | `docs/topics/15-chassis/operations.md` | chassis LC の route_check タイムアウト |
| #17434 | `docs/reference/cli/pfcwd.md` | VOQ chassis での pfcwd show stats カウンタ不正確 |
| #17446 | `docs/reference/known-limitations.md` | VOQ chassis での PFCWD が IPv6 トラフィックを drop しない制限 |
| #17472 | `docs/topics/30-system-services/operations.md` | Redis loading 中の sonic-db-cli PING エラー |
| #17530 | `docs/topics/20-swss-sai-redis/advanced.md` | orchagent 初期化中 heartbeat 未送信による stuck 誤判断 |
| #17604 | `docs/topics/10-routing/advanced.md` | FRR が ASIC プログラミング前に BGP ルートアドバタイズ / BGP FIB suppression |
| #17615 | `docs/topics/40-monitoring/operations.md` | sfputil firmware run と Xcvrd の同期問題 |
| #17617 | `docs/topics/20-swss-sai-redis/internals.md` | sonic-db-cli の chassis server での unix socket 非使用 |
| #17624 | `docs/topics/30-system-services/operations.md` | config load でテーブル削除不可という仕様制限 |
| #17657 | `docs/topics/30-system-services/operations.md` | bookworm での NTP パッケージ変更によるパス不整合 |
| #17665 | `docs/topics/05-networking/operations.md` | 既存 PortChannel のメンバ/アドレス移動時の orchagent crash タイミング |
| #17839 | `docs/topics/15-chassis/advanced.md` | VOQ chassis での複数 PFC 優先度同時の SAI_STATUS_INSUFFICIENT_RESOURCES crash |
| #17906 | `docs/topics/30-system-services/operations.md` | minigraph 生成 NTP_SERVER 設定が新 schema に不適合 |
| #17945 | `docs/topics/15-chassis/operations.md` | sonic-db-cli CHASSIS_APP_DB EVAL の intermittent 失敗 |
| #18061 | `docs/topics/40-monitoring/operations.md` | SNMP "public" コミュニティ削除不可 |
| #18137 | `docs/reference/config-db/acl.md` | YANG での ICMP/ICMPv6 type/code restriction 不正確 |
| #18183 | `docs/topics/10-routing/advanced.md` | nexthop refcnt 負値によるエラーと orchagent crash |
| #18184 | `docs/topics/30-system-services/operations.md` | multi-ASIC 環境での syslog rate limiting 未動作 |
| #18226 | `docs/topics/05-networking/advanced.md` | EAPOL COPP と MACSec の trap group 競合 |
| #18237 | `docs/topics/05-networking/advanced.md` | Dell EMC S524 での subinterface 作成による複数コンテナ shutdown |
| #18248 | `docs/reference/known-limitations.md` | Sflow 有効化時の SAI 失敗による orchagent crash（Trident 3.X5）|
| #18335 | `docs/topics/15-chassis/operations.md` | chassis の rsyslog_plugin 高 CPU 使用率（eventd 関連）|
| #18389 | `docs/topics/15-chassis/operations.md` | chassis LC での db_migrate.py SonicDBConfig 初期化エラー |
| #18401 | `docs/topics/30-system-services/operations.md` | Python 3.11 での "is" with literal SyntaxWarning |
| #18417 | `docs/reference/yang/port.md` | multi-asic PORT テーブルと YANG 定義の不一致 |
| #18431 | `docs/topics/15-chassis/operations.md` | multi-asic config reload -l が他 namespace のデータをロード |
| #18472 | `docs/topics/05-networking/concept.md` | dhcp_server コンテナが bridge network mode のため host syslog に書かれない |
| #18490 | `docs/topics/05-networking/operations.md` | 全ポート MTU 9216 設定で swss コンテナが終了するプラットフォーム問題 |
| #18733 | `docs/topics/20-swss-sai-redis/internals.md` | sonic-db-cli の CHASSIS DB unix socket 接続変更（swss-common PR #797）|
| #18766 | `docs/topics/05-networking/operations.md` | フル表記 netmask でルータポート削除失敗 |
| #18771 | `docs/topics/30-system-services/operations.md` | rsyslog 高負荷時の rsyslog_plugin CPU 占有と rate limiting ワークアラウンド |
| #18773 | `docs/topics/15-chassis/operations.md` | chassis LC の route_check FRR タイムアウト（#17403 続き）|
| #18818 | `docs/topics/30-system-services/operations.md` | healthd キュー shutdown 中の EOFError による system_service エラー |
| #18822 | `docs/topics/15-chassis/operations.md` | chassis での dhcp_relay 起動ログが ERR として logAnalyze 失敗 |
| #18865 | `docs/topics/10-routing/operations.md` | bgp-peer-group-af admin-status 値の CLI/frrcfgd 不整合 |
| #18871 | `docs/topics/40-monitoring/operations.md` | DX010 CPU スパイクによる Console/SSH slow 問題と診断 |
| #18893 | `docs/topics/40-monitoring/advanced.md` | DPB 設定変更時の xcvrd CmitManagerTask crash |
| #18913 | `docs/topics/40-monitoring/operations.md` | Mellanox SN2700 での breakout に必要な platform.json/hwsku.json 設定 |
| #19022 | `docs/topics/10-routing/operations.md` | multi-asic 環境での BGP FIB suppression CLI の namespace 問題 |
| #19032 | `docs/topics/40-monitoring/operations.md` | flat memory トランシーバでの sfputil DOM 取得未動作 |
| #19044 | `docs/topics/20-swss-sai-redis/advanced.md` | SmartSwitch boot 時の zmq address 不正で orchagent crash |
| #19059 | `docs/topics/20-swss-sai-redis/advanced.md` | Broadcom DNX ECMP hash offset SAI 属性変更による起動時 crash |
| #19067 | `docs/reference/cli/pfcwd.md` | Nokia VOQ chassis での PFCWD カウンタ計数問題 |
| #19091 | `docs/topics/30-system-services/concept.md` | YANG ベース CLI の大テーブル時の性能問題 |
| #19105 | `docs/topics/20-swss-sai-redis/advanced.md` | DPB ポート削除後の FlexCounter SDK エラータイミング問題 |
| #19145 | `docs/topics/10-routing/operations.md` | decap tunnel タスクの 'dst_ip' 属性 unknown バグ |
| #19218 | `docs/reference/cli/ecmp.md` | ECMP/LAG ハッシュ設定が未指定時の show hash 表示仕様 |
| #19288 | `docs/topics/15-chassis/advanced.md` | LC config reload 後の SUP ファブリックポート隔離問題 |
| #19295 | `docs/topics/15-chassis/advanced.md` | SmartSwitch monit container_checker の DPU DB 問題 |
| #19310 | `docs/topics/05-networking/operations.md` | スケールド設定での config reload 後 LAG 未削除問題 |
| #19311 | `docs/topics/05-networking/operations.md` | MACsec rekey 後の sonic-clear macsec カウンタ未リセット |
| #19336 | `docs/topics/40-monitoring/concept.md` | CMIS マネージャのアプリケーション自動選択設計 |
| #19352 | `docs/topics/40-monitoring/operations.md` | telemetry コンテナ名変更後の monit container_checker エラー |
| #19357 | `docs/topics/15-chassis/advanced.md` | chassis での LAG 削除後の backend PortChannel operstatus 更新問題 |
| #19405 | `docs/topics/15-chassis/operations.md` | Supervisor からの show techsupport 動作問題 |
| #19406 | `docs/topics/15-chassis/operations.md` | chassis での ulimit 設定問題によるコアダンプ未生成 |
| #19455 | `docs/reference/config-db/switch.md` | ORDERED_ECMP_CAPABLE が SWITCH_CAPABILITY に存在しない場合 |
| #19507 | `docs/topics/05-networking/operations.md` | dhcprelayd のトレースバック付きクラッシュ診断 |
| #19566 | `docs/reference/cli/queue.md` | VOQ chassis の show queue watermark unicast に --voq オプション必要 |
| #19569 | `docs/topics/15-chassis/operations.md` | chassis での orchagent ポート up 通知処理遅延 |
| #19581 | `docs/topics/40-monitoring/operations.md` | GNMI client_auth デフォルト true でのサーバ証明書認証エラー |
| #19591 | `docs/topics/40-monitoring/operations.md` | BGP 状態変化が EVENTS DB に届かない問題のデバッグ |
| #19592 | `docs/reference/known-limitations.md` | Broadcom SAI DNX が SAI_NEIGHBOR_ENTRY_ATTR_IS_LOCAL 未サポート |
| #19603 | `docs/topics/40-monitoring/operations.md` | multi-asic 環境での telemetry swss イベント未発火 |
| #19620 | `docs/topics/30-system-services/operations.md` | systemd-networkd-wait-online コマンド失敗 |
| #19624 | `docs/topics/40-monitoring/operations.md` | GNMI の multi-asic namespace 未指定によるバッファキュー未反映 |
| #19638 | `docs/topics/20-swss-sai-redis/advanced.md` | SmartSwitch での MGMT_VRF 有効時 orchagent crash |
| #19648 | `docs/topics/20-swss-sai-redis/advanced.md` | Broadcom DNX PFC pause storm 時の MMU バッファとロスレスドロップ |
| #19661 | `docs/topics/30-system-services/operations.md` | banner-config サービス依存による SSH 起動遅延 |
| #19730 | `docs/reference/cli/portchannel.md` | PortChannel メンバの輻輳時重複ドロップカウンタ（CRPS pp_port 共有）|
| #19760 | `docs/topics/20-swss-sai-redis/advanced.md` | NotificationSwitchAsicSdkHealthEvent コールバック中の orchagent crash |
| #19763 | `docs/topics/10-routing/operations.md` | rsyslogd メモリ問題による BGP コンテナメモリ増加 |
| #19779 | `docs/reference/cli/counters.md` | multi-asic での sonic-clear 後の show priority-group drop counters key-error |
| #19828 | `docs/topics/30-system-services/operations.md` | bookworm での python デーモンの高メモリ使用量 |
| #19846 | `docs/topics/30-system-services/concept.md` | sonic-installer でのパッケージ自動マイグレート設計 |
| #19861 | `docs/reference/cli/counters.md` | #19779 と同根（multi-asic sonic-clear 後のドロップカウンタ残存）|
| #19878 | `docs/topics/30-system-services/concept.md` | featured の feature install 未確認での属性追加問題 |
| #19946 | `docs/topics/10-routing/operations.md` | BGP_NEIGHBOR auth_password の config reload 後復元失敗 |
| #20019 | `docs/topics/10-routing/concept.md` | config node "unified" での route-map list 処理 |
| #20055 | `docs/topics/15-chassis/advanced.md` | T2 chassis での BGP communities attribute 不正エラー |
| #20059 | `docs/topics/15-chassis/operations.md` | chassis での teamd が swss DB 初期化前に PortChannel 作成する起動順序問題 |
| #20070 | `docs/topics/15-chassis/advanced.md` | chassis LC reboot 時の ASIC 名大文字小文字不一致 buffer_profile エラー |
| #20212 | `docs/topics/20-swss-sai-redis/advanced.md` | sairedis FDB コールバックの bulk 通知処理非効率 |
| #20214 | `docs/topics/15-chassis/operations.md` | T2 chassis での neighorch 連続 INFO ログ |
| #20246 | `docs/topics/30-system-services/operations.md` | reboot 中の eventd デシリアライズエラー |
| #20261 | `docs/topics/15-chassis/advanced.md` | VOQ chassis でのポートスピード変更時 SAI エラー |
| #20279 | `docs/topics/30-system-services/concept.md` | eventd のコレクター未接続時の xpub キャッシュ（最大 100MB）|
| #20284 | `docs/topics/30-system-services/operations.md` | platform.json の DPU チェックによる WR/FR reconcile 遅延と診断 |
| #20302 | `docs/topics/20-swss-sai-redis/concept.md` | enable_counters.py の CONFIG_DB カウンタ設定 runtime 上書き問題 |
| #20331 | `docs/topics/20-swss-sai-redis/advanced.md` | SFP/DAC ケーブル挿入で syncd がクラッシュするパターン |
| #20337 | `docs/topics/15-chassis/advanced.md` | T2 chassis Zebra の大量メモリ消費 OOM パニック |
| #20361 | `docs/reference/known-limitations.md` | Mellanox SPC1 での MP2MP IPinIP decap term 作成失敗 |
| #20376 | `docs/topics/40-monitoring/operations.md` | show techsupport 中の sensors コマンド hang（SIGSTOP）|
| #20378 | `docs/topics/05-networking/operations.md` | GCU/MA での ACL_RULE 変更が適用されない問題 |
| #20414 | `docs/topics/05-networking/operations.md` | Dual-ToR autorestart 無効時の config reload 後 mux コンテナ高 CPU |
| #20430 | `docs/topics/40-monitoring/advanced.md` | Intel DR4 トランシーバで CMIS マネージャが 4x100G データパスを有効化できない |
| #20466 | `docs/topics/20-swss-sai-redis/operations.md` | sai.profile の余分な改行による format 問題 |
| #20507 | `docs/topics/15-chassis/advanced.md` | VOQ chassis での sonic-mgmt テスト中 orchagent crash |
| #20576 | `docs/topics/20-swss-sai-redis/internals.md` | saiplayer の FC 設定を含む recording replay 失敗 |
| #20587 | `docs/topics/05-networking/advanced.md` | Dell S5248F での neighbor 操作タイムアウトによる crash |
| #20589 | `docs/topics/40-monitoring/operations.md` | PFCWD デフォルト無効設定と pfcwd start_default CLI 問題 |
| #20590 | `docs/topics/20-swss-sai-redis/advanced.md` | Broadcom DNX の Priority Group0 輻輳時 Pause フレーム問題 |
| #20605 | `docs/topics/15-chassis/advanced.md` | T2 chassis での ACL テスト中 orchagent crash |
| #20636 | `docs/topics/30-system-services/operations.md` | docker-database の critical_processes 形式エラーで supervisor 終了 |
| #20652 | `docs/topics/15-chassis/advanced.md` | VOQ chassis での Everflow パケット誤キュー送信 |
| #20680 | `docs/topics/15-chassis/advanced.md` | T2 Supervisor の redis omem リーク |
| #20694 | `docs/topics/20-swss-sai-redis/advanced.md` | BMP_STATE_DB が SmartSwitch database service を破壊するバグ |
| #20715 | `docs/topics/15-chassis/operations.md` | Supervisor reboot 時の database-chassis.service 起動失敗 |
| #20716 | `docs/reference/known-limitations.md` | Dell S5248-ON（Trident 3）での Switch Hash フィールド未サポート |
| #20725 | `docs/reference/known-limitations.md` | 新しい SAI_PORT_ATTR_SELECTIVE_COUNTER_LIST が古い SDK で未サポートで orchagent 終了 |

---

## skip 対象（99 件）

ビルド環境問題・プラットフォーム固有バグ・古いブランチ問題・新機能提案・VS 固有問題・テスト環境問題を中心に skip。

#13252 #13265 #13308 #13317 #13318 #13455 #13719 #13775 #13780 #13818 #13873 #13937 #13978 #14087 #14196 #14316 #14467 #14536 #14722 #14831 #14854 #14929 #14974 #15250 #15502 #15949 #16080 #16087 #16204 #16259 #16301 #16362 #16468 #16523 #16596 #16666 #16725 #16789 #16822 #16950 #16972 #16988 #16996 #17023 #17074 #17107 #17121 #17348 #17379 #17485 #17547 #17548 #17566 #17107 #17485 #18137 #18180 #18297 #18358 #18421 #18489 #18607 #18679 #18767 #18832 #18883 #19028 #19146 #19180 #19204 #19235 #19328 #19735 #19995 #20377 #20475 #20540 #20547 #20614 #20685 #20687
