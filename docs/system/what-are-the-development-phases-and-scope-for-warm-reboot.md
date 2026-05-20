---
title: Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison）
description: Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison）
  — SONiC の Warm Reboot 設計に関する open issues / 設計の選択肢 を整理した文書。
area: system
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/warm-reboot/open_issues.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - WARM_RESTART
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  - BGP_DEVICE_GLOBAL
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  cli:
  - config warm_restart
  - show warm_restart
  - sonic-installer upgrade_docker
  - config bgp
  - show bgp
  yang:
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-warm-restart
  - sonic-bgp-peergroup
  - sonic-bgp-aggregate-address
  - sonic-bgp-sentinel
  - sonic-bgp-peerrange
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 11 章: Reboot / Warm/Fast/Express/Cold](../topics/11-reboot/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: Code-verified"
    `sonic-utilities/config/main.py` L3938-3969 で `config warm_restart` group / `enable` コマンドを確認。`sonic-utilities/sonic_installer/main.py` L800-814 で `sonic-installer upgrade-docker` (旧 `upgrade_docker` は deprecation warning) を確認。`sonic-utilities/scripts/warm-reboot` は `fast-reboot` への symlink として存在（verified 2026-05-09）。OID 復元戦略は **syncd view comparison** が master に採用されている（syncd 内 SAI redis view-comparison ロジック）。

# Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison）

## 概要

[SONiC](../reference/glossary.md#term-sonic) の [Warm Reboot](../reference/glossary.md#term-warm-reboot) 設計に関する **open issues / 設計の選択肢** を整理した文書[^1]。3 段階の development phase、docker warm upgrade の手順、kernel warm reboot コマンド、[SAI](../reference/glossary.md#term-sai) API 互換性、OID 復元の 2 アプローチ、planned vs unplanned warm restart、成功判定方法を扱う。

## 動作仕様

### 開発フェーズ[^1]

| Phase | 範囲 |
|-------|------|
| Phase 1 | swss / [BGP](../reference/glossary.md#term-bgp) の docker warm restart |
| Phase 2 | [teamd](../reference/glossary.md#term-teamd-teamsyncd-teammgrd) / [syncd](../reference/glossary.md#term-syncd)（libsai / SDK 含む）の docker warm restart |
| Phase 3 | system 全体 warm reboot（DB save/restore、Linux 環境 graceful 復元） |

### Docker warm upgrade 手順[^1]

```bash
# 1. enable warm restart for swss (or system level)
config warm_restart enable swss
show warm_restart config
# name   enable  timer_name  timer_duration
# swss   true    NULL        NULL

# 2. upgrade docker
sonic-installer upgrade_docker --cleanup_image swss swss_test_02 ./docker-orchagent-brcm_test_02.gz

# 3. restart container
systemctl restart swss
```

system レベル enable は docker レベルを暗黙に有効化する[^1]:

```bash
config warm_restart enable
# system が enable される際 swss も enable される
```

### Kernel warm reboot

`fast-reboot` 同様の system level warm reboot コマンドが提供される。warm 側は state save/restore があるため fast-reboot より多くのオプションを取る[^1]。

### SAI API 互換性

データプレーン影響のある SAI API は **後方互換** 期待。互換切れは個別対応。libsai redis interface（libsairedis）はやや自由度が高い[^1]。

### OID 復元: 2 つのアプローチ

```mermaid
flowchart LR
  WR[warm restart 後] --> Q{OID 復元方式}
  Q -->|案 A| ID[idempotent libsairedis API<br>libsairedis 内で重複操作を吸収]
  Q -->|案 B| VC[syncd view comparison<br>syncd が old view と new view を diff]
  ID --> ASIC1[(ASIC)]
  VC --> ASIC2[(ASIC)]
```

#### A. idempotent libsairedis API[^1]

- 設計: [sai_redis_api_idempotence.md](https://github.com/sonic-net/SONiC/blob/master/doc/warm-reboot/sai_redis_api_idempotence.md)
- 実装ドラフト: [sonic-sairedis idempotent ブランチ](https://github.com/sonic-net/sonic-sairedis/compare/master...jipanyang:idempotent)
- 状況: VS テストが実装済、swss docker warm restart/upgrade の E2E まで通過。コードレビュー前で再構成余地あり。**1 コマンドで feature on/off 可能化** が望ましい

#### B. syncd view comparison[^1]

- 主要実装: [`syncd/syncd_applyview.cpp`](https://github.com/sonic-net/sonic-sairedis/blob/d54977f297301f972e2839d526d8130a5f66e893/syncd/syncd_applyview.cpp)
- 設計ドキュメント: 未公開
- 状況（[HLD](../reference/glossary.md#term-hld) 時点）: コードは sairedis に入っているが SONiC 通常パスでは使われていない。production 検証なし。syncd docker 内 unit test のみ
- 現状（最新コード裏取り）: verification block も参照。`syncd_applyview.cpp` の view-comparison ロジックは master に取り込み済み。HLD 起草時点の「通常パス未使用」記述は時点依存で、現行 master では OID 復元戦略として採用されている

### Planned vs Unplanned warm restart[^1]

libsai に対し **planned warm restart のみ必須**。SONiC が SDK / libsai に明示要求する。unplanned は要求なし。

### 成功判定[^1]

warm restart は 2 段階:

1. **state restore**: 設定 / 状態整合性チェック → 期待状態に到達したかバリデーション
2. **state sync up**: 最新状態へ同期。sync 状態はデターミニスティックでないので **アプリ毎タイマー** で打ち切り、内部固有チェックを実施

## 制限事項

- syncd view comparison は HLD 起草時点では production 検証無し（現行 master では採用済み。verification block 参照）
- idempotent 案も完全 review 未実施
- SAI 互換切れは個別対応
- unplanned warm restart は libsai 要件外

## 干渉する機能

- **fast-reboot**: 関連だが state save 規模が異なる
- **libsai / SDK**: warm restart 対応の baseline
- **[sonic-sairedis](../reference/glossary.md#term-sonic-sairedis)**: 両アプローチの主舞台
- **[CONFIG_DB](../reference/glossary.md#term-config_db) / [APPL_DB](../reference/glossary.md#term-appl_db) save/restore**: Phase 3 の system warm reboot

## 引用元

[^1]: [sonic-net/SONiC doc/warm-reboot/open_issues.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/warm-reboot/open_issues.md)

<!-- glossary-links-injected: 167700005048 -->
