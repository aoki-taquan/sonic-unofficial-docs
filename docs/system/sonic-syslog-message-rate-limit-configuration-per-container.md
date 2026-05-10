---
title: syslog rate limit のコンテナ単位設定（SYSLOG_CONFIG / SYSLOG_CONFIG_FEATURE）
area: system
verification: hld-only
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/syslog/syslog-rate-limit-design.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - SYSLOG_CONFIG
    - SYSLOG_CONFIG_FEATURE
  cli:
    - config syslog rate-limit-host
    - config syslog rate-limit-container
    - show syslog rate-limit-host
    - show syslog rate-limit-container
  yang: []
---

!!! info "裏取りステータス: HLD-only"
    HLD は Rev 0.1。`containercfgd` の sonic-buildimage 取り込み、`hostcfgd` の SYSLOG_CONFIG 監視、`rsyslog-container.conf.j2` の rate-limit 変数化、APP extension 経由の設定は未確認。

# syslog rate limit のコンテナ単位設定（SYSLOG_CONFIG / SYSLOG_CONFIG_FEATURE）

## 概要

SONiC の syslog は **コンテナ毎の rsyslogd** + **host の rsyslogd** で構成され、host 側の rsyslogd が container からの message を集約して `/var/log/syslog` に書き出す。コンテナ側の rsyslog は従来 **ハードコード** で[^1]:

```
$SystemLogRateLimitInterval 300
$SystemLogRateLimitBurst 20000
```

の rate limit が掛かっていた。flood 防止のためだが、運用上「もっと緩く」「もっと厳しく」したいケースがある。host 側には rate limit が無く、追加したいニーズもあった。本機能はこれらを **CONFIG_DB から動的に変更** できるようにする[^1]。

`SystemLogRateLimitInterval` 秒の窓内に `SystemLogRateLimitBurst` 件を超えると以降は drop（FIFO）。

## 動作仕様

### CONFIG_DB スキーマ

新設 2 テーブル[^1]:

```
SYSLOG_CONFIG|GLOBAL
  rate_limit_interval = <秒>     # 0 で無効化
  rate_limit_burst    = <件数>   # 0 で無効化

SYSLOG_CONFIG_FEATURE|<container_name>
  rate_limit_interval = <秒>     # 既定 300
  rate_limit_burst    = <件数>   # 既定 20000
```

`init_cfg.json.j2` で既存 built-in container ぶんの default を流し込む。host (GLOBAL) は既定 0/0（=制限なし）[^1]。

### コンポーネントの責務分離

```mermaid
flowchart LR
  CLI[config syslog rate-limit-*] --> CDB[CONFIG_DB<br/>SYSLOG_CONFIG /<br/>SYSLOG_CONFIG_FEATURE]
  subgraph HOST[host]
    HCD[hostcfgd]
  end
  CDB -->|GLOBAL 変化を購読| HCD
  HCD -->|rsyslog.conf.j2 再描画<br/>rsyslog 再起動| HSY[host rsyslog]
  subgraph CON[container]
    CCD[containercfgd<br/>(新 daemon)]
  end
  CDB -->|FEATURE 変化を購読| CCD
  CCD -->|rsyslog-container.conf.j2 再描画<br/>rsyslog 再起動| CSY[container rsyslog]
  EXT[App extension] -->|自身の SYSLOG_CONFIG_FEATURE<br/>を聴く責務を持つ| EX[ext rsyslog]
```

要点[^1]:

1. **CLI は CONFIG_DB に書くだけ**
2. **`hostcfgd`** が host 側を担当（既存）。`SYSLOG_CONFIG|GLOBAL` を購読し、テンプレ再描画 + rsyslog restart
3. **新 daemon `containercfgd`** が各 container 内に登場。`SYSLOG_CONFIG_FEATURE|<container>` を購読
4. **`rsyslog.conf.j2` / `rsyslog-container.conf.j2`** に `rate_limit_interval` / `rate_limit_burst` 変数を追加
5. single-ASIC でも `rsyslog-container.conf.j2` テンプレを使うよう統一（旧 `rsyslog.conf` 撤廃）
6. **App extension** はこの機能の capability を申告し、自分で rate limit を CONFIG_DB から読む / rsyslog に反映する責務を負う

### Container 起動時の流れ

`docker_image_ctl.j2` から生成される起動スクリプトに `preStartAction` フェーズがあり、その中の **`updateSyslogConf`** 関数が `rsyslog-container.conf.j2` を CONFIG_DB の値で render する[^1]:

```mermaid
flowchart LR
  CSTART[container start] --> PRE[preStartAction]
  PRE --> US[updateSyslogConf<br/>rsyslog-container.conf.j2 render]
  US -->|docker cp| FILE[/etc/rsyslog.conf<br/>(stopped container)]
  FILE --> RUN[start container]
  RUN --> POST[postStartAction]
```

> 注: docker は **stopped container にもファイル copy** できるので、起動前に rsyslog.conf を更新してから container 本体を立ち上げられる[^1]。

### Runtime 変更

CLI から CONFIG_DB を更新すると、`containercfgd` がそれを観測して container 内 rsyslog を再 render し restart する[^1]。host 側は `hostcfgd` が同等の処理。

> 重要: 検証によると **host 側の rate limit 設定はコンテナ側に影響しない**[^1]（双方独立）。

### Multi-ASIC 考慮

multi-ASIC では設定は **per-namespace** で持つ[^1]。namespace ごとの container 群が別々に SYSLOG_CONFIG_FEATURE を持つ。

<!-- evidence:
source: sonic-net/SONiC/doc/syslog/syslog-rate-limit-design.md#L52-L96 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  1. CLI is only responsible for putting rsyslog configuration to CONFIG DB
  2. hostcfgd shall be extended to handle host side rsyslog configuration by listening CONFIG DB change
  3. A new daemon containercfgd shall be added to each container to handle container side rsyslog configuration
  ... > Note: according to test, syslog rate limit configuration on host side would not affect container side.
reasoning: 責務分離 (CLI/hostcfgd/containercfgd/App extension) と host-container の独立性の根拠。
-->

## 設定

### 関連する CONFIG_DB

| Table | Key | フィールド |
|-------|-----|------------|
| `SYSLOG_CONFIG` | `GLOBAL` | `rate_limit_interval`, `rate_limit_burst` |
| `SYSLOG_CONFIG_FEATURE` | `<container_name>` | 同上 |

### 関連する CLI

HLD には `config syslog rate-limit-host` / `rate-limit-container` 系が想定されている（具体名は実装側で確認）。

### 設定例

```bash
# host: 60 秒に 5000 件
sudo config syslog rate-limit-host -i 60 -b 5000

# bgp container: 制限解除
sudo config syslog rate-limit-container bgp -i 0 -b 0

# 表示
show syslog rate-limit-container
show syslog rate-limit-host
```

## 制限事項

- HLD は Rev 0.1 で日付欄空欄
- App extension は **自分で** SYSLOG_CONFIG_FEATURE を読む実装が必要（強制ではなく capability 申告ベース）
- host 設定はコンテナに伝播しないため、**全体を抑制したいなら全 container に同じ設定** を配る必要がある
- single-ASIC で `rsyslog.conf` から `rsyslog-container.conf.j2` への切替は **後方互換破壊** の可能性あり
- 設定変更の反映には rsyslog **restart** が走るため、その瞬間の syslog は欠ける

## 干渉する機能

- **`hostcfgd`**: 既存 daemon。listening する table が増える
- **`docker_image_ctl.j2`**: container 起動スクリプト雛型。`preStartAction` の hook を活用
- **multi-ASIC**: per-namespace で設定を持つ
- **App extension framework**: capability 申告経由
- **journald**: SONiC は rsyslog を主軸にしているので journald 直接設定とは別軸

## トラブルシューティング

```bash
# 設定の確認
redis-cli -n 4 HGETALL "SYSLOG_CONFIG|GLOBAL"
redis-cli -n 4 KEYS "SYSLOG_CONFIG_FEATURE|*"

# container 内 rsyslog 設定が反映されているか
docker exec bgp grep -E "RateLimit" /etc/rsyslog.conf

# rsyslog の再起動ログ
journalctl -u rsyslog
docker exec bgp supervisorctl status | grep rsyslog
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/syslog/syslog-rate-limit-design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
