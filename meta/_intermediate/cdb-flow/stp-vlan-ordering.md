# STP_VLAN / STP_VLAN_PORT — Phase B 書込み順依存スキャンノート

対象テーブル: `STP_VLAN`, `STP_VLAN_PORT`
Consumer: `stpmgrd` / `StpMgr` (`sonic-swss/cfgmgr/stpmgr.cpp`)
スキャン範囲: `doStpVlanTask()`, `doStpVlanPortTask()`, `isVlanStateOk()`, `l2ProtoEnabled` ガード全行精読

---

## 検出した順序依存・タイミング依存

### 1. stpGlobalTask + stpPortTask が先行必須 — STP_VLAN のガード条件

`doStpVlanTask()` (`stpmgr.cpp:183-185`) は以下の条件で早期 `return` する:

```cpp
if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
    return;
```

- `stpGlobalTask` は `doStpGlobalTask()` が `STP|GLOBAL` の最初の SET を受け取った時点で `true` になる (`stpmgr.cpp:85-86`)
- `stpPortTask` は `doStpPortTask()` が `STP_PORT` の最初の SET を受け取った時点で `true` になる (`stpmgr.cpp:637-638`)
- `isStpPortEmpty()` が `true`（STP_PORT エントリが存在しない）場合は stpPortTask 待ちをスキップする（ポートなし構成への配慮）

**順序依存**: `STP_VLAN` を書き込む前に `STP|GLOBAL` と `STP_PORT` が受信済みでなければ、SET は `return` で破棄されず次 SELECT ループに持ち越されるが、silent defer となりログも出ない。

証跡: `stpmgr.cpp:179-188`

---

### 2. l2ProtoEnabled ガード — STP モード確定が先行必須

`doStpVlanTask()` の SET ハンドラ (`stpmgr.cpp:210`):

```cpp
if (l2ProtoEnabled == L2_NONE || !isVlanStateOk(key))
{
    it++;
    continue;
}
```

`l2ProtoEnabled` は `doStpGlobalTask()` が `STP|GLOBAL` の `mode` フィールドを受け取った時点で `L2_PVSTP` または `L2_MSTP` に設定される (`stpmgr.cpp:119, 127`)。

**順序依存**: `STP|GLOBAL.mode` が CONFIG_DB に書き込まれ、stpmgrd が受信するまで、`STP_VLAN` の SET は全件スキップされる（silent skip、`it++` で次イテレーションへ）。DEL 操作でも `L2_NONE` 時はスキップして即 erase する (`stpmgr.cpp:246-249`)。

証跡: `stpmgr.cpp:95-133, 207-214`

---

### 3. isVlanStateOk — STATE_VLAN 存在確認が先行必須

`doStpVlanTask()` の `isVlanStateOk(key)` (`stpmgr.cpp:1276-1290`) は `STATE_DB:STATE_VLAN_TABLE` に対象 VLAN のエントリが存在するかを確認する:

```cpp
bool StpMgr::isVlanStateOk(const string &alias)
{
    if (!alias.compare(0, strlen(VLAN_PREFIX), VLAN_PREFIX))
    {
        if (m_stateVlanTable.get(alias, temp))
            return true;
    }
    return false;
}
```

`STATE_VLAN_TABLE` は `vlanmgrd` が VLAN を ASIC に適用した後に書き込む。

**順序依存**: `vlanmgrd` が `STATE_VLAN_TABLE|Vlan<vid>` を書き込む前に `STP_VLAN|Vlan<vid>` を CONFIG_DB に書き込んでも、`doStpVlanTask()` は SET を `it++` でスキップし続ける。エラーログなし（silent defer）。`vlanmgrd` が STATE_VLAN を書き込んだ後、次回 SELECT ループで処理される。

証跡: `stpmgr.cpp:210, 1276-1290`

---

### 4. stpGlobalTask + stpVlanTask + stpPortTask — STP_VLAN_PORT のガード条件

`doStpVlanPortTask()` (`stpmgr.cpp:444-448`) は 3 フラグ全てが必要:

```cpp
if (stpGlobalTask == false || stpVlanTask == false || stpPortTask == false)
    return;
```

- `stpVlanTask` は `doStpVlanTask()` が最初の STP_VLAN SET を受け取った時点で `true` になる
- `stpVlanTask` が立つ前に届いた `STP_VLAN_PORT` の SET は全件 silent defer となる

**順序依存**: PVST 推奨書き込み順序は `STP|GLOBAL` → `STP_PORT` → `STP_VLAN` → `STP_VLAN_PORT`。`STP_VLAN_PORT` は他全テーブルの受信完了後でなければ処理されない。

証跡: `stpmgr.cpp:444-450`

---

### 5. m_vlanInstMap 依存 — STP_VLAN_PORT は VLAN→インスタンスマップが必須

`doStpVlanPortTask()` の SET ハンドラ (`stpmgr.cpp:486-492`):

```cpp
if ((l2ProtoEnabled == L2_NONE) || (m_vlanInstMap[vlan_id] == INVALID_INSTANCE))
{
    it++;
    continue;
}
```

`m_vlanInstMap[vlan_id]` は `doStpVlanTask()` 内で `stpd` からの IPC 応答 (`allocateStpVlanInstance()`) によって設定される。

**順序依存**: `STP_VLAN` エントリの処理（stpd へのメッセージ送信と応答受信）が完了するまで、同 VLAN の `STP_VLAN_PORT` 処理は `INVALID_INSTANCE` チェックによりスキップされる。DEL 操作も同様 (`stpmgr.cpp:495`)。

証跡: `stpmgr.cpp:483-503`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `STP\|GLOBAL` + `STP_PORT` → `STP_VLAN` 受信 | 先行必須（欠如時 silent defer） | 全フラグ揃った後に次 SELECT で処理 |
| 2 | `STP\|GLOBAL.mode` 受信 → `l2ProtoEnabled` 確定 → `STP_VLAN` 処理 | 先行必須（欠如時 silent skip） | `mode` フィールドの受信後に自動復旧 |
| 3 | `STATE_VLAN_TABLE\|Vlan<vid>` 書込み → `STP_VLAN\|Vlan<vid>` 処理 | 先行必須（欠如時 silent skip） | `vlanmgrd` による STATE_VLAN 書込み後に自動復旧 |
| 4 | `STP\|GLOBAL` + `STP_PORT` + `STP_VLAN` → `STP_VLAN_PORT` 受信 | 先行必須（欠如時 silent defer） | PVST: GLOBAL→PORT→VLAN→VLAN_PORT の順で書き込む |
| 5 | `STP_VLAN` 処理完了（stpd インスタンス割当） → `STP_VLAN_PORT` 処理 | 先行必須（欠如時 silent skip） | stpd の IPC 応答後に `m_vlanInstMap` が設定される |
