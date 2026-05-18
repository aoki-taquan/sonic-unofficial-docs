# STP_VLAN / STP_VLAN_PORT — Phase C 暗黙参照調査メモ

調査対象: `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 参照テーブル・状態一覧

### 1. STP|GLOBAL — l2ProtoEnabled フラグ源

- **参照箇所**: `stpmgr.cpp:210` (`l2ProtoEnabled == L2_NONE` チェック)
- `doStpGlobalTask()` が `STP|GLOBAL` の `mode` フィールドを受信し `l2ProtoEnabled` を `L2_PVSTP` / `L2_MSTP` に設定する
- `l2ProtoEnabled == L2_NONE` の場合、`doStpVlanTask()` は全 SET をスキップ（silent skip、イテレータ進める）
- **方向**: 読み取り（stpmgrd 内部状態 `l2ProtoEnabled` 経由）

### 2. STP_PORT — stpPortTask フラグ源

- **参照箇所**: `stpmgr.cpp:183-185`
  ```cpp
  if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
      return;
  ```
- `doStpPortTask()` が `STP_PORT` の最初の SET を受け取ると `stpPortTask = true` に設定
- ポートが空の場合（`isStpPortEmpty()` = true）はフラグなしで通過可
- **方向**: 読み取り（stpmgrd 内部フラグ `stpPortTask` 経由）

### 3. STATE_DB:STATE_VLAN_TABLE — VLAN 準備確認

- **参照箇所**: `stpmgr.cpp:210`, `isVlanStateOk()` (`stpmgr.cpp:1276-1290`)
  ```cpp
  if (m_stateVlanTable.get(alias, temp)) { return true; }
  ```
- `vlanmgrd` が VLAN を ASIC に適用後 `STATE_VLAN_TABLE|Vlan<vid>` を書き込む
- 対象 VLAN が STATE_VLAN_TABLE に存在しない場合、SET はイテレータを進めて持ち越し（silent skip）
- **方向**: 読み取り（`m_stateVlanTable` 接続）

### 4. STATE_DB:STATE_VLAN_MEMBER_TABLE — ポートメンバー参照

- **参照箇所**: `stpmgr.cpp:938`, `getAllVlanMem()` (`stpmgr.cpp:930-1021`)
- PVST で新 VLAN インスタンス割当時 (`newInstance = 1`)、`STATE_VLAN_MEMBER_TABLE` から当該 VLAN の全メンバーポートを取得し `STP_VLAN_CONFIG` IPC メッセージに付加
- **方向**: 読み取り（`m_stateVlanMemberTable` 接続）

### 5. stpd IPC socket — STP デーモンへの通知

- **参照箇所**: `stpmgr.cpp:332` (`sendMsgStpd(STP_VLAN_CONFIG, ...)`)
- `STP_VLAN` SET 処理後、Unix Domain Socket (`/var/run/stpipc.sock`) 経由で `STP_VLAN_CONFIG` メッセージを stpd に送信
- `m_vlanInstMap[vlan_id]` は stpd 側の応答（`allocL2Instance()` / `deallocL2Instance()`）によって設定される
- **方向**: 書き込み（IPC 送信）

### 6. m_vlanInstMap — STP_VLAN_PORT の暗黙依存

- **参照箇所**: `stpmgr.cpp:486-495` (`doStpVlanPortTask()`)
  ```cpp
  if ((l2ProtoEnabled == L2_NONE) || (m_vlanInstMap[vlan_id] == INVALID_INSTANCE))
  {
      it++;
      continue;
  }
  ```
- `STP_VLAN` 処理後に `m_vlanInstMap[vlan_id]` が有効インスタンス ID に設定される
- `STP_VLAN_PORT` は同 VLAN の `m_vlanInstMap` が INVALID_INSTANCE の間、全 SET を silent skip
- **方向**: stpmgrd 内部配列（STP_VLAN 処理完了後に書き込まれ、STP_VLAN_PORT 処理時に読み取られる）

### 7. STP_VLAN_PORT (cfg) — 遅延参照

- **参照箇所**: `stpmgr.cpp:732`, `844` (`m_cfgStpVlanPortTable.get()`)
- `doVlanMemUpdateTask()` が新規ポートメンバー追加時に既存 `STP_VLAN_PORT` エントリを参照し、設定済みの path_cost/priority を stpd へ再送する
- **方向**: 読み取り（`m_cfgStpVlanPortTable` 接続）

## 参照関係サマリ

```
STP_VLAN / STP_VLAN_PORT
  |- [必須フラグ] STP|GLOBAL → l2ProtoEnabled (stpmgrd 内部)
  |- [必須フラグ] STP_PORT → stpPortTask (stpmgrd 内部)
  |- [必須状態]   STATE_DB:STATE_VLAN_TABLE|Vlan<vid> (vlanmgrd が書込)
  |- [必須状態]   STATE_DB:STATE_VLAN_MEMBER_TABLE (PVST インスタンス割当時)
  |- [内部配列]   m_vlanInstMap[] (STP_VLAN→STP_VLAN_PORT の暗黙依存)
  |- [内部配列]   m_cfgStpVlanPortTable (VlanMem 追加時の遅延再送)
  `- [出力]       stpd IPC socket (STP_VLAN_CONFIG メッセージ)
```
