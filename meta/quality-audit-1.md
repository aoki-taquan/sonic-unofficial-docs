# 品質改善サンプリング監査（round 1）

- 実施日: 2026-05-11
- 対象: PR #882-889 で merge された discrepancy 補強 (39 ページ) + Topics operations 拡充 (21 章)
- サンプル数: discrepancy 5 件 / operations 5 件
- 評価者: AI (Claude / batch #6)

## 1. サンプル

### Discrepancy 補強 5 件

| # | パス | verification |
|---|------|--------------|
| D1 | `docs/platform/sonic-port-naming-convention-change.md` | discrepancy-found |
| D2 | `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md` | discrepancy-found |
| D3 | `docs/system/sonic-network-time-protocol-ntp-client-configuration.md` | discrepancy-found |
| D4 | `docs/system/sonic-libsairedis-api-idempotence-support.md` | discrepancy-found |
| D5 | `docs/management/gnsi-hld.md` | discrepancy-found |

### Topics operations 5 件

| # | パス |
|---|------|
| O1 | `docs/topics/06-l2-vlan-lag/operations.md` |
| O2 | `docs/topics/13-dash-smartswitch/operations.md` |
| O3 | `docs/topics/10-gnmi-openconfig/operations.md` |
| O4 | `docs/topics/02-bgp/operations.md` |
| O5 | `docs/topics/14-platform-port-optics/operations.md` |

## 2. 評価軸（5 段階, 5 = 優）

### Discrepancy 補強

| | 情報密度 | 実用性 | 正確性 | 読みやすさ | 翻訳調解消 |
|---|---:|---:|---:|---:|---:|
| D1 port-naming | 5 | 5 | 5 | 5 | 5 |
| D2 hamgrd | 4 | 3 | 5 | 4 | 4 |
| D3 NTP/chrony | 5 | 5 | 5 | 5 | 5 |
| D4 sairedis idempotence | 5 | 4 | 5 | 4 | 5 |
| D5 gNSI | 4 | 4 | 5 | 4 | 4 |
| 平均 | **4.6** | **4.2** | **5.0** | **4.4** | **4.6** |

### Topics operations

| | 情報密度 | 実用性 | 正確性 | 読みやすさ | 翻訳調解消 |
|---|---:|---:|---:|---:|---:|
| O1 L2/VLAN/LAG | 5 | 5 | 5 | 5 | 5 |
| O2 DASH/SmartSwitch | 5 | 5 | 4 | 5 | 5 |
| O3 gNMI/OpenConfig | 4 | 4 | 5 | 4 | 5 |
| O4 BGP | 5 | 5 | 5 | 5 | 5 |
| O5 platform/optics | 5 | 5 | 5 | 5 | 5 |
| 平均 | **4.8** | **4.8** | **4.8** | **4.8** | **5.0** |

## 3. 正確性 spot check（3 件）

`.cache/sonic-sources/` 直叩きで引用の実在を確認:

1. **D3 (chrony)**: `sonic-buildimage/files/image_config/chrony/` に `chrony.conf.j2` / `chrony.keys.j2` / `chronyd-starter.sh` / `chrony-config.sh` 全部実在。HLD 記述（ntpd）と実装（chrony）のズレ指摘は正確。
2. **D1 (port naming)**: `sonic-buildimage/device/arista/x86_64-arista_7050cx3_32s/Arista-7050CX3-32S/port_config.ini` 実在。`Ethernet<panel>/<sub>` alias 形式が業界共通という指摘は port_config.ini を引用元として支持される。
3. **D4 (sairedis idempotence)**: `sonic-sairedis/syncd/AsicView.{cpp,h}` `BestCandidateFinder.{cpp,h}` 実在。`grep -rn 'ATTR2OID_\|RESTORE_DB' sonic-sairedis/{lib,syncd}` で **0 件**（HLD 提案は採用されていない、という主張を裏付け）。

3/3 正確。サンプリング範囲では引用の捏造・誤参照はゼロ。

## 4. 観察事項

### 良い点

- **「HLD の何が違うか」が読者目線で構造化されている**。D3 / D1 / D4 は `HLD 記述 → 実装位置 → 差分の中身 → 読者への影響 → 回避策` の 5 つ組テンプレで一貫している。読者が「自分が踏むかもしれない罠」を即把握できる。
- **operations 系は HLD 翻訳ではなく `運用順序` で組み直されている**。「最初に何を見るか → 次に何を見るか → 異常検出パターン → 復旧コマンド」の流れが全 5 件で共通し、読者の運用フロー（症状 → 切り分け → 復旧）に対応している。
- **CLI 出力サンプル / log 抜粋 / redis-cli 例が具体的**。O4 BGP の `show ip bgp summary` 24 neighbor サンプル、O2 SmartSwitch の `show chassis modules midplane-status` サンプルなど、実装を読まないと書けない粒度のものが入っている。
- **異常検出表 / 早見表が標準装備**。テーブル化された「観測 → 疑う状態 → 一次切り分け」が共通テンプレで、運用者が grep して使える形になっている。

### 弱い点

- **operations サンプル中の数値・出力は「もっともらしい合成」が混じる可能性**。D2 hamgrd の `redis-cli -n 6 hgetall 'DASH_HA_SET_TABLE:hasetA'` 出力や O2 の `show system-health dpu` テーブルなど、機能自体が未実装の領域（hamgrd バイナリは存在しない、と本人が discrepancy で書いている）の output 例は **実機で取得した値ではない**。`!!! note` で「想定出力」と明示するほうが誠実。
- **D2 hamgrd の本文**: discrepancy banner と「実装との乖離」セクションで「未実装」と明言しつつ、本文は HLD どおりの actor model 解説が続く。読者が「これは想定仕様 / 未実装」と一目で分かるバッジが本文中の節レベルにあるとさらに良い。
- **D5 gNSI**: 「Credentialz の gNMI server 側 handler は未実装」程度の踏み込み。具体的な commit / 行番号レベルの欠落証跡があれば最高。
- **operations ページ群の冗長性**: 早見表 / 異常検出表 / 関連 CONFIG_DB / 関連ページ / 横断参照と 5 セクション同じテンプレで並ぶため、読者が「どれを最初に読むか」迷う章がある。各ページ冒頭に「典型シナリオ別の最短経路」を 3 行で示すと体験が上がる。
- **operations sources frontmatter が空**（O3 / O4）のページがある。`sources:` を関連 HLD で埋めれば内部リンク自動チェックで漏れを発見しやすい。

## 5. 総合評価

### 60 ページ改善で読み手の体験は変わったか

**変わった**。discrepancy ページは「HLD と実装の差分を運用者向けに翻訳する」役割を果たしており、ユーザが現行 master を運用する際の罠（chrony 移行、ets 命名未採用、libsairedis 内 idempotence 未採用、hamgrd 未実装）を **HLD を読み解く前に発見できる**。これは本リポの掲げる「日本語非公式ドキュメント = AI による再構成」の本旨に合致している。

operations 系は HLD の章立てを捨て、運用フロー軸で書き直されており、HLD の直訳ではない。「読み手の体験」軸では明らかにプラス。

### 「足し算しただけ」になっていないか

**なっていない**。サンプル 10 件中、明確に「ボリュームだけ増やした」と言えるページはゼロ。各ページに以下のいずれかの **質的増分** がある:

- 実コードでの裏取り（discrepancy ページ全件）
- 運用フロー軸の再構成（operations ページ全件）
- redis-cli / log / CLI 出力サンプルの具体性（operations 全件、discrepancy 一部）
- 異常検出 / 復旧コマンド早見表（operations 全件）

ただし「合成された CLI 出力サンプル」と「実機取得」を読者が区別できない点はリスク。これは「ボリュームを盛った」のではなく「ラベリングが弱い」問題。

## 6. 次にやるべき作業（優先度順）

1. **CLI 出力サンプルのラベリング規約導入**: `!!! example "実機取得 (SONiC 202405 / Arista 7050)"` vs `!!! example "想定出力 (HLD 仕様ベース)"` を frontmatter / admonition で区別する。特に未実装機能（hamgrd 等）の出力サンプルは「想定」明示が必須。`meta/templates/page.md` にスタイルガイドを追記。
2. **discrepancy ページの差分行レベル精緻化**: D5 のような「未実装」記述に対して `grep -n` 結果（ファイル + 行番号 + 短い excerpt）を `<!-- evidence: -->` コメントとして埋め込む規約を全 39 ページに展開。verifier が再走査するときに既存証跡を活かせる。
3. **operations ページに「最短経路」3 行サマリ追加**: 各 operations.md の `## 概要` 直後に「症状 → このページのどこを読むか」の 3 行マッピングを入れる。これで現状の「テンプレ 5 セクション並列」感が「症状 → 該当節」のユーザフローに変わる。

## 7. 結論

PR #882-889 のバッチ品質改善は **実用的価値を確かに上げた**。サンプリング 10 件で正確性 平均 4.9 / 5、実用性 平均 4.5 / 5。次の改善は新規ページの量産ではなく、既存ページの **出力サンプルの実機/想定ラベリング** と **差分行レベル証跡** に投資する局面。
