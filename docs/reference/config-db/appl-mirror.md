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
