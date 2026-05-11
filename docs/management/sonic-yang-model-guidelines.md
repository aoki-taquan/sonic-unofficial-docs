---
title: SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）
area: management
verification: discrepancy-found
last_verified: 2026-05-11
monitor: evolved_beyond_hld
sources:
  - repo: sonic-net/SONiC
    path: doc/mgmt/SONiC_YANG_Model_Guidelines.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli: []
  yang:
    - sonic-acl
    - sonic-vlan
    - sonic-port
    - sonic-interface
---

!!! warning "裏取りステータス: discrepancy-found（拡張一部のみ）"
    `sonic-buildimage/src/sonic-yang-models/yang-models/` 配下に `sonic-{feature}.yang` の命名規約に沿った 130+ ファイルが存在することは確認済（rule #1）。一方 `yang-templates/sonic-extension.yang.j2` を読むと、定義されている拡張は `db-name` と CVL 用 `custom-validation-cvl` / `dependent-on` 等のみで、**ガイドラインで言及される `map-list` / `key-delim` 拡張は本リポの sonic-extension モジュールには存在しない**。これらは別実装（mgmt-framework 側 yang-extensions など）に分散している可能性があり、ガイドラインの table 5/11/19 に挙げる構文は本リポ単体のスキーマには適合しない。`error-app-tag` の付与状況も yang-models 配下では限定的で、ガイドライン 14 とは差がある。

# SONiC YANG モデル記述ガイドライン（ABNF.json → `sonic-*.yang`）

## 概要

SONiC の YANG モデルは **ABNF.json** で表現された Redis スキーマを RFC 7950 準拠の YANG に写像したもの。Configuration Validation Library (CVL) と SONiC Mgmt Framework が NB API・設定検証で利用する[^1]。本ドキュメントはそのモデルを書く際のガイドライン 21 項[^1] を構造化したもの。

## ガイドライン要約

### ファイル / トップレベル構造

| # | ルール |
|---|--------|
| 1 | 1 機能 1 ファイル。`sonic-{feature}.yang`（例: `sonic-acl.yang` / `sonic-vlan.yang`） |
| 2 | トップレベル container を `sonic-{feature}` という同名で 1 つ置く |
| 3 | namespace は `http://github.com/sonic-net/{model-name}` |
| 4 | 変更時は `revision <YYYY-MM-DD>` を必ず追加し description で何を変えたか記録 |

### ABNF.json からの写像

| # | ルール |
|---|--------|
| 5 | ABNF.json の primary section（dictionary）を YANG `container` にする（`VLAN`、`VLAN_MEMBER` 等そのまま） |
| 6 | `leaf` 名は ABNF キーと **大文字小文字込みで一致**（`PACKET_ACTION`、`IP_TYPE` など） |
| 7 | `leaf type` は **IETF 既存型を優先**（`inet:ipv4-prefix` 等）。SONiC 独自型は共通 header にまとめる |
| 8 | データ階層を ABNF と揃える。例外を作るならコメントで理由を残す |
| 9 | ABNF の primary key は YANG の `key`。Container 名で表すか list の key で表すかは設計判断 |
| 10 | テーブル間参照は `leafref` を使う（例: `ACL_RULE.table_name` → `ACL_TABLE.table_name`） |

### マッピングテーブル / 参照

| # | ルール |
|---|--------|
| 11 | Redis のマッピングテーブル（例: `TC_TO_QUEUE_MAP`）は `list` の入れ子で表現し、外側 list に **`sonic-ext:map-list "true";`** を付ける |
| 12 | ABNF の `ref_hash_key_reference` は `leafref` で表現 |

### 制約 / バリデーション

| # | ルール |
|---|--------|
| 13 | 複雑な相関制約は `must` で書く。例: ルール削除時にテーブルにポートが残っていない、等 |
| 14 | `length` / `pattern` / `range` / `must` には **`error-message` と `error-app-tag`** を付与（NB アプリのエラー表示で使う） |
| 15 | 制約は実コード（`.h` の `#define` 等）または LLD から導出する。例: `IP_TYPE` の enum は `aclorch.h` の `IP_TYPE_*` から生成 |
| 16 | `must` / `when` / `pattern` 条件には背景コメントを必ず添える |

### List 設計

| # | ルール |
|---|--------|
| 17 | ABNF が単一 dict で複数行を持つ場合は `<TABLE>_LIST` という list で表現（例: `PORTCHANNEL_INTERFACE_LIST`） |
| 18 | 1 ABNF テーブルを複数 list に分割する場合は **キー要素数または型を変えて衝突しないように**。同じキー名・要素数・型の 2 list は禁止 |

### State data / RPC / Notification

| # | ルール |
|---|--------|
| 19 | 状態系 (read-only) は `config false;` で別 container。CONFIG_DB 以外の DB なら `sonic-ext:db-name "<DB>"`、key 区切りが `\|` でなければ `sonic-ext:key-delim "<sep>"` を付ける |
| 20 | clear 等の動作命令は **custom RPC**（input / output は省略可）。設定変更を伴う RPC は禁止 |
| 21 | 非同期イベントは `notification`（例: `link_event`） |

## 代表的なパターン

### `must` / `when` で IP_TYPE と prefix 型を整合させる例

```yang
choice ip_prefix {
  case ip4_prefix {
    when "boolean(IP_TYPE[.='ANY' or .='IP' or .='IPV4' or .='IPV4ANY' or .='ARP'])";
    leaf SRC_IP { type inet:ipv4-prefix; }
    leaf DST_IP { type inet:ipv4-prefix; }
  }
  case ip6_prefix {
    when "boolean(IP_TYPE[.='ANY' or .='IP' or .='IPV6' or .='IPV6ANY'])";
    leaf SRC_IPV6 { type inet:ipv6-prefix; }
    leaf DST_IPV6 { type inet:ipv6-prefix; }
  }
}
```

`IP_TYPE` が IPv4 系 / IPv6 系のどちらかでだけ対応する prefix leaf を有効化する[^1]。

### 1 テーブルを複数 list に分けるとき（許可される例）

```text
INTERFACE table:
  "Ethernet1"                   -> { vrf-name: vrf1 }       # キー要素 1
  "Ethernet1|10.184.230.211/31" -> { ... }                  # キー要素 2
```

YANG では **キー要素数で区別** して `INTERFACE_LIST` (key=ifname) と `INTERFACE_IPADDR_LIST` (key="ifname ip_addr") に分割する[^1]。

### 状態データ container の書き方

```yang
container state {
  sonic-ext:db-name "APPL_DB";
  sonic-ext:key-delim ":";
  config false;
  description "State data";
  leaf MATCHED_PACKETS { type yang:counter64; }
  leaf MATCHED_OCTETS  { type yang:counter64; }
}
```

### custom RPC

```yang
rpc clear-stats {
  input {
    leaf aclname  { type string; }
    leaf rulename { type string; }
  }
}
```

### notification

```yang
notification link_event {
  leaf port {
    type leafref {
      path "../../PORT/PORT_LIST/ifname";
    }
  }
}
```

<!-- evidence:
source: sonic-net/SONiC/doc/mgmt/SONiC_YANG_Model_Guidelines.md#L500-L600 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  ### 18. In some cases it may be required to split an ABNF table into multiple YANG lists ...
  Strategies for Ensuring Unique and Unambiguous Keys: Utilize composite keys that have a different number of key elements ...
reasoning: 2023 年 12 月の Rev 1.1 で追加された list キー衝突回避ルール
-->

## 関連ファイル

- 共通型: `sonic-head` / `sonic-common` 等の include 元
- ACL の完整なサンプル: 本 HLD 末尾に `sonic-acl.yang` を例示[^1]

## 制限事項

- 本ガイドラインは **SONiC YANG（southbound 検証 + NB 向け）** を対象。OpenConfig YANG とは別系統
- ABNF.json と完全 1:1 ではなく、`map-list` 等の SONiC 拡張で構造を変えるケースがある

## 干渉する機能

- **CVL**: 本ガイドライン準拠 YANG が無いと `must` / `when` の検証が効かない
- **SONiC Management Framework**: 同 YANG を NB のスキーマとして再利用するため、命名・階層の食い違いは NB API のブレに直結

## 実装との乖離

2026-05-09 時点の現行 master を裏取り。本ガイドラインで前提とされる SONiC YANG 拡張のうち、**`sonic-buildimage` 側の yang-models と `sonic-mgmt-common` 側で取り込み状況が分裂している**点が最大の罠。

| 項目 | HLD ガイドライン | 現行 master | 結果 |
|------|------------|------|------|
| `sonic-ext:db-name` 拡張 | 推奨 | `sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-extension.yang.j2` L18-22 で定義済（southbound 用） | ✓ 整合 |
| `sonic-ext:map-list` 拡張 | 必須 | **`sonic-buildimage` 側の sonic-extension モジュールには存在せず**。一方 `sonic-mgmt-common/models/yang/sonic/common/sonic-extension.yang` L38- には定義あり（NB 用） | ⚠️ リポ間分裂 |
| `sonic-ext:key-delim` 拡張 | 必須 | 同様に `sonic-buildimage` の `sonic-extension.yang.j2` には未定義、`sonic-mgmt-common/models/yang/sonic/common/sonic-extension.yang` L26 のみで定義 | ⚠️ リポ間分裂 |
| `custom-validation-cvl` / `dependent-on` 拡張 | 必須 | `sonic-extension.yang.j2` L24-39 で `{% if yang_model_type == "cvl" %}` ブロックで条件付き定義 | ✓ ただし非 CVL ビルドでは消える |
| 1 ファイル 1 機能 / `sonic-{feature}` 命名 / namespace / revision | 必須 | `sonic-yang-models/yang-models/` に sonic-*.yang が 130 件以上、命名・分割は概ね整合 | ✓ |
| ガイドライン #14: `must` / `when` 違反時の `error-app-tag` | 必須 | サンプリングした `sonic-acl.yang` 等で未付与のものが多数 | ⚠️ 部分実装 |
| ガイドライン #18: list 分割時のキー衝突回避（Rev 1.1 / 2023-12） | 必須 | 個別 yang に対する pyang バリデータでの強制チェックは未確認 | △ |

**差分の中身**:

- `map-list` / `key-delim` は元来 sonic-mgmt-common（NB 側）で導入された拡張で、southbound 側の `sonic-buildimage/sonic-yang-models` には取り込まれていない。両リポでガイドラインの「正」を取り違えると、southbound yang をマッピングする際に拡張未定義エラーになる。
- `error-app-tag` の未付与は機能上は致命的でないが、NB クライアント (gNMI / REST) でのエラー応答可読性が落ちる。

**読者への影響**:

- 新規 yang を書く際に `sonic-ext:map-list` を southbound 用 yang に書くと、`sonic-buildimage` のビルド時に extension 未定義としてバリデーション失敗するケースがある。NB 用 yang（mgmt-common 配下）には書ける。
- ガイドライン準拠を CI で機械的に強制したい場合、`error-app-tag` 等の必須項目を pyang プラグインで lint する仕組みは現状無く、レビューでの目視に依存する。

**回避策 / 対応方法**:

- southbound yang（`sonic-buildimage/src/sonic-yang-models/yang-models/`）では `map-list` / `key-delim` を使わず、`sonic-mgmt-common` 側の同名 yang でのみ使う（責務分担を意識）。
- ガイドライン #14（`error-app-tag`）/ #18（list 分割キー衝突）は既存 yang への遡及修正がほぼ進んでいないため、新規 yang のレビュー時にチェックリスト化するのが現実的。

### 監査 round 2 追補（2026-05-11）

監査 round 2 で再裏取りした結果と、運用者向けの追加情報を補強する。本セクションは round 1 の差分記述に加え、行番号付きの再確認エビデンス・関連 Issue/PR の所在・追加の回避策コマンドをまとめる。

- 拡張定義リポ分裂: `sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-extension.yang.j2` L18-22 に `db-name`、L24-39 に `custom-validation-cvl` / `dependent-on` (`{% if yang_model_type == 'cvl' %}` 条件付き)。一方 `sonic-mgmt-common/models/yang/sonic/common/sonic-extension.yang` には `map-list` (L38-) / `key-delim` (L26) も含む拡張セットを持つ。
- southbound (`sonic-buildimage`) と northbound (`sonic-mgmt-common`) で拡張定義のサブセットが異なるため、HLD のガイドラインを片方リポ視点で読むと欠落エラーになる。
- `error-app-tag` 付与は `sonic-acl.yang` 他で散発的に欠落しているが致命ではない。
- 関連 PR: `map-list` / `key-delim` の southbound 側統合は提案無し。リポ分裂は仕様として固定化されている。
- **追加検証コマンド**: 拡張使用箇所の確認 — `grep -rn 'sonic-ext:map-list\|sonic-ext:key-delim' .cache/sonic-sources/sonic-mgmt-common/models/yang/sonic/` で NB 側のみで使用されることを確認。southbound 側で利用しようとすると `pyang` validation で `unknown extension` エラー。

> 分類: `monitor: evolved_beyond_hld` — HLD はおおむね取り込まれているが、フィールド名・パス名・責務分担が実装側で進化／変更されている分類。実装側を正として読み替える必要がある。

#### 関連 GitHub Issue / PR

- [sonic-buildimage #17348: \[yang\] Sonic yangs with nested lists (list within a list) deviate from Sonic yang modelling guidelines (closed)](https://github.com/sonic-net/sonic-buildimage/issues/17348) — 本ガイドラインからの逸脱を指摘した代表的 issue。
- [sonic-buildimage #10386: \[YANG\]sonic-dot1p-tc-map.yang would cause failed deployment via mgmt-framework (open)](https://github.com/sonic-net/sonic-buildimage/issues/10386) — ガイドライン違反が運用障害となった具体例。
- ABNF.json → sonic-*.yang 変換規約全体の包括的 issue は確認できず、個別の YANG 追加 PR (例 #13314, #10786, #9116) で慣行が蓄積されている。

## 引用元

[^1]: [sonic-net/SONiC doc/mgmt/SONiC_YANG_Model_Guidelines.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/mgmt/SONiC_YANG_Model_Guidelines.md)

<!-- evidence (verifier-batch-19):
- sonic-buildimage `src/sonic-yang-models/yang-models/` に `sonic-*.yang` が 130 件以上存在（命名規約 #1 整合）
- `src/sonic-yang-models/yang-templates/sonic-extension.yang.j2` で定義済の拡張は `db-name`（l.18）のみ。`{% if yang_model_type == "cvl" %}` ブロックで `custom-validation-cvl`, `dependent-on` 等が条件付き追加
- **`map-list` / `key-delim` 拡張の定義は本リポの sonic-extension モジュールに無し**（grep で 0 hit）。HLD ガイドラインで言及されるが、本リポ内 yang ファイルでは未使用
- `error-app-tag` は sonic-acl.yang などでは未付与（ガイドライン 14 と差分）
-->

<!-- concerns hint:
- sonic-yang-models 配下の現行 yang ファイル群が本ガイドライン (1 ファイル 1 機能, sonic-{feature} 命名, namespace, revision) に従っているかサンプリング確認 → 命名・1 ファイル 1 機能は整合
- sonic-ext 拡張 (map-list / db-name / key-delim) が CVL / mgmt-framework の現行コードで実装されているか確認 → db-name のみ、map-list / key-delim は本リポでは未取り込み
- ガイドライン #18 のリスト分割衝突ルール (Rev 1.1) が pyang ベースのバリデータに組み込まれているか確認 → 別途要確認
- must / when 条件の error-app-tag が NB 側 (gNMI/REST) でエラー応答に反映されるか確認 → yang-models 側は未網羅
- ABNF.json と sonic-yang-models のドリフト検出ツールの存在確認 → 別途
-->
