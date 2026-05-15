---
title: APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT)
description: "APPL_DB FIXED_MIRROR_SESSION_TABLE — P4RT ランタイムが書き込む ERSPAN ミラーセッション定義テーブル。MirrorSessionManager が APPL_DB を購読し SAI MIRROR_SESSION オブジェクトに変換する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/p4orch/mirror_session_manager.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/p4orch/mirror_session_manager.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/p4orch/p4orch_util.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/mirrororch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/p4orch/acl_rule_manager.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - MIRROR_SESSION
  appl_db:
    - FIXED_MIRROR_SESSION_TABLE
---

# APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT)

## 概要

`APPL_DB FIXED_MIRROR_SESSION_TABLE` は [P4RT](../../reference/glossary.md#term-p4rt) ランタイムが書き込む ERSPAN ミラーセッション定義テーブル。
`p4orch` 内の `MirrorSessionManager` が [APPL_DB](../../reference/glossary.md#term-appl_db) を購読し、[SAI](../../reference/glossary.md#term-sai) MIRROR_SESSION オブジェクトに変換する[^1]。

通常の CONFIG_DB `MIRROR_SESSION` テーブルとは独立したパスであり、P4RT 経由のプログラムにのみ利用される。
セッションタイプは常に **ERSPAN (Enhanced Remote SPAN)** に固定され、GRE トンネルパラメータをすべて明示的に指定する必要がある。

## key 構造

```text
FIXED_MIRROR_SESSION_TABLE|{"match/mirror_session_id":"<id>"}
```

key は JSON 形式でエンコードされる。`<id>` は P4RT テーブルのマッチフィールド `mirror_session_id` の値。

## 主要フィールド

| フィールド | 型 | 必須 | 既定 | 説明 |
|-----------|----|------|------|------|
| `action` | string `mirror_as_ipv4_erspan` | yes | - | アクション識別子。固定値のみ受け付ける |
| `param/port` | string (物理ポート名) | yes | - | ミラーパケット送出先の物理ポート |
| `param/src_ip` | ip-address | yes | - | ERSPAN 外側 IP のソース |
| `param/dst_ip` | ip-address | yes | - | ERSPAN 外側 IP の宛先 |
| `param/src_mac` | mac-address | yes | - | ERSPAN 外側イーサネットの送信元 MAC |
| `param/dst_mac` | mac-address | yes | - | ERSPAN 外側イーサネットの宛先 MAC |
| `param/ttl` | hex uint8 | yes | - | ERSPAN 外側 IP の TTL (16 進数文字列) |
| `param/tos` | hex uint8 | yes | - | ERSPAN 外側 IP の TOS (DSCP+ECN, 16 進数文字列) |

全フィールドが必須。1 つでも欠けると `processAddRequest()` が `SWSS_RC_INVALID_PARAM` を返しセッションは作成されない[^2]。

## 制約

- `param/port` は物理ポート (`Port::Type::PHY`) のみ有効。VLAN / PortChannel は拒否される[^3]。
- `action` は `mirror_as_ipv4_erspan` のみ有効。他の値は `SWSS_RC_INVALID_PARAM`[^4]。
- APPL_DB のキー形式は JSON エンコード。パース失敗時は `SWSS_RC_INVALID_PARAM`[^4]。
- 更新時は個別フィールドを部分的に送信できる (`has_*` フラグで管理)。

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

<!-- evidence: sonic-swss/orchagent/p4orch/mirror_session_manager.h L20-21 / mirror_session_manager.cpp prepareSaiAttrs() L120-187 / p4orch_util.h P4MirrorSessionAppDbEntry struct L253-279 -->

| フィールド | APP_DB デフォルト | C++ 実装デフォルト | 種別 | 備考 |
|-----------|-----------------|-------------------|------|------|
| `param/ttl` | **なし (必須)** | `uint8_t ttl = 0` (struct 初期値) | 必須フィールド — デフォルト無効 | `has_ttl=false` のまま ADD 操作を行うと `SWSS_RC_INVALID_PARAM` |
| `param/tos` | **なし (必須)** | `uint8_t tos = 0` (struct 初期値) | 必須フィールド — デフォルト無効 | `has_tos=false` のまま ADD 操作を行うと `SWSS_RC_INVALID_PARAM` |
| `SAI_MIRROR_SESSION_ATTR_IPHDR_VERSION` | (APP_DB フィールドなし) | **`4`** (IPv4 固定) | ハードコード | `MIRROR_SESSION_DEFAULT_IP_HDR_VER = 4` (`mirror_session_manager.h:20`) — IPv6 ヘッダ非対応 |
| `SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE` | (APP_DB フィールドなし) | **`0x88be`** | ハードコード | `GRE_PROTOCOL_ERSPAN = 0x88be` (`mirror_session_manager.h:21`) — 変更不可 |
| `SAI_MIRROR_SESSION_ATTR_TYPE` | (APP_DB フィールドなし) | **`SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE`** | ハードコード | セッションタイプは ERSPAN 固定。SPAN は不可 |
| `SAI_MIRROR_SESSION_ATTR_ERSPAN_ENCAPSULATION_TYPE` | (APP_DB フィールドなし) | **`SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL`** | ハードコード | L3 GRE トンネルカプセル化固定 |

### 主要な discrepancy 詳細

**IP ヘッダバージョン固定 = 4 — IPv6 ERSPAN 非対応**:
`prepareSaiAttrs()` では `SAI_MIRROR_SESSION_ATTR_IPHDR_VERSION` に定数 `MIRROR_SESSION_DEFAULT_IP_HDR_VER = 4` を設定する。
`src_ip` / `dst_ip` に IPv6 アドレスを渡しても、SAI には IPv4 ヘッダバージョンが設定されるため動作しない。
P4RT ERSPAN は IPv4 outer ヘッダのみサポート。

**GRE type ハードコード = 0x88be — 設定変更不可**:
`prepareSaiAttrs()` は `SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE` に定数 `GRE_PROTOCOL_ERSPAN = 0x88be` をハードコードする。
APP_DB に gre_type フィールドは存在せず変更できない。CONFIG_DB `MIRROR_SESSION.gre_type` (Mellanox で `0x8949`) のような platform 分岐もない。

**TOS と TTL は hex 文字列 — 0 は有効な値だが省略不可**:
`deserializeP4MirrorSessionAppDbEntry()` は TOS / TTL を `std::stoul(value, 0, 16)` で 16 進数としてパースする。
`0x00` (= 0) は有効値として受け付けられるが、フィールド自体の省略は `has_ttl=false` / `has_tos=false` のまま ADD を発行することになり `SWSS_RC_INVALID_PARAM` が返る。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存・タイミング依存 (Phase B)

`FIXED_MIRROR_SESSION_TABLE` は P4RT 経路で `MirrorSessionManager` (`orchagent/p4orch/mirror_session_manager.cpp`) が直接処理する。CONFIG_DB `MIRROR_SESSION` を扱う `MirrorOrch` と異なり、**route/neighbor/fdb の動的解決機構を持たず**、`dst_mac` を APPL_DB フィールドとして直接受け取る fail-fast 設計になっている[^5]。リトライ機構や pending キューがないため、書込み順は P4RT クライアント側で正しく保証する必要がある。

### 1. dst port readiness — PortsOrch::getPort() 先行必須（fail-fast、リトライなし）

```cpp
// mirror_session_manager.cpp:122-136 (prepareSaiAttrs)
swss::Port port;
if (!gPortsOrch->getPort(mirror_session_entry.port, port)) {
  LOG_ERROR_AND_RETURN(ReturnCode(StatusCode::SWSS_RC_NOT_FOUND)
                       << "Failed to get port info for port "
                       << QuotedVar(mirror_session_entry.port));
}
if (port.m_type != Port::Type::PHY) {
  LOG_ERROR_AND_RETURN(ReturnCode(StatusCode::SWSS_RC_INVALID_PARAM)
                       << "Port " << QuotedVar(mirror_session_entry.port)
                       << "'s type " << port.m_type
                       << " is not physical and is invalid as destination "
                          "port for mirror packet.");
}
```

CONFIG_DB 側 `MirrorOrch::doTask()` は `gPortsOrch->allPortsReady()` が false なら `doTask()` 全体を即 return して後で再 drain される (`mirrororch.cpp:1571-1574`) が、`MirrorSessionManager::drain()` には **`allPortsReady()` ガードがない** (`mirror_session_manager.cpp:62-119`)。`m_entries.pop_front()` で即時取り出し、`prepareSaiAttrs()` が `SWSS_RC_NOT_FOUND` を返すと `m_publisher->publish()` で結果通知してそのまま破棄する。

→ 順序依存: `param/port` で指定する物理ポートが PortsOrch に登録済みであること。port 未登録時の SET は `SWSS_RC_NOT_FOUND` で失敗確定し、自動再試行されない（P4RT クライアントが再送する必要がある）。

### 2. PHY 型固定 — LAG / VLAN は SET しても回復不能

`prepareSaiAttrs()` は `port.m_type != Port::Type::PHY` の場合 `SWSS_RC_INVALID_PARAM` を即返す。port の type は同一 alias で変動しないため、後から PHY に切り替わる遷移は存在しない。

→ 順序依存ではなく**設計時の制約**。LAG/VLAN を `param/port` に指定したエントリは何度再送しても受理されない。

### 3. drain() の head-of-line blocking — エラー発生で同一 drain 内の以降エントリが滞留

```cpp
// mirror_session_manager.cpp:114-118
m_publisher->publish(APP_P4RT_TABLE_NAME, kfvKey(key_op_fvs_tuple),
                     kfvFieldsValues(key_op_fvs_tuple), status,
                     /*replace=*/true);
if (!status.ok()) {
  break;
}
```

`drain()` のメインループは最初の失敗時点で `break` し、残った `m_entries` は `drainWithNotExecuted()` で「未実行」として publisher に返すだけ。同一 P4RT トランザクション内で複数セッションを SET する場合、**先頭エントリの失敗で後続セッションは全て未処理**になる。CONFIG_DB `MirrorOrch::doTask()` (`mirrororch.cpp:1576-1607`) が各エントリを独立に処理するのとは異なる。

→ 順序依存（バッチ内）: P4RT クライアントは port readiness のばらつきがあるバッチを避け、エラーが出たロットは個別再送する。

### 4. ACL_RULE での mirror_session_id 参照 — FIXED_MIRROR_SESSION_TABLE 先行必須

```cpp
// acl_rule_manager.cpp:1403-1419
case SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS:
case SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_EGRESS: {
    sai_object_id_t mirror_session_oid;
    std::string key = KeyGenerator::generateMirrorSessionKey(attr_value);
    if (!m_p4OidMapper->getOID(SAI_OBJECT_TYPE_MIRROR_SESSION, key, &mirror_session_oid))
    {
        return ReturnCode(StatusCode::SWSS_RC_NOT_FOUND)
               << "Mirror session " << QuotedVar(attr_value) << " does not exist for "
               << QuotedVar(acl_rule->acl_table_name);
    }
    ...
}
```

P4RT ACL の `AclRuleManager` は mirror アクション処理で `m_p4OidMapper->getOID(SAI_OBJECT_TYPE_MIRROR_SESSION, ...)` を呼び、未登録なら `SWSS_RC_NOT_FOUND` で即失敗する。CONFIG_DB 側 `AclRuleMirror::create()` は `SUBJECT_TYPE_MIRROR_SESSION_CHANGE` 通知（`mirrororch.cpp:1095-1096, 1110-1111`）で後から activate される pending 機構を持つが、**p4orch の `AclRuleManager` には同等の遅延 activate 機構がない**。

→ 順序依存: P4RT クライアントは「`FIXED_MIRROR_SESSION_TABLE` SET → publish 成功確認 → `ACL_*_TABLE` SET（mirror action 付き）」の順で発行すること。

### 5. processUpdateRequest の port 切替 — 新 port も readiness 必須・ref count 移管

`processUpdateRequest()` で `param/port` が変わる場合、`gPortsOrch->getPort(new_port_name, new_port)` を呼び (`mirror_session_manager.cpp:493`)、失敗時は `SWSS_RC_NOT_FOUND` で即返り、SAI 属性更新も ref count 移管も行われず**旧 port が保持される**。成功時のみ `decreasePortRefCount(old)` → `increasePortRefCount(new)` の順で実行 (`mirror_session_manager.cpp:517-518`)。

→ 順序依存: port 切替時は新 port が PortsOrch に登録済みであること。新 port 作成後に UPDATE を発行する。

### 6. policer 先行依存は不在（CONFIG_DB との差異、要注意）

`FIXED_MIRROR_SESSION_TABLE` には **`policer` フィールドが存在しない**。`P4MirrorSessionAppDbEntry` 構造体 (`p4orch_util.h:253-279`) は ttl/tos/src_ip/dst_ip/src_mac/dst_mac/port のみ保持し、`prepareSaiAttrs()` も `SAI_MIRROR_SESSION_ATTR_POLICER` を設定しない (`mirror_session_manager.cpp:122-188`)。

CONFIG_DB 側 `MirrorOrch::createEntry()` (`mirrororch.cpp:432-443`) は `MIRROR_SESSION_POLICER` フィールドに対して `m_policerOrch->policerExists()` をチェックし、未登録なら `task_need_retry` で **POLICER 先行を強制する**が、FIXED_MIRROR_SESSION_TABLE 経路ではこの依存は**ない**。

→ 含意: P4RT で QoS 制御が必要な場合は ACL_RULE の meter (`getMeterSaiAttrs`, `acl_rule_manager.cpp:124-`) 側で行う設計。MIRROR_SESSION への policer attach は P4RT 経路では対象外。

### 7. routeOrch / neighbor / fdb 動的解決は不在（ERSPAN 固定、dst_mac 直接指定）

CONFIG_DB ERSPAN セッションは `m_routeOrch->attach(this, entry.dstIp)` (`mirrororch.cpp:517`) で next hop 解決を待ち、`SUBJECT_TYPE_NEXTHOP_CHANGE` / `NEIGH_CHANGE` / `FDB_CHANGE` / `LAG_MEMBER_CHANGE` 通知で `updateSession()` を回す動的解決機構を持つ (`mirrororch.cpp:160-198, 760-808`)。

P4RT 経路は `param/dst_mac` を **APPL_DB の必須フィールドとして直接受け取る** ため、neighbor / fdb / route の動的解決は行われない。`MirrorSessionManager` は `Observer` ではなく、PortsOrch/NeighOrch/FdbOrch/RouteOrch に attach もしない。

→ 含意: P4RT クライアントは事前に dst MAC を解決して `param/dst_mac` で渡す責務を負う。トポロジ変化で MAC が変わった場合は `FIXED_MIRROR_SESSION_TABLE` の UPDATE を発行し直す必要がある（自動追従しない）。

### 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | PORT 初期化 → `FIXED_MIRROR_SESSION_TABLE` SET (`param/port`) | 強制先行（fail-fast、リトライなし） | P4RT クライアント側で再送 |
| 2 | port は PHY 型 | 設計時制約（LAG/VLAN 不可） | 設計時に PHY を選定 |
| 3 | drain() head-of-line blocking | バッチ内順序注意 | エラー発生ロットは個別再送 |
| 4 | `FIXED_MIRROR_SESSION_TABLE` SET 完了 → ACL_RULE (mirror action) | 強制先行（pending 機構なし） | クライアントが SET 順序を保証 |
| 5 | 新 port PortsOrch 登録済み → UPDATE 発行 | 強制先行 | 新 port 作成後に UPDATE |
| 6 | policer 先行依存は**不在** | (CONFIG_DB との差異) | QoS 制御は ACL meter で |
| 7 | route/neighbor/fdb 動的解決は**不在** | (CONFIG_DB との差異) | クライアント側で `dst_mac` 再解決 |

詳細スキャンノート: `meta/_intermediate/cdb-flow/appl-mirror-ordering.md`

<!-- /ordering -->

<!-- pubsub -->
## 通信メカニズム (Phase G) — ZMQ 経由の購読

<!-- evidence: sonic-swss/orchagent/p4orch/p4orch.h L46 / p4orch.cpp L36-43, L80, L126-200 / orchagent/orchdaemon.cpp L848-849 / p4orch/mirror_session_manager.cpp L82, L111 -->

`FIXED_MIRROR_SESSION_TABLE` は **通常の redis ConsumerStateTable / keyspace 通知パスではなく、専用 ZMQ チャネル経由で配送される**。
これは CONFIG_DB `MIRROR_SESSION` を購読する `MirrorOrch`（`orchagent/mirrororch.cpp` — 通常の `Orch` + `ConsumerStateTable`）とは根本的に異なる通信モデルである[^pubsub-1]。

### 転送経路

| 層 | クラス / 実体 | 役割 |
|----|--------------|------|
| 受信エンドポイント | `swss::ZmqServer` (`m_p4OrchZmqServer`, エンドポイント `m_p4OrchZmqServerEp`) | P4RT クライアントからの ZMQ フレームを受信 |
| Orch 基底 | `P4Orch : public ZmqOrch` | 全 P4RT テーブルを 1 インスタンスで保有。`ZmqOrch(db, tableNames, zmqServer, orderedQueue=true, dbPersistence=false)` で初期化[^pubsub-2] |
| ディスパッチ | `P4Orch::doTask(ConsumerBase &consumer)` | バッチ受信時に `table_name == APP_P4RT_TABLE_NAME` を検証し、`m_p4TableToManagerMap` でテーブル別マネージャに振り分け[^pubsub-3] |
| ハンドラ | `p4orch::MirrorSessionManager` | `APP_P4RT_MIRROR_SESSION_TABLE_NAME` (= `"FIXED_MIRROR_SESSION_TABLE"`) で登録[^pubsub-4] |
| 応答パス | `ResponsePublisher m_publisher("APPL_DB", buffered=true, db_write_thread=true, zmqServer)` | 処理結果ステータスを同じ `ZmqServer` 経由で P4RT に返す[^pubsub-5] |

### redis keyspace ベースとの差異

- `Consumer` / `ConsumerStateTable` の redis SUBSCRIBE / keyspace 通知は **使わない**。トリガは redis イベントではなく ZMQ フレーム受信である。
- そのため `redis-cli psubscribe '__keyspace@*__:FIXED_MIRROR_SESSION_TABLE*'` 等での観測はできない。
- P4RT クライアントは ZMQ ソケットに対して書き込み、orchagent 側 `ZmqServer` がキューに積み、`P4Orch::doTask` が同期的にドレインする。
- APPL_DB への書き込みは `ResponsePublisher` 経由で行われるが、これは下流リーダのための副作用であり、購読のトリガではない。

### コンストラクタの構造的証拠

```cpp
// orchagent/p4orch/p4orch.cpp:36-43
P4Orch::P4Orch(swss::DBConnector* db, std::vector<std::string> tableNames,
               ZmqServer* zmqServer, VRFOrch* vrfOrch, CoppOrch* coppOrch)
    : ZmqOrch(db, tableNames, zmqServer, /*orderedQueue=*/true,
              /*dbPersistence=*/false),
      m_zmqServer(zmqServer),
      m_publisher("APPL_DB", /*bool buffered=*/true,
                  /*db_write_thread=*/true, zmqServer)
```

`MirrorOrch`（CONFIG_DB 側）のコンストラクタは `Orch(confDbConnector.first, confDbConnector.second)` を呼ぶだけで `ZmqServer` を一切受け取らない。両経路は構造的に完全に独立している[^pubsub-1]。

[^pubsub-1]: CONFIG_DB 側 `MirrorOrch` の通常 Orch 経路: `orchagent/mirrororch.cpp` L79-110. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/mirrororch.cpp#L79-L110>
[^pubsub-2]: `P4Orch : public ZmqOrch`: `orchagent/p4orch/p4orch.h` L46. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/p4orch/p4orch.h#L46>. コンストラクタ: `orchagent/p4orch/p4orch.cpp` L36-43.
[^pubsub-3]: `P4Orch::doTask(ConsumerBase&)` 振り分け: `orchagent/p4orch/p4orch.cpp` L126-200. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/p4orch/p4orch.cpp#L126-L200>
[^pubsub-4]: ZmqServer 生成と `MirrorSessionManager` 登録: `orchagent/orchdaemon.cpp` L848-849, `orchagent/p4orch/p4orch.cpp` L80.
[^pubsub-5]: 応答 publish: `orchagent/p4orch/mirror_session_manager.cpp` L82, L111.

<!-- /pubsub -->

## 購読者

- `p4orch` 内の `MirrorSessionManager` (`orchagent/p4orch/mirror_session_manager.cpp`)。`P4Orch::doTask(ConsumerBase&)` から ZMQ 経由で配送される
- CONFIG_DB `MIRROR_SESSION` テーブルの `MirrorOrch` とは独立した別経路（redis ConsumerStateTable ベース）

## 関連リファレンス

- [CONFIG_DB MIRROR_SESSION](./mirror-session.md) — 通常の SPAN/ERSPAN セッション設定 (CLI 経由)
- P4RT: `APP_P4RT_MIRROR_SESSION_TABLE_NAME = "FIXED_MIRROR_SESSION_TABLE"` (`sonic-swss-common/common/schema.h:70`)

## 確認コマンド

```bash
# APPL_DB の FIXED_MIRROR_SESSION_TABLE を確認
sonic-db-cli APPL_DB keys 'FIXED_MIRROR_SESSION_TABLE*'
sonic-db-cli APPL_DB hgetall 'FIXED_MIRROR_SESSION_TABLE|{"match/mirror_session_id":"my_session"}'
```

## 引用元

[^1]: `MirrorSessionManager` 説明: `orchagent/p4orch/mirror_session_manager.h` L69-70. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/p4orch/mirror_session_manager.h#L69-L70>
[^2]: `processAddRequest()` の必須フィールドチェック: `orchagent/p4orch/mirror_session_manager.cpp` L339-363. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/p4orch/mirror_session_manager.cpp#L339-L363>
[^3]: 物理ポート制約: `orchagent/p4orch/mirror_session_manager.cpp` L124-135. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/p4orch/mirror_session_manager.cpp#L124-L135>
[^4]: `deserializeP4MirrorSessionAppDbEntry()`: `orchagent/p4orch/mirror_session_manager.cpp` L190-323. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/p4orch/mirror_session_manager.cpp#L190-L323>
[^5]: `MirrorSessionManager::drain()` と `prepareSaiAttrs()` の書込み順依存: `orchagent/p4orch/mirror_session_manager.cpp` L62-188. CONFIG_DB 経路の `MirrorOrch::doTask()` (`orchagent/mirrororch.cpp` L1567-1611) と動的解決機構 (L160-198, L760-808) との対比は `meta/_intermediate/cdb-flow/appl-mirror-ordering.md` を参照。 <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/p4orch/mirror_session_manager.cpp#L62-L188>
