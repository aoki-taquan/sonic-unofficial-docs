# 読み手ペルソナ別ガイド提案

## 目的

現行の `docs/` は area 階層で整理されており、既に関心領域が決まっている読者には探しやすい。一方で、初学者やラボ評価者のように「最初に何を読めばよいか」が定まっていない読者は、area 名から自分の導線を組み立てる必要がある。

本提案では、既存ページを差し替えずに読み手別の入口を追加する前提で、4 種類のペルソナと reading path を定義する。

## 調査範囲

`find docs -name "*.md"` 相当の全 Markdown ページを確認した。実作業環境では `find` が利用できなかったため、同等の一覧取得として次を使用した。

```bash
rg --files docs -g '*.md' | sort
```

確認した主な構成は以下。

- `docs/index.md`: サイト全体の説明と area への入口
- `docs/architecture/`: SONiC 全体構成、ビルド、拡張基盤、GNS3 / VS bring-up など
- `docs/routing/`: BGP、VRF、static route、EVPN/VXLAN、SRv6、FRR 関連など
- `docs/switching/`: VLAN、LAG、MCLAG、STP、MACsec、L2 forwarding など
- `docs/overlay/`: VXLAN、Dual ToR、DASH など
- `docs/acl-qos/`: ACL、QoS、PFC、buffer、watermark、mirroring など
- `docs/system/`: reboot、warm boot、ZTP、show techsupport、syslog、NTP、SNMP、health、telemetry など
- `docs/management/`: CLI / management framework、gNMI/gNOI/gNSI、AAA/TACACS、YANG validation、application extension など
- `docs/platform/`: platform、multi-ASIC、PMON、SFP、thermal、PSU、SAI failure handling など
- `docs/internals/`: swss schema、flex counter、P4 orchagent、Redis multi namespace など
- `docs/reference/cli/`: `config` / `show` / `clear` / installer / package manager の運用 CLI リファレンス
- `docs/reference/config-db/`: CONFIG_DB テーブル単位のリファレンス
- `docs/reference/yang/`: SONiC YANG モデル単位のリファレンス

## ペルソナ 1: 初学者

### 想定シナリオ

SONiC を初めて触る読者。ネットワーク OS としての SONiC の位置付け、コンテナ、Redis DB、SAI、設定反映の流れを把握し、各 area の意味を理解したい。

### 推奨 reading path

1. `docs/index.md`
2. `docs/architecture/index.md`
3. `docs/reference/config-db/index.md`
4. `docs/reference/cli/index.md`
5. `docs/management/sonic-nos-configuration-methods.md`
6. `docs/architecture/sonic-on-gns3-vm.md`
7. `docs/architecture/steps-to-bring-up-sonic-vs.md`
8. `docs/system/zero-touch-provisioning-ztp.md`
9. 関心に応じて `docs/routing/index.md`、`docs/switching/index.md`、`docs/system/index.md`

### 不足コンテンツ

- 「SONiC の全体像」を 1 ページで説明する導入記事が不足している。`docs/index.md` には要約があるが、CONFIG_DB / APPL_DB / STATE_DB / ASIC_DB、SwSS、syncd、SAI の関係を初学者向けに順序立てて読む導線はまだ弱い。
- 「最小用語集」がない。SAI、orchagent、syncd、CONFIG_DB、YANG、FRR、PMON、multi-ASIC などが各ページに散っている。
- area index の多くが stub のため、初学者が area の中で何を読むべきか判断しにくい。

## ペルソナ 2: 運用者

### 想定シナリオ

既に SONiC を運用している読者。日々の確認、設定変更、障害調査、CONFIG_DB の意味確認、show techsupport やログ・ヘルスチェックの使い方を素早く引きたい。

### 推奨 reading path

1. `docs/reference/cli/index.md`
2. `docs/reference/cli/show-interfaces.md`
3. `docs/reference/cli/show-ip.md`
4. `docs/reference/cli/show-bgp.md`
5. `docs/reference/cli/show-platform.md`
6. `docs/reference/cli/show-system-health.md`
7. `docs/reference/cli/show-techsupport.md`
8. `docs/reference/cli/config-interface.md`
9. `docs/reference/cli/config-bgp.md`
10. `docs/reference/cli/config-vlan.md`
11. `docs/reference/config-db/index.md`
12. `docs/reference/config-db/port.md`
13. `docs/reference/config-db/interface.md`
14. `docs/reference/config-db/bgp-neighbor.md`
15. `docs/reference/config-db/vlan.md`
16. `docs/system/show-techsupport.md`
17. `docs/system/sonic-system-health-monitor-high-level-design.md`
18. `docs/system/sonic-syslog-source-ip.md`
19. `docs/system/sonic-network-time-protocol-ntp-client-configuration.md`
20. `docs/system/static-dns-configuration.md`

### 不足コンテンツ

- 障害別の逆引き導線が不足している。例: 「BGP が上がらない」「ポートが down」「VLAN に疎通しない」「CPU / memory / disk を見たい」から CLI、CONFIG_DB、関連 HLD に飛ぶページ。
- CLI と CONFIG_DB の相互参照は各リファレンスで整備されつつあるが、運用手順として「確認、変更、保存、rollback、再起動影響」をまとめた runbook 形式のページがない。
- `show techsupport`、system health、ログ、カウンタ、platform health をまとめたトラブルシュート入口が必要。

## ペルソナ 3: 開発者

### 想定シナリオ

SONiC に機能追加・拡張を入れたい読者。HLD、YANG、CONFIG_DB、CLI、daemon / orch、テスト計画の対応関係を追い、実装前に関連設計を把握したい。

### 推奨 reading path

1. `docs/architecture/index.md`
2. `docs/architecture/sonic-application-extension-infrastructure.md`
3. `docs/management/sonic-application-extension-guide.md`
4. `docs/management/sonic-yang-model-guidelines.md`
5. `docs/reference/yang/index.md`
6. `docs/reference/config-db/index.md`
7. `docs/management/sonic-config-update-validation-via-yang.md`
8. `docs/management/json-patch-ordering-using-yang-models.md`
9. `docs/internals/swss-schema.md`
10. `docs/internals/sonic-flexcounter-refactor.md`
11. `docs/architecture/build-system-improvements.md`
12. `docs/architecture/build-profiles.md`
13. 機能領域別に `docs/routing/`、`docs/switching/`、`docs/acl-qos/`、`docs/platform/` の HLD
14. test plan がある機能では該当する `*-test-plan.md`

### 不足コンテンツ

- 「新機能追加時のチェックリスト」がない。YANG 追加、CONFIG_DB schema、CLI、orch / daemon、test plan、migration、docs 反映を 1 本の流れで示すページが必要。
- HLD と実コードの対応を横断検索する入口が弱い。各ページの sources はあるが、開発者が「この CONFIG_DB テーブルを読む daemon はどれか」「この CLI がどの DB を書くか」を俯瞰する索引が欲しい。
- テスト観点の導線が area 別に散っているため、開発者向けに test plan の読み方、既存テストとの対応、検証粒度をまとめるとよい。

## ペルソナ 4: 評価者

### 想定シナリオ

ラボで SONiC を試用する読者。仮想環境または評価機で起動し、管理 IP、ポート、VLAN、BGP などの基本設定を入れ、状態確認まで一連の流れを辿りたい。

### 推奨 reading path

1. `docs/index.md`
2. `docs/architecture/sonic-on-gns3-vm.md`
3. `docs/architecture/steps-to-bring-up-sonic-vs.md`
4. `docs/system/zero-touch-provisioning-ztp.md`
5. `docs/reference/cli/sonic-installer.md`
6. `docs/reference/cli/config-interface.md`
7. `docs/reference/cli/config-vlan.md`
8. `docs/reference/cli/config-portchannel.md`
9. `docs/reference/cli/config-bgp.md`
10. `docs/reference/cli/show-interfaces.md`
11. `docs/reference/cli/show-vlan.md`
12. `docs/reference/cli/show-ip.md`
13. `docs/reference/cli/show-bgp.md`
14. `docs/reference/config-db/device-metadata.md`
15. `docs/reference/config-db/mgmt-interface.md`
16. `docs/reference/config-db/port.md`
17. `docs/reference/config-db/vlan.md`
18. `docs/reference/config-db/bgp-neighbor.md`

### 不足コンテンツ

- 「ラボ評価 30 分チュートリアル」がない。起動、初期ログイン、管理 IP、NTP / DNS、ポート up、VLAN、BGP neighbor、確認コマンドまでの直線的なページが欲しい。
- 既存ページはリファレンスとして強いが、評価者がそのまま打てる最小構成例が不足している。
- GNS3 / VS bring-up と実機評価の分岐が明示されていない。仮想評価、単体スイッチ評価、ToR 評価で reading path を少し変える案が必要。

## 実装案 A: `docs/guides/<persona>.md` を追加する

### 概要

`docs/guides/beginner.md`、`docs/guides/operator.md`、`docs/guides/developer.md`、`docs/guides/evaluator.md` のように、読み手別の短いガイドページを作る。各ページは既存ページへのリンク集と、読む順番、到達目標、次に進む area を示す。

### Pros

- ペルソナごとの文脈を十分に書ける。
- area 階層を崩さず、横断導線だけを追加できる。
- 将来、初学者向け用語集、運用者向け runbook、評価者向けチュートリアルなどに自然に拡張できる。
- `docs/index.md` が長くなりすぎない。

### Cons

- `docs/guides/` の新設と navigation への露出方法を決める必要がある。awesome-pages 任せでよいか、`.pages` を置くかの判断が必要。
- ページが増えるため、既存ページの追加・改名時にリンクメンテナンス対象が増える。
- 初回訪問者が `docs/index.md` から guides に気づけるよう、結局 index 側にも短い入口が必要になる。

## 実装案 B: `docs/index.md` 冒頭に「読み手別の入口」セクションを追加する

### 概要

トップページの「SONiC とは」の前後に、4 ペルソナ分の短い入口を置く。各ペルソナは 3 から 5 個程度の主要リンクだけを並べ、詳細導線は各 area / reference に委ねる。

### Pros

- 初回訪問者が必ず目にする場所に導線を置ける。
- 新規ページを増やさず、導入改善の差分が小さい。
- 既存の area 階層と reference 階層にすぐ誘導できる。

### Cons

- 4 ペルソナ分の詳細な reading path を書くとトップページが長くなる。
- ペルソナごとの不足コンテンツや分岐条件までは書きにくい。
- 将来、運用 runbook や評価チュートリアルを追加する場合、結局 `docs/guides/` 相当の置き場が必要になる。

## 推奨

段階的には案 B から始め、トップページに短い「読み手別の入口」を追加するのが最小変更で効果が高い。その後、各ペルソナの導線が育ってきた段階で案 A の `docs/guides/` に分離する。

最終形としては、`docs/index.md` に 4 つの入口カードまたは短いリンクリストを置き、詳細は `docs/guides/<persona>.md` に逃がす構成がよい。これにより、初回訪問者は迷わず入口を選べ、既存の area / reference 階層は専門的な探索用として維持できる。
