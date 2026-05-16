# stp-orch ordering — Phase B 調査メモ

調査対象:
- sonic-swss/orchagent/stporch.cpp
- sonic-swss/orchagent/stporch.h
- sonic-swss/orchagent/orchdaemon.cpp

## 1. StpOrch 自体の前提: allPortsReady() ガード

`StpOrch::doTask()` (`stporch.cpp:578-581`) は冒頭で `gPortsOrch->allPortsReady()` を確認し、
false なら**即 return** してすべての APPL_DB テーブル処理を保留する。

```cpp
void StpOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady())
        return;
    // ...
}
```

→ 順序依存: `PortsOrch` が `PORT_INIT_DONE` を受信するまで StpOrch は何も処理しない。
  保留エントリはエラーログなしで次サイクルまで `m_toSync` に残る。

## 2. STP_VLAN_INSTANCE_TABLE (doStpTask) の処理依存

### 2a. VLAN が PortsOrch に登録されていること

`addVlanToStpInstance()` (`stporch.cpp:115-163`) の冒頭:
```cpp
if (!gPortsOrch->getPort(vlan_alias, vlan))
{
    return false;
}
```
VLAN が PortsOrch に存在しない場合、関数は false を返す。
呼び出し元 `doStpTask()` (`stporch.cpp:410-414`) は:
```cpp
if(!addVlanToStpInstance(vlan_alias, instance))
{
    it++;
    continue;
}
```
→ `it++` (erase せず進む) で残置、次サイクルで再試行。
  VLAN の PortsOrch 登録が STP_VLAN_INSTANCE_TABLE の SET より先行必須。

### 2b. SAI STP インスタンス作成の成否

`addStpInstance()` (`stporch.cpp:59-77`) は `sai_stp_api->create_stp()` を呼ぶ。
失敗時は `SAI_NULL_OBJECT_ID` を返し、上位 `addVlanToStpInstance()` も false を返す
→ 上記と同様に残置。

### 2c. removeVlanFromStpInstance() の依存

`doStpTask()` DEL 分岐 (`stporch.cpp:417-424`):
```cpp
if(!removeVlanFromStpInstance(vlan_alias, 0))
{
    it++;
    continue;
}
```
`removeVlanFromStpInstance()` も `gPortsOrch->getPort()` を呼ぶため、
DEL 時も VLAN が PortsOrch に存在することが前提。

## 3. STP_PORT_STATE_TABLE (doStpPortStateTask) の処理依存

### 3a. ポートが PortsOrch に登録されていること

`doStpPortStateTask()` (`stporch.cpp:449-453`):
```cpp
if (!gPortsOrch->getPort(port_alias, port))
{
    return;  // ← it++ でなく return
}
```
ポートが未登録の場合は `return` (ループ全体を抜ける)。
**`it++` ではなく `return`** であるため、同一コンシューマの後続エントリもブロックされる。
→ 順序依存: 物理ポート / LAG の PortsOrch 登録が STP_PORT_STATE_TABLE の SET より先行必須。

### 3b. キー形式 `<port>:<instance>` の検証

`doStpPortStateTask()` (`stporch.cpp:439-443`):
```cpp
if (found == string::npos)
{
    return;  // 不正キーでループ全体ブロック
}
```
キーに `:` が含まれない場合も `return` でブロック。

### 3c. addStpPort() / bridge port 依存

`addStpPort()` (`stporch.cpp:218-227`):
```cpp
if(port.m_bridge_port_id == SAI_NULL_OBJECT_ID)
{
    gPortsOrch->addBridgePort(port);
    if(port.m_bridge_port_id == SAI_NULL_OBJECT_ID)
    {
        SWSS_LOG_ERROR("Failed to add STP port %s invalid bridge port id STP instance %d", ...);
        return SAI_NULL_OBJECT_ID;
    }
}
```
Bridge port が未作成の場合、自動的に `addBridgePort()` を試みるが失敗すると SAI_NULL_OBJECT_ID を返す。
→ PortsOrch が bridge port を作成済みであることが暗黙の前提。

## 4. STP_FASTAGEING_FLUSH_TABLE (doStpFastageTask) の依存

`stpVlanFdbFlush()` (`stporch.cpp:363-378`):
```cpp
if (!gPortsOrch->getPort(vlan_alias, vlan))
{
    return false;
}
gFdbOrch->flushFdbByVlan(vlan_alias);
```
- VLAN が PortsOrch 未登録: false を返すが doStpFastageTask は戻り値を無視して消去する
  (`it = consumer.m_toSync.erase(it)` は常に実行)
- `gFdbOrch` (FdbOrch) が初期化済みであること: 起動シーケンスで保証

→ FDB フラッシュは fail-silent (VLAN 未登録でもエントリは消える)

## 5. STP_INST_PORT_FLUSH_TABLE (doMstInstPortFlushTask) の依存

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
`m_vlanAliasToStpInstanceMap` に対象インスタンスが存在しない場合は no-op。
このマップは `addVlanToStpInstance()` が `STP_VLAN_INSTANCE_TABLE` を処理した際に更新される。

→ 順序依存: MST フラッシュは `STP_VLAN_INSTANCE_TABLE` の SET (VLAN→インスタンス割当) が先行必須。
  先行していなければフラッシュ対象 VLAN リストが空で no-op になる (エラーなし)。

## 6. 処理依存グラフ (StpOrch 観点)

```
PORT_INIT_DONE (PortsOrch) ← 全テーブルの前提
        │
        ▼
STP_VLAN_INSTANCE_TABLE SET
  requires: VLAN が PortsOrch に登録済み
        │
        ▼
STP_PORT_STATE_TABLE SET
  requires: ポートが PortsOrch に登録済み
            + bridge port が作成済み
            (+ STP インスタンスが存在しない場合は自動作成)
        │
        ▼
STP_FASTAGEING_FLUSH_TABLE SET
  requires: VLAN が PortsOrch に登録済み (未登録でも消去)
            FdbOrch が初期化済み

STP_INST_PORT_FLUSH_TABLE SET
  requires: STP_VLAN_INSTANCE_TABLE で VLAN→インスタンス登録済み
```

## 7. retry 挙動サマリー

| テーブル | 不成立条件 | 挙動 |
|---------|----------|------|
| 全テーブル | `allPortsReady()` = false | `return` (ループ到達前) |
| STP_VLAN_INSTANCE_TABLE SET | VLAN 未登録 / SAI 失敗 | `it++` 残置 (次サイクル再試行) |
| STP_VLAN_INSTANCE_TABLE DEL | VLAN 未登録 | `it++` 残置 |
| STP_PORT_STATE_TABLE SET/DEL | ポート未登録 / 不正キー | `return` (コンシューマ全体ブロック) |
| STP_PORT_STATE_TABLE SET | SAI 失敗 | `it++` 残置 |
| STP_FASTAGEING_FLUSH_TABLE SET | VLAN 未登録 | fail-silent (消去) |
| STP_INST_PORT_FLUSH_TABLE SET | インスタンス未登録 | no-op (消去) |

## 証跡

- stporch.cpp:17-43 (コンストラクタ)
- stporch.cpp:59-77 (addStpInstance)
- stporch.cpp:115-163 (addVlanToStpInstance)
- stporch.cpp:165-204 (removeVlanFromStpInstance)
- stporch.cpp:207-258 (addStpPort)
- stporch.cpp:363-378 (stpVlanFdbFlush)
- stporch.cpp:380-427 (doStpTask)
- stporch.cpp:429-486 (doStpPortStateTask)
- stporch.cpp:488-519 (doStpFastageTask)
- stporch.cpp:521-571 (doMstInstPortFlushTask)
- stporch.cpp:574-601 (doTask)
