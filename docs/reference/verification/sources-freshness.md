---
title: ソース pinned SHA の新鮮度（sources-freshness）
description: "ソース pinned SHA の新鮮度（sources-freshness） — meta/index/repos.json で固定している commit SHA と各リポの upstream HEAD を突き合わせ、本サイトのスナップショットがどれだけ master から遅れているかを一覧化する。"
verification: meta
last_verified: 2026-05-13
tags:
  - verification
  - sources
---

# ソース pinned SHA の新鮮度（sources-freshness）

本サイトの各ページは frontmatter `sources[].ref` で [SONiC](../../reference/glossary.md#term-sonic) 上流リポのコミット SHA を**固定**している。固定 SHA は `meta/index/repos.json` で一元管理しており、Indexer 再走時に更新される。

このページは `meta/scripts/check_sources_freshness.py --write` で生成され、各対象リポについて pinned SHA と upstream HEAD の差分を可視化する。**読者はサイトの記述がどの時点の SONiC master を反映しているかをここで確認できる**。

## サマリ

- 対象リポ数: **15**
- upstream より遅れているリポ: **0**
- ローカル cache が見つからなかったリポ: **0**

## 一覧

| repo | repos.json SHA | cache HEAD | upstream HEAD | behind by | pinned commit date | note |
|------|----------------|------------|---------------|-----------|--------------------|------|
| `sonic-net/SONiC` | `49bab5b5ff0e` | `49bab5b5ff0e` | 49bab5b5ff0e (origin/master) | 0 | 2026-05-07 |  |
| `sonic-net/sonic-buildimage` | `9ea932ec2e18` | `9ea932ec2e18` | 9ea932ec2e18 (origin/master) | 0 | 2026-05-08 |  |
| `sonic-net/sonic-utilities` | `39732bceb8bd` | `39732bceb8bd` | 39732bceb8bd (origin/master) | 0 | 2026-05-08 |  |
| `sonic-net/sonic-swss` | `4305596156d7` | `4305596156d7` | 4305596156d7 (origin/master) | 0 | 2026-05-08 |  |
| `sonic-net/sonic-swss-common` | `158de8d3463f` | `158de8d3463f` | 158de8d3463f (origin/master) | 0 | 2026-04-29 |  |
| `sonic-net/sonic-sairedis` | `88bc51ae95df` | `88bc51ae95df` | 88bc51ae95df (origin/master) | 0 | 2026-05-08 |  |
| `sonic-net/sonic-mgmt-common` | `f71cf829883c` | `f71cf829883c` | f71cf829883c (origin/master) | 0 | 2026-04-16 |  |
| `sonic-net/sonic-platform-common` | `64beade8cdde` | `64beade8cdde` | 64beade8cdde (origin/master) | 0 | 2026-05-07 |  |
| `sonic-net/sonic-platform-daemons` | `4ba9612cb775` | `4ba9612cb775` | 4ba9612cb775 (origin/master) | 0 | 2026-05-07 |  |
| `sonic-net/sonic-snmpagent` | `329f1cca300b` | `329f1cca300b` | 329f1cca300b (origin/master) | 0 | 2026-05-06 |  |
| `sonic-net/sonic-dhcp-relay` | `7316417034fe` | `7316417034fe` | 7316417034fe (origin/master) | 0 | 2026-05-07 |  |
| `sonic-net/sonic-linkmgrd` | `65f563308c68` | `65f563308c68` | 65f563308c68 (origin/master) | 0 | 2026-04-20 |  |
| `sonic-net/sonic-host-services` | `c5bbbe8b07b9` | `c5bbbe8b07b9` | c5bbbe8b07b9 (origin/master) | 0 | 2026-05-07 |  |
| `sonic-net/sonic-gnmi` | `eb635b7679b2` | `eb635b7679b2` | eb635b7679b2 (origin/master) | 0 | 2026-05-08 |  |
| `sonic-net/sonic-frr` | `799f47f215e4` | `799f47f215e4` | 799f47f215e4 (origin/master) | 0 | 2026-02-11 |  |

- `repos.json SHA`: `meta/index/repos.json` に記録されている pinned SHA（本サイトのスナップショット基準）
- `cache HEAD`: `.cache/sonic-sources/<repo>/` ローカル shallow clone の現在 HEAD
- `upstream HEAD`: ローカル clone から見える `origin/master`（無ければ `origin/main`）の HEAD
- `behind by`: pinned から upstream までの commit 数（`git rev-list pinned..upstream --count`）。shallow clone の都合で `pinned` がローカルに居ないと計測不能になる場合がある

## 運用注記

- 定期的に **Indexer を再走させて `meta/index/repos.json` を更新する**（四半期サイクル目安）。更新後は本ページを `python3 meta/scripts/check_sources_freshness.py --write` で再生成する。
- 個別ページの `sources[].ref` は当該ページの裏取り時点で固定する設計であり、サイト全体で一斉に SHA を bump する必要はない。本ページはあくまで「サイト全体としてどの時点の master を見ているか」の俯瞰指標。
- 詳細手順は `meta/discrepancy-operations.md` の「定期実行」節を参照。

<!-- glossary-links-injected: 8ba32e5aa69d -->
