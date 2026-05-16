# POLICER — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/policer.md` Phase C 追加分。
`POLICER` は YANG 未定義テーブルのため leafref は存在しない。
`sonic-swss/orchagent/policerorch.cpp` を全行精読し、外部テーブル・外部 Orch への依存を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/policerorch.cpp` | `PolicerOrch::doTask()` / `handlePortStormControlTable()` |
| `sonic-swss/orchagent/mirrororch.cpp` | `MirrorOrch::createEntry()` — POLICER leafref (L432-441) |
| `sonic-swss/orchagent/orchdaemon.cpp` | `PolicerOrch` 登録 (L396-402) |
| `sonic-utilities/acl_loader/main.py` | `read_policers_info()` — POLICER 読み取り (L254-266) |

## YANG leafref

`POLICER` は YANG 未定義テーブルのため leafref は存在しない。全参照が実装レベルの暗黙参照。

ただし以下の YANG から policer 名 / フィールドが参照される:
- `sonic-mirror-session.yang`: `MIRROR_SESSION.policer` → `POLICER.name` に相当する leafref
- `sonic-copp.yang`: `COPP_GROUP` の policer 属性 (mode / cir / cbs 等) をインライン定義
- `sonic-storm-control.yang`: `PORT_STORM_CONTROL.kbps` — policer へ変換
- `sonic-acl.yang` (P4 orch): policer action フィールド

## 暗黙参照 (実装レベル)

### 1. ACL_RULE — POLICER を action として参照

- **参照先テーブル**: `POLICER`
- **参照方向**: POLICER を消費する (policer OID を取得して ACL action に設定)
- **参照元**: 標準 `aclorch.cpp` は ACL_RULE から POLICER を直接参照しない。`acl_loader/main.py` L254-266 (`read_policers_info()`) が **表示目的のみ** で読み取る。P4 orch (`p4orch/acl_util.cpp`) 経由では policer OID を ACL action に設定する実装がある。
- **条件**: `aclshow` コマンド実行時 / P4 ACL 設定時
- **依存関係**: 標準 ACL_RULE → POLICER の依存は弱い（表示のみ）。P4 環境では POLICER が先行必須。
- **ソース evidence**: `acl_loader/main.py:254-266`

### 2. MIRROR_SESSION — policer フィールドで POLICER を参照

- **参照先テーブル**: `POLICER`
- **参照方向**: POLICER を消費する (policer OID を MIRROR_SESSION に attach)
- **参照元**: `mirrororch.cpp` L432-441 `m_policerOrch->policerExists()` / `m_policerOrch->increaseRefCount()`
- **条件**: `MIRROR_SESSION` の `policer` フィールドが指定されているとき
- **意味**:
  - `policerExists()` が false → `task_need_retry`。POLICER 追加後に自動再処理される。
  - POLICER が存在する場合: OID を取得して session に attach、`increaseRefCount()` で参照カウント増加。
  - MIRROR_SESSION DEL 時: `decreaseRefCount()` を呼んで参照カウント解放。
- **ブロッキング依存**: MIRROR_SESSION の policer attach は POLICER の先行作成が必要。後から POLICER を作成しても session が active になっていれば再処理される。
- **ソース evidence**: `mirrororch.cpp:432-441`

### 3. COPP_GROUP — policer フィールドを内部に保持 (インライン policer)

- **参照先テーブル**: `POLICER` (COPP_GROUP は POLICER テーブルを直接参照しない — 自身に policer 属性をインライン定義)
- **参照方向**: COPP_GROUP 内の `mode`/`cir`/`cbs` 等を `CoppOrch` が SAI policer として作成
- **参照元**: `copporch.cpp` `trapGroupAddPolicer()` / `trapGroupUpdatePolicer()`
- **条件**: 常時 (COPP_GROUP エントリが存在するとき)
- **意味**: `COPP_GROUP` は独立した SAI policer を内部生成する。`POLICER` テーブルとは別物。COPP_GROUP の policer フィールド (mode / cir / cbs / pir / pbs / color / action) は直接 SAI policer API に渡される。
- **注意**: COPP_GROUP は `POLICER` テーブルをキーで参照しない。しかし同一の SAI policer 属性体系を共有するため、混同しやすい。`COPP_GROUP` に policer 名を書いても `POLICER` テーブルとのリンクは発生しない。
- **ソース evidence**: `copporch.cpp:trapGroupAddPolicer()` / `sonic-copp.yang`

### 4. PORT_STORM_CONTROL — POLICER テーブルと PolicerOrch を共有

- **参照先テーブル**: `POLICER` (PolicerOrch が同一インスタンスで両テーブルを管理)
- **参照方向**: PORT_STORM_CONTROL エントリから内部的に SAI policer を生成 (POLICER テーブルへの書き込みは発生しない)
- **参照元**: `policerorch.cpp:394-407` `doTask()` の `table_name == CFG_PORT_STORM_CONTROL_TABLE_NAME` 分岐
- **条件**: `PORT_STORM_CONTROL` テーブルへの SET/DEL 時
- **意味**:
  - PolicerOrch が `CFG_POLICER_TABLE_NAME` と `CFG_PORT_STORM_CONTROL_TABLE_NAME` を同一インスタンスで購読 (`orchdaemon.cpp:396-402`)。
  - storm-control エントリは `handlePortStormControlTable()` にディスパッチされ、内部で SAI policer を作成・attach する。`POLICER` テーブルへのエントリは生成しない。
  - ハードコード属性: `METER_TYPE=BYTES` / `MODE=STORM_CONTROL` / `RED_PACKET_ACTION=DROP`。
  - `kbps` → `CIR = kbps × 1000 / 8` bytes/sec に変換。
- **ソース evidence**: `policerorch.cpp:157-169`, `policerorch.cpp:394-407`, `orchdaemon.cpp:396-402`

## 参照カウント管理

| 参照元テーブル | increaseRefCount | decreaseRefCount | タイミング |
|--------------|-----------------|-----------------|----------|
| `MIRROR_SESSION` | `MirrorOrch::createEntry()` L438 | `MirrorOrch::deleteEntry()` | session 作成/削除 |
| `ACL_RULE` (P4 orch) | P4 ACL rule 作成時 | P4 ACL rule 削除時 | rule install/uninstall |

参照カウント > 0 の POLICER への DEL は `SWSS_LOG_INFO` のみで永続保留される (`policerorch.cpp:563-568`)。
参照元 (MIRROR_SESSION 等) を先に削除して参照カウントを 0 にする必要がある。

## まとめ: POLICER の参照関係グラフ

```
MIRROR_SESSION.policer ──(task_need_retry まで待機)──→ POLICER
ACL_RULE (P4)          ──(POLICER OID 取得)────────→ POLICER
acl_loader (表示)      ──(読み取り専用)─────────────→ POLICER
COPP_GROUP             ──(直接参照なし: インライン)──×
PORT_STORM_CONTROL     ──(内部生成: 共通 PolicerOrch)──×
```

- `MIRROR_SESSION`: 最も重要な暗黙依存。POLICER が先行必要。
- `ACL_RULE` (標準): POLICER の直接参照なし。P4 環境のみ依存。
- `COPP_GROUP`: 独立した内部 SAI policer。`POLICER` テーブルを参照しない。
- `PORT_STORM_CONTROL`: PolicerOrch が兼務するが、`POLICER` テーブルとは独立した SAI policer を生成。
