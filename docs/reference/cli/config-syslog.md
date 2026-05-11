---
title: config syslog サブコマンド
description: "config syslog サブコマンド — config syslog は SONiC ホストおよび feature コンテナの syslog 設定 (リモート送信先 / レート制限 / ログレベル) を CONFIG_DB に書き込む CLI で、config/syslog.py の @click.group()…"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-utilities
    path: config/syslog.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - SYSLOG_SERVER
    - SYSLOG_CONFIG
    - SYSLOG_CONFIG_FEATURE
    - LOGGER
  cli:
    - config syslog
  yang: []
---

# config syslog サブコマンド

## 概要

`config syslog` は SONiC ホストおよび feature コンテナの syslog 設定 (リモート送信先 / レート制限 / ログレベル) を CONFIG_DB に書き込む CLI で、`config/syslog.py` の `@click.group()` がエントリポイントとなる[^1]。

`hostcfgd` および各 feature コンテナの supervisord ラッパが CONFIG_DB を購読して `rsyslog` 設定を再生成する。CLI 自身は rsyslog をリスタートしないため、変更が反映されるまでタイムラグがある。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config syslog add <server_ip> [--source <src>] [--port <p>] [--vrf <vrf>]` | リモート syslog サーバ追加 |
| `config syslog del <server_ip>` | リモートサーバ削除 |
| `config syslog rate-limit-host [-i <sec>] [-b <num>]` | ホスト rsyslog のレート制限 (interval / burst) |
| `config syslog rate-limit-container <service> [-i <sec>] [-b <num>] [-n <ns>]` | feature コンテナのレート制限 |
| `config syslog rate-limit-feature enable [<service>] [-n <ns>]` | feature 単位でレート制限機能を on |
| `config syslog rate-limit-feature disable [<service>] [-n <ns>]` | レート制限を off |
| `config syslog level -i <id> -l <level> [--container <c>] [--program <p>] [--pid] [-n <ns>]` | サブコンポーネントのログレベル設定 |

## 各コマンドの詳細

### `config syslog add <server_ip> [--source ...] [--port ...] [--vrf ...]`

**引数 / オプション**:

- `<server_ip_address>` ... IPv4 / IPv6。`ip_addr_validator` で検証。
- `--source <ip>` ... 送信元 IP (Loopback 等を想定)。`source_validator` がアドレス整合と存在検査を行う。
- `--port <port>` ... 送信先 UDP port (省略時 514)。
- `--vrf <vrf>` ... 出力 VRF。`mgmt` (mgmt-vrf) または CONFIG_DB の `VRF` テーブルに存在する VRF。`source` と組み合わせる場合 `source_to_vrf_validator` で同 VRF 内のインタフェースかをチェックする。

**動作**:
`SYSLOG_SERVER|<server_ip>` を新規作成する。同じ key が既存ならエラー終了 (重複はサポートしない)[^2]。

### `config syslog del <server_ip>`

`SYSLOG_SERVER|<server_ip>` を削除。存在しないアドレスを与えるとエラー終了。

### `config syslog rate-limit-host [-i <interval>] [-b <burst>]`

`SYSLOG_CONFIG|GLOBAL` (または同等のグローバル key) に `rate_limit_interval` / `rate_limit_burst` を書く。`interval` `burst` の `IntRange(0, 2147483647)` 制約だけ CLI 側で適用される。

### `config syslog rate-limit-container <service_name> [-i <interval>] [-b <burst>] [-n <namespace>]`

`SYSLOG_CONFIG_FEATURE|<service>` に同フィールドを書く。`-n` を付けると multi-ASIC namespace の CONFIG_DB に書き込む。

### `config syslog rate-limit-feature enable|disable [<service>] [-n <ns>]`

`get_feature_names_to_proceed` がサービス名を解決し、各 `SYSLOG_CONFIG_FEATURE` エントリの rate-limit 機能 on/off フラグを更新する。`<service>` 省略時は全 feature を一括処理する。

### `config syslog level -i <identifier> -l <level> [--container <c>] [--program <p>] [--pid] [-n <ns>]`

`LOGGER` テーブル (またはサブシステム別の logger テーブル) に `severity` を書く。識別子は `(container, program, pid)` の組み合わせで、`--container` / `--program` を併用すると特定の rsyslog ログタグだけを対象にする。`--pid` は実行中プロセスの PID にひもづけたい場合のオプション。

## 関連する CONFIG_DB

| テーブル | キー | 主なフィールド | 操作するコマンド |
|----------|------|---------------|------------------|
| `SYSLOG_SERVER` | `<server_ip>` | `source`, `port`, `vrf` | `add` / `del` |
| `SYSLOG_CONFIG` | `GLOBAL` | `rate_limit_interval`, `rate_limit_burst` | `rate-limit-host` |
| `SYSLOG_CONFIG_FEATURE` | `<service>` | `rate_limit_interval`, `rate_limit_burst`, enable/disable | `rate-limit-container` / `rate-limit-feature` |
| `LOGGER` | `<identifier>` 等 | `LOGLEVEL`, `LOGOUTPUT` | `level` |

## 注意

- VRF を指定する場合、mgmt-vrf を使うには `is_mgmt_vrf_enabled` で `MGMT_VRF_CONFIG` の有効性が確認される。mgmt-vrf 未設定で `--vrf mgmt` を渡すとエラー。
- `add` コマンドは IPv4 / IPv6 両対応だが、CLI 引数では区別せず、`ipaddress.ip_address()` で自動判別する。
- レート制限の単位は **rsyslog の `imuxsock` ratelimit** (interval 秒間に burst 件まで) であり、CLI が指定するのはそれの interval / burst パラメータそのまま。

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`SYSLOG_SERVER`](../config-db/syslog-server.md) / [`SYSLOG_CONFIG`](../config-db/syslog-config.md) / [`SYSLOG_CONFIG_FEATURE`](../config-db/syslog-config-feature.md) / `LOGGER`

<!-- ref-triangle:end -->

## 引用元

[^1]: `syslog` グループは `config/syslog.py` L361-L368。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/syslog.py#L361>

[^2]: `add` / `delete` は `config/syslog.py` L370-L454。重複検査は `is_exist_in_db`。

<!-- ops-hint -->
## 運用ヒント

### 典型的な利用シーン

- 外部 syslog server への転送設定、severity 調整。
- rate-limit による flood 抑止。

### よくある落とし穴

- VRF (mgmt) 越しに送る場合 `--source` と VRF 指定を忘れると届かない。
- rate-limit を厳しくしすぎると障害時のログが欠落する。

### 関連する show / debug

```bash
show syslog
show runningconfiguration syslog
systemctl status rsyslog
```
<!-- /ops-hint -->

## 関連ページ
- [HLD: Syslog Source IP](../../system/sonic-syslog-source-ip.md)
- [CONFIG_DB: SYSLOG_SERVER](../config-db/syslog-server.md)
- [YANG: sonic-syslog](../yang/sonic-syslog.md)

<!-- usage-example -->
## 実行例

### 典型的な使い方

```bash
# 例 1: リモート syslog サーバを追加
sudo config syslog add 10.0.0.100
```

### よくある引数の組み合わせ

```bash
# VRF / source / port 指定
sudo config syslog add 10.0.0.100 --source 10.0.0.1 --vrf mgmt --port 514

# 削除
sudo config syslog del 10.0.0.100
```

### 期待される出力 (抜粋)

```
Restarting rsyslog-config service ...
```
<!-- /usage-example -->

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->
