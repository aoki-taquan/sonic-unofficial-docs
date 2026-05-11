---
title: show runningconfiguration / startupconfiguration サブコマンド
description: "show runningconfiguration / startupconfiguration サブコマンド — SONiC で「現在の running config」を見るには CLI が show runningconfiguration（show running-config のエイリアスではない、空白なしの…"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - PORT
    - INTERFACE
    - SNMP
    - SNMP_COMMUNITY
    - SNMP_USER
    - ACL_RULE
    - STP
  cli:
    - show runningconfiguration
    - show startupconfiguration
  yang: []
---

# show runningconfiguration / startupconfiguration サブコマンド

## 概要

SONiC で「現在の running config」を見るには CLI が **`show runningconfiguration`**（`show running-config` のエイリアスではない、空白なしの単一トークン）。本ページは同グループ配下のサブコマンドを網羅する。実装は `show/main.py` 内の `runningconfiguration` group[^1]。多くのサブコマンドは `sonic-cfggen -d --var-json <TABLE>` の薄いラッパで、CONFIG_DB から JSON を取り出して表示する。`startupconfiguration bgp` も合わせて扱う。

## コマンド一覧

### `show runningconfiguration ...`

| コマンド | 用途 | 実装 |
|---------|------|-----|
| `show runningconfiguration all` | host + 各 namespace の CONFIG_DB JSON ダンプ + bgpraw | `get_config_json_by_namespace` + `vtysh -c "show running-config"` |
| `show runningconfiguration acl` | ACL_RULE のみ | `sonic-cfggen -d --var-json ACL_RULE` |
| `show runningconfiguration ports [<portname>]` | PORT テーブル | `sonic-cfggen -d --var-json PORT [--key NAME]` |
| `show runningconfiguration bgp [-n NS]` | FRR の vtysh `show running-config` | `bgp_util.run_bgp_show_command` |
| `show runningconfiguration interfaces [<ifname>]` | INTERFACE テーブル | `sonic-cfggen -d --var-json INTERFACE [--key NAME]` |
| `show runningconfiguration ntp` | `/etc/chrony/chrony.conf` を grep | ファイルパース |
| `show runningconfiguration snmp` | SNMP / SNMP_COMMUNITY / SNMP_USER 全部 | `show_run_snmp` |
| `show runningconfiguration snmp community` | community のみテーブル表示 | CONFIG_DB |
| `show runningconfiguration snmp contact` | contact 表示 | CONFIG_DB |
| `show runningconfiguration snmp location` | location 表示 | CONFIG_DB |
| `show runningconfiguration snmp user` | user 一覧 | CONFIG_DB |
| `show runningconfiguration syslog` | `/etc/rsyslog.conf` から `omfwd` Target を抽出 | ファイルパース |
| `show runningconfiguration spanning_tree` | STP / STP_PORT / STP_VLAN / STP_VLAN_PORT を順次 | `sonic-cfggen` |
| `show runningconfiguration copp` | COPP_GROUP / COPP_TRAP | `sonic-cfggen` |

### `show startupconfiguration bgp [-n NS]`

| コマンド | 用途 |
|---------|------|
| `show startupconfiguration bgp` | bgp コンテナ内の `/etc/quagga/bgpd.conf` 等の **起動時にロードされた config** を `cat` する |

実装は `docker ps | grep bgp | awk` から bgp コンテナ名を取り、`docker exec <bgp> cat /etc/quagga/bgpd.conf` 系を呼ぶ。multi-ASIC 対応で各 namespace から取得可能[^2]。

## 各コマンドの詳細

### `show runningconfiguration all`

**動作**:

1. `multi_asic.DEFAULT_NAMESPACE`（host）から `get_config_json_by_namespace` で CONFIG_DB JSON を取得。
2. multi-ASIC では各 namespace 分も同様に取得し、加えて namespace ごとに `bgp_util.is_bgp_feature_state_enabled(ns)` が真なら `vtysh -c "show running-config"` の出力を `bgpraw` フィールドに添付。
3. JSON を `json.dumps(..., indent=4)` で標準出力に書く。

single-ASIC では `output['localhost']` のみを返し、`bgpraw` を host config に直接添付する形になる。

<!-- evidence:
source: sonic-net/sonic-utilities/show/main.py#L1828-L1850 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @runningconfiguration.command()
  def all(verbose):
      output = {}
      bgpraw_cmd = "show running-config"
      ...
      host_config['bgpraw'] = bgp_util.run_bgp_show_command(bgpraw_cmd, exit_on_fail=False)
-->

### `show runningconfiguration ports [<portname>]`

`sonic-cfggen -d --var-json PORT [--key <portname>]` を `run_command` で起動。1 ポート指定で当該エントリのみ JSON 出力。

### `show runningconfiguration bgp [-n NS]`

multi-ASIC では `-n` を必ず単一 namespace 名のいずれかに合わせる必要がある（不一致は ctx.fail）。single-ASIC で `-n` を渡すと拒否される[^3]。各 namespace で `vtysh -c "show running-config bgp"` の結果を `------------Showing running config bgp on <ns>------------` ヘッダ付きで連結。

### `show runningconfiguration ntp`

`/etc/chrony/chrony.conf` を 1 行ずつ読み、`server <addr>` 行から server アドレスを抽出して `tabulate` で 1 列表示する。**CONFIG_DB の `NTP_SERVER` は読まない**点に注意（chrony.conf は別経路で生成される）。

### `show runningconfiguration syslog`

`/etc/rsyslog.conf` から `^action(type="omfwd" Target="(.+?)".*)` 正規表現で送信先を抽出して列挙。CONFIG_DB の `SYSLOG_SERVER` は直接見ない。

### `show runningconfiguration snmp`

サブコマンドなしで叩くと `show_run_snmp(db.cfgdb)` が community / contact / location / user を順番に表示する。`invoke_without_command=True` の Click group なので、サブコマンドありで叩いた場合は当該サブコマンドのみが実行される。

## 関連する CONFIG_DB / ファイル

| ソース | 該当コマンド |
|--------|-------------|
| CONFIG_DB 全体 | `show runningconfiguration all` |
| `PORT` | `show runningconfiguration ports` |
| `INTERFACE` | `show runningconfiguration interfaces` |
| `ACL_RULE` | `show runningconfiguration acl` |
| `SNMP` / `SNMP_COMMUNITY` / `SNMP_USER` | `show runningconfiguration snmp ...` |
| `STP` / `STP_PORT` / `STP_VLAN` / `STP_VLAN_PORT` | `show runningconfiguration spanning_tree` |
| `COPP_GROUP` / `COPP_TRAP` | `show runningconfiguration copp` |
| `/etc/chrony/chrony.conf`（CONFIG_DB ではない） | `show runningconfiguration ntp` |
| `/etc/rsyslog.conf`（CONFIG_DB ではない） | `show runningconfiguration syslog` |
| FRR (`vtysh`) | `show runningconfiguration bgp` / `all`（添付の `bgpraw`） |
| bgp コンテナ内 config | `show startupconfiguration bgp` |

## 注意

- `show running-config`（`-` 区切り）は SONiC の click 上には存在しない。`config/main.py` ではなく **`show runningconfiguration`** を使う。
- `all` の出力は **JSON のみ**、テキスト config 形式ではない。
- `ntp` / `syslog` は CONFIG_DB を見ず、生成済みの conf ファイルを直接 grep する。CONFIG_DB と乖離している場合は乖離が見える。

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`PORT`](../config-db/port.md) / [`INTERFACE`](../config-db/interface.md) / [`SNMP`](../config-db/snmp.md) / [`SNMP_COMMUNITY`](../config-db/snmp.md) / [`SNMP_USER`](../config-db/snmp.md) / [`ACL_RULE`](../config-db/acl-rule.md) / `STP`

<!-- ref-triangle:end -->

## 引用元

[^1]: `runningconfiguration` group 定義は `show/main.py` L1821-L1824。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L1821>

[^2]: `startupconfiguration bgp` は `show/main.py` L2167 〜。bgp コンテナ名を `docker ps` で動的に取得する。

[^3]: `show runningconfiguration bgp` の multi-ASIC バリデーションは `show/main.py` L1890-L1896。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L1890>


<!-- usage-example -->
## 実行例

### 典型的な使い方

```bash
# 例 1: 全 running config をダンプ
show runningconfiguration all
```

### よくある引数の組み合わせ

```bash
show runningconfiguration bgp
show runningconfiguration acl
show runningconfiguration interfaces
show runningconfiguration syslog
```

### 期待される出力 (抜粋)

```
{
    "BGP_NEIGHBOR": {
        "10.0.0.1": {
            "admin_status": "up",
            "asn": "65100"
        }
    },
    ...
}
```
<!-- /usage-example -->
