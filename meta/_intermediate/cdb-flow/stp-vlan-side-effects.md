# stp-vlan side-effects phase (Phase F)

## 調査対象
- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## STP_VLAN SET — 処理時の副作用

### 1. m_vlanInstMap への書き込み（インスタンス割当）

PVST モードで `STP_VLAN` の `enabled=true` SET が初めて処理されると（`m_vlanInstMap[vlan_id] == INVALID_INSTANCE` の場合）、`allocL2Instance(vlan_id)` が呼ばれる:

```cpp
// stpmgr.cpp:263-269
instId = allocL2Instance(vlan_id);
// -> GET_FIRST_FREE_INST_ID(idx); m_vlanInstMap[vlan_id] = idx;
```

この割当により `m_vlanInstMap[vlan_id]` が `INVALID_INSTANCE(-1)` → 実インスタンス ID に変わり、
待機していた `STP_VLAN_PORT` の SET がブロック解除されて次 SELECT ループで処理可能になる。

### 2. stpd IPC — STP_VLAN_CONFIG メッセージ送信

```cpp
// stpmgr.cpp:332
sendMsgStpd(STP_VLAN_CONFIG, len, (void *)msg);
```

`STP_VLAN_CONFIG_MSG` を stpd に送信する。フィールド内容:
- `opcode`: SET=1 / DEL=0
- `vlan_id`, `inst_id`, `newInstance` (初回=1, 更新=0)
- `forward_delay`, `hello_time`, `max_age`, `priority`
- `count`, `port_list[]` (初回有効化時に `getAllVlanMem()` で取得した VLAN メンバーポート一覧)

APPL_DB / ASIC_DB への書き込みは行わない。CONFIG_DB → IPC → stpd → ASIC という経路。

### 3. PVST 初回有効化 — STATE_VLAN_MEMBER_TABLE 読み取り → stpd へポート一覧を付加

`getAllVlanMem()` (`stpmgr.cpp:933-973`) が `STATE_VLAN_MEMBER_TABLE` から当該 VLAN の全メンバーポートを取得し、
`STP_VLAN_CONFIG_MSG.port_list[]` に付加する。
MST モードでは `newInstance` が設定されないため `getAllVlanMem()` は呼ばれない。

```cpp
// stpmgr.cpp:257-263
if (m_vlanInstMap[vlan_id] == INVALID_INSTANCE)
{
    if (l2ProtoEnabled == L2_PVSTP)
    {
        newInstance = 1;
        instId = allocL2Instance(vlan_id);
        portCnt = getAllVlanMem(key, port_list);
    }
}
```

## STP_VLAN DEL — 処理時の副作用

### 4. m_vlanInstMap のリセット（インスタンス解放）

`deallocL2Instance(vlan_id)` が呼ばれ、`m_vlanInstMap[vlan_id]` が `INVALID_INSTANCE(-1)` に戻る:

```cpp
// stpmgr.cpp:913-928
void StpMgr::deallocL2Instance(uint32_t vlan_id)
{
    idx = m_vlanInstMap[vlan_id];
    FREE_INST_ID(idx);                   // ビットマップのフリーリスト更新
    m_vlanInstMap[vlan_id] = INVALID_INSTANCE;
}
```

DEL 後は同 VLAN の `STP_VLAN_PORT` SET が再び `m_vlanInstMap == INVALID_INSTANCE` による silent skip に戻る。

### 5. stpd IPC — STP_DEL_COMMAND 送信

DEL 時は `opcode = STP_DEL_COMMAND`, `inst_id = m_vlanInstMap[vlan_id]`（解放前の値）を stpd に送信する。
VLAN STP が無効化されたことを stpd に通知し、stpd 側でポート状態が初期化される（ASIC 書き込みを含む）。

## STP|GLOBAL DEL — m_vlanInstMap 全リセット（間接副作用）

`doStpGlobalTask()` での DEL (`config spanning-tree disable`) 時:

```cpp
// stpmgr.cpp:149-155
FREE_ALL_INST_ID();
fill_n(m_vlanInstMap, MAX_VLANS, INVALID_INSTANCE);
l2ProtoEnabled = L2_NONE;
```

`STP|GLOBAL` が削除されると `m_vlanInstMap` が全て `-1` にリセットされ、
以降の `STP_VLAN` / `STP_VLAN_PORT` SET が全てブロックされる。

## STATE_VLAN_MEMBER_TABLE 変化 → STP_VLAN_PORT 再送（間接副作用）

`doVlanMemUpdateTask()` (`stpmgr.cpp:679-757`) が `STATE_VLAN_MEMBER_TABLE` のポート参加/離脱イベントを受信すると:

1. `m_cfgStpVlanPortTable.get(key, stpVlanPortEntry)` で既存 `STP_VLAN_PORT` の path_cost / priority を取得
2. `STP_VLAN_MEM_CONFIG_MSG` に含めて `sendMsgStpd(STP_VLAN_MEM_CONFIG, ...)` を送信

`STP_VLAN_PORT` テーブルを直接変更していなくても、ポート参加/離脱が `STP_VLAN_PORT` 設定値の stpd への再送を引き起こす。

## 副作用サマリー

| # | トリガー | 副作用 | 対象 |
|---|---------|-------|------|
| 1 | `STP_VLAN` SET (enabled=true, 初回) | `m_vlanInstMap[vlan_id]` に PVST インスタンス ID を割当 → `STP_VLAN_PORT` SET ブロック解除 | stpmgrd 内部状態 |
| 2 | `STP_VLAN` SET | `STP_VLAN_CONFIG` IPC メッセージを stpd に送信 | stpd プロセス (ASIC へ波及) |
| 3 | `STP_VLAN` SET (PVST 初回) | `STATE_VLAN_MEMBER_TABLE` を参照し全メンバーポートを IPC に付加 | STATE_DB 読み取り |
| 4 | `STP_VLAN` DEL | `m_vlanInstMap[vlan_id]` を INVALID_INSTANCE に解放 → `STP_VLAN_PORT` SET が再ブロック | stpmgrd 内部状態 |
| 5 | `STP_VLAN` DEL | `STP_VLAN_CONFIG` IPC DEL を stpd に送信 → stpd が ASIC ポート状態を初期化 | stpd プロセス (ASIC へ波及) |
| 6 | `STP\|GLOBAL` DEL | `m_vlanInstMap` 全要素を INVALID_INSTANCE にリセット | stpmgrd 内部状態 (間接) |
| 7 | `STATE_VLAN_MEMBER_TABLE` 変化 | `STP_VLAN_PORT` 設定値を stpd に再送 | stpd プロセス (間接; VLAN_PORT 未変更でも発生) |
