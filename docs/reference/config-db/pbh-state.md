---
title: STATE_DB PBH_CAPABILITIES テーブル
description: "STATE_DB PBH_CAPABILITIES テーブル — PBH (Policy Based Hashing) の ASIC ベンダー別フィールド更新可否能力を orchagent 起動時に書き込む読み取り専用テーブル。CLI が config pbh コマンドの操作可否判断に利用する。"
area: reference
verification: code-verified
last_verified: 2026-05-16
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/pbh/pbhcap.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/pbh/pbhschema.h
    ref: HEAD
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: HEAD
  - repo: sonic-net/sonic-utilities
    path: config/plugins/pbh.py
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/orchdaemon.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/pbhorch.h
    ref: HEAD
related:
  config_db:
    - PBH_TABLE
    - PBH_RULE
    - PBH_HASH
    - PBH_HASH_FIELD
  cli:
    - config pbh
  _no_related_yang: true
---

# STATE_DB PBH_CAPABILITIES テーブル

## 概要

`PBH_CAPABILITIES` は [STATE_DB](../../reference/glossary.md#term-state_db) 上に書かれる PBH (Policy Based Hashing) の**フィールド更新可否能力テーブル**[^1]。`orchagent` の `PbhCapabilities` クラスが起動時に `ASIC_VENDOR` 環境変数を参照してプラットフォームを判別し、各 PBH フィールドに対して `ADD` / `UPDATE` / `REMOVE` の組み合わせをカンマ区切り文字列で書き込む。[CONFIG_DB](../../reference/glossary.md#term-config_db) の [`PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD`](pbh.md) テーブルとは別に、運用上のフィールド操作制約をランタイムに公開するための機構。

`sonic-utilities` の `config pbh` コマンドがこのテーブルを参照し、操作可否を事前検証する (`pbhcap.cpp:288-289`)。

## key 構造

```text
PBH_CAPABILITIES|table
PBH_CAPABILITIES|rule
PBH_CAPABILITIES|hash
PBH_CAPABILITIES|hash-field
```

4 サブキー固定。ワイルドカード展開なし。

## フィールド

### PBH_CAPABILITIES|table

| フィールド | 型 | 値 | 説明 |
|-----------|----|---|------|
| `interface_list` | enum string | `"UPDATE"` | interface_list フィールドの対応操作。Generic・Mellanox 共通 |
| `description` | enum string | `"UPDATE"` | description フィールドの対応操作 |

### PBH_CAPABILITIES|rule

| フィールド | 型 | Generic / Mellanox 値 | 説明 |
|-----------|----|----------------------|------|
| `priority` | enum string | `"UPDATE"` | priority フィールドの対応操作 |
| `gre_key` | enum string | `"ADD,UPDATE,REMOVE"` | gre_key フィールドの対応操作 |
| `ether_type` | enum string | `"ADD,UPDATE,REMOVE"` | ether_type フィールドの対応操作 |
| `ip_protocol` | enum string | `"ADD,UPDATE,REMOVE"` | ip_protocol フィールドの対応操作 |
| `ipv6_next_header` | enum string | `"ADD,UPDATE,REMOVE"` | ipv6_next_header フィールドの対応操作 |
| `l4_dst_port` | enum string | `"ADD,UPDATE,REMOVE"` | l4_dst_port フィールドの対応操作 |
| `inner_ether_type` | enum string | `"ADD,UPDATE,REMOVE"` | inner_ether_type フィールドの対応操作 |
| `hash` | enum string | `"UPDATE"` | hash フィールドの対応操作 |
| `packet_action` | enum string | `"ADD,UPDATE,REMOVE"` | packet_action フィールドの対応操作 |
| `flow_counter` | enum string | `"ADD,UPDATE,REMOVE"` | flow_counter フィールドの対応操作 |

### PBH_CAPABILITIES|hash

| フィールド | 型 | 値 | 説明 |
|-----------|----|---|------|
| `hash_field_list` | enum string | `"UPDATE"` | hash_field_list フィールドの対応操作 |

### PBH_CAPABILITIES|hash-field

| フィールド | 型 | 値 | 説明 |
|-----------|----|---|------|
| `hash_field` | enum string | `""` (空) | いずれのプラットフォームでも未設定。UPDATE 禁止の意味 |
| `ip_mask` | enum string | `""` (空) | 同上 |
| `sequence_id` | enum string | `""` (空) | 同上 |

!!! note "hash-field が空の理由"
    `PBH_HASH_FIELD` はコード上 UPDATE が禁止されている (`updatePbhHashField()` は常に `return false`)。
    能力テーブルに UPDATE/REMOVE フラグを持たせると `config pbh hash-field update` が誤って許可されるため、
    空文字列を書き込んでいる。`config pbh hash-field update` はこの値を見て「更新不可」と判断し拒否する
    (`pbh.py:670-679`)。

## 書き込みタイミング

`PbhCapabilities` コンストラクタは `orchagent` 起動時に呼ばれる。

1. `parsePbhAsicVendor()` — `ASIC_VENDOR` 環境変数を読んで Generic / Mellanox を判別。未設定時は Generic へ fallback。
2. `initPbhVendorCapabilities()` — ベンダー別 `PbhVendorFieldCapabilities` サブクラスを構築。
3. `writePbhVendorCapabilitiesToDb()` — 4 サブキーを `Table::set()` で一括書き込み (`pbhcap.cpp:313-321`)。

**起動後は更新されない** (read-once write)。

## ベンダー差異

| ベンダー | 判別条件 | `hash` サブキーの `hash_field_list` | `hash-field` の hashField 系 |
|---------|--------|------|--------------------------|
| Generic | `ASIC_VENDOR != "mellanox"` / 未設定 | `"UPDATE"` (`pbhcap.cpp:123` で `hash.hash_field_list.insert(UPDATE)`) | `setPbhDefaults()` 未呼び出し → 全空 |
| Mellanox | `ASIC_VENDOR = "mellanox"` | `""` (空。`pbhcap.cpp:126-141` に対応 INSERT なし) | 同上 → 全空 |

`PBH_CAPABILITIES|hash` の `hash_field_list` は Generic と Mellanox で**異なる**（Generic=`UPDATE`、Mellanox=空）。Mellanox 環境では `config pbh hash update` が `pbh_capabilities_query()` の検証で拒否される。詳細マトリクスは本ページ Phase H セクションを参照。差異は `pbhcap.cpp:94-141` を参照。

## 購読者

- `config pbh table add/update/del` (`config/plugins/pbh.py:1351`) — `pbh_capabilities_query(db, "table")` で `interface_list`・`description` の操作可否チェック
- `config pbh rule add/update/del` (`config/plugins/pbh.py:1090,1218`) — `pbh_capabilities_query(db, "rule")` で各 match field の操作可否チェック
- `config pbh hash add/update/del` (`config/plugins/pbh.py:781`) — `pbh_capabilities_query(db, "hash")` で `hash_field_list` の操作可否チェック
- `config pbh hash-field add/update/del` (`config/plugins/pbh.py:670`) — `pbh_capabilities_query(db, "hash-field")` で各フィールドの操作可否チェック

<!-- defaults -->
## フィールドデフォルト (Phase A — コード由来)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-state-defaults.md -->

[STATE_DB](../../reference/glossary.md#term-state_db) `PBH_CAPABILITIES` に対応する [YANG](../../reference/glossary.md#term-yang) schema は存在しない。フィールドとその値はすべて `pbhcap.cpp` のコードレベルで定義される。

### PBH_CAPABILITIES|table フィールド別デフォルト

| フィールド | [STATE_DB](../../reference/glossary.md#term-state_db) 書き込み値 | コード由来 | 備考 |
|-----------|-------------------|----------|------|
| `interface_list` | `"UPDATE"` | `this->table.interface_list.insert(PbhFieldCapability::UPDATE)` — `pbhcap.cpp:94` | ADD/REMOVE なし: table 自体は CREATE/DELETE できるが interface_list は後から UPDATE のみ可 |
| `description` | `"UPDATE"` | `this->table.description.insert(PbhFieldCapability::UPDATE)` — `pbhcap.cpp:95` | 同上 |

### PBH_CAPABILITIES|rule フィールド別デフォルト

| フィールド | STATE_DB 書き込み値 | コード由来 | 備考 |
|-----------|-------------------|----------|------|
| `priority` | `"UPDATE"` | `this->rule.priority.insert(UPDATE)` — `pbhcap.cpp:97` | priority は rule 作成後の UPDATE のみ許可 |
| `gre_key` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults(this->rule.gre_key)` — `pbhcap.cpp:98` | match field は ADD/UPDATE/REMOVE すべて許可 (optional field) |
| `ether_type` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults(...)` — `pbhcap.cpp:99` | 同上 |
| `ip_protocol` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults(...)` — `pbhcap.cpp:100` | 同上 |
| `ipv6_next_header` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults(...)` — `pbhcap.cpp:101` | 同上 |
| `l4_dst_port` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults(...)` — `pbhcap.cpp:102` | 同上 |
| `inner_ether_type` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults(...)` — `pbhcap.cpp:103` | 同上 |
| `hash` | `"UPDATE"` | `this->rule.hash.insert(UPDATE)` — `pbhcap.cpp:104` | hash 参照先は rule 作成後 UPDATE のみ可 |
| `packet_action` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults(...)` — `pbhcap.cpp:105` | ADD/UPDATE/REMOVE すべて許可 |
| `flow_counter` | `"ADD,UPDATE,REMOVE"` | `setPbhDefaults(...)` — `pbhcap.cpp:106` | ADD/UPDATE/REMOVE すべて許可 |

### PBH_CAPABILITIES|hash フィールド別デフォルト

| フィールド | STATE_DB 書き込み値 | コード由来 | 備考 |
|-----------|-------------------|----------|------|
| `hash_field_list` | `"UPDATE"` | `this->hash.hash_field_list.insert(UPDATE)` — `pbhcap.cpp:108` | hash_field_list は後から UPDATE のみ可 |

### PBH_CAPABILITIES|hash-field フィールド別デフォルト

| フィールド | STATE_DB 書き込み値 | コード由来 | 備考 |
|-----------|-------------------|----------|------|
| `hash_field` | `""` (空) | どちらの実装も `hashField.hash_field` に INSERT なし — `toStr()` が空 set → `""` | UPDATE 禁止を示す。`updatePbhHashField()` は常に `return false` |
| `ip_mask` | `""` (空) | 同上 | 同上 |
| `sequence_id` | `""` (空) | 同上 | 同上 |

### テスト fixture 確認値

`sonic-utilities/tests/pbh_input/state_db.json` の実際の値と一致することを確認済み。
Generic platform での期待値:

```json
{
    "PBH_CAPABILITIES|table": {"interface_list": "UPDATE", "description": "UPDATE"},
    "PBH_CAPABILITIES|rule": {
        "priority": "UPDATE", "ether_type": "ADD,UPDATE,REMOVE",
        "ip_protocol": "ADD,UPDATE,REMOVE", "ipv6_next_header": "ADD,UPDATE,REMOVE",
        "l4_dst_port": "ADD,UPDATE,REMOVE", "gre_key": "ADD,UPDATE,REMOVE",
        "inner_ether_type": "ADD,UPDATE,REMOVE", "hash": "UPDATE",
        "packet_action": "ADD,UPDATE,REMOVE", "flow_counter": "ADD,UPDATE,REMOVE"
    },
    "PBH_CAPABILITIES|hash": {"hash_field_list": "UPDATE"},
    "PBH_CAPABILITIES|hash-field": {"hash_field": "", "ip_mask": "", "sequence_id": ""}
}
```

<!-- /defaults -->

<!-- ordering -->
## オブジェクト生成順序・依存関係 (Phase B)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-state-ordering.md -->

### PbhCapabilities の初期化位置

`PBH_CAPABILITIES` を STATE_DB へ書き込む `PbhCapabilities` クラスは `PbhOrch` の非 static メンバとして宣言されている (`pbhorch.h:88`)。`PbhOrch` が `new PbhOrch(...)` でインスタンス化される瞬間に `PbhCapabilities()` コンストラクタが呼ばれ、STATE_DB への書き込みが一度だけ実行される。

### orchdaemon 内での生成順序

```text
orchdaemon.cpp:232  gPortsOrch = new PortsOrch(...)
orchdaemon.cpp:533  gAclOrch   = new AclOrch(...)   ← PbhOrch の引数として必要
orchdaemon.cpp:565  gPbhOrch   = new PbhOrch(connectorList, gAclOrch, gPortsOrch)
                                  └─ PbhCapabilities() コンストラクタが即座に実行
                                       1. parsePbhAsicVendor()         — ASIC_VENDOR env var 読み取り
                                       2. initPbhVendorCapabilities()  — ベンダー別能力オブジェクトを構築
                                       3. writePbhVendorCapabilitiesToDb() — STATE_DB に 4 キー一括書き込み
```

### 依存関係まとめ

| 依存対象 | 種別 | 必須か | 備考 |
|---------|------|--------|------|
| `STATE_DB` | [Redis](../../reference/glossary.md#term-redis) 接続 (static member) | 必須 | `PbhCapabilities::stateDb` — `pbhcap.cpp:288` |
| `ASIC_VENDOR` 環境変数 | OS 環境変数 | 任意 | 未設定時 Generic へ fallback (`pbhcap.cpp:297`) |
| `gAclOrch` / `gPortsOrch` | PbhOrch コンストラクタ引数 | PbhOrch の動作に必要 | `PbhCapabilities` 自体はこれらを参照しない |
| [CONFIG_DB](../../reference/glossary.md#term-config_db) PBH エントリ | [CONFIG_DB](../../reference/glossary.md#term-config_db) | 不要 | capabilities 書き込みは CONFIG_DB 読み取りに依存しない |

`PbhCapabilities` の静的メンバは orchdaemon プロセス起動の最初期に初期化されるため、他の Orch オブジェクトが生成される前から STATE_DB 接続が確立されている。

### CONFIG_DB 側との関係

`PBH_CAPABILITIES` は起動時 one-shot write であり、CONFIG_DB の PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD エントリの追加・変更に対して再書き込みは行われない。

### 消費者 (sonic-utilities) の前提条件

`config pbh` コマンドが `pbh_capabilities_query()` を呼ぶ時点で orchestrator が起動済みで STATE_DB に `PBH_CAPABILITIES` が存在しなければ validation が失敗する。[orchagent](../../reference/glossary.md#term-orchagent) の起動完了を待つ明示的な仕組みは CLI 側にない。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-state-cross-refs.md -->

`PBH_CAPABILITIES` は `PbhCapabilities::writePbhVendorCapabilitiesToDb()` が起動時 1 回のみ書き込む STATE_DB テーブルである。書き込まれるフィールド値はすべてコンストラクタ内でハードコードされており、CONFIG_DB / [APPL_DB](../../reference/glossary.md#term-appl_db) / [SAI](../../reference/glossary.md#term-sai) への実行時参照はない。

### 書き込み側の参照先

| 参照先リソース | 参照方向 | 条件 | evidence |
|--------------|---------|------|---------|
| `STATE_DB` 接続 (`PbhCapabilities::stateDb`) | 書き込み先 DB | 必須。static メンバとして orchdaemon 起動の最初期に確立される | `pbhcap.cpp:288` |
| `ASIC_VENDOR` 環境変数 | env var 読み取り → ベンダー分岐 | 任意。未設定時は `GENERIC` platform へ fallback。値は `"mellanox"` のみ分岐 | `pbhcap.cpp:314–329` |
| CONFIG_DB `PBH_TABLE` / `PBH_RULE` / `PBH_HASH` / `PBH_HASH_FIELD` | **参照なし** | フィールド値はコンストラクタ内のハードコード定数のみ。CONFIG_DB エントリは読まない | `pbhcap.cpp:107–124` |
| [APPL_DB](../../reference/glossary.md#term-appl_db) / [SAI](../../reference/glossary.md#term-sai) | **参照なし** | [SAI](../../reference/glossary.md#term-sai) クエリなし。ベンダー判別は env var のみ | `pbhcap.cpp:310–334` |

### 読み取り側 (sonic-utilities) の参照先

`config pbh` コマンドは `pbh_capabilities_query(db, key)` で `STATE_DB.PBH_CAPABILITIES|<key>` を `hgetall` し、操作可否を検証する。

| 参照先 STATE_DB キー | 参照方向 | 使用箇所 |
|--------------------|---------|---------|
| `PBH_CAPABILITIES\|table` | 読み取り | `config pbh table add/update/del` (`pbh.py:1351`) |
| `PBH_CAPABILITIES\|rule` | 読み取り | `config pbh rule add/update/del` (`pbh.py:1090, 1218`) |
| `PBH_CAPABILITIES\|hash` | 読み取り | `config pbh hash add/update/del` (`pbh.py:781`) |
| `PBH_CAPABILITIES\|hash-field` | 読み取り | `config pbh hash-field add/update/del` (`pbh.py:670`) |

!!! note "orchagent 未起動時の挙動"
    `config pbh` コマンドが orchagent 起動前に実行されると、`STATE_DB` に `PBH_CAPABILITIES` キーが存在しないため `pbh_capabilities_query()` が空 dict を返す。各 `config pbh` サブコマンドはこれを「capability 不明 = 操作拒否」と扱い、エラーメッセージを出力する。明示的な orchagent 起動待ち機構は CLI 側に存在しない。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-state-failure.md -->

`PBH_CAPABILITIES` は `PbhCapabilities` コンストラクタが起動時 1 回のみ書き込む STATE_DB テーブルである。
書き込み経路は `parsePbhAsicVendor()` → `initPbhVendorCapabilities()` → `writePbhVendorCapabilitiesToDb()` の 3 段。

### 書き込み側の失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `ASIC_VENDOR` 環境変数が未設定 | `parsePbhAsicVendor()` L314–317 | `WARN` 出力後 `asicVendor = GENERIC` に silent fallback。STATE_DB には Generic 向け値が書かれる | `SWSS_LOG_WARN("Failed to parse ASIC vendor: fallback to %s platform")` | `pbhcap.cpp:295–298` |
| `ASIC_VENDOR` が `"mellanox"` 以外の未知ベンダー文字列 | `parsePbhAsicVendor()` L323–329 | `"mellanox"` の else ブランチで `GENERIC` 扱い。unknown ベンダーは Generic として動作 | なし（分岐なし） | `pbhcap.cpp:323–329` |
| `initPbhVendorCapabilities()` で `fieldCap` が `nullptr`（将来 unknown vendor 追加時） | `initPbhVendorCapabilities()` L356–359 | `SWSS_LOG_ERROR` 出力後 `return`。`this->table` 等が `nullptr` のまま → `writePbhVendorCapabilitiesToDb()` 内で `nullptr` deref = `PBH_CAPABILITIES` が STATE_DB に**書かれない** | `SWSS_LOG_ERROR("Failed to initialize PBH capabilities: unknown ASIC vendor")` | `pbhcap.cpp:356–359` |
| `Table::set()` ([Redis](../../reference/glossary.md#term-redis) `HSET`) が失敗（[Redis](../../reference/glossary.md#term-redis) [ACL](../../reference/glossary.md#term-acl) 等） | `writePbhEntityCapabilitiesToDb()` L381 / L405 / L420 / L437 | 戻り値 void のため silent drop。`SWSS_LOG_NOTICE` はエントリ書き込み後に出力されるが、失敗は未検出 | なし | `pbhcap.cpp:381,405,420,437` |
| `STATE_DB` (static `DBConnector`, timeout=0) 接続失敗 | static member 初期化時 | `swsscommon` 内部で例外発生 → [orchagent](../../reference/glossary.md#term-orchagent) プロセスが起動失敗 (crash)。systemd により自動再起動 | スタックトレース (未捕捉) | `pbhcap.cpp:288–289` |

### 消費側 (`config pbh`) の失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| [orchagent](../../reference/glossary.md#term-orchagent) 未起動 / `PBH_CAPABILITIES` キー欠如 | `pbh_capabilities_query()` | 空 dict を返す → 各 `config pbh` サブコマンドが「操作拒否」エラーを出力 | `pbh.py:670–679, 781, 1090, 1351` |
| `PBH_CAPABILITIES\|<subkey>` に対象フィールドが存在しない | `pbh_capabilities_query()` | `hgetall` 結果に該当フィールドなし → 空文字列として扱われ「capability 不明 = 操作拒否」と判定 | `pbh.py:670–679` |

### 補足

- **write-once の冪等性**: コンストラクタで 1 回のみ書くため、Redis の `HSET` は既存値を上書きする動作になる。orchagent が再起動しても同じ値が再書き込みされる（冪等）。
- **`nullptr` deref の実際のリスク**: 現行コードの分岐は `GENERIC` / `MELLANOX` のみで `default` で `fieldCap` が nullptr になるパスは `nullptr` 状態をチェックして早期 return しているため (L356–359)、実際に deref は発生しない。ただし `writePbhVendorCapabilitiesToDb()` が呼ばれた後にメンバポインタが `nullptr` ならシグナル SIGSEGV が発生するため、`initPbhVendorCapabilities()` の `return` が実質的なガードとして機能している。

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

`PBH_CAPABILITIES` テーブルに関係するハードコード定数の一覧。[YANG](../../reference/glossary.md#term-yang) スキーマは存在せず、テーブル名・フィールド名・値の文字列はすべて C++ `#define` および Python 変数としてコードに埋め込まれている。詳細スキャンノート: [`meta/_intermediate/cdb-flow/pbh-state-constants.md`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/_intermediate/cdb-flow/pbh-state-constants.md)。

### STATE_DB 接続パラメータ

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_STATE_DB_NAME` | `"STATE_DB"` | `DBConnector` 初期化時の DB 名。静的メンバ `PbhCapabilities::stateDb` に使用 | `pbhcap.cpp:35` |
| `PBH_STATE_DB_TIMEOUT` | `0` ms | DB 接続タイムアウト (0 = ブロッキング、タイムアウトなし)。Redis 未起動時はハング | `pbhcap.cpp:36` |
| `STATE_PBH_CAPABILITIES_TABLE_NAME` | `"PBH_CAPABILITIES"` | `Table` オブジェクト初期化時のテーブル名。`sonic-swss-common` で定義 | `schema.h:419` |

### プラットフォーム識別定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_PLATFORM_ENV_VAR` | `"ASIC_VENDOR"` | ベンダー識別に使う環境変数名。`parsePbhAsicVendor()` が `getenv()` で読み取る | `pbhcap.cpp:20` |
| `PBH_PLATFORM_GENERIC` | `"generic"` | Generic プラットフォーム識別文字列。`ASIC_VENDOR` 未設定時の fallback 値 | `pbhcap.cpp:21` |
| `PBH_PLATFORM_MELLANOX` | `"mellanox"` | Mellanox プラットフォーム識別文字列。大文字小文字区別あり (lowercase 固定) | `pbhcap.cpp:22` |
| `PBH_PLATFORM_UNKN` | `"unknown"` | ログ出力専用の未知プラットフォーム文字列。分岐制御には使用されない | `pbhcap.cpp:23` |

### STATE_DB サブキー名定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_TABLE_CAPABILITIES_KEY` | `"table"` | `PBH_CAPABILITIES\|table` サブキー名 | `pbhcap.cpp:25` |
| `PBH_RULE_CAPABILITIES_KEY` | `"rule"` | `PBH_CAPABILITIES\|rule` サブキー名 | `pbhcap.cpp:26` |
| `PBH_HASH_CAPABILITIES_KEY` | `"hash"` | `PBH_CAPABILITIES\|hash` サブキー名 | `pbhcap.cpp:27` |
| `PBH_HASH_FIELD_CAPABILITIES_KEY` | `"hash-field"` | `PBH_CAPABILITIES\|hash-field` サブキー名 | `pbhcap.cpp:28` |

### フィールド操作能力トークン

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_FIELD_CAPABILITY_ADD` | `"ADD"` | STATE_DB に書き込まれる能力トークン。`toStr()` でセットをカンマ連結する | `pbhcap.cpp:30` |
| `PBH_FIELD_CAPABILITY_UPDATE` | `"UPDATE"` | 同上 | `pbhcap.cpp:31` |
| `PBH_FIELD_CAPABILITY_REMOVE` | `"REMOVE"` | 同上 | `pbhcap.cpp:32` |
| `PBH_FIELD_CAPABILITY_UNKN` | `"UNKNOWN"` | `pbhFieldCapabilityMap` に未登録の enum 値が来た場合のフォールバック文字列 | `pbhcap.cpp:33` |

> **`toStr()` のソート順**: `PbhFieldCapability` の enum 値は `ADD=0, UPDATE=1, REMOVE=2` の順に定義されており、`std::set<PbhFieldCapability>` が昇順ソートされるため、3 つ全て有効な場合の書き込み値は `"ADD,UPDATE,REMOVE"` になる（`"ADD,REMOVE,UPDATE"` ではない）。

### Python 側固有定数 (config/plugins/pbh.py)

`sonic-utilities` が C++ 定数とは独立に定義するコンシューマ側定数。

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `PBH_CAPABILITIES_SDB` | `"PBH_CAPABILITIES"` | STATE_DB テーブル名（`STATE_PBH_CAPABILITIES_TABLE_NAME` の Python 側ミラー）| `pbh.py:72` |
| `PBH_ADD` | `"ADD"` | `pbh_capabilities_query()` の戻り値との照合に使用 | `pbh.py:82` |
| `PBH_UPDATE` | `"UPDATE"` | 同上 | `pbh.py:83` |
| `PBH_REMOVE` | `"REMOVE"` | 同上 | `pbh.py:84` |

!!! note "C++ / Python の定数二重管理"
    `pbhschema.h`（C++）と `pbh.py`（Python）はフィールド名文字列を独立して定義している。一方のみを変更した場合、バグがコンパイル時に検出されないリスクがある。

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-state-side-effects.md -->

`PbhCapabilities` は `STATE_DB.PBH_CAPABILITIES` への 4 キー書き込みのみを行う。
その他の DB への副次書き込みは発生しない。

### 副次書込サマリ

| 副次書込先 DB | テーブル / キー | 書き込み内容 | 主なトリガ |
|---|---|---|---|
| STATE_DB | `PBH_CAPABILITIES\|table` / `\|rule` / `\|hash` / `\|hash-field` | フィールド操作能力文字列 (`ADD`, `UPDATE`, `REMOVE` のカンマ区切り、または空文字列) | orchagent (`PbhOrch`) 起動時、`PbhCapabilities` コンストラクタの 1 回のみ |

### スコープ外（書き込まない DB）

- **CONFIG_DB**: `PbhCapabilities` は設定変更を行わない。設定の正本は CONFIG_DB `PBH_TABLE` / `PBH_RULE` 等であり、capability テーブルはそれらを読まない。
- **[APPL_DB](../../reference/glossary.md#term-appl_db)**: PBH エントリの APPL_DB 書き込みは `PbhOrch` が管理する別経路。`PbhCapabilities` は APPL_DB に触れない。
- **[COUNTERS_DB](../../reference/glossary.md#term-counters_db) / [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db)**: flow_counter 関連書込は `PbhOrch → AclOrch` 経路 (`pbhcap.cpp:499` — `createCounter=false` がデフォルト)。`PbhCapabilities` は counter 管理に関与しない。
- **[ASIC_DB](../../reference/glossary.md#term-asic_db)**: SAI API 呼び出しなし。[syncd](../../reference/glossary.md#term-syncd) 経由の間接書込も発生しない (`pbhcap.cpp:371–451` 全域)。

!!! note "読み取り副作用"
    `sonic-utilities` の `config pbh` コマンドが STATE_DB `PBH_CAPABILITIES` を `hgetall` で読み取るが、
    これは読み取りのみであり追加の DB 書き込みは発生しない (`pbh.py:670–679, 781, 1090, 1351`)。

<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-state-pubsub.md -->

### 書き込み側の通信構造

`PbhCapabilities` は `swsscommon::Table` を使って STATE_DB へ直接書き込む。`Table::set()` は Redis `HSET` を実行するのみで、`ProducerStateTable` のようなチャネル PUBLISH を伴わない (`pbhcap.cpp:381, 405, 420, 437`)。

```cpp
// pbhcap.cpp:288-289
DBConnector PbhCapabilities::stateDb(PBH_STATE_DB_NAME, PBH_STATE_DB_TIMEOUT);
Table PbhCapabilities::capTable(&stateDb, STATE_PBH_CAPABILITIES_TABLE_NAME);
```

書き込み後に Redis サーバが keyspace 通知 (`__keyspace@6__:PBH_CAPABILITIES|*`) を発火しうるが、それを購読するプロセスは現行実装に存在しない。

### 読み取り側 (sonic-utilities) の通信方式

`config/plugins/pbh.py` の `pbh_capabilities_query()` は `db.get_all()` で `HGETALL` を実行する。これはコマンド実行時の**ワンショットスナップショット**であり、継続的な購読は行わない (`pbh.py:492–498`)。

### 購読方式サマリ

| コンポーネント | 方式 | API | タイミング |
|--------------|------|-----|---------|
| `PbhCapabilities` (orchagent) | STATE_DB 書き込み専用 | `Table::set()` — チャネル PUBLISH なし | orchagent 起動時 1 回のみ |
| `config pbh *` ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities)) | スナップショット読み取り | `db.get_all()` → Redis `HGETALL` | `config pbh` サブコマンド実行時のみ |

`PBH_CAPABILITIES` を `SubscriberStateTable` / `ConsumerStateTable` / `ConfigDBConnector.subscribe()` で継続購読するプロセスは [sonic-swss](../../reference/glossary.md#term-sonic-swss) / [sonic-utilities](../../reference/glossary.md#term-sonic-utilities) のいずれにも存在しない。継続的な pub/sub 経路はない。

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差異 (Phase H)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-state-platform.md -->

### プラットフォーム識別

`PbhCapabilities` は起動時に `parsePbhAsicVendor()` (`pbhcap.cpp:310-332`) で環境変数 `ASIC_VENDOR` を読み取り、対応する `PbhVendorFieldCapabilities` サブクラスをインスタンス化する。`ASIC_VENDOR` が未設定または `"mellanox"` 以外の値の場合は `"generic"` platform へ fallback する。

| `ASIC_VENDOR` 値 | ロードされるクラス | fallback ログ |
|---|---|---|
| `"mellanox"` | `PbhMellanoxFieldCapabilities` | なし |
| それ以外 / 未設定 | `PbhGenericFieldCapabilities` | `SWSS_LOG_WARN("Failed to parse ASIC vendor: fallback to generic platform")` |

### Generic vs Mellanox の STATE_DB 書き込み差異

`PBH_CAPABILITIES` の 4 サブキーのうち、`|table` / `|rule` / `|hash-field` は Generic と Mellanox で内容が同一。差が出るのは `|hash` サブキーの `hash_field_list` フィールドのみ。

#### PBH_CAPABILITIES|hash

| フィールド | Generic | Mellanox | コード根拠 |
|---|---|---|---|
| `hash_field_list` | `"UPDATE"` | `""` (空) | Generic: `L123` に `hash.hash_field_list.insert(UPDATE)`。Mellanox: 対応行なし (`L126-141`) |

> **Mellanox 固有制約**: `PBH_CAPABILITIES|hash` の `hash_field_list` が空文字列になるため、`config pbh hash update` が `pbh_capabilities_query()` の検証で拒否される。`config pbh hash` サブコマンドの UPDATE 操作は Mellanox 環境では実行不可。

#### 他サブキーの差異なし

`PBH_CAPABILITIES|table` / `|rule` / `|hash-field` は両 platform で同一の値が書き込まれる (`pbhcap.cpp:107-124` vs `pbhcap.cpp:126-141` を比較)。

<!-- /platform -->

## 関連 CONFIG_DB / CLI

- 設定元: [`PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD`](pbh.md) (CONFIG_DB)
- 確認コマンド:

```bash
sonic-db-cli STATE_DB keys 'PBH_CAPABILITIES|*'
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES|table'
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES|rule'
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES|hash'
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES|hash-field'
```

## 引用元

[^1]: `sonic-swss/orchagent/pbh/pbhcap.cpp` — `PbhCapabilities` コンストラクタ・`writePbhVendorCapabilitiesToDb()` (L288-321). <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/pbh/pbhcap.cpp>

<!-- glossary-links-injected: 32f949792f33 -->
