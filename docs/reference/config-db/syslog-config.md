---
title: SYSLOG_CONFIG テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-syslog.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SYSLOG_CONFIG
    - SYSLOG_CONFIG_FEATURE
    - SYSLOG_SERVER
  cli:
    - config syslog
  yang:
    - sonic-syslog
---

# SYSLOG_CONFIG テーブル

## 概要

ホスト全体の rsyslog グローバル設定を CONFIG_DB に保持するシングルトンテーブル[^1]。`hostcfgd` (`sonic-host-services` 内 `syslog` ハンドラ) が `/etc/rsyslog.conf` および各 docker の rsyslog テンプレに反映する。

## key 構造

```
SYSLOG_CONFIG|GLOBAL
```

固定キー `GLOBAL` のみのシングルトン container (`SYSLOG_CONFIG.GLOBAL`)。

## フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `rate_limit_interval` | uint32 (0..2147483647 秒) | なし | rsyslog rate-limit インターバル (`syslog-rate-limit-interval` typedef) |
| `rate_limit_burst` | uint32 (0..2147483647 件) | なし | rate-limit バースト件数 (`syslog-rate-limit-burst` typedef) |
| `format` | enum `welf`/`standard` | `standard` | ログ書式 (`log-format` typedef) |
| `welf_firewall_name` | string | なし | WELF 形式時のファイアウォール名 (`format != 'standard'` の must 制約あり) |
| `severity` | enum `none`/`debug`/`info`/`notice`/`warn`/`error`/`crit` | `notice` | ローカル最低 severity (`rsyslog-severity` typedef) |

## 制約

- `welf_firewall_name` は `must "(../format != 'standard')"` で WELF 形式時にのみ意味を持つ
- container 名 `SYSLOG_CONFIG`、内部 container 名 `GLOBAL` (YANG コメントには `SYSLOG_CONFIG_LIST` と書かれているが、実体は container)[^1]

## 購読者

- `hostcfgd` (`sonic-host-services`): CONFIG_DB → rsyslog テンプレ展開 → systemd reload
- 各 docker 内の `rsyslogd`: ホスト側 rsyslog にフォワード後、グローバル設定で集約

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: [`SYSLOG_CONFIG_FEATURE`](syslog-config-feature.md), [`SYSLOG_SERVER`](syslog-server.md)
- 関連 CLI: `config syslog rate-limit-host` / `config syslog level`
- 関連 YANG: `sonic-syslog`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-syslog`](../yang/sonic-syslog.md)
- CLI: [`config syslog`](../cli/config-syslog.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `src/sonic-yang-models/yang-models/sonic-syslog.yang` (container `SYSLOG_CONFIG` / `GLOBAL`、typedef `log-format`/`rsyslog-severity`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-syslog.yang>

## 関連ページ
- [CONFIG_DB: SYSLOG_CONFIG_FEATURE](syslog-config-feature.md)
- [CONFIG_DB: SYSLOG_SERVER](syslog-server.md)
