---
title: DIP=SIP PTF 検証 制限事項と HLD-実装乖離（pytest 移行）
description: DIP=SIP PTF 検証テストの制限事項・干渉する機能・トラブルシューティング、および ansible/ptftests から sonic-mgmt/tests/ipfwd/test_dip_sip.py (pytest) への移行に伴う HLD-実装乖離を整理する。
area: architecture
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: evolved_beyond_hld
sources:
- repo: sonic-net/SONiC
  path: doc/dip-sip/DIP=SIP_HLD.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  _no_related_yang: true
  config_db: []
  cli: []
  yang: []
---

# DIP=SIP PTF 検証 制限事項と HLD-実装乖離

このページは [DIP=SIP PTF 検証（概要ハブ）](dip-sip-ptf-validation-high-level-design.md) の派生で、**制限事項・干渉機能・トラブルシューティング・pytest 移行に伴う [HLD](../reference/glossary.md#term-hld) 乖離** に絞って整理する。

## 1. 制限事項

- **対応 topology が固定リスト**: `t0` 系と `t1` 系の特定型のみ。それ以外の topology では `dip_sip.yml` の前処理が想定外で動かない可能性がある[^1]。
- **[RIF](../reference/glossary.md#term-rif) 種別が PORT / [LAG](../reference/glossary.md#term-lag) のみ**: [VLAN](../reference/glossary.md#term-vlan) RIF など他の RIF 種は HLD で言及されていない[^1]。
- **テスト対象は L3 ルーティングの可否のみ**: [ACL](../reference/glossary.md#term-acl) / RPF / uRPF など個別機能との相互作用までは本テストでカバーしない。「ルーティングが成立すること」が単一の合否条件[^1]。

## 2. 干渉する機能

- **uRPF (Unicast Reverse Path Forwarding)**: DIP=SIP の本テストは uRPF が **strict mode で有効化されていると pass しない可能性** がある（SRC_IP が自分宛と等価のため）。HLD は uRPF 設定との相互作用には触れていないが、テスト時は確認が必要。
- **ACL**: SRC_IP / DST_IP 同一を deny する ACL を設定していると、本テストは fail する。テスト前提の ACL 構成については HLD 内に記述がない。
- **VM ベースの host エミュレーション**: PTF docker / VM の準備は本 HLD のスコープ外。`sonic-mgmt` の標準 testbed 構築フローに依存する。

## 3. トラブルシューティング

- テストが fail する: ログ `/tmp/dip_sip.DipSipTest.<ts>.log`（旧 ansible 経路）または pytest log (`logs/` 配下) の expected / received ダンプを比較[^1]。MAC が書き換わっていなければ L3 ルーティングが起きていない（L2 で落ちている可能性）。
- TTL が想定と違う: TTL/HL が 1 減っていない場合、DUT 側で L3 forwarding せず L2 で抜けている可能性。
- port index 不一致: `dst_port_ids` / `src_port_ids` の配列が空、または PTF port 番号と DUT 側の物理 port のマッピングがズレている。`dip_sip.yml` の前処理ログ（minigraph / [LLDP](../reference/glossary.md#term-lldp) gather）を確認。

```bash
# PTF テスト失敗時の確認手順
cat /tmp/dip_sip.DipSipTest.*.log | tail -200
ls -la logs/ | grep -i dip_sip
# DUT 側で L3 forwarding が動いているか
show ip route <dst-prefix>
show interfaces neighbor expected
```

## 4. HLD と実装の差分（pytest 移行）

!!! diff "HLD と実装の差分"
    2026-05 時点でテスト実体は **PTF スタンドアロンから pytest 配下へ移行済み** で、HLD の記述（ansible + ptftests）はファイル配置レベルで古い。

    ### 1. どこで乖離が確認されたか

    - 現行の本体は `sonic-mgmt/tests/ipfwd/test_dip_sip.py`（pytest 形式）。HLD が指す旧来の `ansible/roles/test/files/ptftests/dip_sip.py` は **削除済み**（GitHub 検索でヒット 0）。
    - `sonic-mgmt/ansible/roles/test/tasks/dip_sip.yml` は 114 バイトのラッパに縮退しており、中身は `include_tasks: roles/test/tasks/pytest_runner.yml` + `test_node: ipfwd/test_dip_sip.py` のみ。HLD が描写した「前処理 → ptf_runner で `dip_sip.DipSipTest` を起動」という直接呼び出し構造は残っていない。
    - 一方で `sonic-mgmt/ansible/roles/test/vars/testcases.yml`（11721 B）は実在し、testbed / topology 定義は HLD 当時から大きく変わっていない。

    ### 2. HLD と実装の差分の中身

    HLD 当時の構造:

    ```text
    ansible playbook → dip_sip.yml (前処理) → ptf_runner → dip_sip.py (PTF テスト)
    ```

    現行:

    ```text
    ansible playbook → dip_sip.yml (ラッパ) → pytest_runner.yml → pytest tests/ipfwd/test_dip_sip.py
    ```

    すなわち **テストロジック本体は pytest 側に移植され、ansible は単に pytest 起動を仲介するだけ** になった。テストの意味論（DIP=SIP パケットが転送される / TTL が 1 減る / 期待ポートから出る）は HLD と同じだが、起動ファイル名・配置・前処理の責務が違う。

    ### 3. 読者への影響

    - HLD の `dip_sip.py` を探しても見つからない。`tests/ipfwd/test_dip_sip.py` を直接読まないと現行の挙動が分からない。
    - ログ出力先・テスト名（`DipSipTest` クラス → pytest case 名）が変わっており、過去のトラシュー手順「`/tmp/dip_sip.DipSipTest.<ts>.log` を grep」も pytest 化以降は `pytest --log-file` / `logs/` 配下を見るのが正解。
    - 新しい topology 追加時の編集箇所も `vars/testcases.yml` ではなく pytest 側の fixture / pytestmark の場合がある。

    ### 4. 回避策 / 対応方法

    - **テストを走らせる**: 旧 ansible 直叩き `ansible-playbook ... -e 'testcase_name=dip_sip'` は **そのまま動く**（ラッパが pytest を呼ぶため）。HLD の旧手順を保ったまま実行可能。
    - **テストを読み解く**: 本体ロジックは `sonic-mgmt/tests/ipfwd/test_dip_sip.py` を `grep -n` で参照する。クラス名 / log 名のドキュメント不一致は本ページの記述ではなくコード側を真として扱う。
    - **新規 topology / RIF を追加する**: pytest 側の parametrize / fixture を編集し、必要なら `dip_sip.yml` の `test_node` 指定とは別経路で `pytestmark` の設定を変える。

    ### 再裏取り追補（2026-05-11）

    - 旧 PTF スクリプト `ansible/roles/test/files/ptftests/dip_sip.py` は GitHub `sonic-net/sonic-mgmt` master でヒット 0（削除確定）。
    - 現行本体 `tests/ipfwd/test_dip_sip.py` は pytest 形式で、`DipSipTest` 同等のテストが pytest case にリファクタされている。
    - `ansible/roles/test/tasks/dip_sip.yml` (114 B) は pytest_runner ラッパに縮退。HLD の前処理／後処理ステップは pytest fixture (`tests/common/fixtures/duthosts.py` 等) に移行。
    - 関連 PR: `sonic-mgmt` における ansible→pytest 移行は 2021-2023 年に複数 PR で段階実施済み（特定 PR ID は HLD では未参照）。
    - **追加実行コマンド**: 現行で走らせる場合 — `cd sonic-mgmt/tests && pytest ipfwd/test_dip_sip.py --topology=t0 --testbed=<tb>`。旧 `ansible-playbook ... -e testcase_name=dip_sip` 経路もラッパ越しに動作する。

    > 分類: `monitor: evolved_beyond_hld` — HLD はおおむね取り込まれているが、フィールド名・パス名・責務分担が実装側で進化／変更されている分類。

## 5. 関連ページへの導線

- [dip-sip-ptf-validation-high-level-design.md](dip-sip-ptf-validation-high-level-design.md) — 概要ハブ
- [dip-sip-ptf-validation-high-level-design-concepts.md](dip-sip-ptf-validation-high-level-design-concepts.md) — 概念
- [dip-sip-ptf-validation-high-level-design-operations.md](dip-sip-ptf-validation-high-level-design-operations.md) — ファイル構成 / 実行
- [dip-sip-ptf-validation-high-level-design-internals.md](dip-sip-ptf-validation-high-level-design-internals.md) — パケット仕様

## 実装との乖離

`monitor: evolved_beyond_hld` の HLD と実装の差分。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [DIP=SIP PTF 検証 制限事項と HLD-実装乖離 親ページ](dip-sip-ptf-validation-high-level-design.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/dip-sip/DIP=SIP_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: e919cc931c5a -->

## 確認コマンド

dip-sip-ptf limitations の動作確認に使う代表コマンド:

```bash
# 基本動作確認
show platform summary
show version
docker logs --tail 200 $(docker ps --format "{{.Names}}" | head -1)
```

