# VLAN — 暗黙参照テーブル調査 (Phase C)

調査日: 2026-05-16  
対象テーブル: `VLAN`  
調査ソース: `sonic-swss/cfgmgr/vlanmgr.cpp`, `sonic-swss/cfgmgr/vlanmgrd.cpp`

## 調査対象ファイル

### sonic-swss
- `cfgmgr/vlanmgr.cpp` — VLAN 主購読者 (vlanmgrd コンテキスト)
- `cfgmgr/vlanmgrd.cpp` — vlanmgrd エントリポイント・Select ループ

## 暗黙参照関係の全量

### 1. PORT テーブル (必須前提: VLAN_MEMBER 追加時のメンバー解決)

**種別**: 暗黙参照（YANG leafref なし、STATE_DB 経由のランタイム依存）

**根拠**:
- `vlanmgr.cpp:29`: `m_statePortTable(stateDb, STATE_PORT_TABLE_NAME)` — VlanMgr コンストラクタで `STATE_PORT_TABLE` を購読初期化。
- `vlanmgr.cpp:491-514` (`isMemberStateOk`): `VLAN_MEMBER` の SET 処理時、物理ポート (`EthernetN`) の場合 `m_statePortTable.get(alias, temp)` で `state` フィールドを確認。取得できない場合は `false` を返し処理を保留。
- `vlanmgrd.cpp:40`: `STATE_OPER_PORT_TABLE_NAME` を Select 対象テーブルとして登録 — 物理ポートの oper-state 変化を受信して VLAN_MEMBER の再バインドを試みる。

**実装上の挙動**: `VLAN_MEMBER` を SET する際、メンバーポートが `STATE_PORT_TABLE` に登録されるまで vlanmgrd は処理を `m_toSync` に留めて次ポーリングで再試行する。ポートが ready 前に SET しても自動リトライされる。

---

### 2. VLAN_MEMBER テーブル (暗黙参照: 同一 vlanmgrd プロセス内で統合処理)

**種別**: 暗黙参照（同一 vlanmgrd プロセス内で VLAN_MEMBER を処理）

**根拠**:
- `vlanmgr.cpp:28`: `m_cfgVlanMemberTable(cfgDb, CFG_VLAN_MEMBER_TABLE_NAME)` — VlanMgr コンストラクタで `VLAN_MEMBER` を読み込み初期化。
- `vlanmgr.cpp:47`: `m_cfgVlanMemberTable.getKeys(vlanMemberKeys)` — warm-reboot 時に全 VLAN_MEMBER キーを `m_vlanMemberReplay` にキャッシュ。
- `vlanmgr.cpp:552-584` (`processUntaggedVlanMembers`): VLAN エントリの `members@` フィールドに含まれるメンバーリストを VLAN_MEMBER として疑似 SET する。
- `vlanmgrd.cpp:37`: `CFG_VLAN_MEMBER_TABLE_NAME` を Select 対象テーブルとして登録 — VLAN_MEMBER の変更を受信。

**実装上の挙動**: `VLAN` テーブルの `members@` フィールド（レガシー形式）を vlanmgrd が `VLAN_MEMBER` に変換して処理する。`VLAN_MEMBER` は独立テーブルだが vlanmgrd が一体管理している。

---

### 3. VLAN_INTERFACE テーブル (間接依存: VLAN 作成後の L3 IF 設定)

**種別**: 間接参照（YANG leafref: `sonic-vlan.yang` の `VLAN_INTERFACE_LIST.name` が `VLAN_LIST.name` を leafref）

**根拠**:
- `vlanmgr.cpp:517-530` (`isVlanStateOk`): `VLAN_INTERFACE` の SET 処理時に `intfmgr.cpp` 側が `STATE_VLAN_TABLE` を確認。vlanmgrd が `VLAN` を登録した後に `STATE_VLAN_TABLE|Vlan<N>` を書き込むことで `VLAN_INTERFACE` の処理をアンブロックする。
- vlanmgrd が `STATE_DB / VLAN_TABLE` へ `state=ok` を書くことが `VLAN_INTERFACE` 処理の前提条件。

**実装上の挙動**: `VLAN_INTERFACE` は `VLAN` テーブルへの公式 leafref を YANG 上で持ち、かつ intfmgrd が `STATE_VLAN_TABLE` ready を確認してから処理する。`VLAN` を先に SET しないと `VLAN_INTERFACE` が孤立する。

---

### 4. STATE_LAG_TABLE (LAG メンバー参照: PortChannel 対応)

**種別**: 暗黙参照（YANG leafref なし、STATE_DB 経由のランタイム依存）

**根拠**:
- `vlanmgr.cpp:30`: `m_stateLagTable(stateDb, STATE_LAG_TABLE_NAME)` — VlanMgr コンストラクタで `STATE_LAG_TABLE` を購読初期化。
- `vlanmgr.cpp:495-502` (`isMemberStateOk`): `PortChannel` プレフィックスで始まるメンバーの場合 `m_stateLagTable.get(alias, temp)` で LAG 存在を確認。取得できない場合 `false` を返し処理を保留。

**実装上の挙動**: `VLAN_MEMBER` に `PortChannelN` を追加する場合、teamd が `STATE_LAG_TABLE` に対象 LAG を登録するまで vlanmgrd は保留する。

---

## 結論: 参照関係サマリ

| 参照先テーブル / DB | YANG leafref | 実装上の必須度 | 参照方向 | 参照箇所 |
|---|---|---|---|---|
| `PORT` (STATE_PORT_TABLE 経由) | なし | 条件付き必須 (VLAN_MEMBER 追加時) | VLAN → PORT | `vlanmgr.cpp:503`, `vlanmgrd.cpp:40` |
| `VLAN_MEMBER` | なし (同一 mgrd 処理) | 実質必須 (vlanmgrd 統合処理) | VLAN → VLAN_MEMBER | `vlanmgr.cpp:28,47,552` |
| `VLAN_INTERFACE` | ✅ あり (YANG leafref) | 必須 (VLAN_INTERFACE は VLAN 依存) | VLAN_INTERFACE → VLAN | `vlanmgr.cpp:517-530` |
| `PORTCHANNEL` (STATE_LAG_TABLE 経由) | なし | 条件付き必須 (LAG メンバー追加時) | VLAN → PORTCHANNEL | `vlanmgr.cpp:495-502` |
