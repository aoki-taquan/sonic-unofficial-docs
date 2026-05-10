---
title: SONiC における FRR upgrade の手順とパッチ管理
area: routing
verification: hld-only
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/frr_maintainer/sonic-frr_upgrade_process.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli: []
  yang: []
---

!!! warning "裏取りステータス: HLD-only / メタドキュメント"
    本ページは「SONiC FRR 保守者向けの作業手順」を再構成したもの。実際の手順は upstream / SONiC 双方の実装事情に依存し、頻繁に変わる。

# SONiC における FRR upgrade の手順とパッチ管理

## 概要

SONiC は upstream `frrouting/frr` を **branch スナップショット + per-release patch 集** という形で取り込んでいる[^1]。FRR を新しい upstream version に上げる際は次の点を整える必要がある:

- どの upstream tag / commit を base にするか
- SONiC 固有 patch（FPM 拡張、SAI と整合させる修正、SONiC ビルド適合）の rebase
- ビルド成果物（`docker-fpm-frr` 等）の入れ替え
- 既存テスト（PR テスト・mgmt-vrf・graceful restart 等）の通過確認

## upgrade フロー（HLD ベース）

```mermaid
flowchart LR
    PICK[upstream tag 選定\nfrr X.Y.Z] --> FORK[sonic-frr リポジトリで\nbranch を up-rebase]
    FORK --> PATCH[patches/ ディレクトリの\n.patch 群を rebase]
    PATCH --> BUILD[docker-fpm-frr 再ビルド]
    BUILD --> SMOKE[sonic-mgmt smoke\n(BGP / OSPF / GR / VRF / PIM)]
    SMOKE --> PR[sonic-buildimage で\nsubmodule pin 更新 PR]
    PR --> CI[community CI 全 platform]
    CI --> MERGE[merge → release branch backport]
```

各ステップの要点[^1]:

- **patch 集の管理**: `src/sonic-frr/patches/` のような場所に SONiC 固有 patch を `.patch` ファイルで保持し、`quilt` 系で順次適用する設計
- **submodule pin**: `sonic-buildimage` の `src/sonic-frr` submodule が SONiC 側 fork branch を指す
- **互換性**: SONiC 側 `bgpcfgd` / `fpmsyncd` / `frrcfgd` が FRR の vty フォーマットや FPM zebra route 表現に依存している。version up でフォーマットが変わる箇所は patch / SONiC 側コードの両側で対処
- **テスト**: PR テスト・既存 dual-tor / VRF / GR / BMP / SRv6 の sonic-mgmt テストを通過させる

## 注意点

- **patch を upstream に提案するのが第一**: 同じ修正を毎回 rebase するのは負債なので、汎用的な修正は upstream へ
- **バックポート**: 既 release（202311 等）への backport では vendor SDK / SAI 互換性も併せて確認
- **graceful restart 互換**: GR / GR-helper の動作が version で微妙に変わる。warm reboot との相性に直撃する
- **管理 VRF / unnumbered / bfd**: SONiC でよく使われる feature の互換性確認は手厚く

## 干渉する機能

- **bgpcfgd / fpmsyncd / frrcfgd / new-frr-sonic-communication-channel**: FRR と SONiC を繋ぐ周辺コード
- **graceful restart / warm reboot**: GR タイマと convergence の整合
- **management VRF / VRF design**: VRF 周りは upstream 側変更の影響を受けやすい
- **BMP / FRR ext config**: `sonic-frr-bgp-extended-unified-configuration-management-framework` 等の SONiC 拡張

## トラブルシューティング

- 新版 FRR で起動しない → patch 適用順、`vtysh` config 互換性、`config db` 由来 template との差分
- BGP routes がインストールされない → `fpmsyncd` の zebra route 解釈、新版 FRR の FPM 出力フォーマット差分
- GR 効かない → `bgpd` GR タイマ、SONiC 側の warm-restart 連動、log の `BGP gr` メッセージ

## 引用元

[^1]: `sonic-net/SONiC` `doc/frr_maintainer/sonic-frr_upgrade_process.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- src/sonic-frr/patches/ ディレクトリ構造と quilt-like 適用機構の現行実装確認
- sonic-buildimage submodule pin の現行 frr version 確認
- bgpcfgd / fpmsyncd / frrcfgd の FRR version 互換ロジックの現行実装確認
- graceful restart timer / warm-restart との連動の現行値確認
- BMP / SRv6 / VRF / unnumbered 関連 patch の upstream 化進捗確認
- 文書自体（HLD）の改訂日・現行 master FRR version との乖離リスク確認
-->
