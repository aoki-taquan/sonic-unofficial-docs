---
title: JSON Patch ordering（YANG 制約に従う apply-patch のステップ分割）
description: JSON Patch ordering（YANG 制約に従う apply-patch のステップ分割） — config apply-patch
  で投入された JsonPatch (RFC6902) を、SONiC YANG モデル制約を満たしつつ任意の中間状態が valid となるように複数 JsonChange…
area: management
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/config-generic-update-rollback/Json_Patch_Ordering_using_YANG_Models_Design.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - CRM
  - TELEMETRY
  - GNMI
  cli:
  - config apply-patch
  yang:
  - sonic-extension
  - sonic-port
  - sonic-crm
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 10 章: gNMI / OpenConfig / 管理プレーン](../topics/10-gnmi-openconfig/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified"
    `sonic-utilities/generic_config_updater/patch_sorter.py` L2129 `PatchSorterPath` / L2178 `DfsSorter` / L2229 `BfsSorter` / L2268 `MemoizationSorter` / L2349 `StrictPatchSorter` / L2543 `NonStrictPatchSorter` で patch orderer 実装を確認。`sonic-buildimage/src/sonic-yang-mgmt/sonic_yang.py` L283 `validate_data_tree` / L676 `find_data_dependencies` で libyang ラッパーを確認。`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-common.yang` L39 ほかで `import sonic-extension` を確認（verified 2026-05-09）。

# JSON Patch ordering（YANG 制約に従う `apply-patch` のステップ分割）

## 概要

`config apply-patch <jsonpatch>` で投入された JsonPatch (RFC6902) を、**[SONiC](../reference/glossary.md#term-sonic) [YANG](../reference/glossary.md#term-yang) モデル制約を満たしつつ任意の中間状態が valid となるように複数 `JsonChange` に分割** するアルゴリズム[^1]。Generic Config Update and Rollback の "Patch Orderer" 構成要素にあたる。

インタフェース[^1]:

```python
list<JsonChange> order-patch(JsonPatch jsonPatch)
```

- 各 `JsonChange` を順序通り適用すれば running config → target config に到達
- **同一 `JsonChange` 内** の複数操作は順序非保証（applier はそのまま流す）。順序が必要なものは別 `JsonChange` に分ける
- `JsonChange` 適用後の中間 config は **YANG 検証 pass** が必須

## 動作仕様

### 探索 / 制約充足問題への変換

ノード = 「YANG 検証 pass の config 状態」、辺 = 「順序非依存で適用できる `JsonChange`」とするグラフを **DFS / メモ化** で探索する[^1]:

```python
def order_patch(patch):
    cur = get_current_config()
    tgt = simulate_patch(patch, cur)
    return rec(cur, tgt)

mem, visited = {}, {}
def rec(cur, tgt):
    if cur == tgt: return []
    if cur in mem: return mem[cur]
    if cur in visited: return None
    visited[cur] = True
    best = None
    for move in get_all_moves(cur):
        if is_valid(move, cur):
            new = apply_move(move, cur)
            sub = rec(new, tgt)
            if sub is not None and (best is None or len(best) > 1 + len(sub)):
                best = [move] + sub
    mem[cur] = best
    return best
```

メモ化は最短手数最適化に貢献する[^1]。

### 候補 move の生成

`get_all_moves(cur)` は **複数粒度** の移動候補を生やす[^1]:

| 粒度 | 例 |
|------|-----|
| Low level | leaf 値の `replace` / leaf の `remove` / leaf の `add` |
| Upper level | parent そのものを `replace`/`remove`/`add` でまとめて変える |
| Other | `replace` を `remove` に分解 / 参照先がある削除はその参照を先に削除 |

例: `/PORT/Ethernet2` を消すなら、参照側 (`/ACL_TABLE/.../ports/N` や `/VLAN_MEMBER/Vlan100|Ethernet2`) を先に消す `JsonChange` を生やす[^1]。依存解決には `sonic-yang-mgmt/sonic_yang.py` の `find_data_dependencies` を使う想定[^1]。

### 検証

各 move について以下 2 段で検証[^1]:

1. **結果 config 状態**: `validate_data_tree` で YANG 検証
2. **move 自体**: 「2 つの依存ある変更が同 `JsonChange` に同居していないか」をチェック。もし 1 操作の `replace` で全 config を書き換える move を許すと探索が崩壊するため、operation 自体の妥当性も評価対象とする

### `create-only` 拡張

`SAI_PORT_ATTR_HW_LANE_LIST` のように **CREATE_ONLY** な属性は `replace` で書き換え不可。[HLD](../reference/glossary.md#term-hld) は `sonic-extension.yang` に **新拡張 `create-only`** を追加する提案[^1]:

```yang
extension create-only {
  description "During apply-patch operation the field can only be created (i.e. added) or re-created (i.e. removed then added) but cannot be modified (i.e. replaced).";
}
```

例えば `sonic-port.yang` の `lanes`:

```yang
leaf lanes {
  mandatory true;
  ext:create-only;
  type string { length 1..128; }
}
```

評価ルール[^1]:

1. `replace` で `create-only` leaf を書く move は **fail**
2. 親の `replace` で **`create-only` leaf 値が変わる** なら fail
3. 親の `replace` で `create-only` leaf 値が同じなら pass
4. ルール 2/3 は祖父・曾祖父まで再帰

これにより `lanes` 変更は「親 `/PORT/Ethernet0` を `remove` → `add`」経由でしか通らないことが保証される。

### Dynamic Port Breakout の例

100G 1 ポート (`Ethernet0` lanes=`65,66,67,68`) → 10G 4 ポート breakout の場合の出力 `JsonChange` 列[^1]:

```text
1. remove /ACL_TABLE/NO-NSW-PACL-V4/ports
2. remove /VLAN_MEMBER/Vlan100|Ethernet0
3. remove /PORT/Ethernet0
4. add /PORT/Ethernet1 (lanes=66, ...)
5. add /PORT/Ethernet2 (lanes=67, ...)
6. add /PORT/Ethernet0 (lanes=65, ...)
7. add /PORT/Ethernet3 (lanes=68, ...)
8. add /ACL_TABLE/NO-NSW-PACL-V4/ports = [Ethernet0..3]
9-12. add /VLAN_MEMBER/Vlan100|Ethernet{1,2,3,0}
```

`create-only` のおかげで lanes は親ごと recreate され、依存先 (ACL_TABLE.ports / VLAN_MEMBER) は前後で抜き差しされる。

<!-- evidence:
source: sonic-net/SONiC/doc/config-generic-update-rollback/Json_Patch_Ordering_using_YANG_Models_Design.md#L395-L480 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  The new extension `create-only` will be added ...
  1. Fail validation for `replace` move that is updating a field marked with `create-only`.
  2. Fail validation for `replace` move that is updating parent of a field that is marked with `create-only` and the `create-only` field is itself different.
  3. Pass validation for `replace` move that is updating parent of a field that is marked with `create-only` and the `create-only` field is itself the same.
reasoning: create-only 拡張のセマンティクスを直接引用
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/config-generic-update-rollback/Json_Patch_Ordering_using_YANG_Models_Design.md#L395-L480 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/config-generic-update-rollback/Json_Patch_Ordering_using_YANG_Models_Design.md#L395-L480 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    The new extension `create-only` will be added ...
    1. Fail validation for `replace` move that is updating a field marked with `create-only`.
    2. Fail validation for `replace` move that is updating parent of a field that is marked with `create-only` and the `create-only` field is itself different.
    3. Pass validation for `replace` move that is updating parent of a field that is marked with `create-only` and the `create-only` field is itself the same.
    ```

    **判断根拠**: create-only 拡張のセマンティクスを直接引用

<!-- evidence-rendered:end -->

## 主要 CLI コマンド

| Command | 用途 |
|---------|------|
| `config apply-patch <file.json>` | JsonPatch を実 config に適用（内部で patch ordering を行う） |

## 制限事項

- 探索ベースのアルゴリズム上、**大きい patch では計算時間が伸びうる**。本 HLD は scalability 要件を NA としているが実装上は heuristics 必要[^1]
- ConfigDB lock 取得済みであることが呼出側の前提[^1]
- `JsonChange` 内では順序保証なしのため、依存ある変更は必ず別 `JsonChange` に切らなければならない
- `find_data_dependencies` で取れる依存に依存。YANG `must` 経由の暗黙依存（直接 `leafref` ではない）は探索 + 検証で間接的にしか潰せない

## 干渉する機能

- **Generic Config Update and Rollback**: 本機能を内包する上位 HLD
- **`apply-patch` CLI** / **[gNMI](../reference/glossary.md#term-gnmi) Set RPC**: 本 orderer を使う代表的な呼び元
- **Dynamic Port Breakout**: `create-only` 拡張の主要動機
- **[CRM](../reference/glossary.md#term-crm) 等 `must`-based 制約**: ユニットテスト 16 番が直接連動依存と must 依存の両方をカバー[^1]

## 引用元

[^1]: [sonic-net/SONiC doc/config-generic-update-rollback/Json_Patch_Ordering_using_YANG_Models_Design.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/config-generic-update-rollback/Json_Patch_Ordering_using_YANG_Models_Design.md)

<!-- ops-entry -->
## 運用入口

この HLD に対応する運用面の入口（CLI / [CONFIG_DB](../reference/glossary.md#term-config_db) / YANG / Runbook）を以下にまとめる。

### 関連 CLI

- `config apply-patch`

### 関連 YANG

- `sonic-extension`

### 関連 Runbook

- [config-save-diff-unexpected](../reference/runbooks/config-save-diff-unexpected.md)

<!-- /ops-entry -->

<!-- glossary-links-injected: 8038cebfeb87 -->
