# APPL_DB ACL テーブル群 — Phase B 書込み順依存スキャンノート

対象テーブル: `APP_ACL_TABLE_TABLE` / `APP_ACL_TABLE_TYPE_TABLE` / `APP_ACL_RULE_TABLE`
Consumer: `AclOrch::doTask()` → `doAclTableTask()` / `doAclRuleTask()` / `doAclTableTypeTask()` (`sonic-swss/orchagent/aclorch.cpp`)
スキャン範囲: L4272-4299 (doTask dispatch), L5520-5736 (rule task), L4215-4222 (retry cache init), L2697-2710 (pendingPortSet), 関連サブルーチン参照

---

## 検出した順序依存・タイミング依存

### 1. PortsOrch readiness ガード（ポート初期化先行必須）

- `doTask()` L4276-4279: `gPortsOrch->allPortsReady()` が false の間は即 return。
- CONFIG_DB / APPL_DB 双方の ACL_TABLE / ACL_TABLE_TYPE / ACL_RULE すべてが同一 `doTask` でブロックされる。
- vnetorch / mclagsyncd / dashenifwdorch が早期に APPL_DB へ書き込んでも、PortsOrch が `allPortsReady()` を true にするまで処理は保留される。
- evidence: `aclorch.cpp:4276`

### 2. ACL_TABLE_TABLE 先行ガード（APPL_DB ACL_RULE_TABLE の SET）

- `doAclRuleTask()` は CONFIG_DB / APPL_DB 双方を扱う統一ハンドラで、テーブル名で分岐しない (`doTask()` L4287-4290: `CFG_ACL_RULE_TABLE_NAME || APP_ACL_RULE_TABLE_NAME` 共に同じ関数へ dispatch)。
- L5548-5566: `getTableById(table_id)` が `SAI_NULL_OBJECT_ID` を返す場合、コントロールプレーンテーブルは erase、それ以外は `it++` で待機ループに入り、ACL_TABLE 側で SAI OID が割り当てられるまで毎ループ再試行される。
- APPL_DB の `ACL_RULE_TABLE|<table>|<rule>` が先に届いても、対応する `ACL_TABLE_TABLE|<table>` が AclOrch で処理 (SAI 作成) されるまで rule は install されない。
- vnetorch / mclagsyncd / dashenifwdorch の書込み側コードはいずれも `ACL_TABLE_TABLE` → `ACL_RULE_TABLE` の順で `set()` するが、APPL_DB の Producer/Consumer は順序保証しないため、orchagent 側の待機ループでこの依存が解消される。
- evidence: `aclorch.cpp:4287-4290`, `aclorch.cpp:5548-5566`

### 3. ACL_TABLE_TYPE_TABLE 先行ガード（カスタム TYPE 使用時）

- `doAclTableTask()` L5432: `getAclTableType(tableTypeName)` がカスタム型 (e.g. `VNET_TUNNEL_TERM_ACL_TABLE_TYPE`) を返さなければ ACL_TABLE は pending 状態になる。
- vnetorch は `acl_table_type_->set(...)` (vnetorch.cpp:3781) → `acl_table_->set(...)` (vnetorch.cpp:3797) の順で書くが、APPL_DB Consumer 側でも `doAclTableTypeTask()` 完了が必要。
- evidence: `aclorch.cpp:5432`, `aclorch.cpp:4291-4293`

### 4. PortsOrch.getPort() readiness（PORTS フィールド処理）

- `doAclTableTask()` から呼ばれる L5786-5790: 未 ready の port は `pendingPortSet` に積まれ、後続の `update(SUBJECT_TYPE_PORT_CHANGE)` (L4243-4247) が PortsOrch から通知された時点で再評価される (L2884-2904)。
- APPL_DB 側書込み元 (vnetorch の `ports_str`, mclagsyncd の `isolate_src_port`, dashenifwdorch) が指定するポートが PortsOrch に未登録なら、テーブル本体は SAI 作成されつつ未 ready port のみ pending キューに残る。
- ポート登録完了通知 → `AclTable::onUpdate()` で逐次バインド。
- evidence: `aclorch.cpp:2697-2710`, `aclorch.cpp:2884-2904`, `aclorch.cpp:5786-5790`

### 5. Retry cache 経路（SAI resource 枯渇時）

- `AclOrch::AclOrch()` L4220-4222: コンストラクタで `createRetryCache(CFG_ACL_RULE_TABLE_NAME)` と `createRetryCache(APP_ACL_RULE_TABLE_NAME)` を両方初期化。**APPL_DB の ACL_RULE_TABLE も CONFIG_DB と同等の retry cache を持つ**。
- L5673-5693: `addAclRule()` が SAI resource full (`isSaiStatusResourceFull`) で失敗した場合、`make_constraint(RETRY_CST_SAI_RESOURCE, table_id)` で park し `PENDING_CREATION` ステータスを記録、`addToRetry()` で retry cache へ移送。
- L5716-5721: 任意の rule DEL が成功し ASIC リソースが実際に解放された場合、`notifyRetry(this, consumer.getTableName(), make_constraint(RETRY_CST_SAI_RESOURCE, table_id))` で同テーブルの retry cache を起こす。
- 重要: `notifyRetry` の第 2 引数に `consumer.getTableName()` が渡されるため、**CONFIG_DB の DEL は CONFIG_DB の retry を、APPL_DB の DEL は APPL_DB の retry を**起こす。CONFIG_DB / APPL_DB の retry cache は独立。
- evidence: `aclorch.cpp:4220-4222`, `aclorch.cpp:5673-5693`, `aclorch.cpp:5716-5721`

### 6. SET → DEL 順序（MIRROR rule 更新）

- 既存 rule の SET 時 MIRROR rule は `AclRule::update()` 未実装で `return false`。
- APPL_DB 経由でも同じハンドラを通るため、MIRROR rule の内容変更は `DEL → SET` 必須。
- evidence: `aclorch.cpp:1466`, `aclorch.cpp:2415-2420`

---

## まとめ（APPL_DB 側で特有 / 共通する依存）

| 依存 | CONFIG_DB / APPL_DB | 解消メカニズム |
|---|---|---|
| PortsOrch readiness | 共通 | `doTask` の早期 return → 後続の event loop で再投入 |
| ACL_TABLE → ACL_RULE | 共通（同一ハンドラ） | `doAclRuleTask` 内 `it++` 待機ループ |
| ACL_TABLE_TYPE → ACL_TABLE | 共通 | `doAclTableTask` 内 type lookup 失敗で pending |
| PORTS の port readiness | 共通 | `pendingPortSet` + `SUBJECT_TYPE_PORT_CHANGE` 通知 |
| SAI resource full retry | 個別 (CFG / APP 独立) | `createRetryCache` x2、`notifyRetry` は consumer 名で限定 |
| MIRROR rule 更新 | 共通 | DEL → SET 必須 |
