# ACL_TABLE_TYPE — 書込み順依存調査 (Phase B)

調査対象: `sonic-swss/orchagent/aclorch.cpp`, `orchagent/acltable.h`
調査日: 2026-05-17

## 概要

`ACL_TABLE_TYPE` は CONFIG_DB に登録されたユーザー定義の ACL テーブルタイプ。
`AclOrch::doAclTableTypeTask()` が処理し、内部の `m_AclTableTypes` マップに保持する。

## 先行必須条件

### 1. `ACL_TABLE_TYPE` は `ACL_TABLE` より先に登録する必要がある

`doAclTableTask()` (`aclorch.cpp:5432-5436`) でカスタム type の解決:

```cpp
auto tableType = getAclTableType(tableTypeName);
if (!tableType)
{
    it++;    // 保留して m_toSync に残す
    continue;
}
```

`ACL_TABLE` エントリが `ACL_TABLE_TYPE` を参照しているとき、対応する `ACL_TABLE_TYPE` エントリが `m_AclTableTypes` に存在しない場合、`doAclTableTask()` は当該エントリを `it++` で保留し、orchagent の次回 `doTask()` 呼び出しまで再試行する。

一方、組み込み型 (`L3`, `L3V6`, `L3V4V6`, `MIRROR`, `MIRRORV6`, `MIRROR_DSCP`, `PFCWD`, `CTRLPLANE`, `MCLAG`, `MUX`, `DROP`, `MARK_META`, `MARK_METAV6`, `EGR_SET_DSCP`, `UNDERLAY_SET_DSCP`, `UNDERLAY_SET_DSCPV6`, `DTEL_FLOW_WATCHLIST`) は `initDefaultTableTypes()` (`aclorch.cpp:3724`) で orchagent 起動時に自動登録されるため、CONFIG_DB への書き込み順序は不要。

### 2. `ACL_TABLE_TYPE` 削除は参照中 `ACL_TABLE` があっても成功する

`removeAclTableType()` (`aclorch.cpp:4932-4942`) は参照チェックなしで即座に `m_AclTableTypes` から削除する:

```cpp
bool AclOrch::removeAclTableType(const string& tableTypeName)
{
    // It is Ok to remove table type that is in use by AclTable.
    // AclTable holds a copy of AclTableType and there is no
    // SAI object associated with AclTableType.
    if (!m_AclTableTypes.erase(tableTypeName))
    {
        SWSS_LOG_ERROR("Unknown table type %s", tableTypeName.c_str());
        return false;
    }
    return true;
}
```

既存 ACL_TABLE はコピーを保持するため SAI 上の ACL table への影響はないが、削除後に同名 `ACL_TABLE_TYPE` を再登録せずに `ACL_TABLE` の SET を再送すると type 未解決 → 保留状態になる。

## SET 順序まとめ

| 操作順序 | 必須か | 根拠 |
|---------|-------|------|
| `ACL_TABLE_TYPE` SET → `ACL_TABLE` SET (カスタム type 参照時) | 必須 (非同期 retry あり) | `aclorch.cpp:5432-5436` |
| `ACL_TABLE` SET → `ACL_RULE` SET | 必須 (非同期 retry あり) | `aclorch.cpp:5556-5566` |
| `ACL_TABLE_TYPE` SET → `ACL_TABLE_TYPE` SET (依存なし) | 不要 (独立) | `m_AclTableTypes` は単純 map |

## DEL 順序まとめ

| 操作順序 | 必須か | 根拠 |
|---------|-------|------|
| `ACL_RULE` DEL → `ACL_TABLE` DEL | 推奨 | rule 残存時は SAI table 削除が `removeAclTable()` で失敗し `PENDING_REMOVAL` に |
| `ACL_TABLE` DEL → `ACL_TABLE_TYPE` DEL | 不要 (コード上問題なし) | `removeAclTableType()` は参照チェックなし。ただし再 SET 時に type 未登録になる |

## `allPortsReady()` ゲート

`doTask()` 冒頭 (`aclorch.cpp:4276-4279`) で `gPortsOrch->allPortsReady()` が false の場合は `ACL_TABLE_TYPE` を含む全テーブルの処理が skip される。起動時の port 初期化完了まで `ACL_TABLE_TYPE` の書き込みも有効にならない。
