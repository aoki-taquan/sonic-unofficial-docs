---
title: リファレンス横断索引
area: topics
verification: meta
last_verified: 2026-05-10
---

# リファレンス横断索引

この章は、`docs/reference/` 配下に集めた CLI / CONFIG_DB / YANG の辞書ページと、Phase B で新設された機能章 (`docs/topics/`) との間を行き来するための索引である。機能章は読み物として運用導線を提供し、reference は辞書として「テーブル名」「コマンド名」「モジュール名」から逆引きできる。両者は別物だが、本来は両方向にリンクされていることが望ましい。

`docs/reference/` 配下の現状は以下の通り (2026-05-10 時点)。

- CLI ページ: 48 件 (`config-*` / `show-*` / `debug-*` / `clear` / `reboot-fast-warm` / `sonic-*` ツール)
- CONFIG_DB ページ: 76 件 (table family ごと)
- YANG ページ: 39 件 (`sonic-*` モジュールごと)

この章では、これらを「機能章のどこから引かれるか」「逆に辞書からどの章へ戻るか」の対応表で並べ直す。既存 reference ページの本文と frontmatter は変更しない。

## 想定読み手の質問

- CLI / CONFIG_DB / YANG の辞書ページは機能章からどう探すか。
- 既存の `docs/reference/` は章本文に吸収するのか、独立した辞書として残すのか。
- カテゴリページ (`docs/categories/`) と topics 章はどう役割分担するか。
- discrepancy / reference gap はどこに置き、誰が消化していくのか。

## 読み進め方

1. [概要](concept.md): reference を辞書として残す設計と、章 / 辞書 / カテゴリの 3 層の関係。
2. [CLI 横断索引](cli-index.md): `config-*` / `show-*` / `debug-*` / ツール系を機能章ごとに並べた表。
3. [CONFIG_DB 横断索引](config-db-index.md): table family を機能章ごとに並べ、逆引きを提供する。
4. [YANG 横断索引](yang-index.md): native SONiC YANG と OpenConfig / management framework との関係。
5. [品質と gap](quality-gaps.md): discrepancy ページと reference gap の追跡方法。

## 関連ページ

- [リファレンス](../../reference/index.md)
- [CLI リファレンス](../../reference/cli/index.md)
- [CONFIG_DB リファレンス](../../reference/config-db/index.md)
- [YANG リファレンス](../../reference/yang/index.md)
- [Discrepancies](../../_meta/discrepancies.md)
