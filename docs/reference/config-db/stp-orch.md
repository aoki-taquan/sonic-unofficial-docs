---
title: APPL_DB STP Orchagent テーブル — フィールドとコード由来デフォルト
description: "SONiC orchagent が購読する APPL_DB の STP 関連 4 テーブル (STP_VLAN_INSTANCE_TABLE / STP_PORT_STATE_TABLE / STP_FASTAGEING_FLUSH_TABLE / STP_INST_PORT_FLUSH_TABLE) のフィールド定義・暗黙デフォルト・SAI マッピングを詳解。Phase A 分析。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/stporch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/stporch.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/orchdaemon.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: master
related:
  config_db:
    - STP
    - STP_VLAN
    - STP_PORT
    - STP_VLAN_PORT
    - STP_MST
  appl_db:
    - STP_VLAN_INSTANCE_TABLE
    - STP_PORT_STATE_TABLE
    - STP_FASTAGEING_FLUSH_TABLE
    - STP_INST_PORT_FLUSH_TABLE
---

# APPL_DB STP Orchagent テーブル — フィールドとコード由来デフォルト

!!! info "ページの位置付け"
    このページは orchagent (`StpOrch`) が購読する **APPL_DB の STP 関連 4 テーブル** のフィールド定義・暗黙デフォルト・SAI マッピングを詳述する Phase A 分析ページ。
    CONFIG_DB 側のデフォルト (STP/STP_VLAN/STP_PORT テーブル) は [STP/STP_VLAN/STP_PORT テーブル](stp.md) を参照。

## 概要

`StpOrch` (`orchagent/stporch.cpp`) は APPL_DB の 4 テーブルを購読し、STP デーモン (`stpd`) が書き込んだ状態・指示を SAI API に変換してデータプレーンへ反映する。

```
stpd (STP デーモン)
  ↓ IPC (Unix Domain Socket)
stpmgrd (cfgmgr/stpmgrd.cpp)
  ↓ APPL_DB 書き込み
StpOrch (orchagent/stporch.cpp)
  ↓ SAI API
ASIC / SAI アダプタ
```

orchdaemon での登録 (`orchdaemon.cpp:257-262`):

```cpp
vector<string> stp_tables = {
    APP_STP_VLAN_INSTANCE_TABLE_NAME,   // "STP_VLAN_INSTANCE_TABLE"
    APP_STP_PORT_STATE_TABLE_NAME,      // "STP_PORT_STATE_TABLE"
    APP_STP_FASTAGEING_FLUSH_TABLE_NAME, // "STP_FASTAGEING_FLUSH_TABLE"
    APP_STP_INST_PORT_FLUSH_TABLE_NAME  // "STP_INST_PORT_FLUSH_TABLE"
};
gStpOrch = new StpOrch(m_applDb, m_stateDb, stp_tables);
```

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動

<!-- evidence: meta/_intermediate/cdb-flow/stp-orch-defaults.md -->

### 1. 前提: allPortsReady() ガード

`doTask()` (`stporch.cpp:578-581`) は **ポート初期化完了 (`allPortsReady()`) 前は全テーブルの処理をスキップ** する:

```cpp
void StpOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady())
        return;
    // ...
}
```

起動直後はすべての STP APPL_DB エントリが保留される。PortsOrch が `PortInitDone` を受信するまで処理されない (エラーログなし)。

証跡: `stporch.cpp:574-601`

---

### 2. APPL_DB:STP_VLAN_INSTANCE_TABLE

**テーブル名**: `STP_VLAN_INSTANCE_TABLE` (`APP_STP_VLAN_INSTANCE_TABLE_NAME`)

**キー形式**: `<vlan_alias>` (例: `Vlan1000`)

| フィールド | 型 | 値域 | デフォルト / 備考 |
|---|---|---|---|
| `stp_instance` | uint16_t (文字列) | 0–65534 | 欠落時は `STP_INVALID_INSTANCE (0xFFFF)` として処理スキップ |

**SET 処理** (`doStpTask()`):

- `stp_instance` フィールドを読み取り、`addVlanToStpInstance(vlan_alias, instance)` を呼ぶ
- フィールドが存在しない場合はエラーログを出力してスキップ (iterator を進める前に continue)

**DEL 処理**:

- `removeVlanFromStpInstance(vlan_alias, 0)` を呼ぶ。**DEL 時の instance 引数は常に 0 固定**

!!! warning "DEL 時 instance=0 固定"
    `doStpTask()` の DEL 分岐 (`stporch.cpp:417-424`) では `removeVlanFromStpInstance(vlan_alias, 0)` と instance を 0 固定で呼ぶ。
    実際の削除対象インスタンスは `Port.m_stp_id` から取得されるため、引数の 0 は使用されない (関数内で無視される)。

**内部 SAI 操作** (`addVlanToStpInstance()`):

```cpp
// STP インスタンス作成 (未存在時)
sai_attribute_t attr;
attr.id = 0;           // ダミー (STP インスタンスに必須属性なし)
attr.value.u32 = 0;
sai_stp_api->create_stp(&stp_oid, gSwitchId, 0, &attr);

// VLAN へのインスタンス割り当て
attr.id = SAI_VLAN_ATTR_STP_INSTANCE;
attr.value.oid = stp_oid;
sai_vlan_api->set_vlan_attribute(vlan_oid, &attr);
```

STP インスタンス削除時 (`removeVlanFromStpInstance()`) は `SAI_VLAN_ATTR_STP_INSTANCE` を **`m_defaultStpId`** (スイッチ起動時に取得したデフォルト STP インスタンス OID) に戻す。

証跡: `stporch.cpp:115-163, 380-426`

---

### 3. APPL_DB:STP_PORT_STATE_TABLE

**テーブル名**: `STP_PORT_STATE_TABLE` (`APP_STP_PORT_STATE_TABLE_NAME`)

**キー形式**: `<port_alias>:<stp_instance>` (例: `Ethernet0:1`)

| フィールド | 型 | 値域 | デフォルト / 備考 |
|---|---|---|---|
| `state` | uint8_t (文字列) | 0–4 | 欠落時は `STP_STATE_INVALID(5)` として処理スキップ |

**`state` フィールドの値と SAI マッピング** (`getStpSaiState()`):

| 値 | 定数 | SAI ポート状態 | 備考 |
|---|---|---|---|
| `0` | `STP_STATE_DISABLED` | `SAI_STP_PORT_STATE_BLOCKING` | Disabled を BLOCKING に集約 |
| `1` | `STP_STATE_BLOCKING` | `SAI_STP_PORT_STATE_BLOCKING` | |
| `2` | `STP_STATE_LISTENING` | `SAI_STP_PORT_STATE_BLOCKING` | Listening も BLOCKING に集約 |
| `3` | `STP_STATE_LEARNING` | `SAI_STP_PORT_STATE_LEARNING` | |
| `4` | `STP_STATE_FORWARDING` | `SAI_STP_PORT_STATE_FORWARDING` | |

!!! note "SAI は 3 状態のみ"
    STP プロトコルの 5 状態 (DISABLED / BLOCKING / LISTENING / LEARNING / FORWARDING) を SAI の 3 状態 (BLOCKING / LEARNING / FORWARDING) に圧縮する。
    DISABLED・LISTENING はいずれも `SAI_STP_PORT_STATE_BLOCKING` にマップされるため、L2 フォワーディングの観点では同等に扱われる。

**STP ポート作成時の初期状態** (`addStpPort()`):

```cpp
attr[2].id = SAI_STP_PORT_ATTR_STATE;
attr[2].value.s32 = SAI_STP_PORT_STATE_BLOCKING;  // ハードコード
sai_stp_api->create_stp_port(&stp_port_id, gSwitchId, 3, attr);
```

**STP ポートは作成直後に `SAI_STP_PORT_STATE_BLOCKING` で初期化される** (ハードコード)。その後 `set_stp_port_attribute()` で実際の状態に更新される。

証跡: `stporch.cpp:207-258, 314-335, 337-361`

---

### 4. APPL_DB:STP_FASTAGEING_FLUSH_TABLE

**テーブル名**: `STP_FASTAGEING_FLUSH_TABLE` (`APP_STP_FASTAGEING_FLUSH_TABLE_NAME`)

**キー形式**: `<vlan_alias>` (例: `Vlan1000`)

| フィールド | 型 | 値 | 備考 |
|---|---|---|---|
| `state` | string | `"true"` のみ有効 | `"true"` 以外は FDB フラッシュをトリガしない |

**SET 処理** (`doStpFastageTask()`):

- `state == "true"` のとき `stpVlanFdbFlush(vlan_alias)` を呼び、VLAN の FDB エントリを全フラッシュ
- `"true"` 以外の場合はフラッシュなし (silent skip)

**DEL 処理**: **no-op** (コードコメント明記):

```cpp
else if (op == DEL_COMMAND)
{
    // no operation
}
```

!!! info "FASTAGEING とは"
    STP のトポロジー変化 (TCN: Topology Change Notification) に対応した高速エージング。
    ポート状態変化時に FDB をフラッシュして L2 ループを防ぐ。PVST と MST の両方で使用される。

証跡: `stporch.cpp:488-519`

---

### 5. APPL_DB:STP_INST_PORT_FLUSH_TABLE

**テーブル名**: `STP_INST_PORT_FLUSH_TABLE` (`APP_STP_INST_PORT_FLUSH_TABLE_NAME`)

**キー形式**: `<mst_instance>:<port_alias>` (例: `1:Ethernet0`)

| フィールド | 型 | 値 | 備考 |
|---|---|---|---|
| `state` | string | `"true"` のみ有効 | `"true"` のとき対象インスタンスの全 VLAN の FDB をフラッシュ |

**SET 処理** (`doMstInstPortFlushTask()`):

- `state == "true"` のとき `m_vlanAliasToStpInstanceMap[instance]` から VLAN エイリアスリストを取得
- リスト内の全 VLAN に対して `stpVlanFdbFlush()` を呼ぶ (MSTP 用一括フラッシュ)
- 対象インスタンスが `m_vlanAliasToStpInstanceMap` に存在しない場合は no-op

**DEL 処理**: **no-op** (コードコメント明記)

!!! note "PVST と MSTP の違い"
    - `STP_FASTAGEING_FLUSH_TABLE`: 特定 VLAN を対象とする (PVST 向け)
    - `STP_INST_PORT_FLUSH_TABLE`: MST インスタンス単位でフラッシュ (MSTP 向け)。1 インスタンスに複数 VLAN が属する MSTP の特性に対応。

証跡: `stporch.cpp:521-571`

---

### 6. 初期化時の SAI 取得値

`StpOrch::StpOrch()` コンストラクタで以下を取得:

| SAI 属性 | 取得値 | 用途 |
|---|---|---|
| `SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID` | `m_defaultStpId` | VLAN から STP インスタンスを削除する際に元に戻す先 |
| `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` | `m_maxStpInstance = value - 1` | 使用可能な最大 STP インスタンス番号 |

取得失敗時 (`SAI_STATUS_SUCCESS` 以外) は `m_defaultStpId` と `m_maxStpInstance` が未初期化のまま警告ログのみで継続する。

STATE_DB への書き込み:

```
STATE_DB: STP|GLOBAL.max_stp_inst = (SAI_SWITCH_ATTR_MAX_STP_INSTANCE - 1)
```

証跡: `stporch.cpp:17-43, 603-616`

<!-- /defaults -->

## 発見された discrepancy / 暗黙デフォルト サマリー

| # | 種別 | 対象テーブル / フィールド | 内容 |
|---|---|---|---|
| 1 | ハードコード初期値 | `STP_PORT_STATE_TABLE` → SAI STP ポート | 作成直後は常に `SAI_STP_PORT_STATE_BLOCKING` |
| 2 | 状態圧縮 | `STP_PORT_STATE_TABLE.state` | DISABLED(0) / LISTENING(2) → BLOCKING にマップ (SAI 3 状態制約) |
| 3 | DEL 引数固定 | `STP_VLAN_INSTANCE_TABLE` DEL | `removeVlanFromStpInstance(vlan, 0)` と instance=0 固定で呼ぶ (関数内部で無視される) |
| 4 | no-op DEL | `STP_FASTAGEING_FLUSH_TABLE` / `STP_INST_PORT_FLUSH_TABLE` | DEL コマンドは何も実行しない (フラッシュはべき等操作) |
| 5 | silent skip | `STP_VLAN_INSTANCE_TABLE.stp_instance` 欠落 | エラーログのみ、iterator 進めず再試行待ち |
| 6 | 起動ガード | 全テーブル | `allPortsReady()` が false の間は全処理を無音スキップ |
| 7 | SAI 取得失敗 | `m_defaultStpId` / `m_maxStpInstance` | 取得失敗時に未初期化のまま動作継続 (silent failure) |
| 8 | STATE_DB 書き込み | `STP\|GLOBAL.max_stp_inst` | `max_stp_instances - 1` を書き込む (off-by-one は意図的) |

## 引用元

[^1]: StpOrch 実装: `orchagent/stporch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/stporch.cpp>
[^2]: StpOrch ヘッダ: `orchagent/stporch.h`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/stporch.h>
[^3]: orchdaemon 登録: `orchagent/orchdaemon.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/orchdaemon.cpp>
[^4]: テーブル名定数: `common/schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/master/common/schema.h>

## 関連ページ

- [CONFIG_DB: STP / STP_VLAN / STP_PORT テーブル](stp.md)
- [CONFIG_DB: STP_MST テーブル](stp-mst.md)
- [CONFIG_DB: STP_VLAN テーブル](stp-vlan.md)
- [CONFIG_DB: STP_PORT テーブル](stp-port.md)
- [CONFIG_DB: VLAN](vlan.md)
