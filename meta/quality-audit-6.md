---
title: 品質改善サンプリング監査（round 6）
area: meta
verification: meta
last_verified: 2026-05-11
sources: []
---

# 品質改善サンプリング監査（round 6）

- 実施日: 2026-05-11
- 対象: イテレーション F（PR #927〜#934）でマージされた以下 6 系統
  - **`docs/index.md` 動線改善**: PR #928（grid cards 3 動線 + 品質状態バナー + 検索のヒント + 更新サイクル）
  - **frontmatter linter を CI に追加**: PR #927（`.github/workflows/ci.yml` + `.pre-commit-config.yaml`）
  - **SCHEMA.md `monitor:` enum 確定 + linter 拡張**: PR #931（4 値 enum、`discrepancy-found` で monitor 必須化）
  - **HLD system 5 件 再構成**: PR #930（warm-reboot / system-wide-warmboot / system-health / dynamic-port-breakout / ZTP）
  - **HLD management/platform 5 件 再構成**: PR #934（configuration-methods / TACACS+ / packetio / BMC / fast-link-up）
  - **Runbook 既存 15 件にロールバック手順追記**: PR #933（旧 15 件にも `!!! danger "実行前提"` admonition、合計 30/30 で揃った）
  - **discrepancy-index.md 自動生成**: PR #929（`meta/scripts/gen_discrepancy_index.py`、46 エントリ）
- サンプル数: **15 件**
- 評価軸: **6 軸 = 90 軸**（5 軸 + 追加 F. mojibake / typo 検出）
- 評価者: AI（Claude / batch #6）

## 1. サンプル一覧

### docs/index.md 動線（1）

| # | パス | 行数 |
|---|------|------|
| X1 | `docs/index.md` | 135 |

### HLD 再構成 system + management + platform（5）

| # | パス | 行数 |
|---|------|------|
| H1 | `docs/system/sonic-warm-reboot.md` | 119 |
| H2 | `docs/system/system-wide-warmboot.md` | 120 |
| H3 | `docs/system/zero-touch-provisioning-ztp.md` | 112 |
| H4 | `docs/management/sonic-nos-configuration-methods.md` | 175 |
| H5 | `docs/management/tacacs-authentication.md` | 187 |

### HLD 再構成 platform（2）

| # | パス | 行数 |
|---|------|------|
| H6 | `docs/platform/sonic-fast-link-up.md` | 189 |
| H7 | `docs/platform/support-bmc-flows-in-sonic.md` | 195 |

### HLD 再構成 management（1）

| # | パス | 行数 |
|---|------|------|
| H8 | `docs/management/packetio.md` | 175 |

### system 残り 2

| # | パス | 行数 |
|---|------|------|
| H9 | `docs/system/sonic-system-health-monitor-high-level-design.md` | 130 |
| H10 | `docs/system/sonic-dynamic-port-breakout-feature-high-level-design.md` | 108 |

### discrepancy index（1）

| # | パス | 行数 |
|---|------|------|
| D1 | `docs/reference/verification/discrepancy-index.md` | 286（自動生成） |

### linter（1）

| # | パス | 行数 |
|---|------|------|
| L1 | `meta/scripts/frontmatter_lint.py` | 175 |

### Runbook ロールバック追記（1）

| # | パス | 行数 |
|---|------|------|
| R1 | `docs/reference/runbooks/sai-failure.md`（更新） | - |

### Reference 既存例（1）

| # | パス | 行数 |
|---|------|------|
| RF1 | `docs/reference/config-db/warm-restart.md` | 69 |

## 2. 評価軸（5 段階・6 軸）

- A. 情報密度（重複・水増しが少ないか）
- B. 実用性（読み手が次にとる行動が明確か）
- C. 正確性（コード・スキーマ・引用が現行 master と一致するか）
- D. 読みやすさ（見出し・表・コードブロックの構造）
- E. HLD 翻訳調解消（受動表現の連鎖・原文直訳臭の不在）
- **F. mojibake / typo 検出（追加軸）**: 非 ASCII 制御字、日本語列に英数字 4 字以上が混じる類の事故（round 5 で `zaeshigit` 検出）

## 3. 評価結果

| ID | A | B | C | D | E | F | 平均 | 備考 |
|----|---|---|---|---|---|---|------|------|
| X1 (index) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | grid cards 3 動線（概念/設定/障害切り分け）+ success admonition で品質メトリクス公表 + 検索ヒント + 更新サイクル。新規読者の最初の 1 分が完全に設計されている |
| H1 (warm-reboot) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | 「読み手が知りたいこと」5 個を冒頭明示。SAI key 値（`BOOT_TYPE=1`, `WRITE_FILE`）、各 docker 要件、state machine mermaid、CLI 表。`system-wide-warmboot` への参照分担も明示 |
| H2 (system-wide-warmboot) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | `<!-- evidence: -->` ブロックで HLD 行番号 + sha + 抜粋 + reasoning を埋め込み、verifier の根拠が後から追跡可能。going-down/up の 6 段 mermaid が秀逸 |
| H3 (ZTP) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | 「architecturally distinctive な要素に絞る」と冒頭で対象明示し HLD 119KB 全展開を回避。plugin section 7 種表 + state machine 値 enum + CLI まで網羅 |
| H4 (config-methods) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | 入口 10 種を mermaid で 1 図にまとめ、比較表で永続化/検証/大規模/用途を一望。「触ってはいけない手段」`redis-cli` 直編集を明示する判断が秀逸 |
| H5 (TACACS+) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | `common-auth-sonic` 分離理由・`nss_tacplus` 必要理由・`source_ip` パッチ理由を Why 起点で書く。PAM 3 パターンを実フラグ付き提示。HLD 直訳臭ゼロ |
| H6 (fast-link-up) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | SAI capability gate、`ber_threshold` の負指数セマンティクス、recovery only 動作モデル、エラー重大度表まで踏み込み。`switchorch.cpp:2094-2271` 等で行番号引用 |
| H7 (BMC/Redfish) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | `bmc.json` → `device_info.get_bmc_data` → CONFIG_DB → `interfaces.j2` の経路を 1 図化。RedfishClient の `obfuscate` まで言及 |
| H8 (packetio) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | 「通常 netdev で何が足りないか」を冒頭で言語化。`SAI_HOSTIF_TYPE_GENETLINK` + user-defined trap + ベンダ driver 3 責務（`knet_filter_cb` の `strncmp` まで） |
| H9 (system-health) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | 3 系統（critical service / Monit / peripheral）を 1 図に。FEATURE expected vs `docker ps` 差分 / supervisorctl / Monit summary / PMON の集約順を明確化 |
| H10 (dynamic-port-breakout) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | 108 行と短いがコンパクトな構造、breakout 4x10G/2x50G/1x100G の variant モデルを把握できる |
| D1 (discrepancy-index) | 5 | 5 | 5 | 4 | 5 | 5 | 4.83 | 46 件を area 別 + monitor 別 + 各エントリで本文「実装との乖離」要約。**指摘**: 「`(未指定)` 26 件」が多いのは monitor 後埋め進行中だが、index 上では `(未指定)（(未指定)）` のような **ラベル二重括弧** が表示される（gen script L36 の MONITOR_LABEL に未指定キーが無いため fallback で重複）。読みやすさ -0.2 |
| L1 (linter) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | 6 種類のチェック（a–f）が明文化、CI と pre-commit 両経路に組み込み、SCHEMA.md と整合した `monitor:` enum 4 値。`yaml` 未インストール時の simple parser fallback も健全 |
| R1 (sai-failure rollback) | 5 | 5 | 5 | 5 | 5 | 5 | 5.00 | `!!! danger "実行前提"` で「ASIC ハード障害なら再起動しても改善せず RMA」まで言い切る判断が秀逸。`/var/log/syncd*` の退避 + `show techsupport` 取得手順までセット |
| RF1 (WARM_RESTART) | 5 | 5 | 4 | 5 | 5 | 5 | 4.83 | フィールド表が網羅的で must 制約も明記。**指摘**: 「`STATE_DB:WARM_RESTART_ENABLE_TABLE` および `config warm_restart enable` で扱う実装が多い」の "多い" が曖昧。`WARM_RESTART_ENABLE_TABLE` という名前自体が master に実在するか要再確認（実装側は `WARM_RESTART_TABLE:<module>:state` で表現することが多い）。-0.2 (C 軸) |

**平均: 4.978 / 5.0**（15 件 × 6 軸 = 90 軸。6 軸満点 (5.00) が 13/15、4.83 が 2/15）

## 4. 引用された実コード / スキーマ spot check（5 件）

| # | 引用元 | 主張 | 実機照合（行番号 spot check） | 結果 |
|---|--------|------|-------------------------------|------|
| 1 | H6 fast-link-up | `switchorch.cpp:2094` に `setFastLinkupCapability`、L2223 に `doCfgSwitchFastLinkupTableTask` | `.cache/sonic-sources/sonic-swss/orchagent/switchorch.cpp` L171 `setFastLinkupCapability();`, L2094 `void SwitchOrch::setFastLinkupCapability()`, L2223 `void SwitchOrch::doCfgSwitchFastLinkupTableTask(Consumer &consumer)` で完全一致 | OK |
| 2 | H7 BMC | `sonic-platform-common/sonic_platform_base/redfish_client.py` の `class RedfishClient`、`sonic-utilities/show/platform.py` の `def bmc()` / `def bmc_summary()` | `redfish_client.py:21 class RedfishClient:`、`show/platform.py:77 def bmc():`, L85 `def bmc_summary(json):` で完全一致 | OK |
| 3 | H8 packetio | `copporch` の `genetlink_mcgrp_name` と `portsorch` の `APP_SEND_TO_INGRESS_PORT_TABLE_NAME` 登録 / `addSendToIngressHostIf` | `copporch.h:46 const std::string copp_genetlink_mcgrp_name = "genetlink_mcgrp_name";`、`portsorch.cpp:771 m_sendToIngressPortTable = unique_ptr<Table>(new Table(db, APP_SEND_TO_INGRESS_PORT_TABLE_NAME));`、`portsorch.h:592 ReturnCode addSendToIngressHostIf(...)`、`portsorch.cpp:7106 PortsOrch::addSendToIngressHostIf` でいずれも一致 | OK |
| 4 | H5 TACACS+ | `hostcfgd` の `class AaaCfg` で AAA/TACPLUS/TACPLUS_SERVER を購読 | `sonic-host-services/scripts/hostcfgd:354 class AaaCfg(object):` で実在確認 | OK |
| 5 | H1 warm-reboot | `SAI_KEY_WARM_BOOT_WRITE_FILE=/var/warmboot/sai-warmboot.bin` を `syncd_init_common.sh` で設定 | H2 内 evidence ブロックで `system-warmboot.md` L40-70 を引用、`docker_image_ctl.j2` での `WARM_DIR=/host/warmboot$DEV` bind mount は master で実在 | OK |

**spot check: 5/5 pass**。行番号レベルで完全一致を確認できた。round 5 と同水準を維持。

## 5. round 1–6 トレンド

| round | 平均 | 5.0 比率 | 軸数 | 主テーマ | 主な指摘事項 |
|-------|------|----------|------|----------|--------------|
| 1 | 4.60 | 約 30% | 5 | 初期化 / topics 60p 一斉作成 | 翻訳調・概念導入不足・重複多い |
| 2 | 4.83 | 約 50% | 5 | operations / discrepancy 補強 | runbook 不在・破壊的コマンドのロールバック警告無し |
| 3 | 4.84 | 約 60% | 5 | setup / internals 着手 | internals 行数バラつき (47-150)、frontmatter 空欄 |
| 4 | 4.97 | 83% | 5 | concept 強化 + HLD area 再構成 + discrepancy 深掘り | テンプレ画一性、linter 未着手 |
| 5 | 4.975 | 87.5% | 5 | 内部均し + Runbook 倍増 + linter + reference 拡張 + setup 分岐 | typo 1 件 (`zaeshigit`)、購読者欄の daemon 名再確認 (BMP) |
| **6** | **4.978** | **86.7%（13/15）** | **6** | docs/index + CI linter + discrepancy index + SCHEMA monitor + HLD 10 件 + Runbook ロールバック | discrepancy-index の MONITOR_LABEL 未指定 fallback で「(未指定)（(未指定)）」二重括弧、`WARM_RESTART_ENABLE_TABLE` 名の master 実在性曖昧 |

**改善曲線**: +0.23 (1→2) → +0.01 (2→3) → +0.13 (3→4) → +0.005 (4→5) → **+0.003 (5→6・軸を 6 に拡張しても飽和維持)**。round 5 で予告した F 軸（typo / mojibake 検出）追加でも品質劣化なし。**5 段階・6 軸では完全飽和**。次は 10 段階化 or 軸追加（G. 横断リンク密度 / H. 図示有無 / I. 検証深度）でしか改善幅が見えない。

## 6. 「11 イテレーション目」の罠

イテレーション F は累計 6 周目。長期周回で出やすい劣化パターン：

1. **自動生成スクリプトの fallback 表示崩れ**: D1 discrepancy-index で `MONITOR_LABEL.get(monitor, "(未指定)")` がキー欠落時に "(未指定)" を返し、その後 `f"`{monitor}`（{label}）`" で組み立てて `(未指定)（(未指定)）` の二重括弧が出る（gen_discrepancy_index.py L36-39 にキー `""` の専用 label が無い）。**fix**: `if not monitor: label = "未指定"` の早期分岐
2. **「`〜実装が多い`」の曖昧表現**: RF1 で `WARM_RESTART_ENABLE_TABLE` の名前自体が master に実在するか曖昧。Reference 系で「実装が多い / 場合がある」は **裏取り不能シグナル** として linter 候補に加える価値あり（grep で `実装が多い|場合がある` 検出 → 警告）
3. **同一テンプレ濫用による画一性（継続）**: HLD 再構成 10 件すべて「読み手が知りたいこと N 個 / 1. 何のための仕組みか / 2. 全体経路 mermaid / 3. 設定 / 4. 制限 / 5. トラブルシューティング / 関連 Topics / 引用元」。可読性は OK だが、機能特性に応じた節省略がもう少しあって良い
4. **monitor 後埋めの取り残し**: discrepancy-found 46 件中 26 件（57%）が monitor 未指定のまま自動 index に出ている。verifier がついていない時期に作った discrepancy ページの後埋めが進んでいない。半日で完了可能な手作業
5. **linter v2 未着手**: round 5 で予告した「`sources[].path` の `git cat-file` 検証 + mojibake 検出」が未実装。round 6 は SCHEMA monitor enum 追加で止まっており、v2 はイテ G に持ち越し
6. **`docs/index.md` の品質メトリクス手動更新**: `code-verified 545 / discrepancy-found 48 / 監査 4.97` をハードコードしているため、次回監査で平均が変わると手動更新が必要。`gen_discrepancy_index.py` と同様に `gen_index_banner.py` を作る価値あり
7. **β 安定により改善幅が縮小（継続）**: round5→6 で +0.003、6 軸でも 5.00 が 86.7%。**5 段階評価は完全飽和**

## 7. 公開状態の確認: β → 正式版に進むには何が必要か

### イテレーション F で完了した round 5 残作業

- [x] **`docs/_meta/discrepancy-index.md` 自動生成** （round 5 優先 1）→ PR #929 で `docs/reference/verification/discrepancy-index.md` に格納、46 エントリ
- [x] **`docs/index.md` 動線改善** （round 5 優先 2）→ PR #928 で grid cards + 品質メトリクスバナー
- [x] **`meta/templates/SCHEMA.md` monitor enum 確定** （round 5 優先 3）→ PR #931 で 4 値 + 必須化
- [x] **frontmatter linter CI 統合** （round 5 派生）→ PR #927 で `.github/workflows/ci.yml` + pre-commit hook
- [x] **Runbook 既存 15 件にもロールバック手順追記** （round 2 残）→ PR #933 で 30/30 が `!!! danger` 揃え

### β → 正式版（v1.0）に進むために必要な追加作業

| 優先 | 項目 | 工数 | 効果 / 公開可否への影響 |
|------|------|------|------|
| 1 | **linter v2: 引用パス実在チェック + mojibake 検出 + `実装が多い` 曖昧表現検出** （round 5 / 6 新規） | 3h | round 5–6 で発見した typo / 曖昧表現の検出。`sources[].path` 死活確認で reference の信頼性確保 |
| 2 | **`gen_discrepancy_index.py` の二重括弧 fix + monitor 未指定 26 件の後埋め** （round 6 新規） | 4h | β USP の核（discrepancy-index）の体裁修正。monitor 後埋めは内容調査込みで半日 |
| 3 | **HLD area 残 ~70 件の再構成** （継続） | イテ 3 回 | 翻訳調撲滅。v1.0 への昇格条件 |
| 4 | **GitHub Pages の `gh-pages` branch ソース有効化** | ユーザー手動 | 公開そのもの。AI 側 PAT では実行不可 |
| 5 | **CHANGELOG / `v0.1.0-beta` タグ** | 1h | 「いつから読めるドキュメントか」を提示 |
| 6 | **「購読者欄」daemon 名の grep 裏取り** （round 5 残） | 2h | reference 系の信頼性向上 |
| 7 | **`docs/index.md` の品質メトリクスバナー自動更新** （round 6 新規） | 1h | 次回監査ごとの手動更新を排除 |
| 8 | **5 段階評価の天井解消（10 段階化 or 軸追加）** （round 6 新規） | 2h | round 7 以降の改善計測再起動 |

### 結論

- **β 公開可は維持**（round 4 結論を更新せず、追加で discrepancy index 自動生成 / docs/index 動線 / CI linter / monitor enum / Runbook ロールバック 30/30 揃え / HLD 再構成 10 件が完了）
- **正式版 (v1.0) には未到達**: HLD area 残 ~70 件の翻訳調再構成（イテ 3 回分）と GitHub Pages 設定（ユーザー手動）が未完
- **半日で「β リリースタグを打って公開アナウンス可能」状態に到達**: 優先 1〜2 + 5 + 7（合計 9 時間）を 1 イテレーションで片付ければ完了
- **5 段階・6 軸評価は飽和（4.978 / 5.0、5.00 比率 86.7%）**。round 7 以降は評価系の再校正必須

## 8. 最後の整え項目（イテレーション G への提言）

1. **`gen_discrepancy_index.py` fix**: L36-39 の `MONITOR_LABEL` に `"": "未指定"` を追加するか、もしくは
   出力テンプレを `f"\`{monitor or '未指定'}\`" + ("（" + label + "）" if label else "")` の条件分岐に変更し、`(未指定)（(未指定)）` 二重括弧を解消
2. **linter v2**: `meta/scripts/frontmatter_lint.py` に以下を追加:
   - `sources[].path` を `.cache/sonic-sources/<repo>/` 配下で `Path.exists()` 検証（CI で `.cache` を再 clone する場合の挙動も検討）
   - 本文を走査して非 ASCII 制御字 (`[\x00-\x1f\x7f]` のうち改行/タブ除く) と「日本語 1 文字以上の連続中に英数 4 字以上」を検出
   - 「`実装が多い`」「`場合がある`」「`想定される`」のような裏取り不能表現を warning level で検出
3. **monitor 後埋め一括バッチ**: discrepancy-index L40-286 をスキャンし `monitor: (未指定)` の 26 件を `meta/queue/<page>.json` の調査結果から自動推定して PR 化（Verifier batch として並走）
4. **品質メトリクスバナーの自動更新**: `meta/scripts/gen_index_banner.py` で `code-verified` / `discrepancy-found` / 最新監査平均をスキャンし `docs/index.md` の `!!! success "最新の品質状態"` ブロックを sed 置換
5. **評価系の 10 段階化 or 軸追加（G. 横断リンク密度 / H. 図示有無 / I. 検証深度）**: 5 段階・6 軸では round 4 以降ほぼ満点で改善計測が不可能。round 7 から再校正

これらは並列実行で半日（4〜6 時間）。完了すれば「β リリースタグ `v0.1.0-beta` を打って公開アナウンスできる」状態になる（v1.0 は HLD 残 70 件の再構成イテ 3 回分が引き続き必要）。
