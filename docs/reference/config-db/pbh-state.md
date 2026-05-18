---
title: STATE_DB PBH_CAPABILITIES テーブル
description: "STATE_DB PBH_CAPABILITIES テーブル — PBH (Policy Based Hashing) の ASIC ベンダー別フィールド更新可否能力を orchagent 起動時に書き込む読み取り専用テーブル。CLI が config pbh コマンドの操作可否判断に利用する。"
area: reference
hard: 0
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

`PBH_CAPABILITIES` は STATE_DB 上に書かれる PBH (Policy Based Hashing) の**フィールド更新可否能力テーブル**[^1]。`orchagent` の `PbhCapabilities` クラスが起動時に `ASIC_VENDOR` 環境変数を参照してプラットフォームを判別し、各 PBH フィールドに対して `ADD` / `UPDATE` / `REMOVE` の組み合わせをカンマ区切り文字列で書き込む。CONFIG_DB の [`PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD`](pbh.md) テーブルとは別に、運用上のフィールド操作制約をランタイムに公開するための機構。

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

| ベンダー | 判別条件 | hash-field の hashField 系 |
|---------|--------|--------------------------|
| Generic | `ASIC_VENDOR != "mellanox"` / 未設定 | `setPbhDefaults()` 未呼び出し → 全空 |
| Mellanox | `ASIC_VENDOR = "mellanox"` | 同上 → 全空 |

現状 Generic と Mellanox の差異は `rule.priority`・`rule.hash` の INSERT なし (UPDATE のみ) と、`hash.hash_field_list` の INSERT なし (UPDATE のみ) の点で完全に一致する。差異は `pbhcap.cpp:94-109` を参照。

## 購読者

- `config pbh table add/update/del` (`config/plugins/pbh.py:1351`) — `pbh_capabilities_query(db, "table")` で `interface_list`・`description` の操作可否チェック
- `config pbh rule add/update/del` (`config/plugins/pbh.py:1090,1218`) — `pbh_capabilities_query(db, "rule")` で各 match field の操作可否チェック
- `config pbh hash add/update/del` (`config/plugins/pbh.py:781`) — `pbh_capabilities_query(db, "hash")` で `hash_field_list` の操作可否チェック
- `config pbh hash-field add/update/del` (`config/plugins/pbh.py:670`) — `pbh_capabilities_query(db, "hash-field")` で各フィールドの操作可否チェック

<!-- defaults -->
## フィールドデフォルト (Phase A — コード由来)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-state-defaults.md -->

STATE_DB `PBH_CAPABILITIES` に対応する YANG schema は存在しない。フィールドとその値はすべて `pbhcap.cpp` のコードレベルで定義される。

### PBH_CAPABILITIES|table フィールド別デフォルト

| フィールド | STATE_DB 書き込み値 | コード由来 | 備考 |
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
| `STATE_DB` | Redis 接続 (static member) | 必須 | `PbhCapabilities::stateDb` — `pbhcap.cpp:288` |
| `ASIC_VENDOR` 環境変数 | OS 環境変数 | 任意 | 未設定時 Generic へ fallback (`pbhcap.cpp:297`) |
| `gAclOrch` / `gPortsOrch` | PbhOrch コンストラクタ引数 | PbhOrch の動作に必要 | `PbhCapabilities` 自体はこれらを参照しない |
| CONFIG_DB PBH エントリ | CONFIG_DB | 不要 | capabilities 書き込みは CONFIG_DB 読み取りに依存しない |

`PbhCapabilities` の静的メンバは orchdaemon プロセス起動の最初期に初期化されるため、他の Orch オブジェクトが生成される前から STATE_DB 接続が確立されている。

### CONFIG_DB 側との関係

`PBH_CAPABILITIES` は起動時 one-shot write であり、CONFIG_DB の PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD エントリの追加・変更に対して再書き込みは行われない。

### 消費者 (sonic-utilities) の前提条件

`config pbh` コマンドが `pbh_capabilities_query()` を呼ぶ時点で orchestrator が起動済みで STATE_DB に `PBH_CAPABILITIES` が存在しなければ validation が失敗する。orchagent の起動完了を待つ明示的な仕組みは CLI 側にない。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-state-cross-refs.md -->

`PBH_CAPABILITIES` は `PbhCapabilities::writePbhVendorCapabilitiesToDb()` が起動時 1 回のみ書き込む STATE_DB テーブルである。書き込まれるフィールド値はすべてコンストラクタ内でハードコードされており、CONFIG_DB / APPL_DB / SAI への実行時参照はない。

### 書き込み側の参照先

| 参照先リソース | 参照方向 | 条件 | evidence |
|--------------|---------|------|---------|
| `STATE_DB` 接続 (`PbhCapabilities::stateDb`) | 書き込み先 DB | 必須。static メンバとして orchdaemon 起動の最初期に確立される | `pbhcap.cpp:288` |
| `ASIC_VENDOR` 環境変数 | env var 読み取り → ベンダー分岐 | 任意。未設定時は `GENERIC` platform へ fallback。値は `"mellanox"` のみ分岐 | `pbhcap.cpp:314–329` |
| CONFIG_DB `PBH_TABLE` / `PBH_RULE` / `PBH_HASH` / `PBH_HASH_FIELD` | **参照なし** | フィールド値はコンストラクタ内のハードコード定数のみ。CONFIG_DB エントリは読まない | `pbhcap.cpp:107–124` |
| APPL_DB / SAI | **参照なし** | SAI クエリなし。ベンダー判別は env var のみ | `pbhcap.cpp:310–334` |

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
