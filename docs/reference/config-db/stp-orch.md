---
title: APPL_DB STP Orchagent テーブル — フィールドとコード由来デフォルト
description: "SONiC orchagent が購読する APPL_DB の STP 関連 4 テーブル (STP_VLAN_INSTANCE_TABLE / STP_PORT_STATE_TABLE / STP_FASTAGEING_FLUSH_TABLE / STP_INST_PORT_FLUSH_TABLE) のフィールド定義・暗黙デフォルト・SAI マッピング・書込み順依存・暗黙参照テーブルを詳解。Phase A+B+C 分析。"
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

<!-- ordering -->
## 書込み順依存・タイミング依存 (Phase B)

`StpOrch::doTask()` は APPL_DB の 4 テーブルを購読するが、各テーブルの処理には明確な前提条件がある。前提未成立時の挙動はテーブルごとに異なる (残置 `it++` / コンシューマ全体ブロック `return` / fail-silent) ため、運用上のトラブルシューティングで重要になる。

### 1. 全テーブル共通: PortsOrch readiness ガード

```cpp
// stporch.cpp:578-581
void StpOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady())
        return;
    // ...
}
```

`allPortsReady()` が false の間、**すべてのテーブル処理を無音スキップ**する。PortsOrch が `PORT_INIT_DONE` を受信するまで `m_toSync` のエントリは保留され、エラーログも出力されない。

→ 順序依存: PortsOrch の初期化完了が StpOrch 全体の前提。

### 2. STP_VLAN_INSTANCE_TABLE — VLAN 先行ガード

`addVlanToStpInstance()` (`stporch.cpp:123-126`):

```cpp
if (!gPortsOrch->getPort(vlan_alias, vlan))
{
    return false;
}
```

VLAN が PortsOrch に未登録の場合は false を返す。呼び出し元 `doStpTask()` (`stporch.cpp:410-414`) は:

```cpp
if(!addVlanToStpInstance(vlan_alias, instance))
{
    it++;   // erase せず次エントリへ
    continue;
}
```

`it++` で残置し、後続エントリは処理を継続する。DEL 時の `removeVlanFromStpInstance()` も同様に `getPort()` を内部で呼ぶため同じ条件でブロックされる。

→ 順序依存: VLAN の PortsOrch 登録 (`VLAN_MEMBER` / PortsOrch 経由) が `STP_VLAN_INSTANCE_TABLE` の SET より先行必須。

### 3. STP_PORT_STATE_TABLE — ポート先行ガード (コンシューマ全体ブロック)

`doStpPortStateTask()` (`stporch.cpp:449-453`):

```cpp
if (!gPortsOrch->getPort(port_alias, port))
{
    return;   // it++ でなく return
}
```

ポートが PortsOrch に未登録の場合、`it++` ではなく **`return`** で抜ける。これにより同一コンシューマの後続エントリもすべてブロックされる点が `STP_VLAN_INSTANCE_TABLE` と異なる。

不正キー (`<port>:<instance>` 形式でない) も同様に `return` でブロック:

```cpp
// stporch.cpp:439-443
if (found == string::npos)
{
    return;
}
```

→ 順序依存: 物理ポート / LAG の PortsOrch 登録が `STP_PORT_STATE_TABLE` の SET より先行必須。

### 4. STP_PORT_STATE_TABLE — Bridge Port 自動作成

`addStpPort()` (`stporch.cpp:218-227`):

```cpp
if(port.m_bridge_port_id == SAI_NULL_OBJECT_ID)
{
    gPortsOrch->addBridgePort(port);
    if(port.m_bridge_port_id == SAI_NULL_OBJECT_ID)
    {
        SWSS_LOG_ERROR("Failed to add STP port %s invalid bridge port id ...", ...);
        return SAI_NULL_OBJECT_ID;
    }
}
```

Bridge port が未作成の場合は `addBridgePort()` で自動作成を試みる。失敗すると `SAI_NULL_OBJECT_ID` → `updateStpPortState()` が false → `it++` 残置。

→ タイミング依存: bridge port 作成は自動試行されるが SAI 失敗時は残置。

### 5. STP_FASTAGEING_FLUSH_TABLE — VLAN 未登録は fail-silent

`stpVlanFdbFlush()` (`stporch.cpp:369-372`):

```cpp
if (!gPortsOrch->getPort(vlan_alias, vlan))
{
    return false;
}
```

VLAN 未登録時は false を返すが、`doStpFastageTask()` は戻り値を**チェックしない**。エントリは常に `erase()` される (fail-silent)。フラッシュが実行されなくてもエラーログは出ない。

→ タイミング依存: VLAN が PortsOrch に未登録の状態でフラッシュ指示が届いても無音で消える。

### 6. STP_INST_PORT_FLUSH_TABLE — VLAN→インスタンス割当が前提

`doMstInstPortFlushTask()` (`stporch.cpp:553-561`):

```cpp
auto it_map = m_vlanAliasToStpInstanceMap.find(instance);
if (it_map != m_vlanAliasToStpInstanceMap.end())
{
    for (const auto& vlan_alias : it_map->second.stp_inst_vlan_list)
    {
        stpVlanFdbFlush(vlan_alias);
    }
}
```

`m_vlanAliasToStpInstanceMap` は `addVlanToStpInstance()` が `STP_VLAN_INSTANCE_TABLE` を処理した際に更新される。インスタンスが未登録の場合はフラッシュ対象 VLAN リストが空で no-op になる (エラーログなし)。

→ 順序依存: `STP_INST_PORT_FLUSH_TABLE` の SET は `STP_VLAN_INSTANCE_TABLE` の SET (VLAN→インスタンス割当) より後に到達すること。

### 処理依存のまとめ

| テーブル | 必須先行条件 | 不成立時の挙動 |
|---|---|---|
| 全テーブル | `allPortsReady()` (PortsOrch 初期化) | 無音 `return` (保留) |
| `STP_VLAN_INSTANCE_TABLE` SET | VLAN が PortsOrch に登録済み | `it++` 残置 (後続は継続) |
| `STP_VLAN_INSTANCE_TABLE` DEL | VLAN が PortsOrch に登録済み | `it++` 残置 |
| `STP_PORT_STATE_TABLE` SET/DEL | ポートが PortsOrch に登録済み | `return` (コンシューマ全体ブロック) |
| `STP_PORT_STATE_TABLE` SET | Bridge port 作成成功 | `it++` 残置 |
| `STP_FASTAGEING_FLUSH_TABLE` SET | VLAN が PortsOrch に登録済み | fail-silent (消去) |
| `STP_INST_PORT_FLUSH_TABLE` SET | STP_VLAN_INSTANCE_TABLE で割当済み | no-op (消去) |

詳細根拠は `meta/_intermediate/cdb-flow/stp-orch-ordering.md` を参照。
<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`StpOrch` が購読する APPL_DB 4 テーブルは `stpd → stpmgrd` が書き手で、`StpOrch` は読み手兼 SAI 変換器である。以下の暗黙参照は、各テーブルの処理がどのテーブル / Orch / SAI に依存するかを示す。

<!-- evidence: meta/_intermediate/cdb-flow/stp-orch-cross-refs.md -->

| 参照方向 | このテーブル / Orch | 相手テーブル / リソース | 条件 |
|---------|-------------------|----------------------|------|
| 入力 (書き手) | APPL_DB 4 テーブル | stpd → stpmgrd | 常時。stpmgrd が CONFIG_DB `STP` / `STP_VLAN` 等を購読し stpd IPC を仲介して APPL_DB を書く |
| 起動順序ガード | 全テーブル | `PORT` (PortsOrch::allPortsReady) | 常時。false の間は `doTask()` が即 `return` し全処理を保留 |
| VLAN 解決 | `STP_VLAN_INSTANCE_TABLE` SET/DEL | `VLAN` (PortsOrch::getPort) | 常時。未登録 VLAN は `addVlanToStpInstance()` / `removeVlanFromStpInstance()` が false → `it++` 残置 |
| ポート解決 | `STP_PORT_STATE_TABLE` SET/DEL | `PORT` / `LAG` (PortsOrch::getPort) | 常時。未登録ポートは `doStpPortStateTask()` が **`return`** → コンシューマ全体ブロック |
| Bridge Port 自動作成 | `STP_PORT_STATE_TABLE` SET | PortsOrch::addBridgePort | bridge port 未作成時に自動試行。SAI 失敗なら `it++` 残置 |
| 内部 Map 参照 | `STP_INST_PORT_FLUSH_TABLE` SET | `STP_VLAN_INSTANCE_TABLE` (m_vlanAliasToStpInstanceMap) | MSTP フラッシュ。`addVlanToStpInstance()` が更新する Map が未存在なら no-op |
| SAI 書き込み先 | `STP_VLAN_INSTANCE_TABLE` | SAI `sai_stp_api->create_stp` / `set_vlan_attribute(SAI_VLAN_ATTR_STP_INSTANCE)` | 常時 |
| SAI 書き込み先 | `STP_PORT_STATE_TABLE` | SAI `sai_stp_api->create_stp_port` / `set_stp_port_attribute` | 常時 |
| SAI クエリ (起動時) | StpOrch コンストラクタ | `SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID` / `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` | 起動時 1 回。失敗時は未初期化のまま動作継続 (silent failure) |
| STATE_DB 書き込み | StpOrch (書き手) | `STATE_DB STP_TABLE\|GLOBAL.max_stp_inst` | SAI クエリ成功時 (`updateMaxStpInstance()`)。`max_stp_instances - 1` を書き込む |

!!! note "APPL_DB 4 テーブルは StpOrch の入力のみ"
    `STP_VLAN_INSTANCE_TABLE` / `STP_PORT_STATE_TABLE` / `STP_FASTAGEING_FLUSH_TABLE` / `STP_INST_PORT_FLUSH_TABLE` への書き込みは stpd / stpmgrd が行う。StpOrch はこれらを**読み取り専用**（Consumer 経由の購読）で処理し、SAI とオプションで STATE_DB `STP_TABLE` へのみ書き込む。

!!! note "`show spanning-tree` は別の APPL_DB テーブルを参照"
    `show/stp.py` が読む APPL_DB テーブルは `STP_VLAN_TABLE` / `STP_PORT_TABLE` / `STP_VLAN_PORT_TABLE` (stpd が直接書く STP 状態テーブル) であり、StpOrch が購読する 4 テーブルとは別物である。

<!-- /cross-refs -->

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
