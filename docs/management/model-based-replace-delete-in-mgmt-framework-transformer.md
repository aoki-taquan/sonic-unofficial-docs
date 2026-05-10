---
title: Mgmt-Framework Transformer の model-based PUT/REPLACE と DELETE
area: management
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/mgmt/Management_Framework_Transformer_Component_Support_For_Model_based_Replace_And_Delete.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli: []
  yang: []
---

!!! success "裏取りステータス: code-verified (2026-05-10)"
    `sonic-mgmt-common/translib/transformer/` に transformer 本体と `xspec.go:941 case "validate-xfmr"` の処理が入り、`models/yang/annotations/sonic-extensions.yang:78-79 extension validate-xfmr { argument "validate-xfmr-name"; }` で extension 定義が公開されている。テスト用 `openconfig-test-xfmr-annot.yang` でも `sonic-ext:validate-xfmr` を実 annotation として使用しており、HLD で改名された validate-xfmr 名が現行 master に取り込み済み。

# Mgmt-Framework Transformer の model-based PUT/REPLACE と DELETE

## 概要

SONiC の Management Framework Transformer は **YANG（OpenConfig 等）ノードと内部 ABNF / CONFIG_DB スキーマ** を変換するコンポーネント。これまで RESTCONF の `PUT/REPLACE` と `DELETE` は **YANG 階層のどの深さでも正しく動かす** ことに難があった[^1]:

- `PUT`: payload に無い兄弟ノードを残してしまう（純粋な replace ではない）
- `DELETE`: target だけ削除し、その配下を残す

本 HLD は `PUT/REPLACE` と `DELETE` を **YANG 階層の任意の深さで** model 由来の自然な「replace / delete サブツリー」セマンティクスにする[^1]:

- **PUT 完了後**: GET で取れるのは **payload + defaults だけ**（その階層の他データは消える）
- **DELETE 完了後**: GET で配下も含めて空になる
- 親 instance に **無関係な兄弟階層** は影響を受けない

OpenConfig YANG 主体。SONiC YANG への同等対応は Future[^1]。

## 動作仕様

### PUT/REPLACE の処理（2 段階）

```mermaid
flowchart TB
  REQ[PUT/REPLACE<br/>payload + URI] --> S1[Step 1.1<br/>payload を traverse して<br/>annotation で table/key/field を解決<br/>→ create or replace する集合 R を作る]
  S1 --> S2[Step 1.2<br/>URI 配下の YANG hierarchy を<br/>GET-like で traverse し<br/>R に居ない config-true ノードを<br/>「削除対象」としてマーク]
  S2 --> MERGE[R と削除対象集合を merge]
  MERGE --> CVL[CVL 検査]
  CVL --> DBOP[DB 操作 (set/del)]
  DBOP --> READBACK[GET で payload + defaults のみ返る]
```

要点[^1]:

1. **Step 1.1**（payload-driven）:
   - List ノードは payload の各要素を create / replace
   - URI が **存在しない list instance を指す** 場合、そのキーで作る
   - container ノードは entry 単位で create/replace
   - **defaults は payload で運ばれた key instance + その配下** の **同 table 範囲** にのみ適用（深部で別 table に切れたら scope を抜ける）
   - 「複数 owner で 1 table」のとき、target tree 配下の field のみ更新し外側は触らない
2. **Step 1.2**（hierarchy-driven）:
   - URI から下の `config true` を **GET-like で traverse**
   - 各ノードについて R に該当が無ければ delete マーク
   - **non-table-owner**: 該当 table の field だけ削除
   - **table-owner**: instance ごと削除
   - **virtual table**: hierarchy traversal だけ使い、削除対象から **除外**[^1]
   - subtree callback は path 上で呼ばれて結果を merge

### DELETE の処理

PUT の **Step 1.2 と同じ削除フロー** を URI 配下に適用する。Step 1.1 系の payload 処理は無し。例外として **leaf にデフォルト値が定義されている** 場合の DELETE は既存挙動を維持し、**leaf を消すのではなく default にリセット**[^1]。

### `validate-xfmr` annotation（`get-validate` 改名）

旧来 GET 専用だった `get-validate` annotation を **`validate-xfmr`** に改名し、CRUD 全般で使えるようにする[^1]。PUT / DELETE の traversal 中に呼ばれ、ノードが **request 文脈で valid でない** と判定されたら、そのノードと配下は処理 skip される。

例: 機能 disable 中の機能配下の細かい設定は、`validate-xfmr` で「対象外」を返せば PUT/DELETE で勝手に触られない。

### Defaults と DELETE の組合せ（重要）

[^1] の制限事項:

1. **defaults は PUT payload に存在する node とその配下の同 table 範囲のみ** 適用
2. **GET-like delete flow で削除対象になった field / table instance の defaults は適用されない**（つまり明示削除されたら default に戻らずに完全に消える）
3. ただし leaf-only DELETE で default 値があるなら **default にリセット**（既存仕様維持）

<!-- evidence:
source: sonic-net/SONiC/doc/mgmt/Management_Framework_Transformer_Component_Support_For_Model_based_Replace_And_Delete.md#L48-L80 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  1.1 The input json payload is traversed and will be translated to the corresponding tables ... For a list node mapped to a table ...
  1.2 The yang hierarchy from the target URI will be traversed by the infra to identify the tables / instances that are not part of the payload and marked to be deleted.
  Virtual tables will be skipped to be deleted and will be used only for yang hierarchy traversal.
  3) Current annotation of "get-validate" will be changed to "validate-xfmr" so that it can be used for CRUD cases as well as GET.
reasoning: 2 段階処理 / virtual table 除外 / annotation 改名の根拠。
-->

## 設定

### 関連する CONFIG_DB

該当なし。本機能は **transformer infra の挙動変更** であり CONFIG_DB に新スキーマは追加しない。

### 関連する CLI

該当なし。RESTCONF / gNMI 経由の挙動変更。

### 設定例

```bash
# RESTCONF PUT で deep replace
curl -k -X PUT -H "Content-Type: application/yang-data+json" \
  -d '{"openconfig-acl:acl-set":[{"name":"BLOCK","type":"ACL_IPV4", ...}]}' \
  https://<dut>/restconf/data/openconfig-acl:acl/acl-sets/acl-set=BLOCK,ACL_IPV4

# DELETE で配下ごと削除
curl -k -X DELETE \
  https://<dut>/restconf/data/openconfig-acl:acl/acl-sets/acl-set=BLOCK,ACL_IPV4
```

## 制限事項

- 本機能の **対象は OpenConfig YANG 系**[^1]。SONiC YANG への展開は別途 future
- defaults の適用範囲は payload の存在 node + 同 table の配下のみ
- アプリ側 callback（特に **post transformer**）が独自に削除をしていた場合、新挙動と整合させる必要がある
- annotation `get-validate` → `validate-xfmr` への移行はアプリ側の YANG 注釈更新を要する。後方互換期間の取扱は HLD で詳述限定

## 干渉する機能

- **CVL**（Config Validation Library）: 既存どおり呼ばれる
- **subtree transformer / post-transformer callback**: 個別アプリ実装。本機能変更でカバー範囲が変わる
- **gNMI / RESTCONF**: PUT / DELETE のセマンティクス変更による影響先
- **OpenConfig YANG models**: 主対象
- **SONiC YANG**: future scope

## トラブルシューティング

```bash
# Mgmt Framework のログ
docker logs mgmt-framework 2>&1 | tail
sudo journalctl -u mgmt-framework

# RESTCONF の応答コード
curl -i -k -X PUT ... | head -1

# transformer 注釈の確認
ls /usr/sbin/translib*  # 等、実装側で
```

## 引用元

[^1]: `sonic-net/SONiC` `doc/mgmt/Management_Framework_Transformer_Component_Support_For_Model_based_Replace_And_Delete.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
