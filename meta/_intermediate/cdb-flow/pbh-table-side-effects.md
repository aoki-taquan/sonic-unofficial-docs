# PBH_TABLE — 副次 DB 書き込み調査ノート (Phase F)

## スキャン対象

- `sonic-swss/orchagent/pbhorch.cpp` (rev 4305596)
- `sonic-swss/orchagent/pbh/pbhmgr.cpp` (rev 4305596)
- `sonic-swss/orchagent/aclorch.cpp` (副次的参照)

## 結論サマリ

`PBH_TABLE` の SET/DEL 処理は **STATE_DB / APPL_DB への直接書き込みを行わない**。
副次的な状態変更は以下の 2 点に限られる。

1. **SAI ACL テーブルオブジェクト作成/更新/削除** — `aclOrch->addAclTable()` / `updateAclTable()` / `removeAclTable()` 経由で SAI に ACL テーブルオブジェクトが作成される。これは ASIC 側の副作用であり、CONFIG_DB/APPL_DB/STATE_DB には反映されない。
2. **AclOrch 内の pendingPortSet** — `validateAddPorts()` 失敗時に `AclTable::pendingPortSet` にポート名を蓄積する。`SUBJECT_TYPE_PORT_CHANGE` 通知で自動的に再バインドが試みられる。この状態は orchagent プロセス内メモリのみ。
3. **pbhHlpr 内部キャッシュ (tableMap)** — `addPbhTable()` が `tableMap` に PBH_TABLE エントリを追加する。`PBH_RULE` の `incRefCount()` / `decRefCount()` はこの tableMap エントリの refCount を増減させる。PBH_TABLE の DEL 時は `hasDependencies()` が refCount > 0 の間 blocking する。

## grep 証跡

```
grep -n "m_stateDb\|stateDb\|m_applDb\|applDb\|APPL_DB\|STATE_DB\|Table.*set\|m_counter\|FlexCounter" \
  orchagent/pbhorch.cpp
→ 0 件（STATE_DB / APPL_DB への書き込みなし）
```

`pbhorch.cpp` の唯一の副次的な外部書き込みは `this->aclOrch->addAclTable(pbhTable)` (L286) のみ。
`aclOrch->addAclTable()` は SAI `create_acl_table` を呼ぶが、DB への書き込みはしない。
