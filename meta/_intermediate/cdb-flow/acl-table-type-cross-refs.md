# ACL_TABLE_TYPE — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/acl-table-type.md`
解析日: 2026-05-17
根拠ソース: `sonic-swss/orchagent/aclorch.cpp` (sha `4305596`)、`sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-acl.yang.j2` (sha `9ea932ec`)

---

## 目的

`ACL_TABLE_TYPE` エントリが CONFIG_DB に書かれたとき、`AclOrch` が **暗黙的に** 参照・依存する
他テーブルのキー / フィールド、および `ACL_TABLE_TYPE` を**参照する側**のテーブルを網羅する。

---

## 1. ACL_TABLE_TYPE が参照する外部テーブル

`doAclTableTypeTask()` (`aclorch.cpp:5738-5772`) および `AclTableTypeParser::parse()` (`aclorch.cpp:752-894`) を全精査した結果:

**ACL_TABLE_TYPE は CONFIG_DB / APPL_DB / STATE_DB / COUNTERS_DB の他テーブルを一切参照しない。**

フィールド値の検証は純粋にメモリ上の C++ 静的ルックアップテーブルのみで行われる:

| フィールド | 検証対象 | 根拠 |
|---|---|---|
| `MATCHES` 各値 | `aclMatchLookup` (C++ static map, L58-96) および `aclRangeTypeLookup` (L97-101) | `parseAclTableTypeMatches()` L796-830 |
| `ACTIONS` 各値 | `aclL3ActionLookup` (L109-121)、`aclMirrorStageLookup` (L122-127)、`aclDTelActionLookup` (L128-136) | `parseAclTableTypeActions()` L831-880 |
| `BIND_POINTS` 各値 | `aclBindPointTypeLookup` (L103-107): `PORT`→`SAI_ACL_BIND_POINT_TYPE_PORT`、`PORTCHANNEL`→`SAI_ACL_BIND_POINT_TYPE_LAG` | `parseAclTableTypeBindPointTypes()` L881-895 |

ただし、全 ACL テーブルに共通の **PortsOrch ゲート** (`gPortsOrch->allPortsReady()`) が
`doTask()` L4276-4279 で適用される。PortsOrch が全 PORT 初期化を完了するまで
`doAclTableTypeTask()` を含む全処理が skip される。

---

## 2. ACL_TABLE_TYPE を参照する（= 逆参照）テーブル

ACL_TABLE_TYPE はメモリマップ `m_AclTableTypes` に格納され、以下の経路から参照される:

| 参照元テーブル | 参照フィールド | 参照方法 | 根拠 |
|---|---|---|---|
| `ACL_TABLE\|<name>` (CONFIG_DB) | `type` フィールド | `getAclTableType(tableTypeName)` null ならば `it++` 待機 (`aclorch.cpp:5432-5436`) | `doAclTableTask()` L5380-5388, 5432-5436 |
| `ACL_TABLE_TABLE\|<name>` (APPL_DB) | `TYPE` フィールド | 同一コードパス (`APP_ACL_TABLE_TABLE_NAME` が同ハンドラへ dispatch) | `aclorch.cpp:4283-4285` |
| YANG `ACL_TABLE.type` | leafref | `/acl:sonic-acl/acl:ACL_TABLE_TYPE/acl:ACL_TABLE_TYPE_LIST/acl:ACL_TABLE_TYPE_NAME` | `sonic-acl.yang.j2:416-418` |

---

## 3. `m_AclTableTypes` への事前登録（組込み型）

orchagent 起動時に `initDefaultTableTypes()` (`aclorch.cpp:3724`) が呼ばれ、
以下の型が CONFIG_DB への書き込みなしにメモリ登録される。これらを `type` に指定する
`ACL_TABLE` は `ACL_TABLE_TYPE` テーブルへの依存が発生しない:

`L3`, `L3V6`, `L3V4V6`, `MIRROR`, `MIRRORV6`, `MIRROR_DSCP`, `PFCWD`, `CTRLPLANE`,
`MCLAG`, `MUX`, `DROP`, `MARK_META`, `MARK_METAV6`, `EGR_SET_DSCP`, `UNDERLAY_SET_DSCP`,
`UNDERLAY_SET_DSCPV6`, `DTEL_FLOW_WATCHLIST`

---

## 4. 書き込み先（副次 DB）

`doAclTableTypeTask()` は CONFIG_DB / APPL_DB / STATE_DB への書き込みを行わない。
`addAclTableType()` は `m_AclTableTypes` メモリマップへの登録のみ。
SAI オブジェクトも作成されない（純粋なソフトウェア定義）。

---

## 5. cross-refs ブロック（最終形）

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`ACL_TABLE_TYPE` の処理 (`doAclTableTypeTask()`, `aclorch.cpp:5738-5772`) は
CONFIG_DB / APPL_DB の他テーブルを**一切参照しない**。フィールド値の検証は C++ 静的ルックアップマップのみで行われ、外部 DB クエリは発生しない。

ただし `AclOrch::doTask()` 冒頭のゲート (`aclorch.cpp:4276-4279`) により、
`gPortsOrch->allPortsReady()` が false の間は `doAclTableTypeTask()` を含む全処理が skip される。

### このテーブルを参照する側

| 参照元テーブル | 参照フィールド | 参照タイミング | evidence |
|---|---|---|---|
| `ACL_TABLE\|*` (CONFIG_DB) の `type` | カスタム型名 | `ACL_TABLE` SET 処理時。`getAclTableType()` が null なら `it++` 待機（無制限） | `aclorch.cpp:5432-5436` |
| `ACL_TABLE_TABLE\|*` (APPL_DB) の `TYPE` | カスタム型名 | 同一コードパス（CONFIG_DB・APPL_DB 共通ハンドラ） | `aclorch.cpp:4283-4285` |
| YANG `ACL_TABLE.type` | leafref | YANG バリデーション時 | `sonic-acl.yang.j2:416-418` |

### 静的ルックアップ（DB テーブルではない）

`MATCHES` / `ACTIONS` / `BIND_POINTS` 値の可否判定は C++ コンパイル時定数マップで行われる:

| フィールド | 使用ルックアップ | evidence |
|---|---|---|
| `MATCHES` | `aclMatchLookup`, `aclRangeTypeLookup` | `aclorch.cpp:803-825` |
| `ACTIONS` | `aclL3ActionLookup`, `aclMirrorStageLookup`, `aclDTelActionLookup` | `aclorch.cpp:838-858` |
| `BIND_POINTS` | `aclBindPointTypeLookup` | `aclorch.cpp:103-107`, `881-895` |

不明な値を含む場合は `AclTableTypeParser::parse()` が `false` を返し、エントリは erase される（retry なし）。

!!! note "SAI オブジェクト非生成"
    `ACL_TABLE_TYPE` の処理では SAI オブジェクトは一切作成されない。`m_AclTableTypes` メモリマップへの格納のみで、orchagent 再起動時に CONFIG_DB から再構築される。
<!-- /cross-refs -->
```
