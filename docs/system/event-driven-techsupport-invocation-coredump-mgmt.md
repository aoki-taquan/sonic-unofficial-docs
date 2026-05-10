---
title: Event-Driven TechSupport / Coredump 管理（auto-techsupport / rate-limit / quota）
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/auto-techsupport/auto_techsupport_and_coredump_mgmt.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - AUTO_TECHSUPPORT
    - AUTO_TECHSUPPORT_FEATURE
  cli:
    - config auto-techsupport
    - show auto-techsupport
  yang:
    - sonic-auto-techsupport
---

!!! warning "裏取りステータス: code-verified"
    coredump_gen_handler / techsupport_cleanup の現行 master 取り込み、rate-limit と quota 既定値は未確認。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: `sonic-utilities/scripts/coredump_gen_handler.py` / `utilities_common/auto_techsupport_helper.py` / `show/plugins/auto_techsupport.py` で auto-techsupport 経路を確認。yang は `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-auto_techsupport.yang` に CONFIG_DB スキーマを確認。

# Event-Driven TechSupport / Coredump 管理（auto-techsupport / rate-limit / quota）

## 概要

SONiC の docker 内プロセスが crash すると、core ファイルが生成される。**core 生成イベントを契機に自動で `show techsupport` を呼び、結果アーカイブと core を保存** するのが本機能の中核[^1]。狙い:

- 障害解析に必要な状態（log / config / counter / SAI dump）を **障害発生時点** の snapshot として残す
- core / techsupport の **disk 容量爆発を防ぐ**（rate-limit + quota）
- per-feature で発火条件 / 抑制を変えられる（`AUTO_TECHSUPPORT_FEATURE`）

## 動作仕様

```mermaid
flowchart LR
    PROC[docker 内 process crash] --> CORE[/var/core/<feature>/<pid>.core.gz]
    CORE --> HANDLER[coredump_gen_handler]
    HANDLER --> RL{rate-limit /\nfeature 抑制?}
    RL -- skip --> END[終了]
    RL -- ok --> RUN[show techsupport を非同期起動]
    RUN --> AR[/var/dump/sonic_dump_<host>_<ts>.tar.gz]
    AR --> CLEAN[techsupport_cleanup\n(quota 超過なら古い物を削除)]
    HANDLER --> SDB[STATE_DB\nAUTO_TECHSUPPORT|*]
```

主要要素[^1]:

- **trigger**: kernel `core_pattern` が `coredump_gen_handler` を呼ぶ仕組み（`/proc/sys/kernel/core_pattern`）
- **rate-limit**: 同一 feature で短時間に複数 crash しても techsupport は **rate-limit 内 1 回のみ**
- **per-feature 設定**: 自動 techsupport 不要な feature は `AUTO_TECHSUPPORT_FEATURE.<f>.state=disabled`
- **quota**: 全体 / per-feature の保存上限を `since` / `core_cleanup_threshold` 等で制御
- **non-blocking**: 本体 process の crash を妨げない非同期実行

## 関連 CONFIG_DB

| Key | 説明 |
|-----|------|
| `AUTO_TECHSUPPORT|GLOBAL` | global state, rate-limit, max disk usage 等 |
| `AUTO_TECHSUPPORT_FEATURE|<f>` | per-feature の enable / rate-limit override |

## 関連 STATE_DB

| Table | 説明 |
|-------|------|
| `AUTO_TECHSUPPORT|<key>` | 直近の発火時刻、生成 archive のメタ |

## 関連 CLI

| Command | 用途 |
|---------|------|
| `config auto-techsupport global state {enabled,disabled}` | 全体 on/off |
| `config auto-techsupport global rate-limit-interval <sec>` | rate-limit |
| `config auto-techsupport feature state <f> {enabled,disabled}` | per-feature |
| `show auto-techsupport global` / `... feature` | 現状 |
| `show auto-techsupport history` | 履歴 |

## 制限事項

- **`show techsupport` 自体が重い**: SAI dump や log 量が多いと数分単位の負荷
- **disk が逼迫すると却って動けない**: quota / cleanup の不整備で full となる事故あり
- **rate-limit window が短すぎ**: フラッピング crash で抑制過多 → 解析情報を取りこぼす可能性
- **kernel core_pattern を奪う**: 他コンポーネントとの共存はパターン記述しだい

## 干渉する機能

- **show techsupport**: 本体は同 area の別ページ
- **kdump**: kernel panic 系の dump とは別系統。両立可能
- **system health monitor**: critical 通知のトリガに使うこともある
- **persistent log level**: log level 状態と組合せて debug 情報の濃さが変わる

## トラブルシューティング

- 自動発火しない → `core_pattern`、`coredump_gen_handler` の存在、global state、feature state を確認
- 連続 crash で 1 回しか取れない → rate-limit interval を一時的に短く
- disk full → `/var/dump/` の cleanup スクリプト動作、quota 設定

## 引用元

[^1]: `sonic-net/SONiC` `doc/auto-techsupport/auto_techsupport_and_coredump_mgmt.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- coredump_gen_handler / techsupport_cleanup script の現行 sonic-utilities / sonic-buildimage 取り込み確認
- /proc/sys/kernel/core_pattern の現行設定値確認
- CONFIG_DB AUTO_TECHSUPPORT / AUTO_TECHSUPPORT_FEATURE スキーマと sonic-yang-models 取り込み確認
- STATE_DB AUTO_TECHSUPPORT スキーマの現行値確認
- config auto-techsupport / show auto-techsupport CLI の sonic-utilities 取り込み確認
- system health monitor / kdump / persistent log level との連携の現行実装確認
-->
