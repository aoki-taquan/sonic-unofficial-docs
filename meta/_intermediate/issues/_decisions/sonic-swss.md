# sonic-net/sonic-swss Issues Decision Log

生成日: 2026-05-13
対象: meta/_intermediate/issues/sonic-net_sonic-swss.json (41 issues)

## 判定基準

- `apply`: docs に反映する価値ある技術情報（バグ・制限・workaround）
- `skip-ci`: CI/build/test インフラ問題のみ、ドキュメント価値なし
- `skip-question`: 質問形式・回答なし
- `skip-duplicate`: 他 issue と実質重複
- `skip-old`: 古すぎて master との乖離が大きく信頼性なし

---

## 全 41 件判定

| # | Issue | State | 判定 | 対象ページ | 理由 |
|---|-------|-------|------|------------|------|
| 4406 | [handleSai] Prioritize route programming over ACL ACE retries on SAI_STATUS_INSUFFICIENT_RESOURCES | CLOSED | **apply** | acl-in-sonic.md | SAI_STATUS_INSUFFICIENT_RESOURCES 時にルートプログラミングが ACL ACE リトライより優先されない設計上の制限。既知の落とし穴 |
| 4396 | Azure Build got stuck in "Install dependencies" | CLOSED | skip-ci | - | CI インフラ問題 |
| 4247 | Azure Pipeline failing in all Open PRs | CLOSED | skip-ci | - | CI インフラ問題 |
| 3863 | VStest fails with install dependencies | CLOSED | skip-ci | - | CI インフラ問題 |
| 3688 | vstest failures due to icmp session offload test cases | OPEN | skip-ci | - | テスト安定性問題 |
| 3650 | vTest Failures in multiple SWSS PRs | CLOSED | skip-ci | - | CI インフラ問題 |
| 3541 | dash is not have has_vnet function | OPEN | skip-ci | - | DASH 開発中の API 未実装（build 問題）、docs 反映不可 |
| 3539 | no dash_api/appliance.pb.h file | CLOSED | skip-ci | - | build 成果物欠落の問題 |
| 3259 | TD4 - swss not coming up with latest code | OPEN | skip-question | - | 特定ベンダープラットフォーム問題、解決策なし |
| 3270 | [202405][route] EntityBulker.flush remove entries failed SAI_STATUS_ITEM_NOT_FOUND | OPEN | **apply** | routing/bgp-route-install-error-handling.md | EntityBulker が存在しないエントリを削除しようとして SAI_STATUS_ITEM_NOT_FOUND になる既知バグ |
| 3069 | DASH: configuration reordering leads to incorrect ACL configuration | CLOSED | **apply** | overlay/sonic-dash-hld.md | DASH ACL 設定の順序依存性バグ（設定順が変わると ACL が誤設定される） |
| 3051 | [bfdorch] needs to query SAI_BFD_SESSION_ATTR_PORT before programming | OPEN | **apply** | routing/bfd-hw-offload.md | BfdOrch が SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID=False 時に SAI_BFD_SESSION_ATTR_PORT を必須で渡さない実装バグ |
| 2829 | Tunnel Term Attributes validation MP2P and MP2MP types | OPEN | **apply** | overlay/nvgre-tunnel-in-sonic.md / vxlan-sonic.md | SAI トンネルターム DST_IP/SRC_IP が MP2P/MP2MP タイプで必須属性になり orchagent が対応できていない |
| 2602 | Add mclag bridgeport support for Innovium platform | OPEN | skip-question | - | 特定ベンダープラットフォーム機能リクエスト、SAI Isolation Group 非対応プラットフォームの制限 |
| 2573 | [VS] fabric testcase failing | CLOSED | skip-ci | - | VS テスト問題 |
| 2570 | [VS] Mirror tests failing | CLOSED | skip-ci | - | VS テスト問題 |
| 2365 | [VS] All subport tests consistently failing | CLOSED | skip-ci | - | VS テスト問題 |
| 2231 | Don't query buffer profile attributes before APPLY_VIEW | OPEN | **apply** | internals/zmq-producer-consumer-state-table-design.md または swss-schema.md | APPLY_VIEW 前に buffer profile 属性を照会すると zero-buffer pool との相互作用で問題が発生 |
| 2204 | [ACL] IN_PORTS support missing for TABLE_TYPE_MIRRORV6 | CLOSED | **apply** | acl-qos/egress-mirroring-support-and-acl-action-capability-check.md | MirrorV6 ACL テーブルで IN_PORTS マッチフィールドが未サポート |
| 2014 | Couldn't enable zmq for orchagent in docker-sonic-vs | OPEN | skip-ci | - | VS 環境固有の ZMQ 設定問題 |
| 1809 | [VS test stability] Chassis test | OPEN | skip-ci | - | VS テスト安定性問題 |
| 1812 | A bug for using KEY_SET method to deliver message to swss & orchagent | OPEN | **apply** | internals/swss-schema.md | ConsumerStateTable KEY_SET メソッドで DEL メッセージが pops で取得できない設計上の問題 |
| 1684 | COPP trap id map for DHCP | OPEN | **apply** | acl-qos/copp-neighbor-miss-trap-and-enhancements.md | SAI に DHCP_L2 / DHCPv6_L2 トラップが追加されたが COPP トラップ ID マップが未対応 |
| 1574 | orchagent reporting error 'Unknown attribute snat_entry_threshold_type' | CLOSED | **apply** | architecture/nat-in-sonic.md | snat_entry_threshold_type 属性が CRM 改修時に一時的に破損、master では修正済みだが設定互換性に注意 |
| 1400 | [NAT] SNAT does not perform translation for ICMP packet in static NAT/NAPT | CLOSED | **apply** | architecture/nat-in-sonic.md | 静的 NAT/NAPT 環境での ICMP パケット SNAT 非変換バグ（再現不可として close されたが ICMP NAT の挙動確認手順が有用） |
| 1367 | Unable to execute vs test | CLOSED | skip-ci | - | VS 実行環境問題 |
| 1351 | [NAT] ICMP reply packet cannot forward in dynamic NAPT | CLOSED | **apply** | architecture/nat-in-sonic.md | ICMP dynamic NAPT での reply パケット転送問題（ICMP は TCP ハンドシェイク不要で動作するが Identifier フィールドで追跡される） |
| 1234 | NatOrch: No DNAT_POOL object to trigger DNAT_MISS trap | CLOSED | **apply** | architecture/nat-in-sonic.md | DNAT_POOL オブジェクト未作成時に DNAT_MISS trap がトリガーされない NatOrch バグ（修正PR確認要） |
| 1074 | Mellanox platform does not identified correctly | OPEN | skip-old | - | 2019年の旧プラットフォーム識別問題、現行 master と乖離 |
| 961 | [vlan] after rebooting, untagged member cannot link up when port has IP entry | OPEN | **apply** | switching/switch-port-modes-and-vlan-cli-enhancement.md | ポートに IP アドレス設定後に VLAN untagged メンバー追加すると PVID が変更できず再起動後にリンクアップ不可 |
| 951 | [Teamd] Question about LAG fallback | OPEN | skip-question | - | 質問形式、回答なし |
| 827 | orchagent_restart_check fails even when orchagent was successfully frozen | OPEN | **apply** | system/sonic-warm-reboot.md | warm reboot 時 orchagent_restart_check が freeze 後のリクエストを処理しないため継続的に失敗する既知問題 |
| 592 | Need to create a dummy interface in the Bridge | CLOSED | skip-old | - | 古い VLAN bridge 実装の内部問題、現行実装で解決済み |
| 568 | orchagent cannot rebuild when port.h changed | CLOSED | skip-old | - | ビルド依存関係問題、現行ビルドシステムで解決済み |
| 559 | Adding a new HOSTIF trap, syncd says SAI_STATUS_NOT_IMPLEMENTED | OPEN | **apply** | acl-qos/copp-neighbor-miss-trap-and-enhancements.md | SAI_HOSTIF_TRAP_TYPE_STP/OSPF 等は BCM SAI で未実装。SAI spec mandatory ≠ 全ベンダー実装済み |
| 353 | netlink reports an error=-33 on reading a netlink socket | OPEN | **apply** | internals/swss-schema.md または system index | NLE_DUMP_INTR (errno=33) は netlink dump が中断されたことを示す。NLM_F_DUMP_INTR フラグを確認 |
| 201 | GPF in orchagent. ACL counters related code | CLOSED | skip-old | - | 2016年の古い ACL カウンター SIGSEGV、現行修正済み |
| 199 | SAI_OBJECT_TYPE_LAG_MEMBER SAI_STATUS_FAILURE | CLOSED | skip-old | - | 2017年の古い Mellanox LAG 問題 |
| 191 | add lag member failed on mellanox platform | CLOSED | skip-old | - | 2017年の古い LAG メンバー重複作成問題 |
| 160 | Separate LAG/LAG_MEMBER and VLAN/VLAN_MEMBER tables | CLOSED | skip-old | - | 2016年の設計改善、現行実装で解決済み |
| 139 | Failed to set default drop route to a new next hop | CLOSED | skip-old | - | 2016年の Mellanox SAI 制限、現行では修正済み |

---

## apply 対象サマリー（14 件）

### NAT 関連 (4406, 1574, 1351, 1234) → docs/architecture/nat-in-sonic.md

1. **#1574**: `snat_entry_threshold_type` 属性 — CRM 連携時に一時破損 → 制限事項に追記
2. **#1351**: ICMP dynamic NAPT での reply 転送 — Identifier フィールドで追跡、正常動作確認済み
3. **#1234**: DNAT_POOL 未作成時の DNAT_MISS trap 未発火 — NatOrch の既知バグ → 既知の問題に追記

### ACL 関連 (4406, 2204) → docs/acl-qos/acl-in-sonic.md

1. **#4406**: SAI_STATUS_INSUFFICIENT_RESOURCES 時にルートプログラミングが ACL ACE リトライより優先されない
2. **#2204**: MirrorV6 テーブルで IN_PORTS 非サポート

### BFD 関連 (3051) → docs/routing/bfd-hw-offload.md

1. **#3051**: SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID=False 時に PORT 属性が必須だが未渡し

### ルート関連 (3270) → docs/routing/bgp-route-install-error-handling.md

1. **#3270**: EntityBulker が存在しないルートを削除しようとして SAI_STATUS_ITEM_NOT_FOUND

### DASH 関連 (3069) → docs/overlay/sonic-dash-hld.md

1. **#3069**: DASH ACL 設定順序依存性バグ

### VLAN 関連 (961) → docs/switching/switch-port-modes-and-vlan-cli-enhancement.md

1. **#961**: IP + VLAN untagged 共存時の PVID 変更不可 → 再起動後リンクアップ不可

### warm reboot 関連 (827) → docs/system/sonic-warm-reboot.md

1. **#827**: orchagent_restart_check が freeze 後リクエストを処理せず継続的に失敗

### COPP/HOSTIF 関連 (1684, 559) → docs/acl-qos/copp-neighbor-miss-trap-and-enhancements.md

1. **#1684**: DHCP_L2 / DHCPv6_L2 トラップが COPP マップに未対応
2. **#559**: SAI mandatory でも BCM SAI が未実装のトラップが存在

### ConsumerStateTable (1812) → docs/internals/swss-schema.md

1. **#1812**: KEY_SET メソッドで DEL メッセージが ConsumerStateTable::pops に現れない

### Buffer/APPLY_VIEW (2231) → docs/internals/swss-schema.md

1. **#2231**: APPLY_VIEW 前の buffer profile 属性照会で zero-buffer pool との相互作用問題

### Tunnel Term (2829) → docs/overlay/vxlan-sonic.md

1. **#2829**: MP2P/MP2MP トンネルターム作成時に DST_IP/SRC_IP が必須化されオーケストレーターが未対応

### netlink (353) → docs/internals/swss-schema.md 既知の問題

1. **#353**: NLE_DUMP_INTR (errno=-33) は netlink dump 中断、無視せず retry が必要
