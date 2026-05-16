# APPL_DB ACL テーブル群 — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/appl-acl.md`
解析日: 2026-05-15
根拠ソース: `sonic-swss/orchagent/aclorch.cpp` (sha `4305596`)、`sonic-swss/orchagent/aclorch.h`、`sonic-swss-common/common/schema.h` (sha `158de8d3`)

---

## 目的

APPL_DB の `ACL_TABLE_TABLE` / `ACL_TABLE_TYPE_TABLE` / `ACL_RULE_TABLE` エントリが
書き込まれたとき、`AclOrch::doTask()` (`aclorch.cpp:4272-4299`) が **APPL_DB / CONFIG_DB
共通のハンドラ** (`doAclTableTask` / `doAclTableTypeTask` / `doAclRuleTask`) へ
ディスパッチする結果、暗黙的に参照・依存する他テーブル / リソースを網羅する。

APPL_DB 3 テーブルはいずれも `sonic-yang-models` に YANG モジュールが存在せず、
**全参照が「暗黙 leafref」相当**となる。

---

## 1. PORT テーブル (ACL_TABLE_TABLE.PORTS — 暗黙 leafref)

### 参照箇所

- `processAclTablePorts(string portList, AclTable &aclTable)` — `aclorch.cpp:5776-5807`
  ```cpp
  if (!gPortsOrch->getPort(alias, port))
  {
      aclTable.pendingPortSet.emplace(alias);
      continue;
  }
  ```
- `getAclBindPortId(Port &port, sai_object_id_t &port_id)` — `aclorch.cpp:6056-6083`

### APPL_DB での発火条件

- `vnetorch.cpp:3795` — `ACL_TABLE_PORTS` に `ports_str`（VnetTunnel が選んだ物理ポート列）
- `mclaglink.cpp:329` — `ACL_TABLE_PORTS` に `isolate_src_port`（MCLAG isolation 対象ポート）
- `dashenifwdorch.cpp:637` — DASH ENI fwd 用 ACL のポート列

### 依存内容

| 書き込み元 | 参照先テーブル | 参照先キー | バインド種別 |
|---|---|---|---|
| `vnetorch` / `dashenifwdorch` | `PORT` | `PORT\|EthernetN` | `SAI_ACL_BIND_POINT_TYPE_PORT` |
| `mclagsyncd` | `PORT` | `PORT\|EthernetN` | `SAI_ACL_BIND_POINT_TYPE_PORT` |

### 特記事項

- PortsOrch が未登録の場合は `pendingPortSet` に積み、PortsOrch の
  `SUBJECT_TYPE_PORT_CHANGE` 通知受信後に再バインドを試みる (`aclorch.cpp:2884-2904`)。
- ブロッキング依存: `AclOrch::doTask()` は `allPortsReady()` が false の間、
  APPL_DB エントリの処理を **早期 return** で保留する (`aclorch.cpp:4276-4279`)。

---

## 2. PORTCHANNEL テーブル (LAG — 暗黙 leafref)

### 参照箇所

`getAclBindPortId()` — `aclorch.cpp:6073`:
```cpp
case Port::LAG:
    port_id = port.m_lag_id;
    break;
```
`aclBindPointTypeLookup` — `aclorch.cpp:103-107` (`PORTCHANNEL` → `SAI_ACL_BIND_POINT_TYPE_LAG`)

### APPL_DB での発火条件

`vnetorch` / `dashenifwdorch` が `ACL_TABLE_PORTS` に `PortChannelN` を含めると `Port::LAG` で解決される。
`mclagsyncd` は通常物理ポート前提だが、`isolate_src_port` に LAG 名を渡すと同経路。

| 書き込み元 | 参照先テーブル | 参照先キー | バインド種別 |
|---|---|---|---|
| 全書込み元（必要時） | `PORTCHANNEL` | `PORTCHANNEL\|PortChannelN` | `SAI_ACL_BIND_POINT_TYPE_LAG` |

---

## 3. ACL_TABLE_TYPE_TABLE (ユーザ定義 type 参照)

### 参照箇所

`doAclTableTask()` — `aclorch.cpp:5380-5388, 5432`:
```cpp
auto tableType = getAclTableType(tableTypeName);
```
ユーザ定義型は `m_AclTableTypeMap` から検索される。事前定義型 (`L3`/`L3V6`/`MIRROR`/`MIRRORV6`/`CTRLPLANE` 等)
は初期登録済みのため `ACL_TABLE_TYPE_TABLE` を引かない。

### APPL_DB での発火条件

- `vnetorch.cpp:3780` — `VNET_TUNNEL_TERM_ACL_TABLE_TYPE`（カスタム型）を `ACL_TABLE_TYPE_TABLE` に書き込み、
  続けて `ACL_TABLE_TABLE.TYPE` 値として参照する。
- `dashenifwdorch.cpp:619-643` — ENI fwd 用カスタム型も同様。
- `mclagsyncd` は事前定義 `L3` 型のみ使うため発火しない。

| 書き込み元 | 参照先テーブル | 参照先キー |
|---|---|---|
| `vnetorch` / `dashenifwdorch` | `ACL_TABLE_TYPE_TABLE` (APPL_DB) | `ACL_TABLE_TYPE_TABLE\|<type>` |

### 順序依存

カスタム型を使う場合は `ACL_TABLE_TYPE_TABLE\|<type>` が AclOrch で処理済み
(= `m_AclTableTypeMap` 登録済み) でないと `ACL_TABLE_TABLE` 側は pending 状態に留まる
(`aclorch.cpp:5432-5437`)。

---

## 4. ACL_TABLE_TABLE (ACL_RULE_TABLE → 親 table の参照、暗黙必須)

### 参照箇所

`doAclRuleTask()` — `aclorch.cpp:5548-5566`:
```cpp
sai_object_id_t table_oid = getTableById(table_id);
if (table_oid == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_INFO("Wait for ACL table %s to be created", table_id.c_str());
    it++;
    continue;
}
```

### APPL_DB での発火条件

常時。`ACL_RULE_TABLE|<table>|<rule>` の `<table>` 部分は `ACL_TABLE_TABLE|<table>` または
CONFIG_DB の `ACL_TABLE|<table>` のいずれかで SAI 作成済みであることが必須。
未作成なら `it++` で **無限ポーリング再試行** される。

| 書き込み元 | 参照先テーブル | 参照先キー |
|---|---|---|
| `vnetorch` / `mclagsyncd` | `ACL_TABLE_TABLE` (APPL_DB) | `ACL_TABLE_TABLE\|<table_name>` |

---

## 5. MIRROR_SESSION テーブル (MIRROR_*_ACTION)

### 参照箇所

`AclRuleMirror::validateAddAction()` / `activate()` — `aclorch.cpp:2295-2401`:
- `m_pMirrorOrch->sessionExists()` (L2331)
- `getSessionStatus()` (L2337)
- `getSessionOid()` (L2347)
- `increaseRefCount()` / `decreaseRefCount()` (L2376 / L2401)

### APPL_DB での発火条件

現状の APPL_DB 書込み元 (`vnetorch` / `mclagsyncd` / `dashenifwdorch`) は **MIRROR action を使用しない**:

- `vnetorch` は `ACTION_REDIRECT_ACTION` のみ
- `mclagsyncd` は `PACKET_ACTION=DROP` のみ
- `dashenifwdorch` は REDIRECT 系のみ

したがって本参照は APPL_DB 経由では実際には**発火しない**が、CLI 等で APPL_DB に
直接 MIRROR_ACTION を書き込んだ場合は同ハンドラを経由するため記載する。

| 書き込み元 | 参照先テーブル | 参照方向 |
|---|---|---|
| (現状の書込み元では発火なし) | `MIRROR_SESSION` | 存在確認 + OID + refcount |

---

## 6. NEIGH / ROUTE_TABLE / TunnelNhop (REDIRECT_ACTION)

### 参照箇所

`getRedirectObjectId()` — `aclorch.cpp:2078-2165`:

1. PortsOrch — `gPortsOrch->getPort(target, port)` (L2085) → PORT/LAG OID
2. NeighOrch — `m_pAclOrch->m_neighOrch->hasNextHop(...)` (L2102-2116) → next-hop OID + refcount
3. TunnelOrch — `m_redirect_target_tun_nh.load(target)` (L2118-2136) → トンネル next-hop OID
4. RouteOrch — `m_pAclOrch->m_routeOrch->hasNextHopGroup(...)` / `addNextHopGroup()` (L2138-2157) → NHG OID + refcount

### APPL_DB での発火条件

- `vnetorch.cpp:3829` — `ACTION_REDIRECT_ACTION` に `nh_ip.to_string()`（VIP 経由の next-hop IP）を書き込み、
  通常は **NEIGH 経由** で OID 解決される。
- `dashenifwdorch` — ENI fwd 用 REDIRECT 値（PORT/LAG/NEIGH のいずれか）が条件次第で全 4 段経由。
- `mclagsyncd` は `PACKET_ACTION=DROP` のため発火しない。

| 書き込み元 | 参照先 | 参照方向 |
|---|---|---|
| `vnetorch` / `dashenifwdorch` | `NEIGH` (NeighOrch) | OID + refcount |
| `dashenifwdorch` (NHG 形式時) | `ROUTE_TABLE` (RouteOrch) | OID + refcount、不在時自動生成 |
| `dashenifwdorch` (Tunnel 形式時) | TunnelNhop (TunnelOrch) | OID 解決 |

### 特記事項

- 解決順序は PortsOrch → NeighOrch → TunnelOrch → RouteOrch の固定順。
- いずれも失敗すると `SAI_NULL_OBJECT_ID` → rule INACTIVE。
- next-hop が後から解決されても自動再試行はない (rule 自体の再書き込みが必要)。

---

## 7. COUNTERS_DB / FLEX_COUNTER_DB (ACL_RULE_TABLE 統計、書き込み先)

### 参照箇所

- `AclOrch::m_countersDb` / `m_countersTable` — `aclorch.cpp:25-26`
  ```cpp
  swss::DBConnector AclOrch::m_countersDb("COUNTERS_DB", 0);
  swss::Table AclOrch::m_countersTable(&m_countersDb, "COUNTERS");
  ```
- `registerFlexCounter()` — `aclorch.cpp:6020-6044`
  ```cpp
  m_countersDb.hset(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier, counterOidStr);
  ```
  ※ `COUNTERS_ACL_COUNTER_RULE_MAP = "ACL_COUNTER_RULE_MAP"` (`aclorch.cpp:45`)
- `deregisterFlexCounter()` — `aclorch.cpp:6044-6051` — 削除時 `hdel`
- ポーリング間隔: `ACL_COUNTER_DEFAULT_POLLING_INTERVAL_MS = 10000` (`aclorch.cpp:47`)

### APPL_DB での発火条件

`ACL_RULE_TABLE` (APPL_DB) → `AclRule` に対し `m_createCounter == true`（カウンタ自動付与の既定）の場合、
SAI ACL counter が生成され COUNTERS_DB の `ACL_COUNTER_RULE_MAP` に `(table:rule, counterOid)` ペアが
登録される。FLEX_COUNTER_DB 側ポーラが当該 OID をポーリングして `COUNTERS:<oid>` に統計を書き込む。

| 操作 | 参照先 (書き込み) | キー / フィールド |
|---|---|---|
| ACL_RULE_TABLE SET → counter 登録 | `COUNTERS_DB` | `ACL_COUNTER_RULE_MAP` HSET (`<table>:<rule>` → `oid:0x...`) |
| ACL_RULE_TABLE DEL → counter 解除 | `COUNTERS_DB` | `ACL_COUNTER_RULE_MAP` HDEL |
| FLEX counter ポーリング | `FLEX_COUNTER_DB` | ACL counter group / `COUNTERS:<oid>` |

### 特記事項

これらは ACL_RULE_TABLE が**参照する**のではなく ACL_RULE_TABLE 処理が**書き込む**先のため、
厳密には side-effects / runtime-trace に近いが、APPL_DB エントリのライフサイクルと
強く結びついた暗黙依存として cross-refs にも明記する。

---

## 8. STATE_DB / CRM 側依存 (書き込み先)

| 書き込み先 | 目的 | 証跡 |
|---|---|---|
| `STATE_DB / ACL_TABLE` | 作成/削除時の status (`Active`/`Inactive`/`Pending creation`/`Pending removal`) | `aclorch.cpp:6088-6093` |
| `CRM_ACL_TABLE` / `CRM_ACL_ENTRY` カウンタ | ASIC リソース残量管理 | `aclorch.cpp:1361, 1434, 2855, 4877` |

側面挙動。Phase F (side-effects) で扱う。

---

## 参照関係サマリ

```
APPL_DB ACL_TABLE_TABLE
  ├─ [暗黙] PORT.name                     (PORTS — getPort/OID 解決、unready は pendingPortSet)
  ├─ [暗黙] PORTCHANNEL.name              (PORTS の LAG — Port::LAG)
  ├─ [暗黙] ACL_TABLE_TYPE_TABLE.name     (TYPE がカスタム型のとき、必須先行)
  └─ [side] STATE_DB.ACL_TABLE / CRM      (書き込み)

APPL_DB ACL_TABLE_TYPE_TABLE
  └─ (他テーブル参照なし。AclTableType 定義のみ)

APPL_DB ACL_RULE_TABLE
  ├─ [暗黙] ACL_TABLE_TABLE / CFG_ACL_TABLE   (table_name — SAI OID 必須、未作成時 it++)
  ├─ [暗黙] PORT.name / PORTCHANNEL.name      (IN_PORTS/OUT_PORTS/REDIRECT_ACTION 経由)
  ├─ [暗黙] NEIGH (NeighOrch)                 (REDIRECT_ACTION = next-hop IP)
  ├─ [暗黙] ROUTE_TABLE (RouteOrch)           (REDIRECT_ACTION = next-hop group)
  ├─ [暗黙] TunnelNhop (TunnelOrch)           (REDIRECT_ACTION = tunnel next-hop)
  ├─ [暗黙/未発火] MIRROR_SESSION             (MIRROR_*_ACTION — 現書込み元では未使用)
  └─ [side] COUNTERS_DB.ACL_COUNTER_RULE_MAP  (rule 統計 OID 登録)
            FLEX_COUNTER_DB                    (ACL counter group ポーリング)
            STATE_DB.ACL_TABLE / CRM_ACL_ENTRY (status / リソース)
```

## evidence

- `aclorch.cpp`: L25-26 (`m_countersDb` / `m_countersTable`), L45-47 (`COUNTERS_ACL_COUNTER_RULE_MAP`), L961-1034 (match 系 PORT OID 解決), L2078-2165 (`getRedirectObjectId()` 全解決ステップ), L2295-2401 (`AclRuleMirror`), L4272-4299 (`doTask()` ディスパッチ), L4276 (`allPortsReady()` ガード), L5380-5437 (`doAclTableTask()` type lookup), L5548-5566 (`doAclRuleTask()` 親テーブルガード), L5776-5807 (`processAclTablePorts()`), L6020-6051 (`registerFlexCounter` / `deregisterFlexCounter`), L6056-6083 (`getAclBindPortId()`)
- `aclorch.h`: L60-62 (`MATCH_IN_PORTS` / `MATCH_OUT_PORT` / `MATCH_OUT_PORTS`), L112 (`ACTION_REDIRECT_ACTION`), L543 (`acl_stage_type_t stage = ACL_STAGE_INGRESS`)
- 書込み元: `vnetorch.cpp` L3775-3837 / `mclaglink.cpp` L325-373 / `dashenifwdorch.cpp` L619-643
- スキーマ定数: `sonic-swss-common/common/schema.h` L94-96 (`APP_ACL_TABLE_TABLE_NAME` / `APP_ACL_TABLE_TYPE_TABLE_NAME` / `APP_ACL_RULE_TABLE_NAME`)
