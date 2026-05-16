# VLAN_MEMBER — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/vlan-member.md` Phase C 追加分。
VLAN_MEMBER は `sonic-vlan.yang` に leafref 定義を持つが、実装側 (`vlanmgrd`) は
YANG バリデーション経路と独立に STATE_DB テーブルを参照して ready 判定を行う。
leafref による宣言的参照と実装上の暗黙参照の両方を網羅する。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/cfgmgr/vlanmgr.cpp` | `VlanMgr::doVlanMemberTask()` / `isMemberStateOk()` / `isVlanStateOk()` / PAC 経路 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang` | leafref・must 制約定義 |

## YANG leafref (宣言的参照)

| フィールド | leafref 先 | 定義箇所 |
|-----------|-----------|---------|
| key[0] `name` | `VLAN/VLAN_LIST/name` | sonic-vlan.yang L283 |
| key[1] `port` | `PORT/PORT_LIST/name` (union 1st) | sonic-vlan.yang L291–292 |
| key[1] `port` | `PORTCHANNEL/PORTCHANNEL_LIST/name` (union 2nd) | sonic-vlan.yang L294–295 |

これらは CVL (Config Validation Library) が CONFIG_DB への書き込み時に検証する。
ただし warm-restart や直接注入の場合は CVL をバイパスするため実装上のチェックが代替となる。

## 暗黙参照 (実装レベル — vlanmgrd)

### 1. VLAN テーブル (STATE_DB — isVlanStateOk)

- **参照先テーブル**: `STATE_DB::STATE_VLAN_TABLE` (`STATE_VLAN_TABLE_NAME`)
- **参照方向**: 存在確認（ready 判定）
- **条件**: `VLAN_MEMBER` エントリを処理する前に毎回確認
- **参照元**: `vlanmgr.cpp:517–531` (`isVlanStateOk()`), L642 (`!isVlanStateOk(vlan_alias)`)
- **意味**: 対応する `Vlan<id>` エントリが STATE_DB に存在しない（VLAN 未作成・未 ready）場合は
  `SWSS_LOG_DEBUG("not ready, delaying")` としてリトライキューに残す。
  VLAN が後から作成されると自動的に再処理される。
- **ブロッキング依存**: VLAN テーブルの ready 化が VLAN_MEMBER 処理の前提必須条件。

### 2. PORT テーブル (STATE_DB — isMemberStateOk)

- **参照先テーブル**: `STATE_DB::STATE_PORT_TABLE` (`STATE_PORT_TABLE_NAME`)
- **参照方向**: 存在確認 + `state` フィールド確認（ready 判定）
- **条件**: port_alias が `PortChannel` プレフィクスで始まらない場合（物理ポート判定）
- **参照元**: `vlanmgr.cpp:503–512` (`isMemberStateOk()` の else ブランチ), L642
- **意味**: `m_statePortTable.get(alias, temp)` が false、または `state` フィールドが存在しない場合は
  not ready 扱い → `delaying` リトライ。物理ポートが netdev として初期化完了するまで待機。
- **ブロッキング依存**: PORT ready 化が VLAN_MEMBER 処理の前提必須条件（LAG と独立）。

### 3. PORTCHANNEL テーブル (STATE_DB — isMemberStateOk, LAG 分岐)

- **参照先テーブル**: `STATE_DB::STATE_LAG_TABLE` (`STATE_LAG_TABLE_NAME`)
- **参照方向**: 存在確認（ready 判定）
- **条件**: port_alias が `PortChannel` (`LAG_PREFIX`) で始まる場合
- **参照元**: `vlanmgr.cpp:495–501` (`isMemberStateOk()` の if ブランチ), L642
- **意味**: `m_stateLagTable.get(alias, temp)` が false の場合は not ready → `delaying` リトライ。
  LAG 自体が LAG orch によって STATE_DB に登録されるまで待機。
- **ブロッキング依存**: PORTCHANNEL ready 化が VLAN_MEMBER 処理の前提必須条件（PORT と独立）。

### 4. VLAN テーブル (CONFIG_DB — CFG_VLAN_TABLE)

- **参照先テーブル**: `CONFIG_DB::CFG_VLAN_TABLE` (`CFG_VLAN_TABLE_NAME`)
- **参照方向**: 初期化時の getKeys によるバルク読み取り
- **条件**: `VlanMgr` 初期化時 (`vlanmgr.cpp:46–47`)
- **参照元**: `m_cfgVlanTable.getKeys(vlanKeys)` で VLAN 一覧を取得し replay 用マップを構築
- **意味**: warm-restart・cold-start 時のリプレイ処理で CONFIG_DB の VLAN エントリを先読みする。
  VLAN が存在しない状態で VLAN_MEMBER エントリが先行している場合の処理順序を制御する。

### 5. VLAN_MEMBER テーブル自体 (STATE_DB — 重複ガード)

- **参照先テーブル**: `STATE_DB::STATE_VLAN_MEMBER_TABLE` (`STATE_VLAN_MEMBER_TABLE_NAME`)
- **参照方向**: 存在確認（重複防止）
- **条件**: SET コマンド処理の冒頭で毎回確認 (L633)
- **参照元**: `vlanmgr.cpp:533–542` (`isVlanMemberStateOk()`), L633, L691
- **意味**: STATE_DB に既に `ok` 状態で存在する場合は重複処理をスキップし `m_vlanMemberReplay` から削除する。
  これにより warm-restart 時の二重処理が防止される。

## 参照関係サマリ

```
VLAN_MEMBER (CONFIG_DB)
  ├─ [YANG leafref] VLAN.name             (key[0] — CVL バリデーション時)
  ├─ [YANG leafref] PORT.name             (key[1] union 1st — CVL バリデーション時)
  ├─ [YANG leafref] PORTCHANNEL.name      (key[1] union 2nd — CVL バリデーション時)
  ├─ [暗黙/STATE] STATE_VLAN_TABLE        (VLAN ready 確認 — ブロッキング依存)
  ├─ [暗黙/STATE] STATE_PORT_TABLE        (PORT ready 確認 — ブロッキング依存)
  ├─ [暗黙/STATE] STATE_LAG_TABLE         (PORTCHANNEL ready 確認 — ブロッキング依存)
  ├─ [暗黙/STATE] STATE_VLAN_MEMBER_TABLE (重複エントリ検出・warm-restart 保護)
  └─ [暗黙/CONFIG] CFG_VLAN_TABLE         (初期化時の replay マップ構築)
```

## evidence

- `vlanmgr.cpp`: L27–36 (テーブル初期化), L491–531 (`isMemberStateOk()` / `isVlanStateOk()`),
  L533–542 (`isVlanMemberStateOk()`), L595–688 (`doVlanMemberTask()` SET 処理),
  L633–642 (ready ガード二重確認)
- `sonic-vlan.yang`: L282–295 (VLAN_MEMBER key leafref 定義)
