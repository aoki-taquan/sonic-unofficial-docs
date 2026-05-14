---
title: APPL_DB NAT テーブル群
description: "APPL_DB NAT テーブル群 — NAT_TABLE / NAPT_TABLE / NAT_TWICE_TABLE / NAPT_TWICE_TABLE / NAT_GLOBAL_TABLE / NAPT_POOL_IP_TABLE / NAT_DNAT_POOL_TABLE の全フィールド定義と書き込み条件。natmgrd / natsyncd が CONFIG_DB から変換した結果を orchagent / NatOrch へ伝達する中間 APPL_DB テーブル群。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: cfgmgr/natmgr.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: cfgmgr/natmgr.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: natsyncd/natsync.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - NAT_GLOBAL
    - NAT_POOL
    - NAT_BINDINGS
    - STATIC_NAT
    - STATIC_NAPT
  cli:
    - config nat
    - show nat
  yang:
    - sonic-nat
---

# APPL_DB NAT テーブル群

## 概要

[NAT](../../reference/glossary.md#term-nat) 機能の [APPL_DB](../../reference/glossary.md#term-appl_db) 側テーブル群。[CONFIG_DB](../../reference/glossary.md#term-config_db) の静的 NAT 設定 (`STATIC_NAT` / `STATIC_NAPT` / `NAT_POOL` / `NAT_BINDINGS`) は `natmgrd` が変換し、kernel conntrack から検出された動的エントリは `natsyncd` が書き込む。`orchagent / NatOrch` がこれらのテーブルを購読し [SAI](../../reference/glossary.md#term-sai) NAT object を作成する[^1]。

テーブル名定数は `sonic-swss-common/common/schema.h`[^2] で定義される。

## テーブル一覧

| テーブル定数 | APPL_DB テーブル名 | 用途 |
|------------|-----------------|------|
| `APP_NAT_TABLE_NAME` | `NAT_TABLE` | IP のみ変換 (basic NAT) のエントリ |
| `APP_NAPT_TABLE_NAME` | `NAPT_TABLE` | IP + L4 ポート変換 (NAPT) のエントリ |
| `APP_NAT_TWICE_TABLE_NAME` | `NAT_TWICE_TABLE` | Twice NAT (SIP/DIP 両方変換) のエントリ |
| `APP_NAPT_TWICE_TABLE_NAME` | `NAPT_TWICE_TABLE` | Twice NAPT (SIP/DIP + ポート変換) のエントリ |
| `APP_NAT_GLOBAL_TABLE_NAME` | `NAT_GLOBAL_TABLE` | admin_mode / timeout のグローバル設定 |
| `APP_NAPT_POOL_IP_TABLE_NAME` | `NAPT_POOL_IP_TABLE` | NAPT pool の IP + port_range (natsync 用) |
| `APP_NAT_DNAT_POOL_TABLE_NAME` | `NAT_DNAT_POOL_TABLE` | DNAT pool IP の存在確認 (ref-count 管理) |

---

## NAT_TABLE

### key 構造

```text
NAT_TABLE|<ip_address>
```

`ip_address` は変換対象の外部 IP (DNAT) または内部 IP (SNAT)。Static / Dynamic のどちらのエントリも同一形式。

### フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `translated_ip` | IPv4 アドレス文字列 | yes | 変換後の IP アドレス |
| `nat_type` | `"snat"` / `"dnat"` | yes | SNAT / DNAT の別 |
| `entry_type` | `"static"` / `"dynamic"` | yes | 静的設定 / conntrack 由来の別 |
| `twice_nat_id` | 文字列 (1..9999) | no | Twice NAT のペア ID (static のみ) |

### 書き込み元

- `natmgr.cpp` `addStaticSingleNatEntry()` — static NAT (`STATIC_NAT` CONFIG_DB)
- `natsync.cpp` `addNatEntry()` L564-573 — dynamic conntrack イベント (SNAT 側 + DNAT 逆エントリ)

---

## NAPT_TABLE

### key 構造

```text
NAPT_TABLE|<protocol>:<ip_address>:<l4_port>
```

`protocol` は `"TCP"` または `"UDP"`。例: `TCP:192.168.1.1:1024`。

### フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `translated_ip` | IPv4 アドレス文字列 | yes | 変換後の IP アドレス |
| `translated_l4_port` | 文字列 (ポート番号) | yes | 変換後の L4 ポート番号 |
| `nat_type` | `"snat"` / `"dnat"` | yes | SNAT / DNAT の別 |
| `entry_type` | `"static"` / `"dynamic"` | yes | 静的設定 / conntrack 由来の別 |
| `twice_nat_id` | 文字列 (1..9999) | no | Twice NAT のペア ID (static のみ) |

### 書き込み元

- `natmgr.cpp` `addStaticSingleNaptEntry()` — static NAPT (`STATIC_NAPT` CONFIG_DB)
- `natsync.cpp` `addNatEntry()` L665-689 — dynamic SNAPT / DNAPT conntrack イベント

---

## NAT_TWICE_TABLE

### key 構造

```text
NAT_TWICE_TABLE|<src_ip>:<dst_ip>
```

Twice NAT ペアの (送信元 IP, 宛先 IP) を key とする。正方向と逆方向で 2 エントリが同時に書き込まれる。

### フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `entry_type` | `"static"` / `"dynamic"` | yes | 静的設定 / conntrack 由来の別 |
| `translated_src_ip` | IPv4 アドレス文字列 | yes (SET 時) | 変換後の送信元 IP |
| `translated_dst_ip` | IPv4 アドレス文字列 | yes (SET 時) | 変換後の宛先 IP |

### 書き込み元

- `natmgr.cpp` `addStaticTwiceNatEntry()` — static Twice NAT
- `natsync.cpp` `addNatEntry()` L534-539 — dynamic Twice NAT conntrack

---

## NAPT_TWICE_TABLE

### key 構造

```text
NAPT_TWICE_TABLE|<protocol>:<src_ip>:<src_port>:<dst_ip>:<dst_port>
```

### フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `entry_type` | `"static"` / `"dynamic"` | yes | 静的設定 / conntrack 由来の別 |
| `translated_src_ip` | IPv4 アドレス文字列 | yes (SET 時) | 変換後の送信元 IP |
| `translated_dst_ip` | IPv4 アドレス文字列 | yes (SET 時) | 変換後の宛先 IP |
| `translated_src_l4_port` | 文字列 (ポート番号) | yes (SET 時) | 変換後の送信元 L4 ポート |
| `translated_dst_l4_port` | 文字列 (ポート番号) | yes (SET 時) | 変換後の宛先 L4 ポート |

### 書き込み元

- `natmgr.cpp` `addStaticTwiceNaptEntry()` — static Twice NAPT
- `natsync.cpp` `addNatEntry()` L493-498 — dynamic Twice NAPT conntrack

---

## NAT_GLOBAL_TABLE

### key 構造

```text
NAT_GLOBAL_TABLE|Values
```

key は `"Values"` 固定 (singleton)。

### フィールド

| フィールド | 型 | 送信条件 | デフォルト | 説明 |
|-----------|----|---------|-----------|------|
| `admin_mode` | `"enabled"` / `"disabled"` | 常に送信 | `"disabled"` | NAT 機能の有効 / 無効 |
| `nat_timeout` | 文字列 (整数) | 非デフォルト(!=600)の場合のみ | `600` | 非 TCP/UDP セッションのタイムアウト秒 |
| `nat_tcp_timeout` | 文字列 (整数) | 非デフォルト(!=86400)の場合のみ | `86400` | TCP セッションのタイムアウト秒 |
| `nat_udp_timeout` | 文字列 (整数) | 非デフォルト(!=300)の場合のみ | `300` | UDP セッションのタイムアウト秒 |

### 書き込み元

- `natmgr.cpp` `enableNatFeature()` L5680-5706 — admin_mode=enabled 時
- `natmgr.cpp` `disableNatFeature()` L5736-5756 — admin_mode=disabled 時 (admin_mode フィールドのみ)
- `natmgr.cpp` `doNatGlobalTask()` L7317, L7360 — timeout 変更時 + DEL 時

---

## NAPT_POOL_IP_TABLE

### key 構造

```text
NAPT_POOL_IP_TABLE|<ip_address>
```

NAT pool 内の各 IP アドレスが個別エントリとなる。`natsyncd` が pool IP を確認する際に参照する。

### フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `port_range` | 文字列 (例: `"1024-65535"`) | yes | pool に設定された L4 ポート範囲 |

### 書き込み条件

`natmgr.cpp` L289: `port_range` が空文字列または `"NULL"` の場合はこのテーブルに書き込まない。pool に port 制限のない設定 (full-cone MASQUERADE) ではエントリが作成されない。

### 書き込み元

- `natmgr.cpp` `addNaptPoolIpEntry()` L285-328

---

## NAT_DNAT_POOL_TABLE

### key 構造

```text
NAT_DNAT_POOL_TABLE|<ip_address>
```

DNAT ターゲット IP の存在確認テーブル。ref count で重複管理され、0 になると `del` が呼ばれる。

### フィールド

| フィールド | 値 | 説明 |
|-----------|-----|------|
| `NULL` | `"NULL"` | 番兵値。実質フィールドなし (存在確認のみ) |

### 書き込み元

- `natmgr.cpp` `addDnatPoolEntry()` L1502-1522 — static NAT / NAPT で DNAT IP が追加されるたびに ref count をインクリメント。新規の場合のみ SET

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

### NAT_GLOBAL_TABLE の条件付き書き込み

`enableNatFeature()` (natmgr.cpp L5688-5703) でのタイムアウト書き込みは非デフォルト値の場合のみ実行される。

```cpp
// natmgr.cpp L5688-5703
if (m_natTcpTimeout != NAT_TCP_TIMEOUT_DEFAULT)   // !=86400
{
    FieldValueTuple q(NAT_TCP_TIMEOUT, std::to_string(m_natTcpTimeout));
    fvVector.push_back(q);
}
if (m_natUdpTimeout != NAT_UDP_TIMEOUT_DEFAULT)   // !=300
{
    FieldValueTuple r(NAT_UDP_TIMEOUT, std::to_string(m_natUdpTimeout));
    fvVector.push_back(r);
}
if (m_natTimeout != NAT_TIMEOUT_DEFAULT)           // !=600
{
    FieldValueTuple s(NAT_TIMEOUT, std::to_string(m_natTimeout));
    fvVector.push_back(s);
}
```

つまり全タイムアウトをデフォルトのまま `admin_mode=enabled` にすると、APPL_DB の `NAT_GLOBAL_TABLE|Values` には `admin_mode=enabled` のみが書き込まれ、timeout フィールドは省略される。orchagent / NatOrch はこれらのフィールドが不在の場合に内部デフォルト (同値) を使用する。

| フィールド | YANG default | コード hardcode | 省略条件 | 備考 |
|-----------|-------------|----------------|---------|------|
| `admin_mode` | `"disabled"` | — | 省略なし (常に送信) | enableNatFeature / disableNatFeature 両方で送信 |
| `nat_timeout` | `600` | `NAT_TIMEOUT_DEFAULT=600` | デフォルトと同値なら省略 | L5700-5703 |
| `nat_tcp_timeout` | `86400` | `NAT_TCP_TIMEOUT_DEFAULT=86400` | デフォルトと同値なら省略 | L5688-5691 |
| `nat_udp_timeout` | `300` | `NAT_UDP_TIMEOUT_DEFAULT=300` | デフォルトと同値なら省略 | L5694-5697 |

### DEL_COMMAND 時の挙動 (doNatGlobalTask)

`NAT_GLOBAL` の DEL 時 (L7344-7365): 全タイムアウトをデフォルト値にリセット後、`natAdminMode == ENABLED` の場合のみ APPL_DB にデフォルト値を書き込んでから `disableNatFeature()` を呼ぶ。`admin_mode=disabled` のまま DEL した場合は APPL_DB への書き込みなし。

### NAPT_POOL_IP_TABLE — port_range 省略時は非書き込み

| 条件 | 挙動 | ソース |
|------|------|------|
| `port_range` が空 or `"NULL"` | NAPT_POOL_IP_TABLE にエントリなし | `natmgr.cpp:289` |
| `port_range` が有効文字列 | 各 IP ごとに SET | `natmgr.cpp:321` |

pool に port 制限なし (`nat_port` 未設定) の場合、`NAPT_POOL_IP_TABLE` は更新されない。`natsyncd` は `matchingSnaptPoolExists()` でこのテーブルを参照するため、pool IP が無 port-range 設定の場合は `false` が返り、SNAPT 判定に影響する。

### NAT_DNAT_POOL_TABLE — 番兵値のみ

フィールドは `"NULL":"NULL"` の番兵 1 件のみ。このテーブルの目的は IP の存在確認であり、フィールド値は意味を持たない。orchagent NatOrch は key の存在で DNAT pool IP を判定する (`natorch.cpp` `doNatDnatPoolTableTask`)。

### Dynamic エントリ (natsync) における entry_type

`natsync.cpp` L380: `FieldValueTuple dynamic_entry("entry_type", "dynamic")` が常にセットされる。static エントリが同 key で存在する場合は dynamic で上書きしない (static 優先)。

```cpp
// natsync.cpp L412
if ((fvField(iter) == "entry_type") && (fvValue(iter) == "static"))
{
    // Static エントリが優先 — dynamic を無視して return
    return 1;
}
```

この priority チェックは NAT_TABLE / NAPT_TABLE / NAT_TWICE_TABLE / NAPT_TWICE_TABLE の全テーブルで共通に実装されている。
<!-- /defaults -->

## 購読者

- `orchagent / NatOrch` (`natorch.cpp`): 全 APPL_DB NAT テーブルを `ConsumerStateTable` で購読し、SAI NAT object (`sai_nat_api->create_nat_entry()`) を作成 / 削除する。
- `NatOrch::doNatGlobalTableTask()`: `NAT_GLOBAL_TABLE` の `admin_mode` 変化を検知し `enableNatFeature()` / `disableNatFeature()` を呼び出す。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `NAT_GLOBAL`、`NAT_POOL`、`NAT_BINDINGS`、`STATIC_NAT`、`STATIC_NAPT`
- 関連 CLI: `show nat translations`、`show nat statistics`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-nat`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-nat`](../yang/sonic-nat.md)
- CLI: [`config nat`](../cli/config-nat.md)
- CONFIG_DB: [`NAT_GLOBAL / NAT_POOL`](nat.md)
- CONFIG_DB: [`NAT_BINDINGS`](nat-bindings.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: natmgr + natsync 実装: `sonic-swss/cfgmgr/natmgr.cpp` / `sonic-swss/natsyncd/natsync.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/natmgr.cpp>
[^2]: テーブル名定数: `sonic-swss-common/common/schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h>

<!-- ops-hint -->
## 運用ヒント

### 確認コマンド

```bash
# APPL_DB NAT エントリ確認
sonic-db-cli APPL_DB keys 'NAT_TABLE:*'
sonic-db-cli APPL_DB keys 'NAPT_TABLE:*'
sonic-db-cli APPL_DB hgetall 'NAT_GLOBAL_TABLE:Values'

# 変換テーブル表示
show nat translations
show nat statistics

# Dynamic エントリの確認 (conntrack)
conntrack -L
```

### よくある問題

- `NAT_GLOBAL_TABLE|Values` に timeout フィールドが存在しない → デフォルト値と同じ値のため省略されている (正常動作)
- `NAPT_POOL_IP_TABLE` にエントリがない → pool に `nat_port` が未設定 (full-cone MASQUERADE) のため非書き込み (正常動作)
- `NAT_DNAT_POOL_TABLE` の値が `"NULL":"NULL"` のみ → 仕様通り (存在確認テーブル)
<!-- /ops-hint -->
