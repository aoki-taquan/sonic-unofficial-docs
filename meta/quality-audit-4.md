# 品質改善サンプリング監査（round 4）

- 実施日: 2026-05-11
- 対象: イテレーション D（PR #911 直後 #912-#918）で merge されたコンテンツ
  - Topics concept 強化 4 PR (#912/915/917/918)：合計 22 章 × 平均 +90 行 ≒ +2000 行（concept.md を「読み手の質問順」で再構成）
  - HLD area 再構成 2 PR (#914/916)：routing 5 件 + switching/overlay 5 件 = **計 10 件**（章立てを質問順に組み直し、Topics への誘導リンク追加）
  - discrepancy 残 20 件深掘り 1 PR (#913)：`monitor: not_implemented|evolved_beyond_hld` タグ追加 + 行番号付きエビデンス + 追加回避策コマンド
  合計約 52 件のページ強化
- サンプル数: 12 件
  - concept 強化 5 章 (C1-C5)
  - HLD area 再構成 4 件 (H1-H4)
  - discrepancy 残深掘り 3 件 (D1-D3)
- 評価者: AI（Claude / batch #6）

## 1. サンプル

### Topics concept 強化（5）

| # | パス | 行数 |
|---|------|------|
| C1 | `docs/topics/01-overview/concept.md` | 161 |
| C2 | `docs/topics/05-dual-tor/concept.md` | 134 |
| C3 | `docs/topics/13-dash-smartswitch/concept.md` | 170 |
| C4 | `docs/topics/16-nat-dhcp-dns/concept.md` | 189 |
| C5 | `docs/topics/20-swss-sai-redis/concept.md` | 156 |

### HLD area 再構成（4）

| # | パス | 行数 |
|---|------|------|
| H1 | `docs/routing/srv6-vpn-hld.md` | 147 |
| H2 | `docs/routing/sonic-fine-grained-ecmp.md` | 175 |
| H3 | `docs/overlay/vxlan-sonic.md` | 315 |
| H4 | `docs/switching/macsec-sonic-high-level-design-document.md` | 160 |

### discrepancy 残深掘り（3）

| # | パス | monitor タグ |
|---|------|---------------|
| D1 | `docs/architecture/build-profiles.md` | not_implemented |
| D2 | `docs/management/gnmi-master-arbitration-hld.md` | evolved_beyond_hld |
| D3 | `docs/platform/fec-flr-support-in-sonic.md` | evolved_beyond_hld |

## 2. 評価軸（5 段階）

- A. 情報密度（重複・水増しが少ないか）
- B. 実用性（読み手が次にとる行動が明確か）
- C. 正確性（コード・スキーマ・引用が現行 master と一致するか）
- D. 読みやすさ（見出し・表・コードブロックの構造）
- E. HLD 翻訳調解消（受動表現の連鎖・原文直訳臭の不在）

## 3. 評価結果

| ID | A | B | C | D | E | 平均 | 備考 |
|----|---|---|---|---|---|------|------|
| C1 (overview) | 5 | 5 | 5 | 5 | 5 | 5.00 | 「読み手の質問順」の見本。CONFIG_DB / APPL_DB / STATE_DB / ASIC_DB の役割分担表、Kubernetes desired/observed との比較が秀逸 |
| C2 (dual-tor) | 5 | 5 | 5 | 5 | 5 | 5.00 | active-active と active-standby の対比、`linkmgrd` / `mux_mgr` / Y-cable / soc_address の用語整理が密 |
| C3 (dash-smartswitch) | 5 | 5 | 5 | 5 | 5 | 5.00 | DASH（API）と SmartSwitch（箱）の混同を冒頭で解消。`has_per_dpu_scope` や `redisdpuN` まで踏み込んだ用語表、Service Tunnel/Private Link 言及。比較表 5 件（SmartNIC / Multi-ASIC / OVS / VPP / MPLS）が良質 |
| C4 (nat-dhcp-dns) | 5 | 5 | 5 | 5 | 5 | 5.00 | 4 群（NAT / DHCP relay / DHCP server / Time-DNS）に分解。Option 82 / 79 / giaddr 固定、management VRF 経由の必要性まで言及 |
| C5 (swss-sai-redis) | 5 | 5 | 4 | 5 | 5 | 4.80 | mermaid 地図と用語表が共通語彙の基盤になる。frontmatter `sources: []` 空欄（前回 audit からの持ち越し罠）-0.2 |
| H1 (srv6-vpn) | 5 | 5 | 5 | 5 | 5 | 5.00 | 「読者が知りたいこと」4 項目で冒頭が引き締まる。`srv6_prefix_agg_id_table_` L1721, `createSrv6Vpn` L1025 など実コード行番号引用が code-verified を担保 |
| H2 (fg-ecmp) | 5 | 5 | 5 | 5 | 5 | 5.00 | match_mode 3 種を表で並べ、`prefix-based` が Rev 1.5 追加である事実まで明示。bucket_size 設計指針も実用 |
| H3 (vxlan-sonic) | 5 | 5 | 5 | 5 | 5 | 5.00 | `VxlanOrch` 表記 vs 実装 `VxlanTunnelOrch` 分割の不一致を冒頭 admonition で明示。Phase 1/2 の差、warm restart の可否、最低限見るテーブル列挙の Q 7 件構成 |
| H4 (macsec) | 5 | 5 | 5 | 5 | 5 | 5.00 | `PAUSE_ETHER_TYPE 0x8808` / `PFC_MODE_BYPASS` の実コード突合せ。MKA は誰がやるか / wpa_supplicant 拡張版が必要な理由を Q 形式で解消 |
| D1 (build-profiles) | 5 | 5 | 5 | 4 | 5 | 4.80 | `grep -n profiles Makefile.work` ヒット 0 件を再確認、`BUILD_PROFILE=secure` wrapper の追加回避策コマンド提示。round 2 追補章のヘッダが他章とテンプレ的に揃いすぎて -0.2 |
| D2 (gnmi-master-arbitration) | 5 | 5 | 5 | 5 | 5 | 5.00 | `server.go:1329-1331` の `codes.Unimplemented` 拒否、HLD では「無視」と書かれているが実装は「明示拒否」と差分を明文化。Go gNMI client コード例で「Role 空のまま投げる」回避策まで提示 |
| D3 (fec-flr) | 5 | 5 | 5 | 5 | 5 | 5.00 | `port_flr.lua` L29-32 の hardcoded 定数列挙 (`BIN_FILTER_VALUE=10` 等)、`counterpoll port flr-interval-factor` 未実装の grep 結果、`docker exec swss sed -i` で in-place 編集する泥臭い回避策が現場感ある |

**平均: 4.97 / 5.0**（12 件、計 60 軸。5.0 が 10/12、4.8 が 2/12）

## 4. 引用された実コード行番号 spot check

| 引用元 | 主張 | 実機照合 | 結果 |
|--------|------|----------|------|
| H4 macsec | `sonic-swss/orchagent/macsecorch.cpp` の `PAUSE_ETHER_TYPE 0x8808` / `PFC_MODE_BYPASS` | L26 / L29 で完全一致、L3120 で `pfc_mode == PFC_MODE_BYPASS` の use、L3186 で `attr.value.aclfield.data.u16 = PAUSE_ETHER_TYPE` の use | OK |
| H1 srv6-vpn | `srv6orch.cpp` L1721 `srv6_prefix_agg_id_table_`、L1025 `createSrv6Vpn`、L776 `deleteSrv6Vpn` | 3 件とも完全一致 | OK |
| H3 vxlan-sonic | `vxlanorch.h` L268/414/462/499/512/541 で `VxlanTunnelOrch` 他 6 派生クラス | 6 件とも `class XxxOrch : public Orch2` で完全一致 | OK |
| H3 vxlan-sonic | `schema.h:85-87` で `APP_VXLAN_TUNNEL_MAP_TABLE_NAME` / `APP_VXLAN_TUNNEL_TABLE_NAME` / `APP_VXLAN_FDB_TABLE_NAME` | L85/86/87 完全一致 | OK |
| D3 fec-flr | `port_flr.lua` L29-32 で `BIN_FILTER_VALUE=10` / `MIN_SIGNIFICANT_BINS=2` / `FEC_FLR_POLL_INTERVAL=120` / `MFC=8` | 4 件とも完全一致（順序も同じ） | OK |

参考: D2 gnmi の「`server.go:1329-1331` の `codes.Unimplemented`」は実機 L1327 開始（`if ma.Role != nil` が L1327、`Unimplemented` が L1329）。2 行ずれだが内容は一致。前回監査でも D1 routeorch で同様の 1-2 行ずれが観測されており、許容範囲。

**5/5 spot check pass**（うち 4 件は完全一致、1 件は ±2 行ずれ）。round 3 と同水準で裏取り強度を維持。

## 5. round 1 / 2 / 3 / 4 比較トレンド

| round | 平均 | サンプル | 5.0 比率 | ばらつき | 主な強み | 主な弱み |
|-------|------|----------|----------|----------|----------|----------|
| 1 | 4.60 | 10 | 30% | 4.0-5.0 (1.0) | operations 7 ステップ運用シナリオ | discrepancy が「乖離 1 行」で終わる、Reference が schema dump 寄り |
| 2 | 4.83 | 10 | 40% | 4.4-5.0 (0.6) | Verifier 昇格判断、Reference batch B の YANG/CLI 連結 | verification frontmatter 昇格漏れ |
| 3 | 4.84 | 15 | 60% | 3.8-5.0 (1.2) | setup の (CLI/JSON/show) 三段化、Runbook 症状逆引き、discrepancy 五段化 | internals 章の行数バラつき (47↔150)、frontmatter `sources:` 空欄 |
| **4** | **4.97** | **12** | **83%** | **4.8-5.0 (0.2)** | concept の「読み手の質問順」テンプレ、HLD area 再構成での冒頭 Q 形式、discrepancy の monitor タグ + 追加コマンド | frontmatter `sources: []` がまだ残る (C5)、テンプレ化による画一性（D1） |

**主要トレンド**:

- 平均値は 4.60 → 4.83 → 4.84 → **4.97** で round 3 → 4 で +0.13 と再加速。漸近域を抜けた印象
- 5.0 ページ比率: 30% → 40% → 60% → **83%** と単調増加
- ばらつきは round 3 の 1.2 から **0.2 に劇的圧縮**。「読み手の質問順」テンプレが全章で機能した結果、外れ値（47 行 outlier）が消えた
- 弱点は frontmatter linter 未導入の `sources: []` 残存と、テンプレ化による画一性のみ。前者はスクリプト一発、後者は概念上の制約（テンプレ統一の対価）で軽微
- discrepancy 深掘りに **`monitor:` frontmatter タグ**（`not_implemented` / `evolved_beyond_hld`）が導入され、機械的なフィルタリング・一覧化が可能になった。これは構造的進化

## 6. 「9 イテレーション目」（本タスクを含むイテレーション E）で気をつけるべき罠

過去 8 イテレーションで実害が出た / 兆候が出ている罠を整理する。

1. **テンプレ画一性の慢性化（中）**: concept 22 章が「機能とは / 何を解決 / SONiC 内の位置 / 用語 / 典型シーン / 似た機能との違い / 読了後にできること」の **同一見出しで揃いすぎ**。読み手は 2 章目以降スキップしやすくなる。次イテレーションでは「章の固有性が薄い章（例: 19 build-packaging, 21 lab-vs-developer）」の見出しを意図的に変える検討
2. **frontmatter `sources: []` 残存（中）**: C5 (20 swss-sai-redis) で空欄。internals 章でも前回 I4 で同じ事象。**`meta/scripts/check_frontmatter.py` で `sources` 空 + `verification: code-verified` を FAIL** にする linter を CI に挟むべき。これは round 3 で挙がったが未着手
3. **行番号引用の ±2 行ずれ（低）**: D2 gnmi のように 1-2 行ずれが累積中。実害は小さいが「verified at 2026-05-09 → 上流が再 push して行ずれ」を検知する仕組み（`sources[].ref` SHA + line-range cross check スクリプト）を Verifier に組み込みたい
4. **`monitor:` タグの semantics 拡散（中）**: 今回 `not_implemented` / `evolved_beyond_hld` の 2 値を導入したが、定義が `meta/templates/SCHEMA.md` に未反映。3 値目以降（`partially_implemented` / `deprecated` / `superseded`）が必要になる前に enum を確定すべき
5. **HLD area 再構成の取りこぼし（中）**: routing 5 / switching+overlay 5 = 10 件のみ。残り area（architecture / management / platform / system / acl-qos / internals）合計 ~80 件は **HLD 翻訳調が残ったまま**。次イテで area あたり 5 件ペースで継続的に再構成
6. **並走 PR の reviewer/lgtm スループット限界（低）**: イテレーション D だけで 8 PR merge、CI 並走 8 ジョブが偶発的に flaky の温床。次イテでは 1 PR = 1 area か 1 batch に集約してマージ列を短く保つ
7. **アンカー / 相互リンク切れ（低）**: concept で `[BGP](../02-bgp/index.md)` 形式リンクが頻発。`index.md` が無い章（例: 01-overview/index.md は存在するが、22-reference-index は別形式）がある。`mkdocs --strict` で検知される範囲だが、`href#anchor` の anchor 側は素通り
8. **discrepancy 「やり残し」リスト未公開（中）**: discrepancy-found 全数（推定 60-80 件）のうち、深掘り済み = 10 (round 3) + 20 (round 4) = **30 件**。残り ~30-50 件は「いつ深掘りするか」が trackable でない。`meta/discrepancy-backlog.json` を立てて昇格管理にすべき

## 7. プロジェクト全体の到達度: 公開可否

### 結論: **「非公式ドキュメント β 版」として公開可**。

#### 公開可と判断する根拠

- **量**: 455 ページ merge 済（HLD 系 + Reference 4 種 + Topics 22 章 × concept/setup/operations/internals/advanced）。コミュニティ HLD の主要分布をカバー
- **質**: round 4 サンプリングで平均 **4.97 / 5.0**、5.0 ページ比率 **83%**。spot check 5/5 pass で実コード裏取り強度も維持
- **検証ステータス**: `verification: hld-only` が **0 件**（全ページ code-verified / discrepancy-found に到達）。discrepancy 30 件は深掘り済みで「監査 round X 追補」セクション付き
- **構造**: Diataxis の Concept / How-to / Reference / Explanation 4 軸が `topics/{concept,setup,operations,internals,advanced}` + `reference/{cli,config-db,yang,runbooks}` + 既存 HLD 翻訳という 3 階で実現済み
- **CI / Deploy**: `mkdocs build --strict` PR ごと green、`gh-pages` への deploy workflow 稼働中
- **信頼性表示**: 各ページ frontmatter で `verification:` `last_verified:` `sources:` `monitor:` を表示し、「裏取り済み」「実装が HLD から外れた」「未実装」を読み手に区別させられる

#### 「α」ではなく「β」と表現する理由（未完了点）

下記は致命的でないが、公開前に整えるとより安心:

1. **frontmatter linter（必須レベル / 数時間で実装可）**: `sources: []` の空欄を CI で FAIL に。round 3 から繰り越し
2. **discrepancy 一覧ビュー（高 / 半日）**: `monitor:` タグで filter した「実装と HLD が乖離しているページ一覧」を `docs/_meta/discrepancy-index.md` として自動生成。読み手が「公式 HLD を読んだあと SONiC 実装はどう違うか」を一望できる強力な差別化ポイント
3. **HLD area 残 ~80 件の再構成（中 / イテ 3 回分）**: 翻訳調が残る area が architecture / management / platform / system / acl-qos / internals。質には影響しないが体感の一貫性のため継続
4. **「読み始め方」トップページ（高 / 1 時間）**: `docs/index.md` から `topics/01-overview/concept.md` への動線が暗黙。新規読者向けに **「初めての方はここから」セクション** を index に明示
5. **`monitor:` タグの enum 化（中 / 1 時間）**: `meta/templates/SCHEMA.md` に列挙し、`unknown` 値を CI で reject
6. **GitHub Pages 公開設定（ユーザー手動マター）**: Settings → Pages → Source: `gh-pages` branch を有効化（PAT 権限不足で AI 側からは不可）
7. **OGP / sitemap / search 重み（低 / 半日）**: `mkdocs.yml` の `site_url` / `theme.features` で社内 / 外部検索エンジンに乗りやすくする
8. **CHANGELOG.md（中 / 1 時間）**: 公開後の継続更新でユーザーに「何が変わったか」を示す入口

これらは並列で半日〜2 日で全部回せる規模。**「公開ボタンを押せる状態」と「公開して恥ずかしくない状態」の差は 1〜2 イテレーション分**。

## 8. 公開可なら最後に何を整えるべきか（優先度順）

| 優先 | 項目 | 工数 | 効果 |
|------|------|------|------|
| 1 | `docs/index.md` に「初めての方はここから」動線追加 | 1h | 新規読者の離脱を防止 |
| 2 | frontmatter linter (`sources` / `verification` / `monitor` の空欄・enum 検査) を CI に追加 | 2h | 進化中の品質保証 |
| 3 | `docs/_meta/discrepancy-index.md` 自動生成（`monitor:` タグ filter） | 4h | 「HLD vs 実装」一覧という強力 USP の見せ場 |
| 4 | `meta/templates/SCHEMA.md` に `monitor:` enum 確定 | 1h | tag 拡散を防ぐ |
| 5 | GitHub Pages の `gh-pages` branch ソース有効化（ユーザー作業） | ユーザー手動 | 公開そのもの |
| 6 | `mkdocs.yml` の `site_url` / `social` / `analytics` 整備（任意） | 2h | 検索エンジン / SNS 経由流入 |
| 7 | CHANGELOG / リリースノート（最初の `v0.1.0` タグ） | 1h | 継続更新を読み手に伝える |
| 8 | 残 HLD area 再構成（architecture / management / platform / system / acl-qos / internals）| イテ 3 回 | β → 1.0 への昇格条件 |

優先 1-5 は **半日で全部終わる規模**。これを完了した時点で「公開して恥ずかしくないβ」になる。優先 8 は公開後の継続改善で問題ない。

## 9. 結論

- 平均 **4.97 / 5.0**（round 3 から +0.13、5.0 比率 83%）。テンプレ化と「読み手の質問順」導入で品質が再加速
- コード行番号引用 5/5 pass。±2 行ずれは累積中だが許容範囲
- **「非公式ドキュメント β 版」として公開可**。残作業は半日規模の 5 項目（index 動線、linter、discrepancy 一覧、schema enum、Pages 有効化）
- 次イテで気をつける罠は「テンプレ画一性」「frontmatter linter 未着手」「monitor タグ semantics 拡散」「HLD area 残 80 件の翻訳調」の 4 つ
