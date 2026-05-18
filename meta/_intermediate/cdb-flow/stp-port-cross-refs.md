# STP_PORT — Phase C 暗黙参照調査メモ

調査対象: `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 参照テーブル・状態一覧

### 1. STP|GLOBAL — stpGlobalTask フラグ源 + l2ProtoEnabled 確定

- **参照箇所**: `stpmgr.cpp:630-634`
  ```cpp
  if (stpGlobalTask == false)
      return;
  ```
- `doStpGlobalTask()` が `STP|GLOBAL` の最初の SET を受け取ったときに `stpGlobalTask = true` をセットし、`mode` フィールドで `l2ProtoEnabled` を `L2_PVSTP` / `L2_MSTP` に確定する
- `stpGlobalTask` が立っていない場合 `doStpPortTask()` は即 return（エラーなし）
- **方向**: 読み取り（stpmgrd 内部フラグ経由）

### 2. m_lagMap — PortChannel 空メンバーチェック

- **参照箇所**: `stpmgr.cpp:648-653`, `isLagEmpty()` (`stpmgr.cpp:1306-1325`)
  ```cpp
  if (isLagEmpty(key))
  {
      it = consumer.m_toSync.erase(it);
      continue;
  }
  ```
- キーが `PortChannel` を含む場合、`m_lagMap` にエントリが存在しない（= LAG にメンバーが一人もいない）場合は SET を **即消去**（silent drop）
- `m_lagMap` は `doLagMemUpdateTask()` が `PORTCHANNEL_MEMBER` テーブルの変更を受信するたびに更新される
- **方向**: 読み取り（stpmgrd 内部 map）

### 3. STATE_DB:STATE_VLAN_MEMBER_TABLE — VLAN メンバーリスト取得

- **参照箇所**: `stpmgr.cpp:527`, `getAllPortVlan()` (`stpmgr.cpp:978-1025`)
  ```cpp
  vlanCnt = getAllPortVlan(intfName, vlan_list);
  ```
- `processStpPortAttr()` が SET 操作を処理する際、`m_stateVlanMemberTable` からインタフェースが所属する全 VLAN を取得し、`STP_PORT_CONFIG` IPC メッセージの VLAN リストに付加する
- STATE_VLAN_MEMBER_TABLE にエントリがなければ VLAN リストが空になり、stpd へのメッセージが VLAN 情報なしで送信される
- **方向**: 読み取り（`m_stateVlanMemberTable` 接続）

### 4. CONFIG_DB:VLAN_MEMBER — tagging_mode 取得

- **参照箇所**: `stpmgr.cpp:1004`, `getVlanMemMode()` (`stpmgr.cpp:1361-1379`)
  ```cpp
  vlan.mode = getVlanMemMode(key);
  ```
- `getAllPortVlan()` 内で VLAN メンバー情報を取得する際、`m_cfgVlanMemberTable` から `tagging_mode` フィールドを読み取り、TAGGED_MODE / UNTAGGED_MODE を判定する
- `tagging_mode` が存在しない場合 `SWSS_LOG_ERROR` が記録され `INVALID_MODE` (-1) が返り、そのエントリは VLAN リストに含まれない
- **方向**: 読み取り（`m_cfgVlanMemberTable` 接続）

### 5. m_vlanInstMap — VLAN インスタンス割当チェック

- **参照箇所**: `stpmgr.cpp:1002-1010`
  ```cpp
  if (m_vlanInstMap[vlan_id] != INVALID_INSTANCE)
  {
      vlan.inst_id = m_vlanInstMap[vlan_id];
      vlan_list.push_back(vlan);
  }
  ```
- `getAllPortVlan()` 内で VLAN ループ時、`m_vlanInstMap[vlan_id]` が `INVALID_INSTANCE` の VLAN はリストに含まれない
- `m_vlanInstMap` は `doStpVlanTask()` 内で stpd の `allocL2Instance()` 呼び出し後に更新される
- **方向**: 読み取り（stpmgrd 内部配列）

### 6. stpd IPC socket — STP デーモンへの通知

- **参照箇所**: `stpmgr.cpp:624` (`sendMsgStpd(STP_PORT_CONFIG, len, msg)`)
- `processStpPortAttr()` 完了後、Unix Domain Socket (`/var/run/stpipc.sock`) 経由で `STP_PORT_CONFIG` メッセージを stpd に送信
- IPC 送信失敗時のエラーハンドリングは `sendMsgStpd()` 内に限定される（`errno` ベースのログ出力）
- **方向**: 書き込み（IPC 送信）

## 参照関係サマリ

```
STP_PORT テーブル処理 (doStpPortTask / processStpPortAttr)
  |- [必須フラグ]  STP|GLOBAL → stpGlobalTask (stpmgrd 内部)
  |- [必須フラグ]  STP|GLOBAL.mode → l2ProtoEnabled (L2_PVSTP / L2_MSTP)
  |- [暗黙チェック] m_lagMap (PortChannel メンバー存在確認 — 空なら silent drop)
  |- [VLAN列挙]    STATE_DB:STATE_VLAN_MEMBER_TABLE (ポート所属 VLAN 一覧取得)
  |- [タグ確認]    CONFIG_DB:VLAN_MEMBER.tagging_mode (TAGGED / UNTAGGED 判定)
  |- [インスタンス] m_vlanInstMap[] (STP_VLAN 処理完了後に有効化される内部状態)
  `- [出力]        stpd IPC socket (STP_PORT_CONFIG メッセージ)
```
