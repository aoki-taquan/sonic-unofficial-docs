---
title: SONiC Disk I/O 削減（writer 分析と tmpfs 化）
description: SONiC Disk I/O 削減（writer 分析と tmpfs 化） — SONiC スイッチの一部が 過剰な disk write
  で SSD が劣化し read-only file system に陥る 問題が顕在化している。
area: system
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/sonic-reduce-disk-io/sonic-reduce-disk-io.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_AGGREGATE_ADDRESS
  - BGP_PEER_GROUP
  cli:
  - show bgp
  - config bgp
  yang:
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-bgp-bbr
  - sonic-bgp-peerrange
  - sonic-bgp-device-global
  - sonic-bgp-sentinel
  - sonic-bgp-monitor
---

!!! info "裏取りステータス: code-verified"
    `sonic-buildimage/files/build_templates/docker_image_ctl.j2` で `--tmpfs /tmp` / `--tmpfs /var/tmp` を確認、`sonic_debian_extension.j2` に `/dev/shm/monit/` 用 `tmpfiles.d/tmpfs-monit.conf` 生成も確認。`/tmp` tmpfs 化と monit 状態の tmpfs 化は master 取り込み済み。

# SONiC Disk I/O 削減（writer 分析と tmpfs 化）

## 概要

[SONiC](../reference/glossary.md#term-sonic) スイッチの一部が **過剰な disk write で SSD が劣化し read-only file system に陥る** 問題が顕在化している[^1]。本ドキュメントは 3 SKU × 3 OS バージョン × 各 100 台 = 900 台でフィールド計測した上で、**主要な disk writer を特定**し、**`/tmp` の tmpfs 化** や **bgpmon の [vtysh](../reference/glossary.md#term-vtysh) 履歴抑止** など低リスクで disk I/O を 78〜91% 削減する最適化を提案する。

## 動作仕様

### 計測

- ツール: **blktrace + blkparse** で block-layer I/O を採取
- データ保存: 影響回避のため **`/dev/shm` (tmpfs)** に書く
- 母数: SKU1/2/3 × Version_1/2/3 × 100 台 = 900 台
- 測定単位: **MiB/day**

### 主要 writer の内訳（全体平均 ~472.5 MiB/day）

| Process | 用途 | % |
|---------|------|--:|
| **jbd2** | EXT4 journaling | 44% |
| **vtysh** | [BGP](../reference/glossary.md#term-bgp) `~/.history_frr` への history 連続書き | 28% |
| **kworker/u8:x** | swss `supervisor-proc-exit-listener` log + OverlayFS xattr | 25% |
| **monit** | `/var/lib/monit/` state file 更新 | 2% |
| **logrotate / bash** | `/var/lib/logrotate/`, shell history 等 | 1% |

### Writer ごとの詳細

| Writer | なぜ書きが大きいか |
|--------|-------------------|
| `jbd2` | EXT4 metadata journal。data + metadata を 2 回書く |
| `vtysh` | `bgpmon.py` 行 80 で `vtysh -c "show bgp summary json"` を高頻度で呼び、その都度 `~/.history_frr` に追記される |
| `kworker/u8:x` | (1) swss container の `supervisor-proc-exit-listener` が `/var/log/supervisor/` に大量 log、(2) OverlayFS が inode の extended attr を継続更新 |
| `monit` | state file の周期書き |
| `logrotate` | rotation status 周期書き |
| `/tmp` writes | low-priority kernel worker が `/tmp` に短命 file を作成・削除し、metadata journaling 経由で disk に波及 |

### 最適化案

| | 内容 |
|---|------|
| **Optimization A** | user space 修正のみ。`/tmp` は disk のまま |
| **Optimization B** | user space 修正 + **`/tmp` を tmpfs にマウント** |
| **Optimization C** | A + **kernel journaling 無効化** |

ユーザ空間修正の具体策:

- `bgpmon.py` の cmd を **`vtysh -H /dev/null -c '...'`** に変更し history 書込を抑止
- `supervisor-proc-exit-listener` の log を `/dev/shm/supervisor/` に移動
- `monit` の state を `/dev/shm/monit` に移動
- `logrotate` の status を `/dev/shm/logrotate` に移動

```python
# bgpmon/bgpmon.py L80 想定の置換
cmd = "vtysh -H /dev/null -c 'show bgp summary json'"
```

### 結果（MiB/day, 集約値）

| Scenario | Disk Writes | 削減率 |
|----------|------------:|-----:|
| Unoptimized | 701.78 | - |
| Optimization A | 147.09 | 78.6% |
| Optimization B | 98.30 | 86.0% |
| Optimization C | 64.79 | 90.7% |

`/tmp` を tmpfs に移すだけで A→B でさらに ~7% 改善。journaling off の C は最大効果だがリスク有[^1]。

### Journaling 無効化のトレードオフ

Pros:
- write 重複 (data + journal) が消えて write が減る
- SSD 寿命延長

Cons:
- **クラッシュ時の data corruption リスク増**
- 復旧時 `fsck` が長くなる
- metadata 整合性（permissions / ownership 等）が壊れる可能性

⇒ 信頼性重視なら **Optimization B** 推奨[^1]。

<!-- evidence:
source: sonic-net/SONiC/doc/sonic-reduce-disk-io/sonic-reduce-disk-io.md#L46-L65 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  | jbd2 | Kernel journaling thread | 44% |
  | vtysh | CLI for network protocols | 28% |
  ... vtysh: "show bgp summary json" repeatedly written to ~/.history_frr within BGP container due to bgpmon command repetition.
reasoning: 主要 writer の比率と vtysh history 書込みの根因の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/sonic-reduce-disk-io/sonic-reduce-disk-io.md#L46-L65 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/sonic-reduce-disk-io/sonic-reduce-disk-io.md#L46-L65 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    | jbd2 | Kernel journaling thread | 44% |
    | vtysh | CLI for network protocols | 28% |
    ... vtysh: "show bgp summary json" repeatedly written to ~/.history_frr within BGP container due to bgpmon command repetition.
    ```

    **判断根拠**: 主要 writer の比率と vtysh history 書込みの根因の根拠。

<!-- evidence-rendered:end -->

## 推奨

| 優先度 | 戦略 |
|--------|------|
| 1 | **Optimization B**: 信頼性 (journaling 維持) と削減を両立 |
| 2 | **Optimization A**: tmpfs が memory 不足で使えない場合 |
| 3 | **Optimization C**: 最大削減が必要、かつ journaling 無効のリスクを許容できる場合のみ |

## 制限事項

- 計測対象は 3 SKU 限定（一般化に注意）
- `/tmp` を tmpfs にすると memory 消費が増える
- `~/.history_frr` 抑止は debug 時の trace 性とのトレードオフ
- Journaling 無効化は power loss を想定する環境では非推奨

## 干渉する機能

- **bgpmon (sonic-[bgpcfgd](../reference/glossary.md#term-bgpcfgd))**: vtysh history 抑止の対象
- **swss `supervisor-proc-exit-listener`**: log path 変更
- **monit / logrotate**: state file 配置
- **OverlayFS**: kernel worker による xattr 書込み（OS image 設計の根幹）
- **system upgrade**: tmpfs 化部位は再起動で初期化される前提のため state を残したい用途とは別整理が必要

## 関連 reference

- [HLD: sonic-storage-monitoring-daemon](sonic-storage-monitoring-daemon-design.md)
- [HLD: ssdhealth-design](../architecture/ssdhealth-design.md)
- [CLI: show system-health](../reference/cli/show-system-health.md)
- [Topics: Platform / Port / Optics](../topics/14-platform-port-optics/index.md)
- [CLI: show techsupport](../reference/cli/show-techsupport.md)
- [CLI: show services](../reference/cli/show-services.md)
- [Topics: Telemetry / SNMP / Observability](../topics/09-telemetry-snmp/index.md)
- [Glossary](../reference/glossary.md)
- [Reference 索引](../reference/index.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/sonic-reduce-disk-io/sonic-reduce-disk-io.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- bgpmon.py の vtysh -H /dev/null 化の sonic-buildimage / sonic-bgpcfgd 取り込み確認
- /tmp の tmpfs 化が image 構成に反映されているか確認 (fstab / cloud-init / build_templates)
- supervisor-proc-exit-listener の log 出力先 /dev/shm/supervisor/ への変更の sonic-buildimage 取り込み確認
- monit / logrotate の state path 変更の取り込み確認
- jbd2 無効化を採用しない方針の確認 (現行 master で journaling は有効維持か)
- 計測再現性 (新しい SKU での確認、recent OS バージョンでの再測)
-->

<!-- glossary-links-injected: 7ac8e66e1af3 -->
