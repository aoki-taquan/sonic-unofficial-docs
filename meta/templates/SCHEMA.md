# ページ frontmatter スキーマ

すべてのドキュメントページは以下の frontmatter を持つ。Reviewer はこのスキーマに従って機械検査する。

## フィールド

| キー | 必須 | 値 | 説明 |
|------|------|----|------|
| `title` | ✅ | string | 表示タイトル |
| `area` | ✅ | enum | `routing` / `switching` / `overlay` / `acl-qos` / `system` / `management` / `platform` / `architecture` / `internals` / `reference` / `topics` (`topics` は `docs/topics/NN-*/` 配下の章扉・解説ページ用) |
| `verification` | ✅ | enum | `hld-only` / `issue-confirmed` / `code-verified` / `discrepancy-found` / `runbook-verified` / `stub` / `meta` |
| `last_verified` | ✅ | date | `YYYY-MM-DD`。裏取りまたは更新を行った日 |
| `sources` | ✅ | list | このページの根拠となる一次情報のリスト |
| `sources[].repo` | ✅ | string | `sonic-net/<repo>` 形式 |
| `sources[].path` | ✅ | string | リポジトリルートからの相対パス |
| `sources[].ref` | ✅ | string | commit SHA（master のスナップショット固定） |
| `related.config_db` | optional | list | 関連 CONFIG_DB テーブル名 |
| `related.cli` | optional | list | 関連 CLI コマンド |
| `related.yang` | optional | list | 関連 YANG モジュール |
| `related._no_related` | optional | bool | `true` のとき本ページは **3 種すべて** (`cli` / `config_db` / `yang`) について related が空であることを意図的に許容する opt-out マーカー。Reference の index ページ / glossary / style-guide 等の meta ページに付与する |
| `related._no_related_yang` | optional | bool | `true` のとき `related.yang` のみ空を許容する narrower opt-out（CLI / CONFIG_DB は通常通り埋める）。daemon 内部設計の HLD など、YANG モデルが存在しないテーマで使う |
| `related._no_related_cli` | optional | bool | `true` のとき `related.cli` のみ空を許容する narrower opt-out（内部 daemon / SAI レイヤなど、CLI 公開コマンドを持たないテーマ向け） |
| `related._no_related_config_db` | optional | bool | `true` のとき `related.config_db` のみ空を許容する narrower opt-out（CONFIG_DB に固有テーブルを持たないテーマ向け） |
| `related._no_yang` | optional | bool | `_no_related_yang` の旧名（互換 alias）。新規ページは `_no_related_yang` を使うこと |
| `monitor` | conditional | enum | `not_implemented` / `evolved_beyond_hld` / `partially_implemented` / `deprecated`。`verification: discrepancy-found` のとき **必須**。それ以外は optional |
| `page_kind` | optional | enum | `chapter-index` / `split-child` / `split-hub`。22 章扉 (`docs/topics/NN-slug/index.md`) には `chapter-index` を付与する。大型 HLD の章分割で派生した `<base>-concepts.md` / `-operations.md` / `-internals.md` / `-limitations.md` 等のサブページには `split-child`、その親（概要ハブとして残した元 HLD ページ）には `split-hub` を付与する。品質監査の評価軸を区別するためのタグ。未指定 = 通常の解説ページ |

## page_kind の意味（品質監査での扱い）

`page_kind: chapter-index` は章扉（導線ページ）であることを示す。章扉は配下ページへのリンク集が本体であり、本文の厚みや個別主張ごとの裏取りは通常ページと評価軸が異なる。

- **章扉に対して緩和される軸**: 完結性（本文ボリューム）、裏取り（個別主張ごとの脚注 / evidence コメント）
- **章扉でも維持される軸**: タイトル / description / keywords の整備、配下リンクの網羅性、frontmatter スキーマ準拠

`frontmatter_lint.py` は `page_kind` を optional フィールドとして受理する（hard violation 対象外）。次世代の品質監査ロール (round 14 以降) は `page_kind` を参照して軸別の評価を行う想定。

`page_kind: split-child` は大型 HLD を `<base>.md`（概要ハブ）+ `<base>-concepts.md` / `<base>-operations.md` / `<base>-internals.md` / `<base>-limitations.md` に分割した派生ページに付与する。元ハブの `verification` / `sources` をそのまま継承し、本文は各サブテーマに切り出した内容のみで構成される。章扉と同様に「本文ボリューム単独での完結性」では評価せず、ハブとの導線・主張の網羅性で評価する。

`page_kind: split-hub` は分割後に概要ハブとして残した元 HLD ページに付与する。本文の大半は維持しつつ冒頭で派生ページへの導線（concepts / operations / internals / limitations）を提示する責務を負う。`split-child` ページ群と同じ HLD ソースを共有するため `verification` / `sources` は一致する。監査では「ハブとして派生群を網羅的にリンクしているか」「概要として読み終えられるか」を主に見る。

`hub` (optional, `split-child` 専用) は、hub ページが標準命名規約 (`<base>.md`) に従わない場合のオーバーライド。例: `switch-port-modes-and-vlan-cli-{concepts,internals,operations}.md` の hub は `switch-port-modes-and-vlan-cli-enhancement.md` のため、各 split-child の frontmatter に `hub: switch-port-modes-and-vlan-cli-enhancement` を記載する。`check_link_density.py` の 2 層 split-child リンクルール (hub への戻りリンク + 全 sibling split-child へのリンク) で参照される。

`related.*` は **空配列でも合格**。HLD で言及されていない実装由来の項目を推測で書いてはならない。確実なもののみ列挙し、不明なら空配列にして本文側に「該当する CLI / CONFIG_DB は HLD では未定義」等を注記する。

## related の opt-out マーカー

リファレンス章の index ページや用語集 / style-guide / 404 等の **meta 系ページ** は、設計として related triangle (cli / config_db / yang) を埋められない（あるいは埋める意味が無い）。この種のページが `find_empty_related.py` や `check_discrepancy_related.py` 等の lint で「related が空」と継続的に報告されると、本当に埋めるべきページの shortfall が埋もれてしまう。

そこで以下 4 種の opt-out マーカーを `related:` 配下に置ける:

| マーカー | 効果 | 用途 |
|---------|------|------|
| `_no_related: true` | 3 種すべて (`cli` / `config_db` / `yang`) について空を許容 | Reference 章 index、`glossary.md`、`style-guide.md`、トップ `index.md`、`about.md`、`404.md`、`categories/index.md` 等 |
| `_no_related_yang: true` | `related.yang` のみ空を許容 | YANG モデルが存在しない daemon 内部設計（hamgrd 等）。CLI / CONFIG_DB は通常通り埋める |
| `_no_related_cli: true` | `related.cli` のみ空を許容 | CLI 公開コマンドを持たない内部レイヤ（SAI / orchagent 内部 etc.） |
| `_no_related_config_db: true` | `related.config_db` のみ空を許容 | CONFIG_DB に固有テーブルを持たないテーマ（経路計算ロジックの内部解説等） |

`_no_yang` は `_no_related_yang` の旧名で、互換のために引き続き受理する。新規ページは `_no_related_yang` を使うこと。

マーカーは `related:` dict の中に置く:

```yaml
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
```

opt-out マーカーが付いたページは `frontmatter_lint.py` / `find_empty_related.py` / `check_discrepancy_related.py` / `find_partial_empty_related.py` の関連検査から除外される（hard violation・warning ともに抑止）。安易に付けず、「設計として埋まる余地が無い」ページに限定して使うこと。

## verification の意味

| 値 | 意味 | 表示バッジ |
|----|------|----------|
| `stub` | 章 index 等のプレースホルダ | （非表示） |
| `meta` | プロジェクト説明など SONiC 仕様外のページ | （非表示） |
| `hld-only` | 公式 HLD だけを根拠に書いた。コード未確認 | 📘 HLD-only |
| `issue-confirmed` | issue/PR コメントで補強済み | 🔍 Issue-confirmed |
| `code-verified` | 該当実装を読んで一致確認済み | ✅ Code-verified |
| `discrepancy-found` | HLD と実装に差分あり。本文に注記 | ⚠️ Discrepancy-found |
| `runbook-verified` | Runbook 専用。実運用で症状再現性が確認されており、HLD 一致は副次的 | 🛠 Runbook-verified |

## monitor の意味（discrepancy-found 専用タグ）

`verification: discrepancy-found` のページは、HLD と実装の差分の **性質** を表す `monitor:` タグを必ず持つ。Verifier / 読み手が「設計が未着手なのか、それとも実装が進化して別物になったのか」を一目で判別できるようにするため。

| 値 | 意味 | 判定基準 |
|----|------|---------|
| `not_implemented` | HLD は提案段階で、master に対応コードが一切無い | 関連 orch / table / CLI / yang を grep してヒット 0 件。HLD は採用見送りか着手前 |
| `evolved_beyond_hld` | 実装は HLD から進化し、名前・構造・経路が異なる | 機能としては存在するが、CONFIG_DB テーブル名 / 引数 / 変数名 / クラス名 / 設定経路が HLD と一致しない |
| `partially_implemented` | HLD のうち一部だけ取り込まれ、残りは欠落 | 取り込み済み要素と未取り込み要素が **両方** 列挙されており、ユーザに見える機能境界が HLD と一致しない |
| `deprecated` | HLD の方針自体が廃止され、後発別機能に置き換えられた | 「本 HLD は採用されず X に置き換えられている」「migration-to-Y で置換」等を本文に明記 |

判定が迷う場合の優先順位は **`deprecated` > `not_implemented` > `partially_implemented` > `evolved_beyond_hld`**。後発の置き換えがあるなら `deprecated`、全く取り込まれていないなら `not_implemented`、一部のみなら `partially_implemented`、全部実装はあるが形が違うなら `evolved_beyond_hld`。

`verification` が `discrepancy-found` 以外（`hld-only` / `code-verified` 等）でも、将来 monitor タグを再利用する余地はあるが現状は optional 扱い。

軸 6 (完結性) を `monitor` の subtype 別に読み替える詳細なルール（`partially_implemented` の境界明示要件、`evolved_beyond_hld` の差分明示要件、`not_implemented` の N/A 扱い、`deprecated` のリンクのみ評価）は [`meta/quality-audit-guide.md` §5 「`discrepancy-found` subtype 別評価基準」](../quality-audit-guide.md#5-discrepancy-found-subtype-別評価基準) を参照。`partially_implemented` ページの境界明示はフェーズ別境界表（Phase / 実装済 / 未実装 の列）が推奨形であり、`meta/scripts/check_partial_boundary.py` で機械検査される。

## `discrepancy-found` ページの軸 6 評価基準

品質監査 (`meta/quality-audit-*.md`) では各ページを 6 軸 5 点満点で評価しているが、その **軸 6 (完結性)** は通常ページ向けの基準（本文ボリューム / 機能の網羅性 / ops-hint や troubleshooting の有無）で測ると `discrepancy-found` ページが構造的に天井 4 点に張り付く（実装が未着手 / 進化済みのため「機能としての完結」を書きようがない）。

`discrepancy-found` ページは「機能としては完結していなくても、代わりに HLD と実装の差分を整理して読み手に渡す」ことが本来の役目である。したがって軸 6 は **「乖離説明の構造的整理が出来ているか」** に読み替える。具体的には以下の 4 サブ項目で評価する。

| サブ項目 | 5 点満点判定基準 |
|---------|-----------------|
| (a) monitor タグ妥当性 | frontmatter の `monitor:` が `not_implemented` / `evolved_beyond_hld` / `partially_implemented` / `deprecated` のいずれかで、本文の乖離パターンと整合している |
| (b) 「実装との乖離」セクションの構造化 | HLD 側の主張 / 現行 master の状態 / 差分のインパクトの 3 点が分けて記述されている（箇条書き / 表 / 段落いずれの形式でも可） |
| (c) 裏取り evidence | 「実装が存在しない」「別名で実装されている」等の判定根拠が grep 結果 / commit SHA / 該当ファイル行範囲付きの evidence コメントで埋め込まれている |
| (d) 読み手への next-action | 「現行 master ではこの設定経路は使えない」「実機運用では Y を参照」など、HLD と実装が乖離した状況下での読み手の次の一手が明示されている |

4 サブ項目すべて満たせば軸 6 = 5 点。1 つでも欠ければ 4 点以下に減点する。通常ページの「機能としての完結性」では評価しない。

監査ロール (`meta/prompts/reviewer.md`、`meta/quality-audit-*.md` 起票時) は本セクションを参照して `discrepancy-found` ページの軸 6 評価を行うこと。詳細な運用ルールは `meta/quality-audit-guide.md` を参照。

## 引用ルール

- ページ末に **「引用元」セクション必須**。frontmatter `sources` と本文中の脚注を統合する
- 本文中で込み入った主張には脚注 `[^1]` で commit パーマリンクを付与
- HTML コメントで詳細なエビデンス（実コード抜粋・推論）を埋め込む。Verifier がここを根拠に裏取り判定する
- evidence の `source: <repo>/<path>#L<start>-L<end>` の行範囲は **「該当行を含む」程度の精度で良い**。完全一致は要求しない（参照ヒントとしての誤差は許容する）

## related フィールドの表記

- `related.config_db`: テーブル名のみ（例: `BGP_NEIGHBOR`、`PORT_STORM_CONTROL`）
- `related.cli`: コマンドの先頭フォーム（例: `config bgp`、`show interface counters`）
- `related.yang`: YANG モジュール名のみ。**拡張子 `.yang` やリビジョンは付けない**（例: `sonic-bgp`、`sonic-port`）

## title の長さ

- frontmatter `title`（日本語）は **40 字を目安**。長い注釈は本文 H1 以降の説明文で扱う
- nav 表示が崩れない範囲で短く意味重視

## verification-queue.entries[].concerns の表現ガイド

- 各 concern は **動詞句で終わる**（「〜の確認」「〜の実装存在確認」「〜が現行 master にあるか未確認」等）
- 主語は省略可、対象（Orch / daemon / DB スキーマ / CLI / SAI 属性）を必ず含める
- 1 行 60 〜 120 字程度に収める。長くなるなら分ける
- 6 軸を網羅できれば十分: **(1) Orch / daemon の実装存在 (2) CONFIG_DB / STATE_DB スキーマ (3) CLI 取り込み (4) SAI 属性 / API (5) HLD 改訂日と現行 master の乖離 (6) upstream 仕様との差分**

## エビデンスコメントの形式

```markdown
<!-- evidence:
source: <repo>/<path>#L<start>-L<end> (sha: <commit-sha>)
excerpt: |
  <該当コードまたは HLD の生抜粋>
reasoning: <この記述が妥当である理由>
-->
```
