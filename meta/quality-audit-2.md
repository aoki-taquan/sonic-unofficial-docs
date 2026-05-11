# 品質改善サンプリング監査（round 2）

- 実施日: 2026-05-11
- 対象: イテレーション B (PR #894-902) で merge された Verifier batch 28/29/30 (42 ページ昇格・降格) + Reference CLI/CONFIG_DB batch A/B (35 ページ追加) + coverage 自動生成 + フィードバック導線整備、合計約 100 件
- サンプル数: Verifier 5 件 + Reference 5 件
- 評価者: AI (Claude / batch #6)

## 1. サンプル

### Verifier 昇格ページ 5 件

| # | パス | verification |
|---|------|--------------|
| V1 | `docs/acl-qos/asymmetric-pfc-test-plan.md` | code-verified |
| V2 | `docs/architecture/sonic-policy-based-hashing.md` | code-verified |
| V3 | `docs/routing/default-route.md` | code-verified |
| V4 | `docs/management/save-on-set-hld.md` | code-verified |
| V5 | `docs/internals/swss-schema.md` | code-verified |

### 新規 Reference ページ 5 件

| # | パス |
|---|------|
| R1 | `docs/reference/cli/config-ssh.md` |
| R2 | `docs/reference/cli/show-storm-control.md` |
| R3 | `docs/reference/cli/show-flowcnt.md` |
| R4 | `docs/reference/config-db/mclag-domain.md` |
| R5 | `docs/reference/config-db/buffer-port-egress-profile-list.md` |

## 2. 評価軸（5 段階, 5 = 優）

### Verifier 昇格ページ

| | 情報密度 | 実用性 | 正確性 | 読みやすさ | 翻訳調解消 |
|---|---:|---:|---:|---:|---:|
| V1 asymmetric PFC test plan | 5 | 4 | 5 | 5 | 5 |
| V2 PBH | 5 | 5 | 5 | 5 | 5 |
| V3 default-route (linkmgrd) | 5 | 5 | 5 | 5 | 5 |
| V4 save-on-set | 5 | 5 | 5 | 5 | 5 |
| V5 swss-schema | 4 | 4 | 5 | 4 | 4 |
| 平均 | **4.8** | **4.6** | **5.0** | **4.8** | **4.8** |

### Reference ページ

| | 情報密度 | 実用性 | 正確性 | 読みやすさ | 翻訳調解消 |
|---|---:|---:|---:|---:|---:|
| R1 config ssh | 5 | 5 | 5 | 5 | 5 |
| R2 show storm-control | 5 | 5 | 5 | 5 | 5 |
| R3 show flowcnt-* | 5 | 5 | 5 | 5 | 5 |
| R4 MCLAG_* | 5 | 5 | 5 | 5 | 5 |
| R5 BUFFER_PORT_EGRESS_PROFILE_LIST | 4 | 4 | 5 | 5 | 5 |
| 平均 | **4.8** | **4.8** | **5.0** | **5.0** | **5.0** |

**round 2 全体平均: 4.83 / 5.0**（round 1: 4.6）

## 3. 正確性 spot check（3 件）

`.cache/sonic-sources/` 直叩きで引用された実コード行番号を確認:

1. **V1 asymmetric PFC** — `sonic-swss/orchagent/portsorch.cpp` L2519 `bool PortsOrch::setPortPfcAsym(...)` 実在、L5413 で `setPortPfcAsym(p, pCfg.pfc_asym.value)` 呼び出し実在。本文の「L2519-L2573 / L5407-L5434」と一致。
2. **V4 save-on-set** — `sonic-gnmi/gnmi_server/server.go` L1051 `func SaveOnSetEnabled() error` 実在、L1067 `saveOnSetDisabled` 実在、L551 で既定値 `saveOnSetDisabled` を結線、L1208 で `s.SaveStartupConfig()` 呼び出し実在。本文記述（L1051 / L1068）と一致（L1067 vs L1068 は 1 行差だが本文の意図と整合）。
3. **R1 config ssh** — `sonic-utilities/config/main.py` L9979 `@ssh.command('inactivity-timeout')` 実在。本文の「L9979-L9988」と一致。

3 件とも引用先が **行レベルで実在**。正確性は round 1 同様 5.0。

## 4. round 1 比較トレンド

| 観点 | round 1 | round 2 | trend |
|------|--------:|--------:|:-----:|
| Discrepancy / Verifier 平均 | 4.6 | 4.8 | 向上 |
| Reference / Operations 平均 | 4.8 | 4.8 | 維持 |
| 正確性 | 5.0 | 5.0 | 維持 |
| 翻訳調解消 | 4.8 | 4.9 | 微向上 |

**総合: 向上（4.6 → 4.83）**。理由:

- Verifier batch 29/30 は単に「裏取り済み」と書くだけでなく、**該当ファイル + 行番号 + 関数名 + 周辺ロジックの解釈**を末尾セクションにまとめており、読み手が `.cache` を引かなくても妥当性を判断できる
- Reference batch A/B は CLI/CONFIG_DB ともに **「key 構造」「フィールド表」「購読者」「制約」「関連 CONFIG_DB/YANG/CLI」** の章立てが完全に統一されており、ページ間で文体ブレが消えた
- Verifier 昇格と同時に降格 (discrepancy-found) も並行して記録するルールが定着し、`hld-only` 0 件状態を維持

## 5. 発見した品質課題

### 5.1 admonition と frontmatter の整合性ズレ（中程度）

V3 `default-route.md`, V4 `save-on-set-hld.md`, V5 `swss-schema.md` で **frontmatter は `verification: code-verified` なのに、本文冒頭の `!!! warning "裏取りステータス: HLD-only"` admonition が残存**。Verifier は frontmatter のみ更新し、本文上部の warning ブロックを書き換えていない。読み手は frontmatter ではなく目立つ admonition を信じるため、見た目は「HLD-only のまま」に映る。

→ Verifier prompt に「`!!! warning` / `!!! success` の admonition も verification ステータスに同期せよ」を追記すべき。または `mkdocs --strict` の lint で frontmatter と admonition の不整合を検出するヘルパを追加。

### 5.2 Verifier 末尾セクションのスタイル統一不足（低）

V1 は「裏取り済み実装位置 (2026-05-11)」、V3 は「裏取りメモ (batch 30, 2026-05-11)」、V4 は「裏取りメモ（Verifier batch 29）」、V5 は本文中に統合と、見出し名がバラバラ。検索性が落ちる。`## 実装位置の裏取り（YYYY-MM-DD, batch N）` で統一を推奨。

### 5.3 Reference の「関連ページ」リンク先未生成（低）

R4 `mclag-domain.md` 末尾は `[CONFIG_DB: PORTCHANNEL](portchannel.md)` を貼っているが `portchannel.md` は CONFIG_DB ディレクトリ未生成。`mkdocs --strict` は通っているので link check は緩い可能性。Reference batch C で `BGP_NEIGHBOR` / `PORTCHANNEL` / `VLAN` の中核 CONFIG_DB を埋めるとリンク網が完成する。

### 5.4 swss-schema が「要点抜粋」止まり（低）

V5 は元の sonic-swss/doc/swss-schema.md が 54KB 超で全網羅困難という事情から「抜粋」スタイルになっており、情報密度が他 Verifier より劣る。本ファイルは index 的に残し、APPL_DB の中核テーブル (`PORT_TABLE`, `ROUTE_TABLE`, `NEIGH_TABLE`, `INTF_TABLE`) を Reference 配下に個別ページ化すべき。

## 6. 次のイテレーション C で気をつけるべき罠

イテレーション C は現在進行中: Topics setup/internals + Runbooks + discrepancy 深掘り。並走の前提を踏まえて:

1. **Topics setup と Reference の重複を避ける** — setup 章は手順 (how-to) に徹し、各 CONFIG_DB テーブル / CLI コマンドの仕様は Reference 配下へリンク。Reference 既存ページの内容を setup 章にコピペすると保守が二重化する。Topic 章では `??? note "詳細: [reference/...]"` 形式の collapse でリンクのみ貼る。

2. **Runbook の前提条件は frontmatter ではなく冒頭 admonition で表現** — Runbook は「いつ実行すべきか」「どの状態で実行が壊れるか」が命。`!!! danger "実行前提"` で前提条件を列挙、`!!! warning "ロールバック手順"` で復旧手順を必ず併記。実コード裏取りは Runbook では「該当 daemon の reload を受け付ける CLI が存在すること」のレベルで十分（深掘りすぎない）。

3. **Topics internals は HLD 翻訳調に逆戻りしやすい** — internals 章は orchagent / *syncd / *mgrd のアーキテクチャ図を描く章。元 HLD の "The architecture is composed of three layers..." をそのまま訳すと翻訳調が再発する。**まず「この章の読者が何を持ち帰るか」を 1 文で書き、そこから逆算**して図と説明を起こす。

4. **discrepancy 深掘りで「HLD が古い」結論ばかりにしない** — discrepancy-found は 2 種類ある: (a) HLD 提案が実装されなかった、(b) HLD 後に実装が独自に進化した。深掘り batch では **(a) と (b) を明示的にタグ分け** すべき（例: `discrepancy_type: not_implemented` / `discrepancy_type: evolved_beyond_hld`）。これが無いと「全部 HLD が悪い」というメッセージに偏る。

5. **`!!! warning "HLD-only"` 残骸を Verifier 補完バッチで掃除** — §5.1 の admonition ズレは Verifier 過去バッチに広く存在する可能性。`grep -rn 'verification: code-verified' docs/` で frontmatter が code-verified のページに対し、`!!! warning.*HLD-only` を残しているページを抽出する 1 回限りの cleanup PR を用意すべき。

6. **per-page queue の取り合い** — Topics setup を 4 並列 (`t-setup-0..3`) で走らせているので、同 area の Reference / Verifier と衝突しやすい。Topic 章は `docs/topics/<NN>-<area>/` 配下なので Reference (`docs/reference/`) とはディレクトリ分離されているが、`meta/queue/<area>-*.json` aggregate 時に Topic 章由来の queue 書き換えが Reference を上書きしないか目視確認。

7. **Runbook の「読み手シミュレーション」を skip しない** — Runbook は「実機で打鍵される CLI sequence」が命。書く前に `.cache/sonic-sources/sonic-utilities/config/*.py` で対象 CLI が存在することを確認し、deprecated / hidden コマンドを案内しない。round 2 までは reference は宣言的なので副作用が無かったが、Runbook は副作用を持つので誤情報のコストが跳ね上がる。

## 7. 結論

イテレーション B は round 1 比で **+0.23 ポイント** 改善 (4.6 → 4.83)。Verifier は単なる昇格ではなく「実装位置の説明」を末尾に追加し、Reference は構造の統一化が進んだ。引用は 3/3 spot check で行レベル一致。

主たる残課題は「admonition と frontmatter の同期不足」「Verifier 末尾セクション見出しの統一不足」の 2 つで、いずれも cleanup batch 1 回で吸収可能。次イテレーション C では Topics setup / Runbook の重複・前提条件・翻訳調再発に注意。
