# copp-state ordering — Phase B 調査メモ

調査対象:
- `sonic-swss/cfgmgr/coppmgr.cpp`
- `sonic-swss/orchagent/copporch.cpp`

---

## STATE_DB 書き込み順序（通常起動）

### 1. CoppOrch コンストラクタ（orchagent 起動時）

```
CoppOrch::CoppOrch()
  └─ publishTrapIdsCapability()
       └─ m_trapCapabilityTable->set("traps", ...)
            → STATE_DB COPP_TRAP_CAPABILITY_TABLE|traps を書き込む（最初に 1 回のみ）
```

- SAI の `sai_query_attribute_enum_values_capability()` を呼んでサポート trap_id リストを取得
- 失敗時は静的デフォルトリスト（42 種）にフォールバック（`neighbor_miss` を除外）
- `initDefaultHostIntfTable()` → `initDefaultTrapGroup()` → `initDefaultTrapIds()` はこの後に実行

### 2. CoppMgr コンストラクタ（coppmgrd 起動時）

```
CoppMgr::CoppMgr()
  ├─ parseInitFile()                          // copp_cfg.j2 から init 設定読み込み
  ├─ mergeConfig(trap_cfg, ...)               // CONFIG_DB + init をマージ
  ├─ for each trap in trap_cfg
  │    └─ setCoppTrapStateOk(trap_name)       // STATE_DB COPP_TRAP_TABLE|<trap> state=ok
  ├─ mergeConfig(group_cfg, ...)
  └─ for each group in group_cfg
       ├─ m_appCoppTable.set(group, fvs)      // APPL_DB APP_COPP_TABLE|<group>
       └─ setCoppGroupStateOk(group_name)     // STATE_DB COPP_GROUP_TABLE|<group> state=ok
```

**書き込み順**: `COPP_TRAP_TABLE` state → `COPP_GROUP_TABLE` state

`COPP_TRAP_TABLE` の `hw_status` はこの時点では書かれない（orchagent が APPL_DB を処理してから書かれる）。

### 3. orchagent が APPL_DB を処理した後

```
CoppOrch::addTrapIds()  ← APP_COPP_TABLE の SET を受信
  └─ applyAttributesToTrapIds()
       ├─ sai_hostif_api->create_hostif_trap()  成功
       └─ updateTrapOperStatus(trap_id, "installed")
            → STATE_DB COPP_TRAP_TABLE|<trap-name> hw_status=installed
```

**書き込み順**: SAI create 成功 → `hw_status=installed` の順（失敗時は書かれない）。

---

## 削除・更新の順序

### coppmgr による削除（feature 無効化）

```
setFeatureTrapIdsStatus(feature, false)
  ├─ m_appCoppTable.del(trap_group)           // APPL_DB から削除
  └─ delCoppGroupStateOk(trap_group)          // STATE_DB COPP_GROUP_TABLE|<group> を del
```

trap 削除は orchagent 側で SAI remove → `updateTrapOperStatus(trap_type, "not-installed")` により:
```
sai_hostif_api->remove_hostif_trap()  成功
  └─ updateTrapOperStatus(trap_id, "not-installed")
       → STATE_DB COPP_TRAP_TABLE|<trap-name> hw_status=not-installed
```

### doCoppTrapTask DEL

```
delCoppTrapStateOk(key)   → STATE_DB COPP_TRAP_TABLE|<trap> を del
```

init cfg にエントリが存在する場合は自動復元（`setCoppTrapStateOk(key)` を呼び直す）。

---

## Warm-reboot の扱い

`coppmgr.cpp` では `warm_restart.h` を include しているが、
コード内に `WarmStart::` / `isWarmStart()` 等の呼び出しは存在しない。

これは COPP の State DB 書き込みが **冪等**（同一 key への上書き set）であるため、
warm-reboot 時も通常起動と同一フローで再書き込みを行い、
orchagent 側の SAI reconciliation に委ねる設計であることを示す。

`COPP_TRAP_CAPABILITY_TABLE` は orchagent 起動のたびに
`publishTrapIdsCapability()` で上書きされる（内容は実質変わらない）。

---

## 書き込み依存グラフ

```
[orchagent 起動]
  ↓
COPP_TRAP_CAPABILITY_TABLE|traps (publishTrapIdsCapability)

[coppmgrd 起動]
  ↓
COPP_TRAP_TABLE|<trap> state=ok   (setCoppTrapStateOk, per trap)
  ↓
APPL_DB APP_COPP_TABLE|<group>    (m_appCoppTable.set)
  ↓
COPP_GROUP_TABLE|<group> state=ok (setCoppGroupStateOk)

[orchagent が APPL_DB を処理]
  ↓
SAI create_hostif_trap 成功
  ↓
COPP_TRAP_TABLE|<trap> hw_status=installed (updateTrapOperStatus)
```

`state=ok` と `hw_status` は同一 key に別プロセスが非同期で書き込むため、
両フィールドが揃うタイミングは保証されない（短時間の不整合は正常動作）。

---

evidence: coppmgr.cpp L296-422, L82-155, L439-452, L424-436, L531-808, L840-925
evidence: copporch.cpp L191-215, L222-237, L240-300, L499-533, L1397-1415
