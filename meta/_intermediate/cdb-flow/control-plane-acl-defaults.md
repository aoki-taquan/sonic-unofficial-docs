# control-plane-acl-defaults — Phase A 調査メモ

## 対象テーブル

`ACL_TABLE` で `type=CTRLPLANE` の場合のコード由来デフォルト。
`ACL_TABLE` 自体は YANG 未定義。スキーマ正本は `sonic-swss/orchagent/aclorch.{h,cpp}`。

---

## 訪問ファイル

| ファイル | 目的 |
|---|---|
| `sonic-swss/orchagent/aclorch.cpp` | doAclTableTask(), addAclTable(), validate() |
| `sonic-swss/orchagent/aclorch.h` | AclTable struct, AclStage enum |
| `sonic-swss/orchagent/acltable.h` | TABLE_TYPE_CTRLPLANE マクロ |
| `sonic-buildimage/src/sonic-config-engine/minigraph.py` | ACL_TABLE 生成ロジック |
| `sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-acl.yang.j2` | YANG スキーマ (ACL_TABLE は YANG 外) |

---

## field × デフォルト 分析

### `type` フィールド

- YANG: 存在しない (mandatory 相当 — 省略時 erase)
- コード: 省略時 `processAclTableType()` が `bAllAttributesOk=false` → erase (aclorch.cpp:5823)
- minigraph.py: インターフェースリストが空のとき `'CTRLPLANE'` を自動設定 (minigraph.py:1244-1247)
- **コード由来デフォルト: なし (必須フィールド)**

### `stage` フィールド

- YANG default: なし
- C++ struct: `AclTable::stage = ACL_STAGE_INGRESS` (aclorch.h:543 相当、struct メンバ初期値)
- minigraph.py: `stage` を CTRLPLANE ACL にも設定するが、aclorch はこれを無視 (aclorch.cpp:2727)
- `addAclTable()` 内: `type==CTRLPLANE` → 早期 return (SAI テーブル非生成)、stage 参照せず
- **コード由来デフォルト: `INGRESS` (C++ struct 初期値。CTRLPLANE では SAI に送出されず実質無効)**

### `services` フィールド

- YANG: `leaf-list services` (sonic-acl.yang.j2:431-435); CTRLPLANE 時 `mandatory` 相当 (must 制約)
- 実装: `doAclTableTask()` で `attr_name == ACL_TABLE_SERVICES` → `continue` (aclorch.cpp:5410-5413)
  - つまり CONFIG_DB の `services` フィールドは orchagent に完全無視される
- minigraph.py: `services: [aclservice]` を設定 (minigraph.py:1247)
- **コード由来デフォルト: なし (orchagent が読み捨て; 実際の CoPP サービスは COPP_TRAP/COPP_GROUP 経由)**

### `policy_desc` フィールド

- YANG: 任意 string
- minigraph.py: `'policy_desc': aclname` を自動設定 (minigraph.py:1244)
- 直接書き込み: `AclTable::description` が空文字デフォルト (ログ・show のみ)
- **コード由来デフォルト: `<table_name>` (minigraph.py 経由) / `""` (直接書き込み)**

### `ports` フィールド

- YANG: `leaf-list ports` (任意)
- CTRLPLANE ACL: minigraph.py は `ports` を設定しない (acl_intfs が空のため)
- orchagent: `processAclTablePorts()` が呼ばれても CTRLPLANE では無視 (SAI テーブル非生成)
- **コード由来デフォルト: `[]` (空リスト)**

---

## CTRLPLANE ACL 特有の挙動 (orchagent)

1. `AclTable::validate()` — `type==CTRLPLANE` のとき `stage==ACL_STAGE_UNKNOWN` チェックをスキップして即 `return true` (aclorch.cpp:2727-2730)
2. `addAclTable()` — `type==CTRLPLANE` のとき `m_ctrlAclTables` に追加して即 return、SAI テーブル作成なし (aclorch.cpp:4680-4684)
3. `doAclRuleTask()` — `table_oid == SAI_NULL_OBJECT_ID` かつ `m_ctrlAclTables` にキーあり → INFO ログ + erase。ルール無視 (aclorch.cpp:5556-5560)
4. `ACL_TABLE_SERVICES` フィールド — `doAclTableTask()` で `continue` (完全無視) (aclorch.cpp:5410-5413)
5. 実際の CoPP 処理は `COPP_GROUP` / `COPP_TRAP` テーブル → `coppmgr` → APPL_DB → `CoppOrch` の別経路

---

## minigraph.py 由来 CTRLPLANE ACL の生成値

```python
acls[aclname] = {
    'policy_desc': aclname,       # テーブル名をそのまま
    'type': 'CTRLPLANE',          # 固定
    'stage': stage,               # InAcl/OutAcl タグから派生 (orchagent では無視)
    'services': [aclservice]      # XML <Type> 要素から取得 (orchagent では無視)
}
```

複数の XML エントリが同名 ACL に異なるサービスを束ねる場合、`services` に追記される (minigraph.py:1242)。

---

## 検出サマリ

| フィールド | 種別 | 値 | ソース |
|---|---|---|---|
| `type` | 必須、デフォルトなし | — | aclorch.cpp:5823 |
| `stage` | C++ struct 初期値 | `INGRESS` (CTRLPLANE では実質無効) | aclorch.h struct init |
| `policy_desc` | minigraph fallback / 直接書き込み | `<table_name>` / `""` | minigraph.py:1244, AclTable::description |
| `ports` | 省略時空リスト | `[]` | minigraph.py がセットしない |
| `services` | orchagent 読み捨て | — | aclorch.cpp:5410-5413 |

---

## 証跡ファイル

- `sonic-swss/orchagent/aclorch.cpp:2727-2730` (validate CTRLPLANE bypass)
- `sonic-swss/orchagent/aclorch.cpp:4680-4684` (addAclTable CTRLPLANE path)
- `sonic-swss/orchagent/aclorch.cpp:5556-5560` (doAclRuleTask CTRLPLANE skip)
- `sonic-swss/orchagent/aclorch.cpp:5410-5413` (services field ignore)
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:1229-1249` (CTRLPLANE ACL 生成)
