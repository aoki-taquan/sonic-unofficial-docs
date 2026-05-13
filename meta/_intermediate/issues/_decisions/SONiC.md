# sonic-net/SONiC Issue AI 判定結果

リポジトリ: sonic-net/SONiC  
入力: 85 issues  
判定日: 2026-05-13

## 判定基準

- **apply**: バグの実装上の落とし穴 / HLD 不足 / 仕様変更 / 既知の制限 / 有効な workaround を含む
- **skip**: 単なる質問・重複・運営系・ハードウェア固有・古すぎて現状不明・feature tracking のみ

---

## 判定一覧

| # | タイトル | state | 判定 | 反映先 | 反映内容要約 |
|---|---------|-------|------|--------|-------------|
| 2240 | pmon/thermalctld optimizations | OPEN | apply | `docs/system/transceiver-and-sensor-monitoring-hld.md` | thermalctld が xcvrd 経由で取得済みのトランシーバー温度を二重ポーリングしていた問題。sonic-platform-daemons PR#808 で重複排除。`show platform temperature` コマンドへの影響なし |
| 2169 | Container upgrades to Trixie | OPEN | skip | - | リリース運用 tracking。C++ 標準は 14 を維持（17/20 は不採用方針）。既知の制限として記録不要 |
| 1908 | Dell S5248F-ON hardware not recognized | CLOSED | skip | - | プラットフォーム固有の回帰バグ。buildimage#21656 に移管済み。一般知識として価値低 |
| 1738 | Failed to build virtual switch with SONIC_BUILD_JOBS=4 | OPEN | apply | `docs/architecture/build-system-improvements.md` | `SONIC_BUILD_JOBS=N` (N>1) 並列ビルド時に最終ターゲット間の依存関係が未解決になり失敗するケースあり。回避策: 並列度を下げるか 1 で再試行 |
| 1575 | Mitigating DHCP Starvation Attacks | OPEN | skip | - | HLD PR#1651 merged で feature tracking 終了。docs に HLD 済みページあり |
| 1565 | Upgrade to FRR 10.0.1 | CLOSED | apply | `docs/routing/detailed-steps-to-upgrade-frr-in-sonic.md` | FRR アップグレードには合意済みプロセスあり (#1438)。SONiC はバージョン x.y.z を preferred とし、FRR アップグレード担当は各ベンダーが輪番で担当。FRR 9.1 は Broadcom が 202411 サイクルで担当 |
| 1560 | Arista 7050QX-32 boots then crashes | OPEN | apply | `docs/platform/index.md` (新セクション) | Arista 7050QX-32 で `UnknownPlatformError` によるクラッシュが報告されており未解決。FIPS 対応で symcrypt-openssl が導入された際に pshufb SSE3 命令で失敗するケースあり |
| 1542 | Internal drop counter monitoring | CLOSED | skip | - | HLD PR#1912 merged。orchagent から Lua スクリプトに移行済み。既存ページあり |
| 1539 | Power over Ethernet (PoE) | CLOSED | skip | - | HLD PR#1631 merged。feature tracking 終了 |
| 1520 | Fault Management (Analysis and Handling) | OPEN | skip | - | HLD 策定中の feature tracking。内容不確定 |
| 1512 | Create SONiC AI workgroup | OPEN | skip | - | 運営・ワーキンググループ設立。技術情報なし |
| 1407 | TACACS Passkey encryption feature | OPEN | skip | - | HLD・コード PR が進行中。既存ページ `tacacs-passkey-encryption.md` あり |
| 1401 | UEFI key management secure boot | CLOSED | skip | - | HLD PR#1451 merged。feature tracking 終了 |
| 1253 | IPv6 RS & NS packets loop in L2 MC-LAG | CLOSED | apply | `docs/switching/mclag-enhancements.md` | L2 MC-LAG 環境で ICMPv6 RS/NS (type 133/135) がループを形成する既知問題。回避策: `ebtables -A FORWARD -p 802_1Q --vlan-encap IPv6 -j DROP` を適用 |
| 1192 | TWAMP Light | OPEN | skip | - | HLD PR#1320 merged。既存ページ `twamp-light-hld.md` あり |
| 1135 | Mac-based Vlan Assignment | OPEN | skip | - | HLD 未作成。バックログ状態 |
| 1065 | Installation: Out of memory - any workarounds? | CLOSED | apply | `docs/architecture/build-system-improvements.md` | 古い低スペックスイッチ (2GB flash/RAM) への SONiC インストール時 OOM 問題。回避策: 201811 等の古いイメージ使用、または SWAP 作成。master ブランチのイメージサイズ増大により古いハードウェアでの動作は非保証 |
| 1021 | teamd crashes until max restarts reached | OPEN | apply | `docs/switching/index.md` | teamd が一定回数再起動失敗後に最大再起動数に達してクラッシュする既知問題。根本原因は未解決。要調査 |
| 993 | Does sonic has a gui or web? | OPEN | skip | - | 質問。REST/gNMI 等の管理 I/F 解説は別ページにあり |
| 968 | Adding support for Dell EMC S4048-ON | OPEN | skip | - | プラットフォームサポート要望。技術的落とし穴なし |
| 947 | Failing to retrieve chassis data for Seastone-DX010 | OPEN | apply | `docs/platform/index.md` | Celestica Seastone DX-010 で 202111 以降 PSU/FAN status 取得失敗の回帰バグ。202106 では正常動作。`show system-health summary` も失敗 |
| 907 | TD3: PCIe firmware was not loaded | CLOSED | skip | - | プラットフォーム固有の PCIe 初期化順序問題。解決策不明 |
| 865 | Access Denied when try to download the image | CLOSED | apply | `docs/architecture/build-system-improvements.md` | ビルド成果物ダウンロード先が変更済み。旧: sonic-jenkins.westus2.cloudapp.azure.com → 新: sonic-build.azurewebsites.net/ui/sonic/pipelines |
| 841 | PINS Upstream Tracking for MVP | OPEN | skip | - | PINS feature tracking。HLD PR進行中 |
| 797 | Processes inside Docker containers are not running | OPEN | skip | - | プラットフォーム固有 (Arista 7170-32C vs 32CD 混同) + 設定ミス。一般的知識として価値低 |
| 790 | MACSec ports as member of LAG | OPEN | apply | `docs/switching/macsec-sonic-high-level-design-document.md` | MACsec と LAG の組み合わせ制約: (1) ハイブリッド LAG (MACsec 有効/無効ポート混在) は初期フェーズ非サポート、(2) MACsec を LAG インターフェースに直接適用する場合は内部でメンバーポートに変換が必要 |
| 781 | Sonic-cli Issue (tmp/klish.fifo) | OPEN | apply | `docs/management/sonic-nos-configuration-methods.md` | klish ベース CLI (`sonic-cli`) で `/tmp/klish.fifo` エラーが発生するケースあり。Python2/3 混在が原因の一つ。master で未解決 |
| 775 | How I push CLI commands to a switch using REST? | CLOSED | skip | - | 質問。REST API の範囲説明のみ。`show version` 等は REST ではなく Python サブプロセス経由 |
| 729 | Rif Counters can not work when removing one router interface | OPEN | apply | `docs/routing/router-interface-counters-in-sonic.md` | RIF カウンター: IP アドレス削除→再追加後にカウンターが機能しない問題。201911 で再現、master/202012 では修正済み。201911 向け回避策: `counterpoll rif interval 3000`（1秒超に設定）後、設定インターバル経過後にクエリ |
| 714 | subinterface (subport) Error \| switch crashing | CLOSED | apply | `docs/platform/index.md` | syncd で `saiGetMacAddress: failed to get mac address: SAI_STATUS_ITEM_NOT_FOUND` エラーでクラッシュ。buildimage#6167 参照 |
| 592 | Arista 7050QX-32 boots then crashes (something wrong) | OPEN | apply | `docs/platform/index.md` | Arista 7050QX-32 の 2GB flash 制限: docker を RAM (tmpfs) 展開するが容量不足でインストール失敗。回避策: `boot0` の `flash_size` 判定を無効化し外部ストレージから初回ブート、または 16GB 以上の DOM/USB に換装。FIPS 対応 symcrypt-openssl の pshufb SSE3 命令問題も複合要因 |
| 562 | Interfaces not seen on AS5812-54X | OPEN | skip | - | プラットフォーム固有。解決策なし |
| 549 | Issue with AS9716-32D, cant locate SYSEEPROM | OPEN | skip | - | プラットフォーム固有 |
| 546 | Interfaces not seen on AS5812-54T | OPEN | skip | - | プラットフォーム固有 |
| 492 | AS7816-64X can't setup breakout cable | OPEN | skip | - | プラットフォーム固有 |
| 491 | AS7816-64X untagged VLAN issue | OPEN | skip | - | プラットフォーム固有 |
| 462 | Can't get SONiC running on AG9064 | OPEN | skip | - | プラットフォーム固有 |
| 458 | Orchagent crash on latest SONiC images | OPEN | apply | `docs/system/sonic-system-health-monitor-high-level-design.md` | orchagent が最新イメージでクラッシュするケースあり。複数のプラットフォームで確認。起動順序やデータベース初期化タイミングが原因の可能性 |
| 442 | How to enable ospfd daemon (OSPF) | OPEN | apply | `docs/routing/static-ip-route-configuration.md` | FRR の ospf/isis は vtysh 経由で設定可能。ただし `docker_routing_config_mode: split` を設定しないと再起動後に設定が消える。split モードの設定方法: `config_db.json` の `DEVICE_METADATA.localhost` に追加 |
| 417 | Compile error while building debian stretch | CLOSED | skip | - | 古いビルド環境 (stretch) の問題。現在は bookworm/trixie |
| 405 | make configure PLATFORM=broadcom fails | CLOSED | skip | - | 古いビルド問題 |
| 387 | Pre-ARP support for static route config | CLOSED | skip | - | feature tracking 終了 |
| 384 | Celestica Seastone DX-010 no-carrier on 100gig | OPEN | apply | `docs/platform/media-based-port-settings-in-sonic.md` | Seastone DX-010 の 100G ポートでリンクが上がらない場合の回避策: FEC を RS に変更 (`portconfig -p EthernetX -s 100000 -f rs`)。一部 NIC (CX4) で有効 |
| 340 | Portchannel member is deleted if it is added to vlan | CLOSED | apply | `docs/switching/switch-port-modes-and-vlan-cli-enhancement.md` | ポートチャネルのメンバーポートを直接 VLAN に追加すると削除される。正しい手順: `config vlan member add <vid> PortChannel<N>` (大文字 P・C 注意) でポートチャネル自体を VLAN メンバーに追加 |
| 323 | Why the vlan cli always add member port to cfg_db VLAN table field 'members'? | OPEN | apply | `docs/switching/switch-port-modes-and-vlan-cli-enhancement.md` | `config vlan member add` が `VLAN_MEMBER_TABLE` に加えて `VLAN_TABLE\|members` フィールドにも書き込む (後方互換フィールド)。タグ付きメンバーとして追加したつもりでもタグなし扱いになるバグあり (PR#768 で修正) |
| 307 | Is there any provision to configure FDB aging time? | OPEN | apply | `docs/switching/layer-2-forwarding-enhancements.md` | FDB エイジングタイム: CLI では設定不可 (古いバージョン)。回避策: `/usr/share/sonic/templates/switch.json.j2` の `SWITCH_TABLE:switch` に `fdb_aging_time` を秒単位で指定。デフォルト値はハードウェアデフォルト (0 または 300) |
| 296 | bcmcmd command not working on AG9032V1 | CLOSED | skip | - | ONIE 旧バージョンで解決。現在は ONIE 更新で解消 |
| 295 | Show command is not working on AG9032V1 | CLOSED | skip | - | ONIE 旧バージョンで解決 |
| 269 | ACL's default deny/drop action is not working | CLOSED | apply | `docs/acl-qos/acl-in-sonic.md` | ACL のデフォルト deny は自動では機能しない。JSON 設定では明示的に最低優先度 (最大 PRIORITY 値) で `IP_TYPE: ipv4any` の DROP ルールを追加する必要がある |
| 268 | KeyError: 'alias' after shut/unshut interface | CLOSED | skip | - | 修正済み (PR#424)。無効インターフェース名で config コマンドを実行すると PORT_TABLE に不正エントリが追加されるバグも修正 |
| 265 | Non-Mellanox optics PLUGGED-ERR state | CLOSED | apply | `docs/platform/sfputil-add-the-ability-to-read-write-any-byte-from-eerpom-both-by-page-and-offset.md` | Mellanox スイッチで非 Mellanox 光トランシーバーが `PLUGGED-ERR` になる問題。Mellanox ファームウェアがベンダーを制限している場合あり。回避策: Mellanox サポートに連絡し、ベンダー制限解除ファームウェアを取得 (非公開ファームウェア) |
| 255 | Error changing interface status | CLOSED | skip | - | 古いイメージ問題。現在の CLI コマンド形式は `config interface <intf> shutdown/startup` |
| 250 | Restore configuration issued via vtysh | OPEN | apply | `docs/routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md` | FRR (vtysh) で設定した内容は再起動後にリセットされる (デフォルト動作)。恒久化するには `config_db.json` の `DEVICE_METADATA.localhost` に `"docker_routing_config_mode": "split"` を追加 |
| 249 | Configure static mac (FDB) address | OPEN | apply | `docs/switching/layer-2-forwarding-enhancements.md` | 静的 FDB エントリの設定方法: JSON ファイル (`FDB_TABLE:VlanX:mac-addr` 形式) を作成し `swssconfig ./fdb.json` で `swss` コンテナ内から適用。前提条件: 対象インターフェースが UP かつ VLAN メンバー。設定は再起動後に消える (非永続) |
| 241 | How to set up a static route | CLOSED | skip | - | 質問/FAQ。現在のドキュメントで対応済み |
| 238 | How to check ping at Layer 3 | CLOSED | skip | - | 質問。設定ミスで自己解決 |
| 225 | ERROR: MIBUpdater.start() caught unexpected exception | OPEN | apply | `docs/system/sonic-snmp-table-schema-proposal.md` | SNMP エージェントが `COUNTERS_QUEUE_NAME_MAP` または `COUNTERS_PORT_NAME_MAP` が Redis に存在しない場合に例外。原因: 起動タイミング (初期化遅延)。回避策: `sudo systemctl restart snmp` で SNMP Docker を再起動 |
| 219 | Document on commands that can change settings | CLOSED | skip | - | 質問。CLI リファレンスで対応済み |
| 218 | Use monotonic time or modify process.py | CLOSED | skip | - | 内部ディスカッション。技術的落とし穴なし |
| 194 | PortChannel goes DOWN when one link breaks | CLOSED | apply | `docs/switching/sonic-ip-lag-incremental-update.md` | LACP PortChannel でメンバーリンクの一本が切断されると PortChannel 全体が DOWN になるケース報告。実装の既知の挙動として要確認 |
| 192 | ARP entries not restored during fast reboot | CLOSED | apply | `docs/system/fast-reboot-flow-improvements-hld.md` | fast reboot 後に ARP エントリが Linux カーネルに復元されない既知の問題。`question` ラベル付き |
| 184 | What does SONiC do with STP messages? | CLOSED | apply | `docs/switching/multiple-spanning-tree-protocol.md` | SONiC はデフォルトで STP パケットを CPU にトラップせず、STP プロトコルをサポートしない (アクセス層向け設計ではない)。STP が必要な場合は MSTP 実装 (HLD あり) を参照 |
| 173 | sfputil missing on Wedge 100BF-65X | OPEN | skip | - | Barefoot プラットフォーム固有。`platform-barefoot` ラベル |
| 169 | Unable to boot on Arista 7050QX-32S | CLOSED | skip | - | プラットフォーム固有ブート問題 |
| 163 | Roadmap Update | OPEN | skip | - | ロードマップ管理。技術情報なし |
| 153 | Ports not coming up on AS5712-54x | CLOSED | skip | - | TD2 チップ識別問題。HEAD.518 で修正済み |
| 149 | Failed to run rc.local, bcmcmd on AS5712 | OPEN | skip | - | プラットフォーム固有。PR#1380 で修正済み |
| 145 | Executing config load_minigraph got stuck | CLOSED | apply | `docs/management/sonic-nos-configuration-methods.md` | `config load_minigraph` が失敗すると ConfigDB が空になりロックされる。回避策: `redis-cli -n 4 SET CONFIG_DB_INITIALIZED true` を実行してから再試行。minigraph の hostname は全箇所で一致させる必要がある |
| 139 | Cannot use 10GBase-SR GBIC on EdgeCore AS5712-54X | OPEN | apply | `docs/platform/media-based-port-settings-in-sonic.md` | 一部プラットフォームで Fiber トランシーバーの TX 信号が有効化されない。回避策: `bcmcmd "port xe interface=sr"` でインターフェースタイプを SR に変更後、`accton_as5712_util.py set sfp <port> 0` で TX を有効化。将来的にはトランシーバー挿入時のフックで自動化予定 |
| 135 | Where should I put the config.bcm file? | OPEN | apply | `docs/platform/sonic-dynamic-gearbox-tuning-design-plan.md` | `config.bcm` の配置方法: `libsaibcm_*.deb` に含まれる。カスタマイズ方法: dpkg で展開・修正・再パックか、syncd コンテナ内の `/etc/bcm/` を直接置換して swss 再起動 |
| 123 | Sonic brcm image not loading | CLOSED | skip | - | Jenkins ビルド環境問題。現在は解決済み |
| 118 | Dell S6100: snmpwalk for IF-MIB and IP-MIB fails | OPEN | apply | `docs/system/sonic-snmp-table-schema-proposal.md` | SNMP が初期化遅延で `COUNTERS_PORT_NAME_MAP` が Redis に存在しない場合に IF-MIB が失敗。回避策: SNMP Docker 再起動 (`sudo systemctl restart snmp`)。IP-MIB は部分実装のみ (full IP-MIB は未対応) |
| 116 | Dell: LLDP messages in S6100 | CLOSED | skip | - | `/etc/lldp.conf` 設定で解決。プラットフォーム固有 |
| 109 | arp entry not learned on vlan subinterface | OPEN | apply | `docs/routing/router-interface-counters-in-sonic.md` | VLAN サブインターフェース (dot1q tagged) での ARP 学習問題。Mellanox では L3 VLAN インターフェースが ASIC に同期されない問題あり。デバッグ: `bcmcmd 'l2 show'` で VLAN/物理 I/F マッピング確認、`/var/log/swss/sairedis.rec` でエラー確認 |
| 87 | arp entry not learned on portchannel interface | OPEN | apply | `docs/switching/sonic-ip-lag-incremental-update.md` | PortChannel メンバーポートの一つが異なる MAC アドレスを持つ場合 ARP が不完全になる (0x0 フラグ)。原因: SAI ホストインターフェースの MAC アドレス割り当てバグ。暫定: `arp -s` で静的 ARP を手動追加 |
| 84 | libsai segfault on new Broadcom platform | CLOSED | skip | - | buildimage#5f8e495 で修正済み |
| 82 | Frequently write DB causes memory leak | CLOSED | apply | `docs/system/sonic-system-health-monitor-high-level-design.md` | Redis への頻繁な書き込みでメモリが増加し続ける問題。sonic-py-swsssdk のメモリリーク修正 (commit 4cf7a59) で解消 |
| 78 | How to copy SONiC to local git server | CLOSED | skip | - | 質問。技術情報なし |
| 77 | MTU mismatch between control plane netdev and asic | CLOSED | apply | `docs/platform/index.md` | Mellanox MSN2700 で control plane (netdev) と ASIC 間の MTU 不一致が発生。`bug` ラベル。詳細な root cause はコメントで解析中 |
| 76 | Unicast arp request won't get up to CPU | OPEN | apply | `docs/routing/router-interface-counters-in-sonic.md` | ユニキャスト ARP リクエストが CPU に届かない問題。`question` ラベルだが実装上の制約の可能性 |
| 72 | How to add a device on SONiC's supported list | CLOSED | skip | - | 質問。porting guide 参照で対応 |
| 57 | Investigating dhcp relay option 82 | CLOSED | apply | `docs/architecture/dhcpv4-relay-agent.md` | DHCP relay Option 82 の circuit-id: isc-dhcp-relay はデフォルトで VLAN インターフェース名を記録。物理ポート名の記録はサポートされていない (isc-dhcp-relay の制限)。ソースインターフェースは IP アドレスを持たない場合は使用不可 |
| 46 | Orchagent crashes on start | CLOSED | apply | `docs/system/sonic-system-health-monitor-high-level-design.md` | orchagent 起動時クラッシュ: syncd の hard reinit が DB クリア前に実行される問題。`syncd.service` に `After=swss.service` を追加で対処 (現在は修正済み) |
| 40 | teamd cannot re-create lag after netdev re-creation | OPEN | apply | `docs/switching/sonic-ip-lag-incremental-update.md` | teamd が netdev 再作成後に LAG を再構築できない問題。`--no-ports` オプションでポートなしで起動し、その後 `teamdctl` でポートを追加することで回避可能。swss/teamd Docker 再起動時に teamsyncd がクラッシュする別問題もあり |
| 4 | Repository not opened | CLOSED | skip | - | 2016 年のリポジトリ公開初期の問題 |

---

## apply 対象一覧 (24 件)

1. #2240 → `docs/system/transceiver-and-sensor-monitoring-hld.md`
2. #1738 → `docs/architecture/build-system-improvements.md`
3. #1565 → `docs/routing/detailed-steps-to-upgrade-frr-in-sonic.md`
4. #1253 → `docs/switching/mclag-enhancements.md`
5. #947 → `docs/platform/index.md`（platform known issues セクション）
6. #790 → `docs/switching/macsec-sonic-high-level-design-document.md`
7. #781 → `docs/management/sonic-nos-configuration-methods.md`
8. #729 → `docs/routing/router-interface-counters-in-sonic.md`
9. #384 → `docs/platform/media-based-port-settings-in-sonic.md`
10. #340 → `docs/switching/switch-port-modes-and-vlan-cli-enhancement.md`
11. #323 → `docs/switching/switch-port-modes-and-vlan-cli-enhancement.md`
12. #307 → `docs/switching/layer-2-forwarding-enhancements.md`
13. #269 → `docs/acl-qos/acl-in-sonic.md`
14. #265 → `docs/platform/sfputil-add-the-ability-to-read-write-any-byte-from-eerpom-both-by-page-and-offset.md`
15. #250 → `docs/routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md`
16. #249 → `docs/switching/layer-2-forwarding-enhancements.md`
17. #225 → `docs/system/sonic-snmp-table-schema-proposal.md`
18. #192 → `docs/system/fast-reboot-flow-improvements-hld.md`
19. #184 → `docs/switching/multiple-spanning-tree-protocol.md`
20. #145 → `docs/management/sonic-nos-configuration-methods.md`
21. #139 → `docs/platform/media-based-port-settings-in-sonic.md`
22. #57 → `docs/architecture/dhcpv4-relay-agent.md`
23. #87 → `docs/switching/sonic-ip-lag-incremental-update.md`
24. #442 → `docs/routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md`

## skip 対象 (61 件)

上記以外の全 issue。主な skip 理由:
- プラットフォーム固有 (Arista/Edgecore/Dell 特定モデル)
- feature tracking のみ (HLD merged 済み)
- 単純な質問・FAQ
- 古いバージョン固有で現状不明
- 運営・ワーキンググループ
