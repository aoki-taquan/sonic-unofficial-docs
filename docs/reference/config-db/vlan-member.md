---
title: VLAN_MEMBER テーブル
description: "VLAN_MEMBER テーブル — VLAN とポート (PORT または PORTCHANNEL) のメンバ関係、および各メンバが tagged / untagged のいずれで参加するかを保持する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vlan.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - VLAN
    - VLAN_MEMBER
    - PORT
    - PORTCHANNEL
  cli:
    - config vlan member
  yang:
    - sonic-vlan
---

# VLAN_MEMBER テーブル

## 概要

[VLAN](../../reference/glossary.md#term-vlan) とポート (PORT または PORTCHANNEL) のメンバ関係、および各メンバが tagged / untagged のいずれで参加するかを保持する。VLAN_MEMBER のエントリ追加で `vlanmgrd` が Linux bridge にメンバを add し、`orchagent` が [SAI](../../reference/glossary.md#term-sai) [VLAN](../../reference/glossary.md#term-vlan) member を生成する[^1]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>VLAN")]
  DM["vlanmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>APP_VLAN_TABLE")]
  DM --> APPDB
  SYNCD["syncd"]
  APPDB --> SYNCD
  SAI["SAI<br/>sai_vlan_api"]
  SYNCD --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
VLAN_MEMBER|<vlan_name>|<port>
```

`<vlan_name>` は `VLAN` テーブルへの leafref、`<port>` は PORT または PORTCHANNEL への leafref（union）。

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | leafref `VLAN.name` | ✅ | - | 親 [VLAN](../../reference/glossary.md#term-vlan) |
| `port` (key) | leafref `PORT.name` \| `PORTCHANNEL.name` | ✅ | - | メンバポート / [LAG](../../reference/glossary.md#term-lag) |
| `tagging_mode` | `vlan_tagging_mode` (`tagged`/`untagged`/`priority_tagged`) | ✅ | - | タグ付与モード |

## 制約 (must)

- メンバ port が他の mirror session の `dst_port` であってはならない
- メンバ port が `PORTCHANNEL_MEMBER` のメンバ port になっていてはならない（同一物理ポートの二重所属防止）
- メンバ port が `INTERFACE` (L3) として登録されていてはならない
- 同一 port を `untagged` で登録できる VLAN は最大 1 つ

## 購読者

- `vlanmgrd`: Linux bridge へのメンバ操作
- `orchagent` の `VlanMgr`: [SAI](../../reference/glossary.md#term-sai) VLAN member を生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `VLAN`、`PORT`、`PORTCHANNEL`、`PORTCHANNEL_MEMBER`、`INTERFACE`、`MIRROR_SESSION`
- 関連 CLI: `config vlan member add/del`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-vlan`

<!-- defaults -->
## コード由来の暗黙デフォルト

| フィールド | 暗黙デフォルト | 根拠 | 検出種別 |
|-----------|--------------|------|---------|
| `tagging_mode` | `"untagged"` | vlanmgr.cpp:648 `string tagging_mode = "untagged"`、portsorch.cpp:5916 同じ初期化 | YANG `mandatory true` だが実装側は両 consumer が独立に fallback。cvl バイパス経路（warm-restart・直接注入）で乖離 |
| `tagging_mode` (members@ 経路) | `"untagged"` ハードコード | vlanmgr.cpp:573 `processUntaggedVlanMembers()` | `VLAN` エントリの `members@` フィールド経由の minigraph 互換経路では常に `"untagged"` が注入されユーザー制御不可 |
| `tagging_mode` (PAC 経路) | `"untagged"` ハードコード | vlanmgr.cpp:873 `doVlanPacVlanMemberTask()` | PAC 制御による VLAN_MEMBER は `tagging_mode = "untagged"` 固定 |

### priority_tagged の dead CLI 経路と bridge/SAI 乖離

`priority_tagged` は YANG typedef (`sonic-types.yang`) に列挙されておりコードでも受理されるが、CLI (`config/vlan.py:407`) は `"untagged"` / `"tagged"` のみを書き込み、`priority_tagged` を設定する CLI 経路は存在しない。

加えて、`priority_tagged` と `untagged` は Linux bridge レベルでは同一コマンド (`bridge vlan add ... pvid untagged`) が使われる (vlanmgr.cpp:238) が、orchagent は SAI では `SAI_VLAN_TAGGING_MODE_PRIORITY_TAGGED` として区別する。Linux ホスト転送と ASIC 転送で動作が乖離する。

### APP_DB フィールド欠落伝播

vlanmgr.cpp:672 は CONFIG_DB の raw フィールド列をそのまま APP_DB に転送する (`kfvFieldsValues(t)`)。`tagging_mode` が CONFIG_DB に存在しない場合 APP_DB にも書かれないが、orchagent 側が再度 `"untagged"` で fallback するため二重の暗黙補完が発生する。

### PAC 経路の非公式フィールド注入

`doVlanPacVlanMemberTask()` (vlanmgr.cpp:887) は PAC 経由の VLAN_MEMBER に `{"dynamic": "yes"}` を APP_DB のみに注入する。このフィールドは YANG 定義なく CONFIG_DB には書かれない隠しフィールド。

<!-- /defaults -->

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 実挙動 |
|-----------|-----|--------|
| `tagging_mode` | `untagged` | `bridge vlan add ... pvid untagged`。ポートの PVID として扱われる (vlanmgr.cpp:238) |
| `tagging_mode` | `priority_tagged` | `bridge vlan add ... pvid untagged`（untagged と同一の bridge コマンド） (vlanmgr.cpp:238) |
| `tagging_mode` | `tagged` | `bridge vlan add`（タグあり、pvid/untagged オプションなし） |
| `tagging_mode` | 省略 | `"untagged"` が自動補完される (vlanmgr.cpp:873) |
| `tagging_mode` | その他 | `SWSS_LOG_ERROR("Wrong tagging_mode")` で破棄 (vlanmgr.cpp:659) |

<!-- /value-behavior -->

## 例外条件・特殊挙動 <!-- cdb-exceptions -->

<!-- evidence: sonic-swss/cfgmgr/vlanmgr.cpp; sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang -->

- **キー形式検証**: `Vlan<id>|<port>` 形式必須。`Vlan` プレフィクスがない、またはポート名が含まれない場合 `vlanmgrd` はエントリを破棄する[^exc1]。
- **`tagging_mode` 検証**: `untagged` / `tagged` / `priority_tagged` 以外の値は `SWSS_LOG_ERROR("Wrong tagging_mode")` で破棄される[^exc1]。
- **VLAN / ポート未 ready**: `isVlanStateOk()` または `isMemberStateOk()` が false の場合リトライ待ち（"not ready, delaying"）[^exc1]。
- **重複エントリ**: [STATE_DB](../../reference/glossary.md#term-state_db) に既存の場合は `m_vlanMemberReplay` から削除のみ（"already set"）[^exc1]。
- **重複キー**: consumer pipe 内の重複キーは `SWSS_LOG_WARN("Duplicate key found")` でスキップ[^exc1]。
- **デフォルト補完**: `tagging_mode` 省略時は `"untagged"` が補完される[^exc1]。

[^exc1]: `sonic-swss/cfgmgr/vlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vlanmgr.cpp>

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-vlan`](../yang/sonic-vlan.md)
- CLI: [`config vlan member`](../cli/config-vlan.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-vlan.yang` 内 `VLAN_MEMBER` コンテナ。<https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vlan.yang#L273>

## 関連ページ
- [HLD: Switchport モードと VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md)
- [CLI: config vlan](../cli/config-vlan.md)
- [CONFIG_DB: VLAN](vlan.md)
- [YANG: sonic-vlan](../yang/sonic-vlan.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: L2 / VLAN / LAG / MC-LAG](../../topics/06-l2-vlan-lag/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `VLAN_MEMBER|Vlan100|Ethernet0`。
- `tagging_mode`: `tagged` / `untagged` / `priority_tagged`。

### よくある誤設定

- `tagging_mode: untagged` を 1 ポート上の複数 VLAN に重複指定すると先勝ちで残りが silently 反映されない。
- [PortChannel](../../reference/glossary.md#term-portchannel) メンバを VLAN_MEMBER に直付けすると L2 が壊れる。[LAG](../../reference/glossary.md#term-lag) 親 (`PortChannelN`) を入れる。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'VLAN_MEMBER|Vlan100|Ethernet0'
show vlan brief
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **orchagent / VlanOrch** (`sonic-swss/orchagent/vlanorch.cpp`): `VLAN_MEMBER` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- VlanOrch がポートの VLAN 帰属 (`tagging_mode`) を解析。APP_DB への書き込みなし。

### 段階 3: APPL → SAI

- VlanOrch が `sai_vlan_api->create_vlan_member()` でポートを VLAN に追加。
- `tagging_mode=tagged`: `SAI_VLAN_TAGGING_MODE_TAGGED`、`untagged`: `SAI_VLAN_TAGGING_MODE_UNTAGGED`。

### 段階 4: タイミング + 副作用

- VLAN テーブルと PORT テーブルが両方処理済みであることが前提。
- 副作用: ポートを VLAN から削除すると、そのポートの MAC エントリが FDB から自動削除される。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

VLAN_MEMBER テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config vlan member add/del ...` — `config/vlan.py` が `set_entry('VLAN_MEMBER', (vlan, port), {'tagging_mode': ...})` を呼ぶ (sonic-utilities/config/vlan.py:407, 451)

### minigraph / sonic-cfggen

**minigraph.py** が VLAN_MEMBER を生成し投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での VLAN_MEMBER マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- glossary-links-injected: 6981be1a469d -->
