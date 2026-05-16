# vlan-state-defaults — Phase A 調査メモ

対象: `STATE_DB VLAN_TABLE` フィールドのコード由来デフォルト
調査日: 2026-05-15
精読ファイル:
- `sonic-swss/cfgmgr/vlanmgr.cpp` (SHA 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h` (SHA 158de8d3463ff4b841653f6d57190bb142b80d9c)

---

## テーブル名定義

```c
// sonic-swss-common/common/schema.h:423
#define STATE_VLAN_TABLE_NAME  "VLAN_TABLE"
```

STATE_DB のキー空間: `VLAN_TABLE|<VlanName>` (例: `VLAN_TABLE|Vlan100`)

---

## 書き込み主体と書き込みトリガー

唯一の書き込み主体は `vlanmgrd` の `VlanMgr::doVlanTask()` (vlanmgr.cpp)。

### 作成 (SET_COMMAND)

```cpp
// vlanmgr.cpp:440-443
vector<FieldValueTuple> fvVector;
FieldValueTuple s("state", "ok");
fvVector.push_back(s);
m_stateVlanTable.set(key, fvVector);
```

書き込み条件:
1. CONFIG_DB `VLAN` テーブルに `SET` 操作が来る
2. 既に state が OK でない（warm-restart 重複スキップがない）場合

フィールドは `state = "ok"` の 1 フィールドのみ。固定リテラル。

### 削除 (DEL_COMMAND)

```cpp
// vlanmgr.cpp:463
m_stateVlanTable.del(key);
```

CONFIG_DB `VLAN` テーブルから DEL 操作が来ると、対応エントリが削除される。

---

## フィールド一覧

| フィールド | 型 | コード由来デフォルト | 出典 |
|-----------|-----|---------------------|------|
| `state` | string `"ok"` | `"ok"` 固定リテラル。VLAN 作成完了シグナルとして vlanmgrd が書き込む | vlanmgr.cpp:441 |

---

## 読み取り主体（consumers）

| プロセス | ファイル | 用途 |
|---------|---------|------|
| `vlanmgrd` 自身 | vlanmgr.cpp:523 (`isVlanStateOk`) | VLAN が作成済みかを確認。warm-restart 重複スキップ + member 追加前ガード |
| `intfmgrd` | intfmgr.cpp:655 | VLAN インタフェース設定前にVLAN readiness を確認 |
| `nbrmgrd` | nbrmgr.cpp:48 (宣言のみ) | ネイバー設定前 VLAN readiness ガード |
| `stpmgrd` | stpmgr.cpp:1282 | STP ポート/VLAN 設定前 readiness ガード |
| `natmgrd` | natmgr.cpp:102 | NAT エントリ設定前 VLAN readiness ガード |
| `vxlanmgrd` | vxlanmgr.cpp:774 | VXLAN tunnel member 設定前 VLAN readiness ガード |

すべての読み取りは「VLAN が存在するか (bool)」の用途であり、`state` の値そのものは `"ok"` か存在しないかの 2 値として扱われる。

---

## 設計上の特記事項

1. **シグナル専用テーブル**: STATE_DB VLAN_TABLE は CONFIG_DB VLAN テーブルと同名ではなく、`VLAN_TABLE` として STATE_DB に独立する。CONFIG_DB の `VLAN|VlanX` と混同しないこと。

2. **warm-restart 重複スキップ**: `isVlanStateOk(key)` が true かつ `m_vlans` に存在しない場合、vlanmgrd は再作成をスキップして replay エントリを消去する (vlanmgr.cpp:371-378)。STATE_DB エントリの存在が idempotent な設計の根拠。

3. **Linux bridge 作成との順序**: `addHostVlan(vlan_id)` → `m_appVlanTableProducer.set()` → `m_stateVlanTable.set()` の順。STATE_DB への書き込みは Linux bridge 作成と APP_DB 通知の後。

4. **唯一フィールドの自明性**: `state = "ok"` は固定値であるため、テーブルにエントリが存在すること自体がシグナル。他のフィールドは存在しない。

---

## 確認クエリ

```bash
# STATE_DB 全 VLAN エントリ確認
sonic-db-cli STATE_DB keys 'VLAN_TABLE|*'

# 特定 VLAN の state 確認
sonic-db-cli STATE_DB hgetall 'VLAN_TABLE|Vlan100'
```
