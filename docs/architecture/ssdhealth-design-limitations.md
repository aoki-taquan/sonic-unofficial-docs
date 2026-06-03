---
title: SSD ヘルスチェック 制限事項と HLD-実装乖離
description: SONiC の SSD ヘルスチェック機能の制限事項・干渉する機能・トラブルシューティング、および現行 master と HLD 記述の乖離（ssdutil への移行、sonic_storage 再構成、ssdmond 未取り込み）を整理する。
area: architecture
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: evolved_beyond_hld
sources:
- repo: sonic-net/SONiC
  path: doc/ssdhealth/ssdhealth_design.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  _no_related_yang: true
  config_db: []
  cli:
  - show platform ssdhealth
  yang: []
---

# SSD ヘルスチェック 制限事項と HLD-実装乖離

このページは [SSD ヘルスチェック（概要ハブ）](ssdhealth-design.md) の派生で、**制限事項・干渉機能・トラブルシューティング・[HLD](../reference/glossary.md#term-hld) と現行実装の乖離** に絞って整理する。概念・運用・実装の各ページは概要ハブから辿る。

## 1. 制限事項

- **smartctl のデータベースに無い disk** は health / 温度の取得が **N/A** になりうる。HLD 自身が「some information can be unavailable or incomplete」と明言している[^1]。
- ベンダプラグインが用意されていないプラットフォームは `SsdBase` の fallback（smartctl）に依存。`vendor` モードの出力は基本的に空。
- pmon デーモン (`ssdmond`) は **オプション** であり、HLD では Open Question として残っている。常時監視・アラート発火が必要なら別途実装の確認が必要[^1]。
- 値が取れない場合の表現が API ごとに異なる（health=`-1`、temp=`0`、文字列系=空）。`0 ℃` と「取得不可」が同義になり得る点に注意[^1]。

## 2. 干渉する機能

- **pmon (Platform Monitor)**: `ssdmond` を入れると pmon docker 内に常駐デーモンが増える。閾値判定とアラート発火経路を pmon 側に統合できる。
- **smartmontools / smartctl パッケージ**: ビルドイメージに 1.9M 程度の追加。`sonic-buildimage` 側のパッケージ取り込みに依存[^1]。
- **plugin 配置規約**: `device/{{vendor}}/platform/plugins/ssdutil.py` は **プラットフォームプラグインの一般則** に乗る。他のプラグイン（thermal, fan 等）と同じ取り込み方式の延長線上に位置づく。
- **[SNMP](../reference/glossary.md#term-snmp)**: HLD の Open Questions に「SNMP needed?」とあるとおり、SNMP MIB への露出は本 HLD のスコープ外[^1]。

## 3. トラブルシューティング

- `Health: N/A`: smartctl が当該 disk を識別できていない可能性。`smartctl -i /dev/sdX` で raw に確認。ベンダプラグインが装備されているか `device/<vendor>/platform/plugins/ssdutil.py` の存在を確認。
- `vendor` モードが空: `SsdUtil` の `get_vendor_output()` が未実装、もしくはベンダツールバイナリが image に含まれていない。
- `Temperature: 0` と `N/A` の区別: API の戻り値仕様上、温度の取得不可は `0` となる。`0℃` と取得不可が見分けにくい点は HLD の制約[^1]。
- `show platform ssdhealth` が `command not found`: `show/main.py` の `platform` メニューに項目が登録されているか、`ssdhealth` スクリプトが PATH にあるかを確認。

## 4. HLD と実装の差分

!!! diff "HLD と実装の差分"
    2026-05-09 時点の現行 master を裏取り。HLD の二段プラグイン構造（`SsdBase` / `SsdUtil`）と CLI（`show platform ssdhealth`）は概ね素直に取り込まれているが、HLD で Open Question として残されていた **常時監視デーモン `ssdmond` は現状実装が見当たらない**。さらに、HLD で示された `sonic_ssd/ssd_base.py` の配置は master では `sonic_storage/` 配下に再構成され、独立スクリプト `ssdhealth` も `ssdutil` Python パッケージに置き換わっている。

    | 項目 | HLD | 現行 master | 結果 |
    |------|-----|------|------|
    | `SsdBase` 基底クラス | `sonic_ssd/ssd_base.py` 必須 | `sonic-platform-common/sonic_platform_base/sonic_storage/storage_base.py` 等に再構成 | △ パス変更 |
    | `SsdUtil` ベンダー派生 | 必須 | `device/{vendor}/platform/plugins/ssdutil.py` の plugin 取り込み | ✓ |
    | `show platform ssdhealth [verbose\|vendor]` | 必須 | `sonic-utilities/show/platform.py` のサブコマンドに該当（内部で `ssdutil -d <device>` を呼ぶラッパ） | ✓ |
    | 独立スクリプト `ssdhealth` | `sonic-utilities/scripts/ssdhealth` 必須 | 存在しない。Python パッケージ `sonic-utilities/ssdutil/` (`__init__.py` / `main.py`) が唯一の実体 | ⚠️ 名前変更 |
    | `ssdmond` 常時監視デーモン | Open Question | 現行 `sonic-platform-daemons/` 配下に `ssdmond` 名のデーモン無し | ⚠️ 未取り込み |
    | SNMP MIB への露出 | Open Question | 未取り込み（HLD 上もスコープ外と明記） | ⚠️ スコープ外 |

    **差分の中身**: 常時バックグラウンドで SSD 健全性を polling し、閾値割れ時に syslog / SNMP trap を発火する `ssdmond` は HLD で「optional」扱いのまま、コミュニティ master には取り込まれていない。健全性確認は **on-demand な `show platform ssdhealth` 実行** に依存する。

    **読者への影響**:

    - SSD 寿命警告を「壊れた後に techsupport で気づく」運用になるリスク。連続監視には外部ツール（cron 化、telemetry、Prometheus exporter 等）が必要。
    - `Temperature: 0 ℃` を見たときに「冷えている」のか「取得不可」なのか API 戻り値だけでは判別できない。
    - HLD のクラスパス `sonic_ssd/ssd_base.py` を grep してもヒットしない。master では `sonic_storage/` を見る。

    **回避策 / 対応方法**:

    - 常時監視が必要なら、`show platform ssdhealth` を cron + syslog で wrap するか、`smartctl` を直接 polling する独自 exporter を用意する。
    - 温度 `0` を観測したら、必ず `smartctl -A /dev/sdX | grep -i temperature` で raw 値を併読する運用にする。
    - ベンダープラグインが無い platform で `vendor` モードが空になる場合は、`device/<vendor>/platform/plugins/ssdutil.py` の存在を `dpkg -L sonic-platform-<vendor>` 等で確認。

    ### 再裏取り追補（2026-05-11）

    - `SsdBase` / `SsdUtil` / `show platform ssdhealth` は実装済み (`sonic-platform-common/sonic_platform_base/sonic_storage/`, `sonic-utilities/show/platform.py`)。HLD の主要機能は到達済み。
    - HLD の Open Question として残されていた `ssdmond` 常時監視デーモンは未実装。`sonic-platform-daemons/` 配下に `ssdmond` ディレクトリ無し。
    - SNMP MIB 露出も未実装（HLD でも明示的にスコープ外と記載）。
    - 関連 PR: `sonic-platform-common` への SsdBase 取り込みは 2019-2020 年に merge 済み。`ssdmond` は提案 PR 無し。
    - **追加運用コマンド**: 常時監視を要する場合 — `*/15 * * * * /usr/local/bin/show platform ssdhealth | logger -t ssdhealth` の cron 化で代替。

    > 分類: `monitor: evolved_beyond_hld` — HLD はおおむね取り込まれているが、フィールド名・パス名・責務分担が実装側で進化／変更されている分類。

## 5. 関連ページへの導線

- [ssdhealth-design.md](ssdhealth-design.md) — 概要ハブ
- [ssdhealth-design-concepts.md](ssdhealth-design-concepts.md) — 概念
- [ssdhealth-design-operations.md](ssdhealth-design-operations.md) — CLI / 運用
- [ssdhealth-design-internals.md](ssdhealth-design-internals.md) — API / デーモン

## 実装との乖離

`monitor: evolved_beyond_hld` の HLD と実装の差分。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [SSD ヘルスチェック 制限事項と HLD-実装乖離 親ページ](ssdhealth-design.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/ssdhealth/ssdhealth_design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 1d579f83f1e2 -->

