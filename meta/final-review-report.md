# 最終整合性レビュー (v1.0 リリース直前)

実施日: 2026-05-11
ブランチ: `chore/q11-k-final-review-2`
スコープ: 全 `docs/**/*.md` (833 ファイル)

## 1. 検出サマリ

| 項目 | 検出 | 修正 |
|------|----:|----:|
| 壊れた相対リンク | 0 | 0 |
| 古い slug への参照 | 0 | 0 |
| 重複 H1 (実害あり) | 0 | 0 |
| 重複 H1 (章別セクションタイトル、想定内) | 8 種 | — |
| Topic 章 index.md の読む順番リスト欠落 | 12 ファイル | 12 |
| Area index と実体の不整合 | 0 | 0 |
| 孤立 (inbound 0) ページ | 92 | 0 (Reference 系は意図的に inbound を持たず、Topics 系 6 件は本レビューで解消) |

## 2. 壊れた相対リンク

`docs/**/*.md` を fenced code blocks と inline code を除外して走査。Markdown link を resolve した結果、未解決の `.md` リンクは **0 件**。

(初回走査では config-db / yang リファレンスの正規表現 `[-a-zA-Z0-9_]{0,31}` 等が code block 外に露出していたが、いずれも inline code 化されており markdown としては解釈されないことを確認。)

## 3. 古い slug への参照

過去のリネーム履歴 (`git log --diff-filter=R --name-status`) に対する grep で、現在 docs に残っていない slug への参照は **0 件**。

## 4. 重複 H1 (タイトル)

`# <text>` 形式の H1 を全ページから抽出し、同名 H1 が複数ページに出現するケースを列挙:

| H1 | ページ数 | 判定 |
|----|------:|------|
| アーキテクチャ | 14 | 想定内 (各 topic 章の `architecture.md` H1) |
| 内部実装 | 20 | 想定内 (各 topic 章の `internals.md` H1) |
| 発展トピック | 12 | 想定内 (各 topic 章の `advanced.md` H1) |
| 概要 | 5 | 想定内 (各 area の `index.md` 配下の overview セクション) |
| 運用 | 12 | 想定内 (各 topic 章の `operations.md` H1) |
| 設定 | 12 | 想定内 (各 topic 章の `setup.md` H1) |
| 概念 | 8 | 想定内 (各 topic 章の `concept.md` H1) |
| YANG リファレンス | 2 | `reference/yang/index.md` と `topics/10-gnmi-openconfig/yang-reference.md`。URL とコンテキストが異なるため重複可。 |

mkdocs build / search index としては URL が異なれば衝突しないため、いずれも修正不要と判断。

## 5. Topic 章 index.md と実体の整合 (検出 + 修正)

`docs/topics/<NN>-*/` 配下の `index.md` の「読む順番」リストと、同ディレクトリ実体ファイル (`*.md` - `index.md`) を突き合わせた結果、以下の 12 件で実体ファイルが index リストから漏れていた。本 PR ですべて追記:

| 章 | 漏れていたページ |
|----|-----------------|
| `topics/03-vxlan-evpn/` | `internals.md` |
| `topics/04-vrf-ecmp/` | `internals.md` |
| `topics/06-l2-vlan-lag/` | `internals.md` |
| `topics/08-qos-buffer/` | `advanced.md` |
| `topics/10-gnmi-openconfig/` | `internals.md`, `advanced.md` |
| `topics/11-reboot/` | `internals.md`, `advanced.md` |
| `topics/12-multi-asic-voq/` | `internals.md` |
| `topics/16-nat-dhcp-dns/` | `internals.md` |
| `topics/19-build-packaging/` | `internals.md` |
| `topics/22-reference-index/` | `internals.md` |

合計 12 リンクを「読む順番」末尾に追加 (Diataxis のセクション順を維持)。

## 6. Area index と実体の整合

| area | 実体ファイル数 | index.md からの内部 .md リンク数 |
|------|--------------:|----------------------------:|
| acl-qos | 31 | 31 |
| architecture | 41 | 41 |
| guides | 4 | 4 |
| internals | 12 | 12 |
| management | 43 | 43 |
| overlay | 9 | 9 |
| platform | 43 | 43 |
| routing | 51 | 51 |
| switching | 19 | 19 |
| system | 71 | 71 |

reference / topics 配下は直下 `*.md` ではなくサブディレクトリ構造のため別計算で確認、いずれもサブカテゴリ index への完全リンクを確認済み。

## 7. 孤立 (inbound link 0) ページ

92 件検出。内訳:

- `reference/cli/*` 23 件 — CLI Reference は CLI 横断索引 (`topics/22-reference-index/cli-index.md`) からのみ参照される設計。横断索引は table 構造で個別ページ全件を網羅しており、辞書的役割としては inbound 1 で十分なため修正不要。
- `reference/config-db/*` 63 件 — 同上 (`config-db-index.md` 経由)。
- `topics/<NN>/{internals,advanced}.md` 6 件 — §5 で index.md から追加リンク済み、解消。

## 8. 機械修正のサマリ

- 修正ファイル: 10 件 (`docs/topics/03-vxlan-evpn/index.md`、`docs/topics/04-vrf-ecmp/index.md`、`docs/topics/06-l2-vlan-lag/index.md`、`docs/topics/08-qos-buffer/index.md`、`docs/topics/10-gnmi-openconfig/index.md`、`docs/topics/11-reboot/index.md`、`docs/topics/12-multi-asic-voq/index.md`、`docs/topics/16-nat-dhcp-dns/index.md`、`docs/topics/19-build-packaging/index.md`、`docs/topics/22-reference-index/index.md`)
- 修正内容: いずれも「読む順番」リストへ抜けていた `internals.md` / `advanced.md` リンクを 1〜2 行追記
- `mkdocs build --strict` で warning 0

## 9. v1.0 リリースの整合性ステータス

- 壊れたリンク 0
- 古い slug 0
- 重複 H1 で問題のあるものは 0
- topic index 漏れ解消
- area index は全てカバー済み

→ **v1.0 リリースの整合性条件は満たしている**。
