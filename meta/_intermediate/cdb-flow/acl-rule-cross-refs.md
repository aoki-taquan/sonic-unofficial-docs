# ACL_RULE — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/acl-rule.md` Phase C 追加分。
YANG に leafref 定義がないテーブル（`ACL_RULE` は YANG 未定義）なので、実装上の全参照が「暗黙参照」に相当する。
`sonic-swss/orchagent/aclorch.cpp` を全行精読し、外部テーブル・外部 Orch への依存を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch::doAclRuleTask()` / `AclRulePacket::getRedirectObjectId()` / `AclRuleMirror::activate()` |
| `sonic-swss/orchagent/aclorch.h` | マクロ定数定義 (`MATCH_IN_PORTS`, `ACTION_REDIRECT_ACTION` 等) |
| `sonic-utilities/acl_loader/main.py` | acl-loader の POLICER 読み取り (`read_policers_info()`) |

## YANG leafref

`ACL_RULE` は YANG 未定義テーブルのため leafref は存在しない。全参照が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. PORT テーブル (IN_PORTS / OUT_PORT / OUT_PORTS matchfield)

- **参照先テーブル**: `PORT`
- **参照方向**: 読み取り（OID 解決）
- **条件**: match フィールド `IN_PORTS` / `OUT_PORT` / `OUT_PORTS` にポート名が指定されたとき
- **参照元**: `aclorch.cpp` L961–1034 (`MATCH_IN_PORTS` / `MATCH_OUT_PORT` / `MATCH_OUT_PORTS` の処理ブロック), `gPortsOrch->getPort(alias, port)` 呼び出し
- **意味**: カンマ区切りポート名リストを `PortsOrch::getPort()` で解決し、SAI port OID を取得する。物理ポート (`Port::PHY`) および LAG (`Port::LAG`) のみ受理。それ以外の型（VLAN 等）は `return false` → rule INACTIVE。PORT テーブルにエントリが存在しない場合も `return false` → rule INACTIVE。
- **ブロッキング依存**: `AclOrch::doTask()` は `allPortsReady()` が false の間、全 ACL_RULE 処理をブロックする (`aclorch.cpp:4276`)。PortsOrch の初期化完了が先行必須。

### 2. PORT テーブル (REDIRECT_ACTION — port 先)

- **参照先テーブル**: `PORT`
- **参照方向**: 読み取り（OID 解決）
- **条件**: `REDIRECT_ACTION` フィールドの値がポート名（またはLAG名）と一致するとき
- **参照元**: `aclorch.cpp` L2085–2099 (`getRedirectObjectId()` の第1解決ステップ)
- **意味**: redirect 先として物理ポート (`m_port_id`) または LAG (`m_lag_id`) の OID を取得する。それ以外の Port::Type は `"Wrong port type for REDIRECT action"` ERROR + `SAI_NULL_OBJECT_ID` → rule INACTIVE。

### 3. MIRROR_SESSION テーブル (MIRROR_*_ACTION)

- **参照先テーブル**: `MIRROR_SESSION`
- **参照方向**: 存在確認 + OID 取得 + refcount 管理
- **条件**: action フィールド `MIRROR_ACTION` / `MIRROR_INGRESS_ACTION` / `MIRROR_EGRESS_ACTION` が設定されているとき（`AclRuleMirror` サブクラスが処理）
- **参照元**: `aclorch.cpp` L2331 (`m_pMirrorOrch->sessionExists()`), L2337 (`getSessionStatus()`), L2347 (`getSessionOid()`), L2376 (`increaseRefCount()`), L2401 (`decreaseRefCount()`)
- **意味**:
  - `sessionExists()` が false → `SWSS_LOG_ERROR` + `return false` → rule INACTIVE。ただし MIRROR_SESSION が後から追加されると `MirrorSessionUpdate` イベント経由で遅延 install される（`aclorch.cpp:2426`）。
  - セッションが存在しても `state=false`（inactive）なら SAI entry を作成せずに `return true`（待機）。SESSION が active 化されると `onUpdate()` 経由で install。
  - active セッションの場合: OID を取得して SAI `aclaction.parameter.objlist.list` に設定後 `create_acl_entry()`。refcount を増加させ、ルール削除時に `decreaseRefCount()`。

### 4. NEIGH / ROUTE テーブル (REDIRECT_ACTION — next-hop 先)

- **参照先テーブル**: `NEIGH`（`NeighOrch` 管理）、`ROUTE_TABLE`（`RouteOrch` 管理）
- **参照方向**: OID 解決 + refcount 管理
- **条件**: `REDIRECT_ACTION` フィールドの値が IP アドレス（+インタフェース名）形式または next-hop group 形式のとき
- **参照元**: `aclorch.cpp` L2102–2165 (`getRedirectObjectId()` の第2・第4解決ステップ)
- **意味**:
  - `NextHopKey(target)` が `NeighOrch::hasNextHop()` に存在 → `getNextHopId()` で OID 取得 + `increaseNextHopRefCount()`。存在しなければ次の解決ステップへ。
  - `NextHopGroupKey(target)` が `RouteOrch::hasNextHopGroup()` に不在 → `RouteOrch::addNextHopGroup()` を呼んで自動生成（失敗なら `SAI_NULL_OBJECT_ID` → rule INACTIVE）。存在または生成成功 → `getNextHopGroupId()` + `increaseNextHopRefCount()`。
  - ルール削除時: `decreaseNextHopRefCount()` / `RouteOrch::increaseNextHopRefCount()` を対称的に呼ぶ (`aclorch.cpp:1369–1391`)。
- **注意**: next-hop が解決されない間は rule INACTIVE のまま待機（再試行機構はない。NH が後から解決されても自動再試行なし）。

### 5. TUNNEL next-hop (REDIRECT_ACTION — トンネル先)

- **参照先**: `TunnelNhop` OID (VxLAN/NVGRE Tunnel Orch が管理)
- **参照方向**: OID 解決
- **条件**: `REDIRECT_ACTION` 値がトンネル next-hop 形式のとき（第3解決ステップ）
- **参照元**: `aclorch.cpp` L2118–2136 (`m_redirect_target_tun_nh.load(target)`)
- **意味**: `TunnelNhop::load()` が OID を返せば redirect target として使用。失敗（`logic_error`）は無視して次ステップへ。`runtime_error` は ERROR ログ + `SAI_NULL_OBJECT_ID`。

### 6. ACL_TABLE テーブル (key の table_name 参照)

- **参照先テーブル**: `ACL_TABLE`
- **参照方向**: 存在確認（SAI OID 取得）
- **条件**: 常時（全 ACL_RULE 処理で必須）
- **参照元**: `aclorch.cpp` L5520–5565 (`doAclRuleTask()` の冒頭ガード)
- **意味**: `ACL_RULE|<table_name>|<rule_name>` の `<table_name>` が `ACL_TABLE` として SAI 作成済みでないと `it++`（再試行）。テーブル作成後に自動再処理される。コントロールプレーンテーブル (`m_ctrlAclTables`) に存在する場合は INFO + erase。

### 7. POLICER テーブル (acl_loader の参照)

- **参照先テーブル**: `POLICER`
- **参照方向**: 読み取り（表示用）
- **条件**: `aclshow` コマンドで policer 情報を表示するとき
- **参照元**: `acl_loader/main.py` L254–266 (`read_policers_info()`), L1018, L1022, L1041 (`show_policer()`)
- **意味**: `aclshow` の出力に policer 名と設定を表示するために `POLICER` テーブルを読む。`AclOrch` (orchagent) は `ACL_RULE` のフィールドとして policer を参照しない（`aclorch.cpp` に POLICER 参照なし）。COPP 系 (`CoppOrch`) は policer を使うが ACL_RULE とは別経路。
- **制限**: 標準 `ACL_RULE` からの policer 適用は現状 P4 orch (`p4orch/acl_util.cpp`) 経由のみ。`aclorch.cpp` ベースの ACL_RULE には policer action フィールドなし。

## 参照関係サマリ

```
ACL_RULE
  ├─ [暗黙] PORT.name                    (IN_PORTS/OUT_PORT/OUT_PORTS matchfield — OID 解決)
  ├─ [暗黙] PORT.name / LAG.name         (REDIRECT_ACTION redirect 先 — OID 解決)
  ├─ [暗黙] MIRROR_SESSION.name          (MIRROR_*_ACTION — 存在確認+OID+refcount)
  ├─ [暗黙] NEIGH (NeighOrch)            (REDIRECT_ACTION next-hop — OID+refcount)
  ├─ [暗黙] ROUTE_TABLE (RouteOrch)      (REDIRECT_ACTION next-hop group — OID+refcount)
  ├─ [暗黙] TunnelNhop (TunnelOrch)      (REDIRECT_ACTION tunnel next-hop — OID)
  ├─ [暗黙] ACL_TABLE.name               (key の table_name — SAI OID 解決、必須依存)
  └─ [acl_loader のみ] POLICER           (aclshow 表示用読み取り。orchagent は ACL_RULE から policer を参照しない)
```

## evidence

- `aclorch.cpp`: L961–1034 (IN_PORTS/OUT_PORT/OUT_PORTS OID 解決), L2078–2165 (`getRedirectObjectId()` 全解決ステップ), L2295–2384 (`AclRuleMirror::activate()`), L4276 (`allPortsReady()` ブロック), L5520–5565 (`doAclRuleTask()` ガード群)
- `acl_loader/main.py`: L85 (`POLICER = "POLICER"`), L254–266 (`read_policers_info()`), L1018–1041 (`show_policer()`)
- `aclorch.h`: L60–62 (`MATCH_IN_PORTS`, `MATCH_OUT_PORT`, `MATCH_OUT_PORTS`), L112 (`ACTION_REDIRECT_ACTION`)
