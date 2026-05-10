---
title: System Ready（sysmonitor + per-app closest UP status の event 集約）
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/system_health_monitoring/system-ready-HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - FEATURE
  cli:
    - show system-health sysready-status
  yang:
    - sonic-feature
---

!!! success "裏取りステータス: code-verified (2026-05-10)"
    `sonic-buildimage/src/system-health/health_checker/sysmonitor.py` に sysmonitor 本体が存在し、`sonic-utilities/scripts/sysreadyshow:30` が `SYSREADY_TABLE = "SYSTEM_READY|SYSTEM_STATE"` を STATE_DB から読む。CLI は `sonic-utilities/show/system_health.py:141 @system_health.group('sysready-status', invoke_without_command=True)` で実装、`brief` / `detail` サブコマンドも `tests/system_health_test.py:329-336` で検証されており、HLD どおり。

# System Ready（sysmonitor + per-app closest UP status の event 集約）

## 概要

SONiC の起動は **非同期**。systemd の service が `active` でも、その内部の SWSS 系 daemon が CONFIG_DB を全部食って ASIC に届くまで時間がかかる。「**システムが本当に traffic を受けられる状態か**」を一発で判定する仕組みが従来なく、**Monit** 系の poll（1 分間隔の running 状態チェックのみ）では遅延・粒度ともに不足だった[^1]。

System Ready はこの不足を埋める。**`sysmonitor`** という Python ベース daemon を追加し[^1]:

- 全 essential host service の up を **event-driven** で検出
- 各 docker app に **closest UP status** を能動的に申告させる
- 集約結果として 1 つの "system ready" 状態を出す
- CLI / syslog で公開

`system-health` フレームワークの一部として統合される[^1]。

## 動作仕様

### `sysmonitor` の subtask 構成

`sysmonitor` 内に複数の sub-thread が居る（HLD で具体構造化）[^1]:

- service status 監視（systemd dbus event）
- docker container の running 監視
- 各 app の app-ready 通知 hook

### Service identification

「essential か否か」をどう判定するかが重要。`FEATURE` table の **新フィールド** で表現する[^1]:

```
CONFIG_DB FEATURE|<name>
  state         = "enabled" | ...
  has_per_asic_scope = ...
  ...
  check_up_status = "true" | "false"   # 新規。system ready 判定対象に入れるか
```

`true` の feature が「上がるべき必須サービス」として扱われ、すべて up になるまで system ready にならない。

YANG 側は `sonic-feature` に対応 leaf を追加[^1]。

### App 側からの "closest UP" 通知

各 docker app は **自分が ready** と言えるタイミング（CONFIG_DB 取込完了 / port 設定完了 等）を Sysmonitor に通知する。受け側は `STATE_DB` の **app-ready 系テーブル**[^1]:

```
STATE_DB FEATURE|<name>
  up_status = "true" | "false"
  fail_reason = "..." (任意)
```

これにより `sysmonitor` は単に systemd の active 判定でなく、「**そのアプリが配信した CONFIG_DB を消化し終わったか**」レベルで ready を見る。

### System ready ロジック

```mermaid
flowchart TB
  BOOT[boot] --> START[各 service が systemd で順次 up]
  START --> EV1[sysmonitor: dbus event<br/>service active]
  EV1 --> CHK1{check_up_status?}
  CHK1 -- false --> SKIP[system ready 判定対象外]
  CHK1 -- true --> WAIT[app-ready 通知待ち]
  WAIT --> APP[App が STATE_DB FEATURE<br/>up_status=true を書込]
  APP --> AGG[全対象 feature が up?]
  AGG -- yes --> READY[SYSTEM_READY=UP]
  AGG -- no --> WAIT
  READY --> SYSLOG[syslog "System is ready"]
  AGG -. timeout .-> DOWN[SYSTEM_READY=DOWN<br/>fail_reason 集約]
  DOWN --> SYSLOG2[syslog with fail reason]
```

### Host daemon の扱い（Rev 0.4 で追加）

Rev 0.4 で **host 上の daemon**（コンテナ外で動く `swss` 等以外の daemon）も ready 判定対象に追加[^1]。これにより「コンテナは全部 up でも host daemon が起動失敗」を見逃さない。

### Admin state（Rev 0.4 で追加）

system ready 機能自体を disable できる admin state[^1]。デバッグや特殊ワークロードで個別 service の ready を待たずに判定したい場合に使う。

### `show system-health sysready-status` の出力

3 種[^1]:

- 既定: 1 行サマリ（System Status: ready / not ready, since timestamp）
- `brief`: feature 単位の up/down 行
- `detail`: それぞれの fail_reason / 時刻 まで含む

<!-- evidence:
source: sonic-net/SONiC/doc/system_health_monitoring/system-ready-HLD.md#L84-L92 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  At present, there is no mechanism to know that the system is up and ready with all the essential sonic services and also, all the docker apps are ready along with port ready status to start the network traffic.
  ... if we could get the closest up status of each docker app considering their config receive ready and port ready, the system readiness could be arrived.
  A new python based System monitor tool is introduced to monitor all the essential system host services including docker wrapper services on an event based model and declare the system is ready.
reasoning: SONiC 非同期起動下での "system ready" 判定の動機と event-driven sysmonitor の根拠。
-->

## 設定

### 関連する CONFIG_DB

| Table | Key | フィールド |
|-------|-----|------------|
| `FEATURE` | `<name>` | `check_up_status`, ほか既存 |

### 関連する CLI

| Command | 用途 |
|---------|------|
| `show system-health sysready-status` | サマリ |
| `show system-health sysready-status brief` | feature 一覧 |
| `show system-health sysready-status detail` | fail reason 込み |

### 設定例

```bash
# システムが ready か確認
show system-health sysready-status
# 詳細
show system-health sysready-status detail

# CONFIG_DB で feature を ready 判定対象に
sonic-cfggen -d -v 'FEATURE'
# あるいは config 編集
```

## 制限事項

- HLD Rev 0.4 で日付欄（Rev 0.1〜0.3）は空欄
- ready 判定は app の **自己申告** に依存。app 側がバグで up_status を書かないと永遠に ready にならない
- timeout の絶対値は HLD で固定されておらず、運用 / 実装側に委ねられる
- warm-boot 中の system ready 判定は HLD で別扱い（warm-boot 完了の意味と微妙に異なる）

## 干渉する機能

- **systemd / Monit**: Monit を完全置換するわけではないが、ready 判定だけ sysmonitor が担う
- **system-health フレームワーク**: SystemHealth daemon と統合
- **`FEATURE` 表**: `check_up_status` 追加
- **fastboot / warmboot**: 高速復帰の流儀と整合する必要
- **TACACS / AAA / SNMP の boot 順**: ready 待ちでこれらの起動順を厳守させたいケースで便利

## トラブルシューティング

```bash
show system-health sysready-status detail
# fail_reason を見て該当 feature の status を追跡

docker ps        # container は up?
sudo systemctl status <feature>.service

# STATE_DB 側
redis-cli -n 6 HGETALL "FEATURE|swss"

# sysmonitor のログ
journalctl -u system-health 2>/dev/null
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/system_health_monitoring/system-ready-HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
