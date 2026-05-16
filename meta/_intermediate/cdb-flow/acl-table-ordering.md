# ACL_TABLE — Phase B 書込み順依存スキャンノート

対象テーブル: `ACL_TABLE|<table_name>`
Consumer: `AclOrch` (`sonic-swss/orchagent/aclorch.cpp`)
スキャン範囲: `doAclTableTask()` L5346-5518, `doAclTableTypeTask()` L5738-5774, `removeAclTable()` L4829-4910, `doTask()` L4272-4299, `processAclTablePorts()` L5776-5807
Evidence: sonic-swss `orchagent/aclorch.cpp` sha `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード（ポート初期化先行必須）

- `doTask()` L4276-4279: `gPortsOrch->allPortsReady()` が false の間は即 return。
- `ACL_TABLE` / `ACL_TABLE_TYPE` / `ACL_RULE` すべての処理が **完全にブロックされる**。
- PortsOrch（PORT テーブル + PORTCHANNEL テーブルの初期化完了）が ACL_TABLE より先に処理完了していること。
- evidence: `aclorch.cpp:4276`

### 2. ACL_TABLE_TYPE ユーザ定義型が先行必須（ユーザ定義 type 使用時）

- `doAclTableTask()` L5432-5437: `getAclTableType(tableTypeName)` が nullptr を返すと `it++; continue;` でエントリを **保留キューに残す**（erase しない）。
- 組み込み型（`L3`, `MIRROR`, `CTRLPLANE` 等）は `AclOrch` コンストラクタで事前登録済み (`m_AclTableTypes`) のため依存なし。
- **ユーザ定義型**（`ACL_TABLE_TYPE|<name>` で定義するカスタム type）は `doAclTableTypeTask()` が処理を完了してから ACL_TABLE の SET を行わないと、ACL_TABLE エントリが保留キューに積み上がり続ける。
- orchagent のメインループ次回実行で再試行されるため、ほとんどの場合は自動解消されるが、**起動直後の一括 SET では ACL_TABLE_TYPE を ACL_TABLE より先に書き込むこと**。
- evidence: `aclorch.cpp:5432-5437`

**推奨順序（ユーザ定義型の場合）**:
```
SET ACL_TABLE_TYPE|<type_name>  MATCHES=...,ACTIONS=...,BPOINT_TYPES=...
--- その後 ---
SET ACL_TABLE|<table_name>  type=<type_name> ...
```

### 3. PORT / PORTCHANNEL が先行必須（ports フィールド使用時）

- `processAclTablePorts()` L5776-5806: `ports` リスト内の各エイリアスを `gPortsOrch->getPort(alias, port)` で解決する。
- ポートが未登録の場合は `aclTable.pendingPortSet.emplace(alias)` に追加してそのポートをスキップ（**関数は true を返し処理は続行**）。
- `getAclBindPortId()` でポートの OID 変換に失敗した場合のみ `return false`（erase）。
- 未解決のポートは `pendingPortSet` に残り、`onPortReady()` コールバック (`aclorch.cpp:2884-2889`) でポートが ready になった時点で自動バインドされる。
- **結論**: `ports` フィールドに未登録ポートを含めても ACL_TABLE のエントリ自体は作成されるが、**そのポートへのバインドは PORT 登録完了まで遅延**する。
- evidence: `aclorch.cpp:5786-5804`, `aclorch.cpp:2884`

### 4. MIRROR_SESSION が先行必須（type=MIRROR / MIRRORV6 の場合）

- `type=MIRROR` / `MIRRORV6` 時、`addAclTable()` → ASIC capability 確認 (`aclorch.cpp:3502-3541`)。
- 実際の MIRROR セッションへの紐付けは `ACL_RULE|<table>|<rule>` の `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` フィールドで行われる。
- ACL_TABLE 自体の作成には MIRROR_SESSION の事前存在は**不要**だが、ACL_RULE でミラーアクションを指定する際には対象 `MIRROR_SESSION|<name>` が先に存在している必要がある（ACL_RULE のスコープ）。
- evidence: `aclorch.cpp:3502-3541`

### 5. SET 操作内フィールドの処理順序（フィールド間依存なし）

- `doAclTableTask()` L5369-5421: `kfvFieldsValues(t)` をイテレートし `type`, `stage`, `ports`, `services` を処理。
- フィールドの **CONFIG_DB 上の並び順は問わない**（イテレーション順に処理されるが互いに独立）。
- 唯一の制約: `bAllAttributesOk = false` となる条件（`type` 空文字, `stage` 不正値, 不明属性名）が発生すると **`break` で以降のフィールドをスキップして erase**。
- フィールド処理後に `getAclTableType()` が nullptr → `it++; continue`（保留）。その後 `newTable.validate()` に進む。
- evidence: `aclorch.cpp:5365-5495`

### 6. type / stage は作成後変更不可（DEL → SET が必要）

- `doAclTableTask()` L5450-5454: 既存テーブルへの SET 時、`isAclTableTypeUpdated()` または `isAclTableStageUpdated()` が true の場合は `addAclTable()` を呼んで**既存を削除してから再作成**する（DEL + create）。
- `type` / `stage` を変更するには既存 ACL_RULE をすべて先に削除してから ACL_TABLE を DEL→SET する必要がある（`removeAclTable()` 内 `m_AclTables[table_oid].clear()` がルールを削除するため）。
- `ports` フィールドのみ変更する場合は `updateAclTable()` 経由で差分バインド/アンバインドが可能（erase 不要）。
- evidence: `aclorch.cpp:5450-5486`

---

## SET 操作の推奨順序

```
# 1. PortsOrch 初期化完了（orchdaemon が自動管理、明示的操作不要）
# 2. ユーザ定義 type を使う場合のみ先行
SET ACL_TABLE_TYPE|<type_name>  ...

# 3. ACL_TABLE 本体
SET ACL_TABLE|<table_name>  type=<type> stage=<stage> ports=... policy_desc=...

# 4. ACL_RULE は ACL_TABLE 作成後に書き込む
SET ACL_TABLE|<table_name>|<rule_name>  PRIORITY=... PACKET_ACTION=...
```

---

## DEL 操作の安全順序

```
# 1. ACL_RULE を先にすべて削除（orchagent 内部で自動 clear されるが CLI/REST からは明示削除推奨）
DEL ACL_RULE|<table_name>|*

# 2. ACL_TABLE 本体を削除
DEL ACL_TABLE|<table_name>

# 3. ユーザ定義 type を削除する場合は ACL_TABLE DEL の後
DEL ACL_TABLE_TYPE|<type_name>
```

- `removeAclTable()` L4849-4854: `m_AclTables[table_oid].clear()` で配下の ACL_RULE を先にクリアしてから SAI テーブルを削除するため、orchagent 内部では自動クリーンアップされる。
- ただし CONFIG_DB 上の `ACL_RULE|<table>|<rule>` エントリは残るため、orchagent 再起動時に孤立エントリが再処理されて "Wait for ACL table to be created" ループに入る。
- evidence: `aclorch.cpp:4849-4854`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | allPortsReady() 完了 → ACL_TABLE 処理 | 強制先行 | なし（orchdaemon が自動管理） |
| 2 | ACL_TABLE_TYPE SET → ACL_TABLE SET（ユーザ定義 type 使用時） | 論理的先行（保留キューで自動調停） | orchagent が次ループで再試行 |
| 3 | PORT/PORTCHANNEL SET → ACL_TABLE ports バインド | 部分先行（pendingPortSet で自動遅延）| onPortReady() で自動解消 |
| 4 | ACL_TABLE SET → ACL_RULE SET | 必須（ACL_RULE は table_oid == SAI_NULL_OBJECT_ID の間 wait） | 自動 wait loop（ACL_TABLE 作成後に即解消） |
| 5 | type/stage 変更: DEL → SET の順序 | 必須（SET のみでは内部で DEL+create） | SET でも機能するが配下 ACL_RULE が消える |
| 6 | ACL_TABLE DEL → ACL_TABLE_TYPE DEL（ユーザ定義 type 削除時） | 推奨順序（強制ではないが論理的に必要） | DEL 後 type を消しても既存テーブルへの影響なし |
