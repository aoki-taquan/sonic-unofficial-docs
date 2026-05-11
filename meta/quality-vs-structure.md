# 構造改善 vs コンテンツ改善 効果比較

- 作成日: 2026-05-11
- 評価対象: バッチ #884-#889（quality 系 6 PR、`discrepancy 補強` × 4 batch + `Topics operations 拡充` × 4 batch、合計 40 ファイル、約 3,400 行追加）
- 比較対象案: 構造変更案 v1-v4（archive 案 / 5 タブ / 4 タブ / 3 タブ）
- 立場: D 視点（構造変更ゼロ + 本文品質）が正しかったかの事後検証

## TL;DR

- **D 案は正しかった**。構造変更ゼロでも「discrepancy の中身を読者が掴める」「Topics の operations 章が運用引き継ぎ書として読める」という体験向上は実現した。一方で構造でしか解けない問題（Topics/area 重複、discrepancy 一覧の埋もれ、HLD area 命名）は残る。
- 推奨方針: **コンテンツ改善を主軸に継続。構造変更は最小コストの 1 PR 系（discrepancies 一覧ハブを `_meta` から `verification/` に昇格する程度）に限定し、4 タブ・5 タブの全面再編は引き続き凍結**。

---

## 1. 改善 60 ページの効果測定

### 1.1 サンプル: discrepancy 補強 5 件（#882-#884, #888）

読み手として効果が出ているか、以下を抽出してチェックした。

| ページ | Before | After | 効果 |
|---|---|---|---|
| `architecture/sflow-high-level-design.md` | HLD ベースの記述。sample_rate 既定値が誤値（100G→50000 等） | 冒頭 `!!! danger` で「HLD と実装は揃って `(ifSpeed/1e6)`。ページが書いていた値は誤り」と明示し、`sflowmgr.cpp::findSamplingRate()` を引いて修正 | **大**: 読者が「ページの記述を信じて 50000 で投入する」事故が消える |
| `architecture/build-profiles.md` | HLD-only ステータスのまま | `discrepancy-found` 化 + `slim/marketplace` 等のプロファイル差分を実 build 結果で裏取り | **中**: build 失敗時の切り分け根拠ができた |
| `architecture/sag-high-level-design-for-sonic.md` | HLD 翻訳 | 実装側 SAG MAC 設定経路と HLD の差分を 28 行追記 | **中**: 動作する設定が判る |
| `architecture/debug-framework-in-sonic.md` | HLD 翻訳 | `dump_state` registry の実装位置と HLD 表現のズレを 27 行明示 | **中** |
| `architecture/error-handling-framework-in-sonic.md` | HLD 翻訳 | ERROR_DB スキーマが HLD と実装で異なる点を 29 行で記述 | **中** |

**事実認定**: 「構造変更なしでも、discrepancy の中身が読者に伝わるようになった」は **真**。`!!! danger` ブロックと `sources:` frontmatter は既存テンプレ内に収まっており、構造変更は不要だった。

### 1.2 サンプル: Topics operations 拡充 5 件（#885-#887, #889）

| ページ | Before | After | 効果 |
|---|---|---|---|
| `topics/12-multi-asic-voq/operations.md` | 章スタブ（数十行） | 226 行。supervisor / line card / ASIC namespace の判定表、`show chassis modules`/`show chassis system-ports` 出力、aggregate VOQ counter 章 | **大**: chassis 運用での「どこから見るか」が一発で判る |
| `topics/13-dash-smartswitch/operations.md` | スタブ | 156 行追加。NPU/DPU 切り分けの実際 | **大** |
| `topics/14-platform-port-optics/operations.md` | スタブ | 175 行追加。SFP/QSFP 故障判定フロー | **大** |
| `topics/15-security-aaa/operations.md` | スタブ | +157 行。TACACS+/RADIUS タイムアウト診断 | **大** |
| `topics/16-nat-dhcp-dns/operations.md` | スタブ | +164 行。NAT セッション枯渇 / DHCP relay の syslog 経路 | **大** |

**事実認定**: 「Topics 章の operations が運用引き継ぎ書として読める」は **真**。構造変更なしで、Topics の最大欠点（"22 章あるが概念止まりで運用に使えない"）が、operations.md だけで実質解消されつつある。

### 1.3 構造を変えていたら追加で得られた効果

サンプル読みで「構造でないと得られなかった効果」は次の 3 つだけ:

1. **discrepancy-found ページの一覧ビュー**: 現状 `_meta/discrepancies.md` の埋もれた 1 ページに依存。読者は area 横断で「実装と乖離している箇所」を発見できない。コンテンツ改善では各ページの精度は上がるが「40 件を 1 画面で見渡せる」体験は来ない。
2. **HLD area 名（`architecture/routing/switching/...`）の専門用語性**: 初学者は area 名から内容を予測できない。本文を厚くしても URL とサイドバー名は変わらない。
3. **Topics ⇔ HLD area の重複**: BGP は `topics/02-bgp` と `routing/` の両方にある。本文改善で各ページの完成度は上がるが、検索時の「どっちを読めばいいか」迷いは残る。

逆に言えば、**それ以外（中身の信頼性・運用での使い物・裏取り表示）はすべて構造ゼロで解決した**。

---

## 2. 残る構造問題: コンテンツ改善で解決できたもの / できなかったもの

| 問題 | コンテンツで解決? | 理由 |
|---|---|---|
| Topics ⇔ HLD area 重複 | **不可** | 物理ディレクトリと URL は本文編集で変わらない |
| discrepancy 一覧の埋もれ | **不可** | 一覧ビューは nav/index の問題で、本文では作れない |
| HLD area 命名（architecture/routing/...）の専門用語性 | **部分** | 各 index.md で説明は厚くできるが、サイドバー名は残る |
| HLD 翻訳のまま問題 | **大部分解決** | discrepancy 補強 40 件 + Topics operations 20 件で「翻訳止まり」は実質ゼロに近づく |
| 検索時のページ被り（同じトピックが複数 area） | **不可** | 物理重複は重複のまま |
| 「読み手の動線」(Diátaxis 的) | **部分** | Topics 章で `concept→setup→operations→advanced` の流れは作れたが、トップ nav は HLD area のまま |
| reference の信頼性希釈リスク | **解決不要** | v4 で提案されていた `reference/verification` 混在は実施せず、希釈は発生していない |
| 個別ページの精度・運用での使い物 | **完全解決** | 本件で実証 |

要点: **「読者がページに到達した後の体験」はコンテンツで解ける。「ページに到達する前の体験（nav・検索結果・横断ビュー）」はコンテンツでは解けない**。

---

## 3. 結論

### 3.1 D 案（構造変更ゼロ + コンテンツ改善）は正しかったか

**正しかった**。理由:

- 24h で v1-v4 の 4 案を出した構造変更の暴走に対し、D 視点が止血した。
- バッチ 6 PR / 40 ファイル / 3,400 行という具体物が、構造ゼロでも本文品質を引き上げられることを実証した。
- v4 で提案された `reference/verification` 混在のような副作用リスク（reference 信頼性希釈）を回避できた。
- 実行コストが圧倒的に低い: 構造変更 1 PR でも `.pages` 改修 + redirect + 内部リンク修正 + `mkdocs --strict` デバッグで 2-4h、v4 全面再編なら 1 週間級。本件は 6 PR 並走でほぼ衝突なく回った。

### 3.2 構造変更も並走させるべきだったか

**並走させなくて正解**。理由:

- 並走させた場合、Writer エージェントは構造（`.pages` / nav）とコンテンツの両方を触り、衝突が増える。
- 構造変更は「最終形が決まってから」やる作業で、コンテンツ改善が進む過程で読み手のニーズ（「discrepancy を一覧で見たい」「operations を最初に読みたい」等）が見えてから着手するのが安全。

### 3.3 今後の方針提案

優先度順:

1. **コンテンツ改善を 100-150 ページ追加で継続**（最優先）。残る Topics operations / advanced 章、discrepancy 補強の対象未完分、`hld-only` 残ゼロの維持。
2. **超小型の構造改善を 1-2 個だけ実行**: 具体的には
   - `docs/_meta/discrepancies.md` を `docs/verification/index.md` に移動し、トップ nav にタブとして 1 行追加（discrepancy 一覧の埋もれ解決）。.pages 改修 1 か所、redirect 1 件、内部リンク 6 か所修正で完了。
   - Topics の各章 index.md に「対応する HLD area へのリンク表」を追記（Topics ⇔ area 重複の動線整理。構造でなく本文側で）。
3. **全面構造再編（v1-v4 系）は引き続き凍結**。再開するのは、上記 1-2 を終え、その上で読者ログや GitHub Issue で「nav が原因の迷子」が定量的に観測されてから。
4. **構造提案が出てきたら、必ず「本件 60 ページの効果を超えるか」を基準にレビューする**。タブ数を増減するだけの提案は採用しない。

---

## 付録: 数値サマリ

- merge 済みページ: 累計 ~461（455 + 60 改善で実質増分は本文追記）
- `hld-only` ステータス: 0 件（維持）
- `discrepancy-found`: 40 件（裏取り済み）
- 本件で触れた行数: 約 3,400 行追加 / 67 行削除
- 構造変更 PR: 0 件（D 案順守）
- 構造評価レポート: 14 件累計（v1-v4 × IA/persona/devil/diataxis/radical/third）。本レポートが「実測に基づく事後評価」としては初めて。
