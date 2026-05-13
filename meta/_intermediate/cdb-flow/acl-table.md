# ACL_TABLE テーブル — consumer 例外条件分析

## Consumer: AclOrch (sonic-swss/orchagent/aclorch.cpp)

### 処理関数
- `AclOrch::doAclTableTask(Consumer &consumer)` (L5346)

### 例外条件・特殊挙動

#### 1. 属性不明エラー → skip & INACTIVE
未知の属性名が来ると `bAllAttributesOk = false` に設定し、そのエントリをキューから消去する (erase)。
orchagent はクラッシュしない。

```cpp
// sonic-swss/orchagent/aclorch.cpp:5418
SWSS_LOG_ERROR("Unknown table attribute '%s'", attr_name.c_str());
bAllAttributesOk = false;
break;
```

#### 2. `type` フィールド未知 → skip
`processAclTableType()` が失敗した場合、エントリを erase して次へ。
不正な type 文字列は受け付けない。

#### 3. `ports` フィールドのポート存在確認
`processAclTablePorts()` 内でポート名が PortsOrch に存在しない場合は `return false` → エントリ skip。
物理インターフェース以外を IN_PORTS/OUT_PORTS に指定しても reject。

```cpp
// sonic-swss/orchagent/aclorch.cpp:975
SWSS_LOG_ERROR("Failed to locate port %s", alias.c_str());
return false;
```

#### 4. `stage` 不明 → skip
`processAclTableStage()` が `STAGE_INGRESS` / `STAGE_EGRESS` 以外を受けると `return false`。

#### 5. `services` フィールドは無視
コントロールプレーン ACL の `services` フィールドは `continue` (L5414) されて実質スキップ。

#### 6. 重複 table_id の更新
既存 table_id が存在する場合は `updateAclTable()` を呼ぶ。ポートの変更はバインドし直し。

#### 7. UNDERLAY_SET_DSCP 変換
`TABLE_TYPE_UNDERLAY_SET_DSCP`/`V6` は内部で `TABLE_TYPE_MARK_META`/`V6` に変換して作成される。
元の type 名は保持されるが、SAI 操作は変換後の型で行われる。
