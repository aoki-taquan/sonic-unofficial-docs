---
title: NAT_BINDINGS テーブル
description: "NAT_BINDINGS テーブル — dynamic NAT のバインディング設定。ACL と NAT pool を関連付けて動的 SNAT ルールを定義する CONFIG_DB テーブル。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: cfgmgr/natmgr.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: cfgmgr/natmgr.h
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/natorch.cpp
    ref: HEAD
  - repo: sonic-net/sonic-utilities
    path: config/nat.py
    ref: HEAD
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-nat.yang
    ref: HEAD
related:
  config_db:
    - NAT_GLOBAL
    - NAT_POOL
    - NAT_BINDINGS
    - STATIC_NAT
    - STATIC_NAPT
  cli:
    - config nat
  yang:
    - sonic-nat
---

# NAT_BINDINGS テーブル

## 概要

`NAT_BINDINGS` は dynamic [NAT](../../reference/glossary.md#term-nat) のバインディングを定義する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル。[ACL](../../reference/glossary.md#term-acl) テーブルと [NAT](../../reference/glossary.md#term-nat) pool を関連付け、対象トラフィックの動的 SNAT ルールを `natmgrd` 経由で kernel / [ASIC](../../reference/glossary.md#term-asic) に適用する[^1]。エントリ最大 16 件。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>NAT_GLOBAL")]
  DM["natmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_NAT_GLOBAL_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_switch_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
NAT_BINDINGS|<binding_name>
```

`binding_name` は 1..32 文字、`[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` パターン。

## 主要フィールド

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `nat_pool` | leafref → `NAT_POOL.name` | yes | — | バインディング対象の [NAT](../../reference/glossary.md#term-nat) pool 名 |
| `access_list` | 文字列 ([ACL](../../reference/glossary.md#term-acl) 名, カンマ区切り可) | no | `""` (空) | 対象トラフィックを絞る [ACL](../../reference/glossary.md#term-acl) 名。省略時は全送信元が対象 |
| `nat_type` | enum `snat` / `dnat` | no | `"snat"` | NAT 種別。現時点で `dnat` は未サポート (CLI が拒否) |
| `twice_nat_id` | uint16 1..9999 | no | `""` → Single NAT | Twice NAT 用 ID。省略時 Single NAT として動作 |

<!-- defaults -->
### コード由来の暗黙デフォルト

以下のデフォルトはコードレベルで確認済み（[YANG](../../reference/glossary.md#term-yang) / CLI / natmgr 三箇所一致）。

| フィールド | 暗黙デフォルト | 根拠コード |
|-----------|--------------|-----------|
| `access_list` | `""` (空文字列) | `config/nat.py:797` acl_name=None → `""` / `natmgr.cpp:6879` EMPTY_STRING 初期化 |
| `nat_type` | `"snat"` | [YANG](../../reference/glossary.md#term-yang) `default snat` / `nat.py:821` / `natmgr.cpp:7056-7058` empty → SNAT_NAT_TYPE |
| `twice_nat_id` | `""` → Single NAT | `nat.py:823-824` None → `"NULL"` → DB / `natmgr.cpp:6993-6996` `"NULL"` → EMPTY_STRING |

**`nat_type` が空の場合の natmgr 動作**:

```cpp
// natmgr.cpp:7056-7063
if (nat_type.empty())
{
    m_natBindingInfo[key].nat_type = SNAT_NAT_TYPE;  // "snat"
}
```

**`twice_nat_id` の `"NULL"` 変換**:

```cpp
// natmgr.cpp:6993-6996
if (twice_nat_id == "NULL")
{
    twiceNatFound = false;
    twice_nat_id = EMPTY_STRING;  // "" → Single NAT モード
}
```

**Single NAT / Twice NAT 分岐**:

```cpp
// natmgr.cpp:4663-4679
if (m_natBindingInfo[key].twice_nat_id.empty())
{
    // Single NAT: ACL あり/なしで iptables ルール設定
    setDynamicAllForwardOrAclbasedRules(ADD, pool_interface, ip_range, port_range, acls_name, key);
}
else
{
    // Twice NAT: addDynamicTwiceNatRule() へ
    addDynamicTwiceNatRule(key);
}
```
<!-- /defaults -->

## 制約

- エントリ数上限: **16 件** (YANG `max-elements 16` / CLI `nat.py:812` でも同チェック)
- バインディング名: 最大 32 文字
- `nat_pool`: 存在する `NAT_POOL` エントリへの leafref (必須)
- `nat_type=dnat`: CLI (`config nat add binding`) が `"Ignored, DNAT is not yet supported for Binding"` を表示して拒否
- `twice_nat_id` 有効範囲: 1..9999 (範囲外は YANG / natmgr が拒否)
- 同一 `twice_nat_id` を持てるエントリ: 最大 2 件 (`STATIC_NAT`・`STATIC_NAPT`・`NAT_BINDINGS` 合計)

## 購読者

- `natmgrd` (`doNatBindingTask`): [CONFIG_DB](../../reference/glossary.md#term-config_db) の `NAT_BINDINGS` 変更を検知し、NAT pool・ACL の状態確認後に kernel iptables ルールおよび [APPL_DB](../../reference/glossary.md#term-appl_db) NAT エントリを設定する。
- `orchagent / NatOrch`: [APPL_DB](../../reference/glossary.md#term-appl_db) の NAT エントリを消費して [SAI](../../reference/glossary.md#term-sai) NAT object を作成する。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `NAT_GLOBAL`、`NAT_POOL`、`STATIC_NAT`、`STATIC_NAPT`、`ACL_TABLE`
- 関連 CLI: `config nat add binding`、`config nat remove binding`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-nat`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-nat`](../yang/sonic-nat.md)
- CLI: [`config nat`](../cli/config-nat.md)
- CONFIG_DB: [`NAT_GLOBAL / NAT_POOL`](nat.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義 + natmgr 実装: `sonic-nat.yang` / `sonic-swss/cfgmgr/natmgr.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/natmgr.cpp>

<!-- ops-hint -->
## 運用ヒント

### 典型設定

```bash
# Pool + Binding の追加
config nat add pool POOL1 192.168.100.1-192.168.100.10 1024-65535
config nat add binding BIND1 POOL1

# ACL を指定して特定サブネットのみ NAT
config nat add binding BIND2 POOL1 ACL_SRC_SUBNET

# Twice NAT binding
config nat add binding BIND3 POOL1 -twice_nat_id 100
```

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'NAT_BINDINGS|BIND1'
show nat config bindings
show nat translations
```

### よくある誤設定

- `nat_pool` に存在しない pool 名を指定 → natmgr がルールをスキップ (`"Pool is not yet enabled"` ログ)
- `nat_type=dnat` を指定 → CLI が拒否。Binding は SNAT 専用
- `twice_nat_id` 重複 → 同 ID を持つエントリが 3 件以上になると `"Same Twice nat id is not allowed for more than 2 entries!!"` エラー
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/cfgmgr/natmgr.cpp doNatBindingTask -->

- **バインディング名が 32 文字超 → スキップ**: `"Invalid binding name length - %zu, skipping %s"` をログしてエントリを消費 (`natmgr.cpp:6899-6904`)。
- **`nat_type=dnat` → SWSS_LOG_ERROR + スキップ**: `"Invalid nat_type %s, skipping %s"` をログ (`natmgr.cpp:6986-6991`)。YANG でも snat がデフォルトで dnat は運用非推奨。
- **`twice_nat_id="NULL"` → 空文字列扱い**: CLI が省略時に `"NULL"` を書き込むが、natmgr が `EMPTY_STRING` に変換して Single NAT モードで処理 (`natmgr.cpp:6993-6996`)。
- **Pool が未登録の状態で Binding 追加 → ルール延期**: natmgr はキャッシュに Binding 情報を格納するが `"Pool is not yet enabled, skipping dynamic nat rules addition"` としてルール設定をスキップ。Pool が後から登録されると再トリガーされる。
- **NAT feature が disabled → ルール延期**: `isNatEnabled()=false` の場合、`addDynamicNatRule` 内でスキップし `"NAT is not yet enabled"` をログ (`natmgr.cpp:4632-4636`)。
- **重複エントリ (同 pool_name + acl_name) → スキップ**: `"Duplicate Binding and it's values, skipping"` をログ (`natmgr.cpp:7037`)。
- **エントリ上限 16 件 → CLI が拒否**: `"Failed to add binding, as already reached maximum binding limit 16."` (`nat.py:812-813`)。YANG も `max-elements 16` で同様に制限。
<!-- /cdb-exceptions -->

<!-- value-behavior -->
## 値依存挙動マトリクス

<!-- evidence: sonic-swss/cfgmgr/natmgr.cpp addDynamicNatRule / doNatBindingTask -->

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `access_list` | `""` (省略時デフォルト) | 全送信元トラフィックを NAT 対象にする (ACL なし full-cone NAT) |
| `access_list` | ACL 名 (カンマ区切り) | 指定 ACL に一致するトラフィックのみ NAT |
| `nat_type` | `"snat"` (デフォルト) | 送信元 IP を pool IP に変換 (内 → 外方向) |
| `nat_type` | `"dnat"` | CLI が拒否。natmgr も `SNAT_NAT_TYPE` のみ受け付ける |
| `twice_nat_id` | 省略 / `"NULL"` / `""` | Single NAT モード (`setDynamicAllForwardOrAclbasedRules`) |
| `twice_nat_id` | 1..9999 | Twice NAT モード (`addDynamicTwiceNatRule`) |

enum: `nat_type`=snat/dnat (有効値は snat のみ)。
<!-- /value-behavior -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **[natmgrd](../../reference/glossary.md#term-natmgrd-natsyncd)** (`sonic-swss/cfgmgr/natmgrd.cpp:113`): `CFG_NAT_BINDINGS_TABLE_NAME` を `SubscriberStateTable` で購読。

### 段階 2: CFG → キャッシュ + iptables

- `doNatBindingTask` がフィールドを解析し `m_natBindingInfo[key]` に格納。
- `nat_type` 省略時は `SNAT_NAT_TYPE ("snat")` をキャッシュに設定。
- `twice_nat_id="NULL"` は `EMPTY_STRING` に変換してから格納。
- `addDynamicNatRule` が NAT 有効状態・pool 存在・L3 インタフェース存在を確認してから iptables ルールを設定。

### 段階 3: APPL → SAI

- `natmgrd` が APP_DB の `NAT_DNAT_POOL_TABLE` / iptables 経由で動的 NAT エントリを管理。
- `orchagent / NatOrch` が APP_DB エントリを消費して [SAI](../../reference/glossary.md#term-sai) NAT object を作成。

<!-- /runtime-trace -->

<!-- ordering -->
## 書込み順依存 (Phase B)

<!-- evidence: sonic-swss/orchagent/natorch.cpp NatOrch::addNatEntry L1866-1935 / enableNatFeature L2534-2581 / doDnatPoolTableTask L2968-3031 / doNatGlobalTableTask L2904-2966 / addAllDnatPoolEntries L1854-1864 / addAllNatEntries L3178-3271 / sonic-swss/cfgmgr/natmgr.cpp addDynamicNatRule / doNatBindingTask L6868-7100 -->

### NAT_POOL が先行必須

`natmgr.cpp:addDynamicNatRule()` は `NAT_BINDINGS` エントリ処理時に pool キャッシュ (`m_natPoolInfo[pool_name]`) を参照する。pool が未登録の場合は `"Pool is not yet enabled, skipping dynamic nat rules addition"` をログしてルール設定をスキップする。pool が後から登録された際に binding が自動再トリガーされるため**エントリは失われない**が、iptables/[ASIC](../../reference/glossary.md#term-asic) ルールは pool 登録完了まで反映されない。

```
# 推奨順序
SET NAT_GLOBAL|Values    admin_mode=enabled          # NAT 機能を有効化
SET NAT_POOL|<name>      nat_ip=...  nat_port=...    # pool を先に定義
SET NAT_BINDINGS|<name>  nat_pool=<name>              # pool 登録後に binding を追加
```

### NAT_GLOBAL (admin_mode=enabled) が有効化条件 — natmgr + NatOrch 二層

**natmgr 層**: `natmgr.cpp:addDynamicNatRule()` は `isNatEnabled()` が false の場合 `"NAT is not yet enabled"` をログしてスキップする (`natmgr.cpp:4632-4636`)。

**NatOrch 層 ([orchagent](../../reference/glossary.md#term-orchagent))**: `natorch.cpp:addNatEntry()` L1907-1913 でも同様に `isNatEnabled()` を確認し、false の場合は [SAI](../../reference/glossary.md#term-sai) 操作をスキップして警告をログする。

```cpp
// natorch.cpp:1907-1913 (addNatEntry)
if (!isNatEnabled()) {
    SWSS_LOG_WARN("NAT Feature is not yet enabled, skipped adding %s %s NAT entry ...",
                  entry.entry_type.c_str(), entry.nat_type.c_str(), ...);
    return true;  // SAI 投入せず return
}
```

`admin_mode=enabled` が CONFIG_DB に書き込まれ [natmgrd](../../reference/glossary.md#term-natmgrd-natsyncd) が [APPL_DB](../../reference/glossary.md#term-appl_db) に伝播し、`doNatGlobalTableTask()` が `enableNatFeature()` を呼び出すまで、NatOrch はすべての NAT SAI エントリ投入をスキップする。

### DNAT Pool → NAT エントリの SAI 投入順序 (natorch.cpp 固有)

`enableNatFeature()` (`natorch.cpp:2534-2581`) は NAT feature 有効化時に以下の順序で一括投入する。

```cpp
// natorch.cpp:2576-2580 (enableNatFeature)
addAllDnatPoolEntries();   // SAI_NAT_TYPE_DESTINATION_NAT_POOL を先に投入
addAllNatEntries();        // SNAT/DNAT/NAPT エントリを後に投入
```

DNAT pool entry (`SAI_NAT_TYPE_DESTINATION_NAT_POOL`) が DNAT entry (`SAI_NAT_TYPE_DESTINATION_NAT`) より必ず先行してハードウェアに投入される設計。`doDnatPoolTableTask()` (`natorch.cpp:2968-3031`) も同様に pool entry を先に `sai_nat_api->create_nat_entry()` で登録する。

### ACL_TABLE bind 順序

`natmgr.cpp:addDynamicNatRule()` は `m_natBindingInfo[key].acls_name` に格納された ACL 名を参照して iptables ルール (`-m set --match-set <acl>`) を設定する。ACL_TABLE エントリそのものは [natmgrd](../../reference/glossary.md#term-natmgrd-natsyncd) が直接検証しないが、ACL_TABLE が未定義のまま binding を設定すると iptables ルールに不整合な ACL 名が埋め込まれるため、ACL_TABLE の定義を先行させることを推奨する。

```
# ACL bind を含む場合の推奨順序
SET ACL_TABLE|<acl_name>    ...                      # ACL table を先に定義
SET NAT_POOL|<name>         nat_ip=...               # pool を定義
SET NAT_BINDINGS|<name>     nat_pool=<name> access_list=<acl_name>  # binding を最後に追加
```

### 安全な DEL 順序

```
DEL NAT_BINDINGS|<name>    # binding を先に削除 (iptables/SAI ルールのクリーンアップ)
DEL NAT_POOL|<name>        # pool を後に削除 (binding が残ったまま pool を削除すると孤立エントリになる)
DEL ACL_TABLE|<acl_name>   # ACL は binding 削除後に削除
```

<!-- /ordering -->

<!-- failure -->
## 失敗挙動 (Phase D)

<!-- evidence: sonic-swss/orchagent/natorch.cpp NatOrch::addNatEntry L1866-1935 / addTwiceNatEntry L1981-2004 / addHwSnatEntry L1307-1316 / addHwTwiceNatEntry L1387-1397 / addHwDnatPoolEntry L1806-1814 / NatOrch constructor L107-122 -->

### SNAT ハードウェア容量上限到達 (dynamic SNAT/Twice NAT) → 即時エージアウト通知

`natorch.cpp:1882-1889` (`addNatEntry`) および `natorch.cpp:1996-2003` (`addTwiceNatEntry`):

```cpp
// addNatEntry - dynamic SNAT
if (totalSnatEntries == maxAllowedSNatEntries)
{
    SWSS_LOG_INFO("Reached the max allowed NAT entries in the hardware, dropping new SNAT translation with ip %s and translated ip %s", ...);
    setTimeoutNotifier->send("AGEOUT-SINGLE-NAT", natKey, fvVector);
    return true;
}

// addTwiceNatEntry - dynamic Twice NAT
if (totalSnatEntries == maxAllowedSNatEntries)
{
    SWSS_LOG_INFO("Reached the max allowed NAT entries in the hardware, dropping new Twice NAT translation with src ip %s, dst ip %s ...", ...);
    setTimeoutNotifier->send("AGEOUT-TWICE-NAT", twiceNatKey, fvVector);
    return true;
}
```

- ログ: `SWSS_LOG_INFO "Reached the max allowed NAT entries in the hardware, dropping new SNAT/Twice NAT translation..."`
- 効果: エントリをキャッシュに追加せず `AGEOUT-SINGLE-NAT` / `AGEOUT-TWICE-NAT` 通知を送信して即時エージアウト。SAI 登録なし。`return true` でタスクは消費 (retry なし)。
- **容量 0 の罠**: 起動時に `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` の取得が失敗した場合 `maxAllowedSNatEntries=0` のまま (`natorch.cpp:112-118`)。この状態では最初の dynamic SNAT エントリ到着と同時にドロップが発生する。取得失敗のログ: `SWSS_LOG_NOTICE "Failed to get the SNAT available entry count, rv:%d"`。

### SAI NAT エントリ作成失敗 → ERROR + handleSaiCreateStatus

`natorch.cpp:1307-1316` (SNAT), `natorch.cpp:1387-1397` (Twice NAT), `natorch.cpp:1475-1485` (SNAT NAPT), `natorch.cpp:1806-1814` (DNAT Pool):

```cpp
// SNAT 例 (addHwSnatEntry)
status = sai_nat_api->create_nat_entry(&snat_entry, attr_count, nat_entry_attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create %s SNAT NAT entry with ip %s and it's translated ip %s",
                   entry.entry_type.c_str(), ip_address.to_string().c_str(), entry.translated_ip.to_string().c_str());
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_NAT, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}

// DNAT Pool 例 (addHwDnatPoolEntry)
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create DNAT Pool entry with ip %s", ip_address.to_string().c_str());
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_NAT, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- ログ: `SWSS_LOG_ERROR "Failed to create %s SNAT NAT entry..."` / `"Failed to create %s Twice NAT entry..."` / `"Failed to create %s SNAT NAPT entry..."` / `"Failed to create DNAT Pool entry with ip %s"`
- 効果: `parseHandleSaiStatusFailure()` が abort / retry / erase を決定する。DNAT Pool 登録失敗時は対象 IP への DNAT トラフィックがハードウェアでドロップされる。[STATE_DB](../../reference/glossary.md#term-state_db) への書き込みなし。
- NAT feature 未有効化時は SAI 呼び出し前に `SWSS_LOG_WARN "NAT Feature is not yet enabled, skipped adding DNAT Pool entry with ip %s"` でスキップされる (`natorch.cpp:1789-1793`)。

### 失敗挙動サマリ

| # | 条件 | コンポーネント | パターン | retry | [STATE_DB](../../reference/glossary.md#term-state_db) 記録 |
|---|---|---|---|---|---|
| 1 | SNAT ハードウェア容量上限 (dynamic SNAT) | NatOrch | AGEOUT-SINGLE-NAT 通知 + ドロップ | なし | なし |
| 2 | Twice NAT ハードウェア容量上限 (dynamic) | NatOrch | AGEOUT-TWICE-NAT 通知 + ドロップ | なし | なし |
| 3 | SAI SNAT create 失敗 | NatOrch | handleSaiCreateStatus | SAI 依存 | なし |
| 4 | SAI Twice NAT create 失敗 | NatOrch | handleSaiCreateStatus | SAI 依存 | なし |
| 5 | SAI SNAT NAPT create 失敗 | NatOrch | handleSaiCreateStatus | SAI 依存 | なし |
| 6 | SAI DNAT Pool create 失敗 | NatOrch | handleSaiCreateStatus | SAI 依存 | なし |
| 7 | SNAT 容量取得失敗 ([orchagent](../../reference/glossary.md#term-orchagent) 起動時) | NatOrch | maxAllowedSNatEntries=0 → 全 dynamic SNAT ドロップ | — | なし |

NatOrch は `ERROR_TABLE` への書き込みなし。syslog (`SWSS_LOG_ERROR` / `WARN` / `NOTICE` / `INFO`) のみ。
<!-- /failure -->

<!-- platform -->
## プラットフォーム差・ASIC ベンダー依存 (Phase H)

<!-- evidence: sonic-swss/orchagent/natorch.cpp NatOrch::NatOrch L107-149 / enableNatFeature L2534-2581 / addNatEntry L1866-1935 / sonic-swss/orchagent/orch.h L43 / sonic-swss/orchagent/main.cpp L935-949 -->

### SAI NAT capability チェック（全ベンダー共通）

NatOrch 初期化時に `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を `sai_switch_api->get_switch_attribute()` で照会し、戻り値が **0 より大きい場合のみ** `gIsNatSupported = true` を設定する (`main.cpp:935-949`)。`gIsNatSupported` が `false` の場合、`enableNatFeature()` は即座に `"NAT Feature is not supported in this Platform"` をログして処理を中断し、SAI NAT オブジェクトは一切作成されない (`natorch.cpp:2541-2544`)。

```cpp
// main.cpp:935-948
attr.id = SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY;
status = sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr);
if (status == SAI_STATUS_SUCCESS && attr.value.u32 != 0)
{
    gIsNatSupported = true;
}
```

`maxAllowedSNatEntries` は同属性の戻り値で初期化され、動的 SNAT エントリ上限として使用される。上限に達した新規 SNAT エントリは SAI に投入されず、代わりに `SETTIMEOUTNAT` 通知 (`AGEOUT-SINGLE-NAT`) が送出されてコネクショントラック強制エージアウトが行われる (`natorch.cpp:1882-1889`)。

### Broadcom 専用: DNAT ネクストホップトラッキング

`orchagent/orch.h:43` に `#define BRCM_PLATFORM_SUBSTRING "broadcom"` が定義されており、NatOrch コンストラクタで環境変数 `platform` が `"broadcom"` を含む場合のみ `gNhTrackingSupported = true` が設定される (`natorch.cpp:144-148`)。

```cpp
// natorch.cpp:144-148
char *platform = getenv("platform");
if (platform && strstr(platform, BRCM_PLATFORM_SUBSTRING))
{
    gNhTrackingSupported = true;
}
```

**`gNhTrackingSupported` による DNAT 処理分岐**:

| プラットフォーム | DNAT エントリの扱い |
|----------------|-------------------|
| Broadcom (`gNhTrackingSupported=true`) | `addDnatToNhCache()` でネクストホップ解決キャッシュに格納し、[ARP](../../reference/glossary.md#term-arp)/ルート解決後に `addHwDnatEntry()` を呼び出す |
| 非 Broadcom (`gNhTrackingSupported=false`) | `addHwDnatEntry()` を即座に呼び出す |

Broadcom では ネクストホップ未解決時に DNAT エントリを SAI に書き込まず、`NeighborOrch` / `RouteOrch` の通知 (`update()`) を受けてから遅延投入する。これにより Broadcom [ASIC](../../reference/glossary.md#term-asic) でのブラックホールルート問題を回避している。

**`gNhTrackingSupported` が影響する主な処理**:

- `addNatEntry()` L1923: DNAT 追加パスの分岐
- `enableNatFeature()` L2570: NAT 有効化時の NeighborOrch attach
- `disableNatFeature()` L2607: NAT 無効化時の NeighborOrch detach
- `addNaptEntry()` / `removeNaptEntry()` / `addTwiceNatEntry()` 等: 全 NAT 型で同様に分岐

### 非 Broadcom: 制限事項

非 Broadcom ASIC では `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` が `0` または `SAI_STATUS_NOT_SUPPORTED` を返す実装が多く、その場合 `gIsNatSupported=false` となり NAT 機能全体が無効化される。現行の [SONiC](../../reference/glossary.md#term-sonic) コミュニティ実装では **Broadcom ASIC のみが NAT ハードウェアオフロードを実運用レベルでサポートする**。

### まとめ

| 挙動 | 条件 |
|------|------|
| NAT 機能全体が有効 | `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY > 0` (gIsNatSupported=true) |
| NAT 機能全体が無効 | 上記属性が 0 または不取得 (gIsNatSupported=false) |
| DNAT ネクストホップ追跡 | Broadcom ASIC のみ (gNhTrackingSupported=true) |
| DNAT 即時 SAI 投入 | 非 Broadcom (gNhTrackingSupported=false) |
| SNAT ハードウェア上限超過 | `totalSnatEntries == maxAllowedSNatEntries` → ageout 通知 |

<!-- /platform -->

<!-- constants -->
## ハードコード定数（orchagent/natorch.cpp 由来）(Phase E)

<!-- evidence: sonic-swss/orchagent/natorch.cpp, sonic-swss/orchagent/natorch.h -->

`orchagent/natorch.cpp` の `NatOrch` が使用する主要ハードコード定数。`nat_type` フィールドの文字列値は APPL_DB 経由で [orchagent](../../reference/glossary.md#term-orchagent) に渡され、対応する SAI NAT タイプに変換される。

### `nat_type` enum 文字列値

| 文字列値 | 対応 SAI 定数 | 用途 |
|---------|-------------|------|
| `"snat"` | `SAI_NAT_TYPE_SOURCE_NAT` | 送信元 IP 変換（内→外方向） |
| `"dnat"` | `SAI_NAT_TYPE_DESTINATION_NAT` | 宛先 IP 変換（外→内方向） |

```cpp
// natorch.cpp:1901-1921 (addNatEntry 内での分岐)
if (entry.nat_type == "snat")
{
    snat_entry.nat_type = SAI_NAT_TYPE_SOURCE_NAT;
    ...
}
else if (entry.nat_type == "dnat")
{
    dnat_entry.nat_type = SAI_NAT_TYPE_DESTINATION_NAT;
    ...
}
```

### `entry_type` enum 文字列値

| 文字列値 | 意味 |
|---------|------|
| `"static"` | 静的 NAT エントリ（STATIC_NAT / STATIC_NAPT テーブルから） |
| `"dynamic"` | 動的 NAT エントリ（NAT_BINDINGS + NAT_POOL から生成） |

```cpp
// natorch.cpp:2659
assert(type == "dynamic" || type == "static");
```

### `dnat_pool` NAT タイプ

`NAT_DNAT_POOL_TABLE` エントリは専用の SAI タイプを使用する。

| SAI 定数 | 用途 |
|---------|------|
| `SAI_NAT_TYPE_DESTINATION_NAT_POOL` | DNAT pool エントリ（動的 NAT の逆方向エントリ管理） |
| `SAI_NAT_TYPE_DOUBLE_NAT` | Twice NAT エントリ（双方向同時変換） |

```cpp
// natorch.cpp:1801
dnat_pool_entry.nat_type = SAI_NAT_TYPE_DESTINATION_NAT_POOL;

// natorch.cpp:1009 (Twice NAT)
dbl_nat_entry.nat_type = SAI_NAT_TYPE_DOUBLE_NAT;
```

### NAT_BINDINGS 固有の `nat_type` 制約

`NAT_BINDINGS` テーブルは実質 SNAT 専用。orchagent `NatOrch::addNatEntry` は `nat_type=="snat"` かつ `entry_type=="dynamic"` の組み合わせのみ動的 SNAT フローとして処理する。`nat_type=="dnat"` の動的エントリは natmgr 段（`cfgmgr/natmgr.cpp`）で拒否され orchagent には到達しない。

```cpp
// natorch.cpp:1879-1880
if ((entry.nat_type == "snat") and
    (entry.entry_type == "dynamic"))
{
    // 動的 SNAT ルールの追加処理
}
```

### タイマー周期定数（natorch.h）

`NatOrch` はコンストラクタで 2 種類の `SelectableTimer` を起動する。周期は `natorch.h` でマクロ定義されている。

| マクロ | 値 | 用途 |
|-------|---|------|
| `NAT_HITBIT_N_CNTRS_QUERY_PERIOD` | `5` 秒 | hitbit クエリ＋統計カウンタ更新タイマー |
| `NAT_CONNTRACK_TIMEOUT_PERIOD` | `86400` 秒 (1 日) | conntrack エントリ定期 ageout 通知タイマー |
| `NAT_HITBIT_QUERY_MULTIPLE` | `6` | hitbit は `5×6=30` 秒ごとにクエリ |

```cpp
// natorch.h:37-39
#define NAT_HITBIT_N_CNTRS_QUERY_PERIOD   5        // 5 secs
#define NAT_CONNTRACK_TIMEOUT_PERIOD      86400    // 1 day
#define NAT_HITBIT_QUERY_MULTIPLE         6        // Hit bits are queried every 30 secs
```

### デフォルトタイムアウト値（natorch.cpp コンストラクタ）

コンストラクタでハードコードされるデフォルト値。`NAT_GLOBAL` テーブルの対応フィールドで上書き可能。

| 内部変数 | デフォルト | 単位 | `NAT_GLOBAL` 上書きフィールド |
|---------|-----------|------|--------------------------|
| `timeout` | `600` | 秒 | `nat_timeout` |
| `tcp_timeout` | `86400` | 秒 (1 日) | `nat_tcp_timeout` |
| `udp_timeout` | `300` | 秒 | `nat_udp_timeout` |

```cpp
// natorch.cpp:66-73
timeout = 600;      // NAT default timeout
tcp_timeout = 86400; // NAT default tcp timeout (1 Day)
udp_timeout = 300;  // NAT default udp timeout
```

これらの値は初期化時に `COUNTERS_DB` の `NAT_TABLE|Values` キーへ書き込まれる[^E1]。

[^E1]: `natorch.cpp:127-135` — `MAX_NAT_ENTRIES`, `TIMEOUT`, `UDP_TIMEOUT`, `TCP_TIMEOUT` を `m_countersGlobalNatTable.set("Values", values)` で [COUNTERS_DB](../../reference/glossary.md#term-counters_db) に反映。
<!-- /constants -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`NAT_BINDINGS` エントリが処理される際に `NatOrch` (`natorch.cpp`) が
暗黙的に依存する他テーブルの関係を示す。

<!-- evidence: sonic-swss/orchagent/natorch.cpp NatOrch::isNatEnabled L2345 / addNatEntry L1907 / enableNatFeature L2534-2581 / addAllDnatPoolEntries L1854 / doDnatPoolTableTask L2968 / addHwDnatEntry L414 / updateNextHop L200 / updateNeighbor L259 -->

| 依存方向 | 参照元 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---------|--------|--------------|--------------|---------|------|
| NatOrch → NAT_GLOBAL | `admin_mode` キャッシュ (`isNatEnabled()`) | `NAT_GLOBAL` (CONFIG_DB → APP_NAT_GLOBAL_TABLE) | `NAT_GLOBAL\|Values` | `admin_mode=enabled` が APP_DB に伝播するまで、NAT_BINDINGS に対応する SAI エントリは登録されない。`enableNatFeature()` で有効化後に `addAllNatEntries()` で一括追加 | `natorch.cpp:2345`, `natorch.cpp:1907`, `natorch.cpp:2534-2581` |
| NatOrch → NAT_POOL (APPL_DB 経由) | `doDnatPoolTableTask()` — `m_dnatPoolEntries` | `APP_NAT_DNAT_POOL_TABLE` (APPL_DB) | `NAT_DNAT_POOL_TABLE\|<ip>` | NAT_POOL の各 IP が APPL_DB に DNAT pool エントリとして書き込まれ、NatOrch が SAI `SAI_NAT_TYPE_DESTINATION_NAT_POOL` エントリを作成する。`enableNatFeature()` 内で `addAllDnatPoolEntries()` として一括適用される | `natorch.cpp:2968-3031`, `natorch.cpp:1854-1864`, `natorch.cpp:2576` |
| NAT_BINDINGS → NAT_POOL (YANG leafref) | `nat_pool` フィールド | `NAT_POOL` | `NAT_POOL\|<name>` | YANG バリデーション強制参照整合性。`nat_pool` に指定した名前が `NAT_POOL` に存在しなければ YANG レベルで拒否される | `sonic-nat.yang:271` |
| NAT_BINDINGS → ACL_TABLE | `access_list` フィールド → ACL 名 | `ACL_TABLE` | `ACL_TABLE\|<table_id>` | `access_list` に指定した ACL が `type=L3, stage=INGRESS` で未登録の場合、iptables SNAT ルールがスキップされる。ACL 登録後に `doNatAclTableTask()` が自動再評価 | `natmgr.cpp:7750-7900`, `natmgrd.cpp:119` |
| NAT_BINDINGS → ACL_RULE | `access_list` フィールド → ACL ルール | `ACL_RULE` | `ACL_RULE\|<table_id>\|<rule_id>` | ACL_RULE の追加・削除が NAT binding の iptables MASQUERADE / SNAT ルールを再評価・更新する | `natmgr.cpp:doNatAclRuleTask()`, `natmgrd.cpp:120` |
| NatOrch → RouteOrch (BRCM 専用) | `addHwDnatEntry()` — `m_routeOrch->attach()` | RouteOrch (SUBJECT_TYPE_NEXTHOP_CHANGE) | — | DNAT エントリ追加時に translated IP の next-hop 変化を subscribe。BRCM プラットフォームのみ有効 | `natorch.cpp:414,458,504,591`, `natorch.cpp:144-148` |
| NatOrch → NeighOrch (BRCM 専用) | `enableNatFeature()` — `m_neighOrch->attach()` | NeighOrch (SUBJECT_TYPE_NEIGH_CHANGE) | — | NAT 有効化時に全 neighbor の [ARP](../../reference/glossary.md#term-arp) 解決状態を subscribe し、DNAT translated IP の SAI エントリを neighbor 解決タイミングで差し替える | `natorch.cpp:2573,2610`, `natorch.cpp:259-302` |

### 解決タイミング

- **NAT_GLOBAL `admin_mode` 依存**: `doNatGlobalTableTask()` が `APP_NAT_GLOBAL_TABLE` の `admin_mode=enabled` を検出して `enableNatFeature()` → `addAllNatEntries()` を呼ぶ。有効化前に受信した NAT エントリはキャッシュ (`m_natEntries`) に積まれ、有効化後に一括 SAI 投入される。
- **NAT_POOL (DNAT pool) 依存**: `doDnatPoolTableTask()` が APPL_DB の `APP_NAT_DNAT_POOL_TABLE` を購読し、pool IP ごとに即時 SAI エントリ作成。`enableNatFeature()` 内で `addAllDnatPoolEntries()` として未投入分を一括追加。
- **ACL_TABLE / ACL_RULE 依存**: `doNatAclTableTask()` / `doNatAclRuleTask()` が CONFIG_DB の変化を購読。ACL の登録・削除のたびに iptables SNAT ルールを再評価。未解決の ACL 名は次回 ACL 登録時に自動補完される。
- **RouteOrch / NeighOrch observer (BRCM 専用)**: `gNhTrackingSupported == true` のときのみ有効。DNAT translated IP の next-hop / neighbor 解決状態に応じてリアルタイムに SAI DNAT エントリを差し替える。非 BRCM 環境では経路変更時に stale エントリになるリスクあり。
<!-- /cross-refs -->

<!-- pubsub -->
## 通信メカニズム — Redis Subscribe / SAI nat_api / conntrack (Phase G)

<!-- evidence: sonic-swss/cfgmgr/natmgrd.cpp:100-198 / natmgr.cpp:35-49,4621-4679,6868-7100 / orchagent/natorch.cpp:82-140,1271-1309,3033-3094 -->

### CONFIG_DB 購読 — SubscriberStateTable

`natmgrd` は起動時に `CFG_NAT_BINDINGS_TABLE_NAME` (`"NAT_BINDINGS"`) を含む 11 テーブルを `Orch::addConsumer()` 経由で登録する (`natmgrd.cpp:109-121`)。CONFIG_DB に対しては **`SubscriberStateTable`** が生成され、以下の [Redis](../../reference/glossary.md#term-redis) keyspace チャンネルを PSUBSCRIBE する:

```
PSUBSCRIBE __keyspace@4__:NAT_BINDINGS|*
```

CONFIG_DB の DB 番号は通常 4。`NAT_BINDINGS|<binding_name>` への HSET / HDEL / DEL が pmessage として到達する。

起動時には `SubscriberStateTable` コンストラクタ (`subscriberstatetable.cpp:25-42`) が既存 key を全件取得し SET イベントとして積むため、**natmgrd 再起動後もバインディングが自動再処理**される。

### natmgrd select ループ → doNatBindingTask

```
CONFIG_DB HSET NAT_BINDINGS|<name>
  → __keyspace@4__:NAT_BINDINGS|<name> pmessage
  → SubscriberStateTable::readData() → pops() → KeyOpFieldsValuesTuple
  → natmgrd select ループ (1000ms タイムアウト)
    → Consumer::execute() → NatMgr::doTask(Consumer&)
      → doNatBindingTask(key, op, fvs)           # natmgr.cpp:6868-7100
        → addDynamicNatRule(key)                 # natmgr.cpp:4621-4679
          ├─ isNatEnabled() 確認
          ├─ m_natPoolInfo[pool_name] 存在確認
          ├─ twice_nat_id が空 → setDynamicAllForwardOrAclbasedRules() (iptables)
          └─ twice_nat_id が非空 → addDynamicTwiceNatRule(key)
```

### conntrack 経路 (Dynamic NAT)

Dynamic SNAT は kernel iptables ルール経由で conntrack に委ねられる:

```
送信元パケット → iptables MASQUERADE / SNAT ルール
  → kernel conntrack が動的接続追跡エントリを生成
  → NatOrch::m_natQueryTimer 発火 → conntrack テーブル読み込み
  → APP_NAT_TABLE / APP_NAPT_TABLE に ProducerStateTable::set()
```

natmgr.cpp では以下の `ProducerStateTable` を APPL_DB に向けて保持する (`natmgr.cpp:43-49`):

| Producer | APPL_DB テーブル |
|---|---|
| `m_appNatTableProducer` | `APP_NAT_TABLE` |
| `m_appNaptTableProducer` | `APP_NAPT_TABLE` |
| `m_appTwiceNatTableProducer` | `APP_NAT_TWICE_TABLE` |
| `m_appTwiceNaptTableProducer` | `APP_NAPT_TWICE_TABLE` |
| `m_appNatDnatPoolProducer` | `APP_NAT_DNAT_POOL_TABLE` |

### APPL_DB 購読 → NatOrch → SAI

NatOrch (`orchagent`) は APPL_DB の `APP_NAT_TABLE_NAME` 等を **`ConsumerStateTable`** で購読し、`NatOrch::doTask(Consumer&)` (`natorch.cpp:3033`) でディスパッチする:

```
APP_NAT_TABLE → addHwSnatEntry()
  → sai_nat_api->create_nat_entry()  [SAI_NAT_TYPE_SOURCE_NAT]
APP_NAT_TWICE_TABLE → addHwTwiceNatEntry()
  → sai_nat_api->create_nat_entry()  [SAI_NAT_TYPE_DOUBLE_NAT]
```

`addHwSnatEntry()` (`natorch.cpp:1271-1309`) の主要 SAI 属性:

```cpp
nat_entry_attr[0].id = SAI_NAT_ENTRY_ATTR_SRC_IP;
nat_entry_attr[1].id = SAI_NAT_ENTRY_ATTR_SRC_IP_MASK;
nat_entry_attr[2].id = SAI_NAT_ENTRY_ATTR_ENABLE_PACKET_COUNT;
nat_entry_attr[3].id = SAI_NAT_ENTRY_ATTR_ENABLE_BYTE_COUNT;
snat_entry.nat_type  = SAI_NAT_TYPE_SOURCE_NAT;
status = sai_nat_api->create_nat_entry(&snat_entry, attr_count, nat_entry_attr);
```

### 非同期通知チャンネル

| チャンネル名 | DB | 方向 | 用途 |
|---|---|---|---|
| `SETTIMEOUTNAT` | APPL_DB | NatOrch → natmgrd | conntrack timeout 変更通知 (natorch.cpp:137 / natmgrd.cpp:149) |
| `FLUSHNATENTRIES` | APPL_DB | 外部 CLI → natmgrd | conntrack エントリ全フラッシュ (natmgrd.cpp:152) |
| `NAT_DB_CLEANUP_NOTIFICATION` | APPL_DB | natmgrd → NatOrch | natmgrd 終了時の ASIC/[Redis](../../reference/glossary.md#term-redis) クリーンアップ (natmgrd.cpp:127 / natorch.cpp:89) |

<!-- /pubsub -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

`NAT_BINDINGS` エントリが処理されると、`natmgrd` → `orchagent / NatOrch` の経路で以下の副次書込が発生する。ソース: `sonic-swss/orchagent/natorch.cpp`[^F1]。

### ASIC_DB — SAI nat_entry

`NatOrch` が `sai_nat_api->create_nat_entry()` を呼び出して SAI NAT オブジェクトを [ASIC_DB](../../reference/glossary.md#term-asic_db) 経由で書込む。

| 操作関数 | SAI nat_type | 適用条件 |
|---------|-------------|---------|
| `addHwSnatEntry()` | `SAI_NAT_TYPE_SOURCE_NAT` | dynamic SNAT エントリ (Single NAT) |
| `addHwSnaptEntry()` | `SAI_NAT_TYPE_SOURCE_NAT` + ポート | dynamic SNAPT エントリ |
| `addHwTwiceNatEntry()` | `SAI_NAT_TYPE_DOUBLE_NAT` | `twice_nat_id` 指定時 |
| `addHwDnatPoolEntry()` | `SAI_NAT_TYPE_DESTINATION_NAT_POOL` | DNAT pool エントリ追加時 |

SNAT エントリには `SAI_NAT_ENTRY_ATTR_SRC_IP`（変換後 pool IP）、`SAI_NAT_ENTRY_ATTR_ENABLE_PACKET_COUNT=true`、`SAI_NAT_ENTRY_ATTR_ENABLE_BYTE_COUNT=true` が設定される (`natorch.cpp:1289-1302`)。

**書込前提条件**:

1. `isNatEnabled()` が true — `NAT_GLOBAL.admin_mode=enabled` が APPL_DB に伝播済みであること。
2. dynamic SNAT: `totalSnatEntries < maxAllowedSNatEntries`（SAI クエリ値）。上限到達時は `"AGEOUT-SINGLE-NAT"` 通知を送り最古エントリをエージアウトしてから追加する (`natorch.cpp:1888-1900`)。
3. DNAT + nexthop tracking 有効時: nexthop 解決完了後に遅延書込される。

### COUNTERS_DB — グローバルおよび per-entry カウンタ

| テーブル | キー | 書込フィールド | 更新タイミング |
|---------|------|--------------|-------------|
| `COUNTERS_GLOBAL_NAT` | `Values` | `SNAT_ENTRIES` | SNAT エントリ追加/削除ごと (`natorch.cpp:4569`) |
| `COUNTERS_GLOBAL_NAT` | `Values` | `DNAT_ENTRIES` | DNAT エントリ追加/削除ごと (`natorch.cpp:4580`) |
| `COUNTERS_GLOBAL_NAT` | `Values` | `DYNAMIC_NAT_ENTRIES`, `DYNAMIC_NAPT_ENTRIES` | dynamic エントリ数変化時 |
| `COUNTERS_NAT` | `<global_ip>` | `NAT_TRANSLATIONS_PKTS`, `NAT_TRANSLATIONS_BYTES` | hitbit タイマー 5 秒周期 |
| `COUNTERS_NAPT` | `<proto>:<ip>:<port>` | 同上 | 同上 |
| `COUNTERS_TWICE_NAT` | `<src_ip>:<dst_ip>` | 同上 | 同上 |
| `COUNTERS_TWICE_NAPT` | `<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>` | 同上 | 同上 |

### CRM カウンタ更新

SAI エントリの追加/削除に連動して `gCrmOrch` が [CRM](../../reference/glossary.md#term-crm) リソースカウンタを増減する。

| 操作 | [CRM](../../reference/glossary.md#term-crm) リソース | ソース |
|------|------------|-------|
| SNAT エントリ追加 | `incCrmResUsedCounter(CRM_SNAT_ENTRY)` | `natorch.cpp:1325` |
| SNAT エントリ削除 | `decCrmResUsedCounter(CRM_SNAT_ENTRY)` | `natorch.cpp:1647` |
| DNAT エントリ追加 | `incCrmResUsedCounter(CRM_DNAT_ENTRY)` | `natorch.cpp:791` |
| DNAT エントリ削除 | `decCrmResUsedCounter(CRM_DNAT_ENTRY)` | `natorch.cpp:944` |

`show crm resources all` で使用量を確認できる。

### STATE_DB — 書込なし

`NatOrch` および `NatMgr` は [STATE_DB](../../reference/glossary.md#term-state_db) への書込を行わない。`STATE_PORT_TABLE` / `STATE_LAG_TABLE` / `STATE_VLAN_TABLE` / `STATE_INTERFACE_TABLE` は L3 インタフェース readiness ガード用の**読み取り専用**アクセスのみ。

[^F1]: NatOrch ASIC 書込実装: `sonic-swss/orchagent/natorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/natorch.cpp>

<!-- /side-effects -->

<!-- glossary-links-injected: 865a18402f05 -->
