# sonic-buildimage batch-0 判定ログ (255 件)

処理日: 2026-05-13  apply: 130  skip: 122

| # | title | state | 判定 | 反映先 | 要約 |
|---|-------|-------|------|--------|------|
| 27 | Failure trying to run: chroot /sonic-buildimage/fsroot mount | CLOSED | apply | architecture/build-system-improvements.md | sonic-slave コンテナ内で debootstrap が proc マウントに失敗する場合、`docker run --privileged` フラグが |
| 119 | dpkg-query: error: failed to open package info file `/var/li | CLOSED | skip | - | dpkg 状態ファイル破損 - 環境依存の一時的エラー |
| 134 | docker-fpm and docker-team depend on libsai | OPEN | skip | - | Enhancement request - libsai 依存関係 |
| 389 | The switch will be crashed when inputting "reboot" command u | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | ホストから `reboot` コマンドを実行するとスイッチがクラッシュする既知の問題。SONiC では `sudo reboot` または `sudo soni |
| 428 | Jenkins builds failing due to lack of free space | CLOSED | skip | - | Jenkins ディスク容量不足 - CI 運用上の問題 |
| 482 | portstat fails | CLOSED | skip | - | portstat ツールの問題 - 環境依存 |
| 548 | No such file or directory  #include <switch_sai_rpc_server.h | CLOSED | skip | - | ビルドエラー - ベンダー SDK ヘッダー不足 |
| 579 | quagga cannot start on image installed using sonic2sonic upg | CLOSED | skip | - | クォーガ起動問題 - 古いバージョン固有 |
| 600 | LAG state becomes no-carrier even if there are members in LO | CLOSED | skip | - | LAG state 問題 - 調査中 |
| 602 | Complie error in libsaimetadata | CLOSED | skip | - | コンパイルエラー - SAI メタデータ |
| 633 | Control fans and sensors by BMC | CLOSED | apply | system/platform-monitor-enhancement-design.md | BMC (Baseboard Management Controller) 経由でファン・センサー制御が可能なプラットフォームでは、platform API で |
| 678 | "sfputil" command can't show the  information of 25G AOC pro | CLOSED | skip | - | SFP 25G AOC 情報表示問題 - HW 固有 |
| 762 | supervisord AssertionError: Assertion failed for start.sh: R | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | supervisord の AssertionError: start.sh が RUNNING 状態でないと判断される問題。サービスの起動タイムアウト設定を確 |
| 839 | file system full could cause service not running after reboo | CLOSED | skip | - | ファイルシステム満杯 - 運用上の問題 |
| 990 | Get port alias but not port name in snmp_interface test | CLOSED | skip | - | SNMP テスト失敗 - テスト環境問題 |
| 1023 |  eth0 can't be pinged on the same subnet | CLOSED | skip | - | eth0 ping 不通 - ネットワーク設定問題 |
| 1037 | sfputil broken for multiple platforms | CLOSED | skip | - | sfputil 問題 - 複数プラットフォーム依存 |
| 1054 | Accton-AS5712-54X Boot Up Failed with Errors on the latest J | CLOSED | skip | - | Accton AS5712 ブート失敗 - ベンダー HW 固有 |
| 1364 | How do I put ipmitool to rootfs | CLOSED | skip | - | ipmitool rootfs 追加方法の質問 |
| 1404 | Does sonic support new  format of /etc/machine.conf which is | CLOSED | skip | - | machine.conf フォーマット質問 |
| 1416 | SAI v1.2 does not include the broadcom configure on delta_ag | CLOSED | skip | - | SAI v1.2 delta_ag9032v1 設定不足 - ベンダー固有 |
| 1457 | [LLDP] lldp portidsubtype was NOT set to "locally assigned"  | CLOSED | apply | system/platform-monitor-enhancement-design.md | LLDP の portidsubtype が "locally assigned" ではなく "mac address" にセットされる問題。lldpd の設定 |
| 1461 | question about eeprom.py and sfputil.py | CLOSED | skip | - | eeprom.py と sfputil.py の使用方法質問 |
| 1505 | Newest SAI does not include the broadcom configuration on qu | CLOSED | skip | - | SAI on quanta_ix1b - ベンダー固有 |
| 1519 | /host/machine.conf is incorrent | CLOSED | apply | architecture/build-system-improvements.md | /host/machine.conf の内容が不正な場合、プラットフォーム固有の設定が失敗する。platform フィールドに正しい hwsku 名を設定するこ |
| 1543 | How to edit led linkscan callback? | CLOSED | skip | - | LED linkscan callback 編集方法の質問 |
| 1669 | docker dhcp build failed. | CLOSED | skip | - | docker dhcp ビルド失敗 - 古いバージョン |
| 1762 | bcmsh is blocking bcmcmd, and no timeout either | CLOSED | skip | - | bcmsh タイムアウト問題 - ベンダー SDK 依存 |
| 1873 | interfaces-config.service may hang at sonic-cfggen -d | CLOSED | apply | architecture/build-system-improvements.md | interfaces-config.service が `sonic-cfggen -d` で応答待ちになりハングする問題。Redis が起動していない状態で  |
| 1969 | [Debian9-Accton_AS5712_54X]  - decode-syseeprom/show platfor | CLOSED | skip | - | decode-syseeprom 問題 - Accton 固有 |
| 1981 | Kernel 4.9: race condition seen with port channel creation.  | CLOSED | apply | switching/sonic-ip-lag-incremental-update.md | Kernel 4.9 においてポートチャネル作成時に race condition が発生する既知の問題。並行してポートチャネルを作成・削除するとカーネルクラッ |
| 1990 | [virtual-switch] Port config ini type for portsyncd hardcode | CLOSED | skip | - | portsyncd 設定ハードコード問題 - 仮想スイッチ固有 |
| 2004 | build errors on master, happened again | CLOSED | skip | - | master ブランチのビルドエラー - 一時的CI問題 |
| 2005 | Jenkins build failure buildimage-p4-all. | CLOSED | skip | - | Jenkins ビルド失敗 - CI 問題 |
| 2017 | Can't instantiate abstract class SfpUtil with abstract metho | CLOSED | skip | - | SfpUtil 抽象クラス問題 - 実装方法の質問 |
| 2029 | Get into sonic-slave docker | CLOSED | apply | architecture/build-system-improvements.md | sonic-slave コンテナに入る方法: `docker run -v /var/run/docker.sock:/var/run/docker.sock  |
| 2030 | Got a "libkmod: ERROR" log, if there is no "depmod -a" in on | CLOSED | apply | architecture/build-system-improvements.md | 初期化スクリプトで `depmod -a` が実行されていない場合、`libkmod: ERROR` ログが出力される。カーネルモジュールの依存関係データベース |
| 2042 | Could SONIC provide the offline build package? | CLOSED | skip | - | オフラインビルドパッケージ要望 - Enhancement |
| 2066 | The member ports of portchannel are still in selected state  | OPEN | skip | - | PortChannel メンバーポートが selected 状態のまま残る問題 - 調査中 |
| 2067 | How to remove "ismt_smbus 0000:00:13.0: completion wait time | OPEN | skip | - | ismt_smbus タイムアウトメッセージ除去方法の質問 |
| 2081 | Image build timestamp inconsistency | CLOSED | skip | - | イメージビルドタイムスタンプ不整合 - 軽微な問題 |
| 2102 | Kernel: config reload does not clean up old loopback IP addr | CLOSED | apply | architecture/build-system-improvements.md | config reload 後にカーネルの loopback IP アドレスが残る既知のバグ。`config reload` は CONFIG_DB を更新する |
| 2125 | SAI_STATUS_TABLE_FULL and swss:orchagent shutdown | OPEN | apply | internals/support-multiple-user-defined-redis-database-instances.md | SAI_STATUS_TABLE_FULL エラーで orchagent がシャットダウンする問題。SAI テーブルの容量制限に達した場合、orchagent  |
| 2189 | CLI / redis DB Hangs Upon ARP Cache's Hitting the Default Ma | CLOSED | skip | - | ARP キャッシュ上限によるCLI/Redis ハング - 運用問題 |
| 2276 | Dell S6000: wrong lane mapping in port_config.ini  | CLOSED | skip | - | Dell S6000 レーンマッピング設定不正 - ベンダー固有 |
| 2382 | Reboot has a probability that docker can't start | CLOSED | skip | - | リブート後 docker 起動確率問題 - 環境依存 |
| 2414 | DUT takes more than 7 seconds to finish update ip v6 neighbo | CLOSED | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | IPv6 ネイバーのアップデートに 7 秒以上かかる問題。IPv6 NDP タイムアウト設定がデフォルトで長い場合がある。`/proc/sys/net/ipv6 |
| 2418 | Sonic building image is unsuccessful | CLOSED | skip | - | sonic ビルド失敗 - 環境問題 |
| 2614 | "failed to load plugin io.containerd.snapshotter..." seen du | OPEN | apply | architecture/build-system-improvements.md | Linux カーネルビルド中に `failed to load plugin io.containerd.snapshotter` エラーが発生する問題。con |
| 2627 | Expose FRR /var/run/frr (frr sockets) to the host system | CLOSED | skip | - | FRR sockets ホスト公開 - Enhancement |
| 2646 | lm75 doesn't support written alarm to syslog. | CLOSED | skip | - | lm75 アラームログ問題 - センサー固有 |
| 2658 | Remove port from VLAN leaving the port in default VLAN | CLOSED | apply | switching/switch-port-modes-and-vlan-cli-enhancement.md | VLAN からポートを削除すると、ポートがデフォルト VLAN に残る動作は設計上の制約。ポートを完全に VLAN から切り離す場合は `config vlan |
| 2684 | Core dump in orchagent when assigning router interface to a  | OPEN | apply | switching/switch-port-modes-and-vlan-cli-enhancement.md | VLAN に既に割り当てられているインターフェースにルーターインターフェースを割り当てようとすると orchagent がコアダンプする既知の問題。VLAN メ |
| 2752 | dhcp_relay service stopped with "systemctl stop swss" but no | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | dhcp_relay サービスが `systemctl stop swss` で停止するが、swss 再起動時に dhcp_relay が自動的に再起動されない |
| 2813 | rm: cannot remove './fsroot/var/lib/docker': Device or resou | CLOSED | skip | - | docker レイヤ削除権限エラー - ビルド環境問題 |
| 3008 | [warm-reboot] apps crash due to redis is busy running 'tablu | OPEN | apply | system/fast-reboot-flow-improvements-hld.md | warm-reboot 中に Redis が Lua スクリプト実行でビジー状態となりアプリがクラッシュする問題。warm-reboot 前に Redis のビ |
| 3043 | BGP sessions are not established for both IPv4 and IPv6 due  | CLOSED | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | IPv4 と IPv6 両方の BGP セッションが確立できない問題。デュアルスタック構成では `no bgp default ipv4-unicast` を適 |
| 3150 | PortChannel ip address is missing after do "systemctl restar | CLOSED | skip | - | teamd 再起動後の PortChannel IP 消失 - 重複報告 |
| 3196 | watchfrr is not running | OPEN | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | watchfrr が起動していない状態で FRR の一部デーモンがクラッシュしても自動復旧されない。`supervisorctl status watchfrr |
| 3206 | Deb9 SONiC image work on Accton Wedge100bf_65x, it have many | CLOSED | skip | - | Accton Wedge100bf_65x 多数の問題 - ベンダー固有 |
| 3244 | Multiple restart of swss during config load fails to start s | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | config load 中に swss を複数回再起動するとサービス起動に失敗する問題。手動での複数回 swss 再起動は避けること |
| 3271 | ARM arch support for SONIC | CLOSED | skip | - | ARM アーキテクチャサポート - Enhancement |
| 3331 | Need to move linux kernel repo pointer in branch 201904 | OPEN | skip | - | linux kernel リポジトリポインタ更新 - 古いブランチ問題 |
| 3453 | Change made some time ago to delay snmp in favor of faster f | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | fast-reboot 高速化のため SNMP サービスの起動を遅延させる変更がある。fast-reboot 直後の SNMP ポーリングが失敗する場合があるた |
| 3503 | build error for 201904 because linux_4.9.168-1+deb9u3.dsc li | OPEN | skip | - | linux カーネル dsc ファイル 404 エラー - 古いブランチ問題 |
| 3673 | sonic image compile error happend at "make all" stage. Need  | CLOSED | skip | - | sonic イメージコンパイルエラー - 環境問題 |
| 3798 | Zebra crash is observed when management VRF is disabled. Cra | OPEN | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | management VRF を無効化すると zebra がクラッシュする既知の問題。mgmt VRF の有効/無効切り替えは動的には行えず、設定変更後にコンテ |
| 3803 | dhcp_relay docker results in getting error when management v | OPEN | skip | - | dhcp_relay の management VRF 削除エラー - 関連する別の問題 |
| 3814 | loopback ip not clear in kernel after config reload | CLOSED | skip | - | loopback IP 未クリア問題 - 重複報告 |
| 3822 | during config reload, teamd is restarted twice | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | config reload 時に teamd が 2 回再起動される問題。PortChannel が一時的に Down 状態になる。config reload  |
| 3832 | orchagent crashes due to transfer_attributes: src vs dst att | OPEN | apply | internals/dump-utility-for-easy-debugging.md | orchagent が `transfer_attributes: src vs dst attr id don't match` でクラッシュする問題。syn |
| 3849 | [swssconfig]: Unable to apply large number of config entries | OPEN | skip | - | swssconfig 大量エントリ適用問題 - Enhancement |
| 3934 | syncd crash  and hung seen with warm-reboot and fast-reboot  | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | warm-reboot と fast-reboot で syncd がクラッシュまたはハングする問題。T0 トポロジでの継続的なリブートテストで再現。syncd |
| 3944 | Tomahawk3 (TH3) SDK init fail after  Upgrade broadcom SAI to | CLOSED | apply | architecture/sonic-arm-architecture-support.md | Broadcom SAI を 3.7.3.2 にアップグレード後、Tomahawk3 (TH3) の SDK init が失敗する既知の問題。TH3 対応の S |
| 3976 | sonic-telemetry_0.1_amd64.deb failed to build on 201811 | CLOSED | skip | - | sonic-telemetry ビルド失敗 - 古いブランチ |
| 4009 | [teamd]: different portchannels configured with same LACP ke | CLOSED | skip | - | 同じ LACP キーの PortChannel 設定 - 設定問題 |
| 4019 | [Issue] Monit service cause many regression test cases faile | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | monit サービスが設定した閾値を超えるとプロセスを強制終了するため、回帰テストで失敗が多発する問題。テスト環境では monit の閾値設定を緩和するか、テス |
| 4034 | DaemonBase: object has no attribute 'syslog' | CLOSED | skip | - | DaemonBase の syslog 属性エラー - コードバグ |
| 4059 | [mgmt-framework]: unable to parse schema file sonic-acl-devi | CLOSED | skip | - | mgmt-framework スキーマパースエラー - 開発問題 |
| 4089 | S6100-T0-64-Continuous Orchagent crash is seen in the latest | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | S6100 T0-64 構成で orchagent が継続的にクラッシュする問題。syncd との API バージョン不一致が原因の場合が多い |
| 4096 | SONiC.HEAD.187-dirty-20200130.072127 | CLOSED | apply | architecture/build-system-improvements.md | SONiC HEAD 187-dirty ビルドでのバージョン管理問題。`--dirty` サフィックスが付くビルドは本番環境での使用を避けること |
| 4127 | S6100-T0-64/T1-LAG-64/ Restart of syncd doesnt stop the sync | OPEN | apply | internals/dump-utility-for-easy-debugging.md | syncd の再起動が完了しない問題。syncd プロセスが SIGTERM を無視して終了しない場合、`kill -9` が必要になることがある |
| 4173 | config load_minigraph failed with "Job for sflow.service fai | OPEN | skip | - | config load_minigraph で sflow サービス起動失敗 - 設定問題 |
| 4230 | snmp-subagent MIBUpdater exception loc_chassis_data not subs | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | SNMP subagent の MIBUpdater が `loc_chassis_data not subscriptable` 例外でクラッシュする問題。L |
| 4291 | [mgmt-framework]: service fails to start on 201911 | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | mgmt-framework サービスが 201911 ブランチで起動失敗する問題。Python 3 移行後の依存パッケージ不足が原因の場合がある |
| 4315 | sonic-slave-stretch build failed | CLOSED | skip | - | sonic-slave-stretch ビルド失敗 - 古い Stretch ベース |
| 4331 | [DellEmc S5232]: Orchagent crash is seen with 201911 images | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | DellEmc S5232 で orchagent がクラッシュする既知の問題 (201911 イメージ)。Broadcom SAI の特定バージョンとの互換性 |
| 4339 | [DellEmc S5232]: Orchagent crash is seen in latest master (# | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | DellEmc S5232 で master #238 イメージの orchagent クラッシュ問題。libsaibcm バージョンアップ後に再現 |
| 4347 | Orchagent crashes after moving to libsaibcm_3.7.3.3-3 | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | libsaibcm_3.7.3.3-3 への移行後に orchagent がクラッシュする問題。SAI ライブラリのバージョンと orchagent の互換性を |
| 4358 | Building Sonic With : "KERNEL_PROCURE_METHOD" = download | OPEN | skip | - | KERNEL_PROCURE_METHOD=download でのビルド問題 |
| 4359 | Sonic Building : Host ( Build environment ) Docker Image Res | OPEN | skip | - | ビルド後の孤立コンテナ問題 - ビルド環境 |
| 4366 | “apt-get update” always fail when build base docker image. | OPEN | apply | architecture/build-system-improvements.md | ベース docker イメージのビルド時に `apt-get update` が常に失敗する問題。Debian リポジトリの APT キーが期限切れの場合に発生 |
| 4399 | Warm reboot from 201811 to 201911 failed due to directed-con | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | 201811 から 201911 への warm reboot が失敗する問題。直接接続ルートの処理に互換性のない変更があるため、バージョン間の warm re |
| 4400 | To delete neighbor entries which are next-hop of routing ent | CLOSED | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | ルーティングエントリの next-hop であるネイバーエントリを削除する際の順序が重要。next-hop が有効な状態でルートを削除してからネイバーを削除しな |
| 4404 | build error in latest sonic mainline | CLOSED | apply | architecture/build-system-improvements.md | master mainline でのビルドエラー。`git submodule update --init --recursive` でサブモジュールを最新化し |
| 4407 | getHwCounters returns error during pfc_wd test | CLOSED | skip | - | pfc_wd テスト中の HW カウンターエラー - テスト問題 |
| 4428 | S6100-T0-syncd crash seen on cold reboot- HEAD.253-2872d802 | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | S6100 T0 での cold reboot 後に syncd クラッシュが発生する問題 (HEAD.253) |
| 4429 | S6100 - T0 and T1 - Zebra crash seen with continous cold reb | OPEN | apply | system/fast-reboot-flow-improvements-hld.md | S6100 の T0/T1 トポロジで継続的 cold reboot 中に zebra がクラッシュする問題。FRR の warm-restart との組み合わ |
| 4454 | [dropcounters] after clear new counters have negative values | OPEN | skip | - | drop counters がクリア後に負の値を示す問題 - バグ |
| 4456 | SWSS container stops in case of assigning a vlan to a portch | OPEN | skip | - | VLAN に portchannel メンバーを割り当てると swss コンテナが停止する問題 |
| 4457 | [ACL] A rule with action "REDIRECT:next-hop" can't be create | OPEN | skip | - | ACL next-hop redirect ルール作成失敗問題 |
| 4517 | Unable to compile for Cavium (AS7512-32X) - undefined refere | OPEN | skip | - | Cavium AS7512-32X のコンパイルエラー - ベンダー固有 |
| 4553 | sonic-cfggen is consuming a lot of CPU during switch startup | CLOSED | apply | architecture/build-system-improvements.md | スイッチ起動時に sonic-cfggen が大量の CPU を消費する問題。起動時に複数のサービスが同時に sonic-cfggen を呼び出すため。`sys |
| 4570 | Key  IPV6_NEXT_HEADER is not supported in MIRRORV6 ACL | CLOSED | apply | acl-qos/acl-in-sonic.md | MIRRORV6 ACL では `IPV6_NEXT_HEADER` キーがサポートされていない制約。IPv6 ミラーリング ACL の設定時は対応フィールドを |
| 4572 | BGPv6 Neighbor configuration on config_db not generated to f | CLOSED | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | CONFIG_DB の BGPv6 ネイバー設定が frr.conf に正しく生成されない問題。sonic-cfggen のテンプレートが BGPv6 ネイバー |
| 4576 | Orchagent crash is seen when portchannel is configured | CLOSED | skip | - | portchannel 設定時の orchagent クラッシュ - 調査中 |
| 4586 | ERR syncd#syncd: :- collectPortCounters: Failed to get stats | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | `collectPortCounters: Failed to get stats of port 0` エラーが syncd ログに出力される問題。CPU ポ |
| 4587 | The query on OID ChStackUnitCpuUtil5sec doesnt fetch any o/p | OPEN | skip | - | SNMP ChStackUnitCpuUtil5sec クエリ無応答 - SNMP MIB 問題 |
| 4612 | bgpd exited during regression | CLOSED | skip | - | bgpd 回帰テスト中の終了 - テスト問題 |
| 4646 | Port status not reflected in SONiC | CLOSED | apply | system/platform-monitor-enhancement-design.md | ポートのステータス変更が SONiC に反映されない問題。xcvrd または portsyncd がポートの物理状態変更を正しく検知できていない場合に発生。`s |
| 4664 | BGP_PEER_RANGE is not translated into FRR configuration | CLOSED | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | CONFIG_DB の BGP_PEER_RANGE 設定が FRR 設定に変換されない問題。sonic-cfggen のテンプレートが BGP_PEER_RA |
| 4667 | [device/accton]Syntax error on config.bcm for AS7312-54XS, A | CLOSED | skip | - | Accton AS7312 config.bcm 構文エラー - ベンダー固有 |
| 4682 | [BRCM] syncd has abnormally exited (missing libprotobuf.so.0 | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | syncd が `libprotobuf.so.0` 不足で異常終了する問題。syncd docker イメージのビルド時に protobuf ライブラリが含ま |
| 4736 | After warm-restart swss docker, crm counters were abnormal | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | swss の warm-restart 後に CRM カウンターが異常値を示す問題。次の定期更新サイクルまで不正確な値を返すことがある |
| 4742 | Error in "make configurate PLATFORM=generic" at last step | CLOSED | skip | - | generic プラットフォームの configure ステップエラー - 設定問題 |
| 4782 | The port can not become up on  x86_64-accton_wedge100bf_32x- | CLOSED | skip | - | x86_64-accton_wedge100bf_32x でのポート UP 不可 - ベンダー固有 |
| 4797 | iptables blocking access to /32 Loopback address | CLOSED | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | iptables が /32 ループバックアドレスへのアクセスをブロックする問題。management VRF 有効時に iptables ルールが自動的に追加 |
| 4821 | test_announce_routes failed due to Ethernet24 is down. | CLOSED | skip | - | テスト失敗 - Ethernet24 ダウン問題 |
| 4839 | SNMP ifName and ifDescr are identical and only expose aliase | CLOSED | skip | - | SNMP ifName/ifDescr が同一値を返す問題 |
| 4872 | [Dell S5232]:Rx drop counters incremented for BGP control pa | OPEN | skip | - | Dell S5232 BGP パケットの Rx drop カウンター増加 - ベンダー固有 |
| 4877 | ERR syslog about snmp-subagent [ax_interface] When the devic | CLOSED | skip | - | SNMP subagent ax_interface エラーログ - 軽微な問題 |
| 4879 | Neighbors learned from portchannel, when neighbors are offli | CLOSED | skip | - | portchannel ネイバーのオフライン後タイムアウト問題 |
| 4885 | ARP cannot reach the expected number which does not exceed t | CLOSED | skip | - | ARP キャッシュが期待値に達しない問題 |
| 4907 | orchagent crash observed intermittently on latest SONIC imag | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | 最新 SONiC イメージで orchagent が断続的にクラッシュする問題。コアダンプを収集し、`sudo gdb /usr/bin/orchagent c |
| 4912 | Parallel build are failed on master branch | CLOSED | skip | - | 並列ビルド失敗 - master ブランチ CI 問題 |
| 4961 | ospfclient can be started in FRR installed vm but can't in S | OPEN | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | ospfclient が SONiC docker コンテナ内で起動できない問題。コンテナ内の FRR ソケットパスが `/var/run/frr` であること |
| 4969 | Routes not propagating from kernel to ASIC | OPEN | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | カーネルルートが ASIC に伝播されない問題。fpmsyncd が FRR から APPL_DB への route 書き込みに失敗している場合がある |
| 5001 | show interface transceiver broken in recent builds | CLOSED | apply | system/platform-monitor-enhancement-design.md | 最新ビルドで `show interface transceiver` コマンドが壊れている問題。xcvrd の Python 3 移行後にインターフェース取得 |
| 5015 | Aclshow utility: ACL counters are not available for control  | OPEN | apply | acl-qos/acl-in-sonic.md | aclshow ユーティリティがコントロールプレーン ACL のカウンターを表示しない制約。iptables ベースの COPP ACL は `iptables |
| 5026 | ip route in the kernel does not match routes in bgp | CLOSED | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | カーネルの ip route と BGP ルートが一致しない問題。redistribute connected/kernel の設定や `ip route` で |
| 5031 | [interfaces] some interfaces can't be displayed when arp tab | OPEN | apply | internals/support-multiple-user-defined-redis-database-instances.md | ARP テーブルが上限に近い状態だと `show interfaces` の一部インターフェースが表示されない問題。`net.ipv4.neigh.defaul |
| 5040 | IPv6 routes not propagating from APPL_DB to ASIC_DB | OPEN | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | IPv6 ルートが APPL_DB から ASIC_DB に伝播されない問題。fpmsyncd の IPv6 対応設定と orchagent の IPv6 ルー |
| 5051 | Interfaces are displayed as Portchannel members even after d | CLOSED | apply | switching/sonic-ip-lag-incremental-update.md | PortChannel を削除後もインターフェースが PortChannel メンバーとして表示される問題。`config portchannel member |
| 5054 | [portchannel specification]orchagent crashen when config 100 | OPEN | apply | switching/sonic-ip-lag-incremental-update.md | 1000 個の PortChannel を設定すると orchagent がクラッシュする制約。プラットフォームごとの PortChannel 数上限を事前確認 |
| 5067 | frr.conf doens't reflect running FRR config | CLOSED | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | frr.conf が実行中の FRR 設定と一致しない問題。`vtysh -c "show running-config"` の出力が frr.conf より正 |
| 5097 | build failure at kdump-tools stage while build target/sonic- | CLOSED | skip | - | kdump-tools ステージでのビルド失敗 - 環境問題 |
| 5162 | Celestica DX010  32x100G | OPEN | skip | - | Celestica DX010 サポート - ベンダー固有 |
| 5206 | PFC and Queue counters showing negative values | OPEN | apply | internals/sonic-counter-initialization-optimization.md | PFC とキューカウンターが負の値を示す問題。カウンターのオーバーフローまたは初期化前の読み取りが原因。`sonic-clear` で初期化してから再度確認する |
| 5216 | [fast-reboot] FDB entries are not restored on fast-reboot | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | fast-reboot 後に FDB エントリが復元されない問題。FDB の再学習に時間がかかる場合がある。`show mac` で FDB 学習状況を監視する |
| 5217 | [fast-reboot] ARP entries are not restored after fast-reboot | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | fast-reboot 後に ARP エントリが復元されない問題。ARP エントリの再学習はデフォルト ARP タイムアウトに依存する |
| 5241 | supervisord-dependent-startup print out error log when stop  | CLOSED | skip | - | supervisord-dependent-startup のエラーログ - 軽微 |
| 5258 | Z9264/201911-170/Orchagent and python crash with warm-reboot | OPEN | apply | internals/dump-utility-for-easy-debugging.md | Z9264/201911-170 での warm-reboot 中に orchagent と Python プロセスがクラッシュし、カーネルクラッシュが発生する |
| 5275 | COPP with ~350 rules take more than 10 min to install at ipt | CLOSED | apply | acl-qos/acl-in-sonic.md | COPP に ~350 個のルールを設定すると iptables への適用に 10 分以上かかる制約。大量の COPP ルールは起動時間に大きく影響するため、ル |
| 5277 | sonic-cfggen fails to connect to /var/run/redis/redis.sock | CLOSED | apply | architecture/build-system-improvements.md | sonic-cfggen が `/var/run/redis/redis.sock` への接続に失敗する問題。Redis ソケットファイルが存在しない状態で実行 |
| 5291 | PortChannels may lose IP address after config reload | CLOSED | skip | - | config reload 後に PortChannel の IP が消失する問題 - 重複 |
| 5310 | iccpd service is not running in the image built from latest  | OPEN | apply | system/fast-reboot-flow-improvements-hld.md | iccpd サービスが最新 SONiC mainline ビルドのイメージで実行されていない問題。iccpd は MC-LAG 機能に必要なサービスで、dock |
| 5319 | shutdown the portchannel,but the portchannel member'Oper sta | OPEN | skip | - | PortChannel シャットダウン後もメンバーポートの oper status が変化しない |
| 5331 | [sonic-frr ][grpc compile error] it reports error when enabl | OPEN | skip | - | sonic-frr grpc コンパイルエラー - ビルド問題 |
| 5347 | Interface state is 'down' and not going up when adding and r | CLOSED | apply | switching/sonic-ip-lag-incremental-update.md | インターフェースを追加・削除した後にインターフェース状態が down のままになる問題。`config interface startup <ifname>`  |
| 5377 | [ZTP] "show ztp status" command requires root privileges to  | CLOSED | skip | - | ZTP show コマンドに root 権限が必要 - 権限問題 |
| 5390 | Layer 2 portchannel ping fails | OPEN | skip | - | L2 portchannel での ping 失敗 - 設定問題 |
| 5395 | 【201911】Mgmt IP in show lldp neighbors is wrong, what should | CLOSED | skip | - | LLDP neighbors の mgmt IP 表示問題 - 201911 固有 |
| 5396 | 【201911】ERROR syslog about  mgmt-framework "rest-server ERRO | OPEN | skip | - | mgmt-framework rest-server ログエラー - 201911 固有 |
| 5417 | [DPB] Dynamic Port Breakout feature is not working on the la | CLOSED | apply | architecture/build-system-improvements.md | Dynamic Port Breakout (DPB) 機能が最新 master では動作しない問題。DPB は特定のプラットフォームとカーネルバージョンの組み |
| 5427 | [VLAN] vlan device will down when all member is down | CLOSED | skip | - | VLAN デバイスが全メンバー Down 時に Down になる問題 |
| 5439 | [Warmboot] Error occuring intermittently while executing war | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | warm-boot 実行中に断続的なエラーが発生する問題。`/var/log/warm-reboot` で確認し、失敗箇所を特定すること |
| 5445 | [BGP] FRR docker container goes down after BGP command "aggr | CLOSED | skip | - | FRR docker が BGP aggregate-address コマンドで停止する問題 |
| 5487 | [warm-reboot] warm-reboot aborted with code 1 | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | warm-reboot がコード 1 で中断される問題。warm-reboot スクリプトの各ステージで `set -e` が有効なため、いずれかのサービス確認 |
| 5494 | AS5712-54X operational status | CLOSED | skip | - | AS5712-54X の operational status 問題 - ベンダー固有 |
| 5497 | [mirroring] mirror rule fails to apply after warm reboot  | CLOSED | apply | acl-qos/acl-in-sonic.md | warm reboot 後にミラーリングルールの適用が失敗する問題。ミラー宛先ポートの再設定が warm reboot 後に正しく実行されない場合がある |
| 5502 | [monit/snmp] Tests fail against master image because snmp_su | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | monit/snmp テストが master イメージで失敗する問題。monit が snmp_subagent を監視対象として設定しており、起動タイムアウト |
| 5592 | [SNMP] ifMIB ifName show wrong output | CLOSED | apply | system/platform-monitor-enhancement-design.md | SNMP の ifMIB ifName が間違った値を返す問題。`show interfaces status` の表示名と SNMP の ifName が一致 |
| 5596 | Failed to install SONiC on physical switch | CLOSED | apply | architecture/build-system-improvements.md | 物理スイッチへの SONiC インストールに失敗する問題。ONIE インストーラーのバージョンと SONiC イメージの互換性を確認すること |
| 5598 | ntpd uses incorrect src ip for requests via front panel and  | CLOSED | skip | - | ntpd がフロントパネル経由の要求に誤った src IP を使用する問題 |
| 5603 | There is only IPv6 address(es) in lldp_loc_man_addr in Redis | CLOSED | skip | - | lldp_loc_man_addr に IPv6 アドレスのみが含まれる問題 |
| 5607 | An ACL rule is ignored if this rule contains a key with a lo | CLOSED | skip | - | ACL ルールのキーが小文字の場合に無視される問題 |
| 5663 | Config reload fails sporadically: Job for swss.service cance | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | config reload が断続的に失敗する問題: `Job for swss.service canceled`。`journalctl -u swss`  |
| 5684 | FW tools logging system is broken | CLOSED | skip | - | FW ツールのロギングシステム破損 - 開発問題 |
| 5692 | Build fails on master branch | CLOSED | skip | - | master ブランチのビルド失敗 - CI 問題 |
| 5696 | Issues while parsing port_config.ini | OPEN | skip | - | port_config.ini パース問題 - 設定ファイル形式 |
| 5697 | [lldp] lldpmgrd crashed in test_iface_namingmode | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | lldpmgrd が `test_iface_namingmode` テスト中にクラッシュする問題。インターフェース名前空間の切り替え中に lldpmgrd が |
| 5704 | Orchagent crash in the recent SONiC images | OPEN | apply | internals/dump-utility-for-easy-debugging.md | 最新 SONiC イメージで orchagent がクラッシュする問題。コアダンプが `/var/core/` に生成される。`sudo show techsu |
| 5709 | PortChannel IP addresses are lost after restarting teamd ser | OPEN | skip | - | teamd 再起動後に PortChannel の IP が消失する問題 - 重複 |
| 5732 | Cannot assign DHCP addresses to In-band ports | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | In-band ポートに DHCP アドレスを割り当てられない問題。dhcp_relay が In-band インターフェースをサポートしていない制約 |
| 5738 | DB_MIGRATOR misses FEATURE table during warm upgrade from 20 | CLOSED | skip | - | DB_MIGRATOR が 201811→201912 の FEATURE テーブルマイグレーションを見落とす問題 |
| 5752 | NTP service bind v6 loopback failed and unable to create soc | OPEN | skip | - | NTP サービスが IPv6 ループバックにバインド失敗する問題 |
| 5758 | bulk route API printing not implemented errors when routes a | CLOSED | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | バルクルート API が "not implemented" エラーを出力する問題。一部の SAI 実装ではバルク API をサポートしていないため、orcha |
| 5759 | pmon crashing immediately in latest master image | CLOSED | apply | system/platform-monitor-enhancement-design.md | 最新 master イメージで pmon (Platform Monitor) が即座にクラッシュする問題。プラットフォーム固有のドライバーと pmon の P |
| 5761 | [teamd][warmreboot] LAG flap seen with ioctl SIOCADDMULTI an | OPEN | apply | switching/sonic-ip-lag-incremental-update.md | warm-reboot 中に teamd が SIOCADDMULTI/SIOCDELMULTI ioctl で LAG フラップを引き起こす問題。チームドライ |
| 5795 | [201911][vnet] show vnet [neighbors | routes [all | tunnel]] | CLOSED | apply | overlay/vxlan-sonic.md | 201911 の vnet コマンド (`show vnet neighbors/routes`) がクラッシュする問題。vnet テーブルが空の場合に Non |
| 5812 | SNMP missing expected LLDP data in master image | CLOSED | skip | - | SNMP が master イメージで LLDP データ欠如する問題 |
| 5839 | Multi asic support for config vlan, show vlan and show ip in | CLOSED | skip | - | Multi-ASIC の vlan/ip int コマンドサポート - Enhancement |
| 5853 | [Celestica] PMon error | CLOSED | skip | - | Celestica PMon エラー - ベンダー固有 |
| 5857 | Config reload -y leads to kernel Oops | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | config reload -y でカーネル Oops が発生する問題。特定のカーネルバージョンと config reload の組み合わせで、ネットワークドラ |
| 5858 | [bgpmon] bgpmon error flooding in syslog | CLOSED | skip | - | bgpmon エラーが syslog に大量出力される問題 |
| 5864 | [monit] Report status error for bgpcfgd bgpmon and lldpmgrd | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | monit が bgpcfgd/bgpmon/lldpmgrd のステータスエラーを報告する問題。サービスが動作していても monit の監視設定と実際の状態が |
| 5877 | [Celestica] /sys/class/i2c-adapter/i2c-12/12-0050/eeprom is  | CLOSED | skip | - | Celestica eeprom ファイル欠如 - ベンダー固有 |
| 5880 | rsyslogd display "sendto() error: Network is unreachable" wh | CLOSED | apply | system/sonic-network-time-protocol-ntp-client-configuration.md | management VRF が有効な時に rsyslogd が "sendto() error: Network is unreachable" を出力する問 |
| 5898 | [PFCWD] Packets are dropped with designated queue after PFC  | CLOSED | skip | - | PFCWD テスト後のパケットドロップ問題 - テスト環境 |
| 5928 | Incorrect PVID set for tagged VLAN members | OPEN | apply | switching/switch-port-modes-and-vlan-cli-enhancement.md | タグ付き VLAN メンバーに対して PVID が誤って設定される問題。タグ付きポートに PVID を設定してはいけない。アクセスポートとトランクポートの設定を |
| 5929 | Dynamic BGP_BBR is not working as expected | CLOSED | skip | - | Dynamic BGP_BBR が期待通りに動作しない問題 |
| 5931 | DellEMC : S5232f CPU pool buffer is not added. | CLOSED | skip | - | DellEMC S5232f CPU プールバッファ欠如 - ベンダー固有 |
| 5932 | DellEMC: Need pg_lookup_profile.ini for TD3,TH3 platforms. | CLOSED | skip | - | DellEMC TD3/TH3 pg_lookup_profile.ini 欠如 - ベンダー固有 |
| 5942 | Unable to install sonic_utilities-1.2-py3-none-any.whl with  | CLOSED | skip | - | sonic_utilities-1.2 whl インストール失敗 - パッケージ問題 |
| 5943 | [console] udevprefix.conf not generated after plug-on usb co | CLOSED | skip | - | USB コンソール接続後に udevprefix.conf が生成されない問題 |
| 5944 | [IPv6 BGP] Unable to update routes to eBGP peer | OPEN | skip | - | IPv6 BGP ルートが eBGP ピアに更新されない問題 |
| 5947 | Impossible to do ping between IPs in different VRFs in scena | OPEN | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | 異なる VRF 間のポートを経由した ping が不可能な問題。VRF のルートリークが設定されていない場合、異なる VRF 間の直接通信はできない |
| 5955 | Telemetry services stops working each time I upgrade to the  | CLOSED | apply | architecture/sonic-application-extension-infrastructure.md | テレメトリサービスが SONiC バージョンアップグレード後に停止する問題。gNMI サーバーの証明書やポート設定が新バージョンで変更されている場合がある |
| 5959 | config reload failed on vs image | OPEN | apply | architecture/build-system-improvements.md | VS (Virtual Switch) イメージで config reload が失敗する問題。VS 環境では一部のプラットフォーム固有サービスが利用できないた |
| 5971 | [orchagent] Orchagent keeps flooding ERROR log after teamd r | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | teamd 再起動後に orchagent がエラーログを大量出力する問題。teamd が再起動されると PortChannel メンバーの状態が一時的に不定に |
| 5982 | [build] [debug] [201911] compile failed when enable SONIC_DE | OPEN | apply | architecture/build-system-improvements.md | 201911 で `SONIC_DEBUGGING_ON=y` を設定するとコンパイルが失敗する問題。デバッグビルドオプションは特定のコンパイラバージョンとの互 |
| 5986 | PMON container crashes in latest SONiC images | OPEN | apply | system/platform-monitor-enhancement-design.md | 最新 SONiC イメージで PMON コンテナがクラッシュする問題。プラットフォーム固有の Python プラグインが Python 3 に対応していない場合 |
| 6002 | FDB entry doesn't respect aging configuration | CLOSED | apply | switching/layer-2-forwarding-enhancements.md | FDB エントリのエージング設定が反映されない問題。`config mac aging_time` で設定した値が SAI レベルで正しく適用されていない場合が |
| 6009 | determine-reboot-cause fails due to TypeError seen during du | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | ブート時に `determine-reboot-cause` スクリプトが TypeError で失敗する問題。reboot-cause ファイルのフォーマット |
| 6023 | [DPB] dynamic port breakout configuration not present in CON | CLOSED | skip | - | DPB 設定が config reload 後に CONFIG_DB に残らない問題 |
| 6024 | [DPB] wrong aliases for interfaces | CLOSED | apply | architecture/build-system-improvements.md | DPB 後のインターフェースの alias が誤って設定される問題。Dynamic Port Breakout 実行後は `show interfaces al |
| 6025 | [MGMT] Request: Get yang models from the yang-models dir to  | OPEN | apply | architecture/sonic-application-extension-infrastructure.md | yang-models ディレクトリからの YANG モデル取得のリクエスト。sonic-mgmt-common の YANG モデルは `/usr/model |
| 6027 | [DPB] Dynamic Port Breakout feature is not stable | CLOSED | apply | architecture/build-system-improvements.md | Dynamic Port Breakout (DPB) 機能が不安定な問題。DPB は実行中に複数のサービスを再起動するため、メンテナンスウィンドウでの実行を推 |
| 6028 | [supervisorctl]: status command returns exit code 3 | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | `supervisorctl status` コマンドが exit code 3 を返す問題。すべてのサービスが RUNNING 状態であっても exit co |
| 6036 | Error log found when trying to flush fdb during the test_vne | OPEN | skip | - | vnet_vxlan テスト中の FDB フラッシュエラーログ - テスト問題 |
| 6052 | DHCP relay forwards incorrect DHCP client packet to DHCP ser | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | DHCP relay が不正な DHCP クライアントパケットを DHCP サーバーに転送する問題。クライアントの MAC アドレスと giaddr の整合性チ |
| 6053 | DHCP relay does not forward unicast DHCP packets from client | OPEN | skip | - | DHCP relay がユニキャスト DHCP パケットを転送しない問題 |
| 6068 | [Celestica] Missing 'sonic_platform' for Python 3 | CLOSED | skip | - | Celestica の sonic_platform Python 3 モジュール不足 - ベンダー固有 |
| 6069 | Syncd APPLY_VIEW failure causes Orchagent crash after warm r | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | warm reboot 後の syncd APPLY_VIEW 失敗が orchagent クラッシュを引き起こす問題。syncd の warm-reboot  |
| 6083 | Porting new bcm platform but could not get device-id | OPEN | skip | - | 新 BCM プラットフォームのポーティング問題 - ベンダー固有 |
| 6097 | pmon xcvrd crash on multi asic chassis when all asics are Ba | CLOSED | apply | system/platform-monitor-enhancement-design.md | multi-ASIC chassis で全 ASIC が BackEnd の場合に pmon xcvrd がクラッシュする問題。xcvrd は FrontEnd |
| 6135 | show ip bgp summary fail when configured neighbor through fr | CLOSED | skip | - | FRR 経由で設定したネイバーで show ip bgp summary が失敗する問題 |
| 6138 | [reboot] Fail to start Arista early platform initialization | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | reboot 時に Arista の早期プラットフォーム初期化スクリプト起動が失敗する問題。プラットフォーム固有の初期化スクリプトは `/etc/sonic/p |
| 6146 | bgp 'next-hop-tracking' feature enabled causes port_toggle t | CLOSED | skip | - | BGP next-hop-tracking が port_toggle テストの失敗率を増加させる問題 |
| 6167 | SONiC swss and syncd Exited in brcm when create a subinterfa | OPEN | apply | internals/dump-utility-for-easy-debugging.md | サブインターフェース作成時に BRCM で swss と syncd が終了する問題。サブインターフェースの SAI サポートがプラットフォームによって異なる |
| 6171 | show ip interface CLI support for multi asic | CLOSED | skip | - | Multi-ASIC の show ip interface CLI サポート - Enhancement |
| 6172 | Gearsyncd crash and core observed after continuous warm rebo | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | 継続的な warm reboot 後に gearsyncd がクラッシュしコアが生成される問題 |
| 6240 | IO errors seen during warm reboot causing drop in traffic fr | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | warm reboot 中に IO エラーが発生しサーバーからのトラフィックドロップが発生する問題。warm reboot の移行時間を最小化し、サーバー側でも |
| 6253 | [Syncd failed during boot] syncd#supervisord: syncd /usr/bin | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | ブート時に syncd が共有ライブラリ不足で失敗する問題。syncd の依存ライブラリが正しくインストールされていることを確認すること |
| 6313 | [fdbsyncd] fdbsyncd reports errors when FDB entry is updatin | OPEN | skip | - | fdbsyncd が FDB エントリ更新時にエラーを報告する問題 - 調査中 |
| 6328 | Not sorted interfaces in config_db.json file | CLOSED | apply | architecture/build-system-improvements.md | config_db.json ファイルのインターフェースがソートされていない問題。設定ファイルの可読性のため、sort_keys=True で JSON を整形 |
| 6343 | [Platform system health] ASIC key is not handled properly in | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | Platform system health において ASIC キーが適切に処理されない問題。`show system-health detail` の AS |
| 6381 | [BRCM Th3 Z9332]:  packets are not dropped for class e addre | CLOSED | skip | - | BRCM Th3 Z9332 Class E アドレスのパケットドロップ不正 - ベンダー固有 |
| 6392 | [BRCM Th3 Z9332]: When Ser is injected to a memory , the cor | OPEN | apply | system/critical-resource-monitoring-in-sonic.md | BRCM Th3 Z9332 で SER (Single Error Recovery) が注入されたメモリの修正システムが正しく動作しない問題。ECC エラー |
| 6399 | performance testing VS docker image on ARM (Help wanted) | OPEN | apply | architecture/build-system-improvements.md | ARM アーキテクチャの VS docker イメージでのパフォーマンステスト。ARM ホストでの SONiC テストにはネイティブ ARM ビルドが必要 |
| 6401 | sudo missing from VS docker image | OPEN | skip | - | VS docker イメージに sudo が不足している問題 |
| 6413 | Code optimization cannot be disabled from make command line | OPEN | apply | architecture/build-system-improvements.md | make コマンドラインからコードの最適化を無効化できない問題。`SONIC_DEBUGGING_ON=y` オプションでデバッグビルドを有効化できるが、最適化 |
| 6430 | PortChannel mtu change fails with CLI | OPEN | skip | - | CLI での PortChannel MTU 変更失敗 - 設定問題 |
| 6459 | orchagent crash observed when remove SAI_OBJECT_TYPE_PORT is | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | `SAI_OBJECT_TYPE_PORT` の削除をサポートしない SAI 実装で orchagent がクラッシュする問題。port deletion は全 |
| 6463 | Command not working "show system-health detail" | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | `show system-health detail` コマンドが動作しない問題。`sudo systemctl status system-health` で |
| 6466 | [KVM][warm reboot] syncd crashes during shutdown with double | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | KVM での warm reboot 中に syncd が double-free-corruption でクラッシュする問題。仮想環境では warm-rebo |
| 6486 | Failed to unbreak out a port | CLOSED | skip | - | ポートのブレークアウト解除失敗 - 設定問題 |
| 6495 | Not able to set FEC parameter by default from hwsku.json | CLOSED | apply | system/platform-monitor-enhancement-design.md | hwsku.json から FEC パラメータがデフォルト設定できない問題。FEC の設定は `config interface fec` コマンドで明示的に行 |
| 6498 | config load_minigraph fails due to Redis BGSAVE already in p | CLOSED | apply | architecture/build-system-improvements.md | config load_minigraph が "Redis BGSAVE already in progress" で失敗する問題。前のセーブが完了してから実 |
| 6499 | [DPB] XCVRD not able to fetch the new port SFP info after pe | CLOSED | apply | system/platform-monitor-enhancement-design.md | DPB 実行後に xcvrd が新しいポートの SFP 情報を取得できない問題。DPB 実行後に xcvrd の再起動が必要な場合がある |
| 6503 | [201911][teamd] Interface PortChannel not getting IP assigne | CLOSED | skip | - | 大規模設定で PortChannel の IP が割り当てられない問題 - 201911 固有 |
| 6509 | [KVM][warm reboot] syncd crash when getting virtual router I | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | KVM での warm reboot 中に syncd が仮想ルーター ID 取得時にクラッシュする問題 |
| 6516 | CMIS 4.0 QSFP-DD EEPROM decode fails | OPEN | apply | system/platform-monitor-enhancement-design.md | CMIS 4.0 QSFP-DD の EEPROM デコードが失敗する問題。CMIS 4.0 対応の xcvrd バージョンが必要 |
| 6563 | Not supported attribute SAI_SWITCH_ATTR_AVAILABLE_IPMC_ENTRY | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | `SAI_SWITCH_ATTR_AVAILABLE_IPMC_ENTRY` 属性がサポートされていない SAI 実装でエラーが発生する問題。CRM での IP |
| 6569 | master->master warm reboot fails because of pending tasks in | CLOSED | apply | system/fast-reboot-flow-improvements-hld.md | master→master warm reboot が pending tasks キューのため失敗する問題。warm-reboot 前にキューのタスクが完了す |
| 6622 | syncd crash on master RPC image | CLOSED | apply | internals/dump-utility-for-easy-debugging.md | syncd が master RPC イメージでクラッシュする問題。RPC ビルドの syncd は通常のビルドとは異なるライブラリセットを使用する |
| 6626 | Vrfmgrd crash when enable default vrf | OPEN | apply | routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md | デフォルト VRF を有効化すると vrfmgrd がクラッシュする問題。VRF の有効化/無効化は動的には行えず、起動時設定で行う必要がある |
| 6630 | [DPB] Breakout of interface failed with it is part of PortCh | CLOSED | apply | switching/sonic-ip-lag-incremental-update.md | PortChannel のメンバーとして設定されているインターフェースをブレークアウトしようとするとエラーになる制約。DPB 実行前に PortChannel  |
| 6641 | Command not working "show system-health" | CLOSED | apply | system/critical-resource-monitoring-in-sonic.md | `show system-health` コマンドが動作しない問題。`sudo systemctl status system-health` で確認し、必要に |
| 6645 | [DPB] Different configuration section for interface with app | CLOSED | apply | architecture/build-system-improvements.md | DPB でインターフェースの設定セクションが適用済みと未適用で異なる問題。DPB 後の設定反映状態は `show interfaces breakout` で確 |
| 6657 | [Mellanox] vports creation on Mellanox Spectrum didn't take  | OPEN | skip | - | Mellanox Spectrum での vports 作成問題 - ベンダー固有 |
| 6659 | DB migration does not account mandatory entries in new init_ | CLOSED | apply | architecture/build-system-improvements.md | DB migrator が新しい init_cfg.json/FEATURE テーブルの必須エントリを考慮しない問題。バージョンアップグレード後は FEATUR |
