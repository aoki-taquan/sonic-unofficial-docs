# dscp-to-fc-map — Phase B: 書込み順依存 (ordering)

slug: dscp-to-fc-map
phase: B
source: sonic-swss orchagent/qosorch.cpp

## 調査結果

### 依存関係 1: DSCP_TO_FC_MAP → PORT_QOS_MAP (先行必須)

`handlePortQosMapTable()` (qosorch.cpp:2116-2134) はフィールド `dscp_to_fc_map` を受け取ると
`resolveFieldRefValue(m_qos_maps, "dscp_to_fc_map", CFG_DSCP_TO_FC_MAP_TABLE_NAME, ...)` を呼び出す。

参照先 DSCP_TO_FC_MAP エントリが存在しない場合:
- `resolveFieldRefValue` が `ref_resolve_status::success` 以外を返す
- `handlePortQosMapTable` は `task_need_retry` を返す (qosorch.cpp:2128-2130)
- `PORT_QOS_MAP` の SAI 適用が保留される

→ **DSCP_TO_FC_MAP を先に書かないと PORT_QOS_MAP のポートバインドが task_need_retry ループに入る**

### 依存関係 2: DEL 時の参照ロック (逆方向)

`processWorkItem()` (qosorch.cpp:181-186) は DEL 時に
`gQosOrch->isObjectBeingReferenced(...)` を確認する。

`PORT_QOS_MAP` がこのマップ名を `dscp_to_fc_map` フィールドで参照している場合:
- DEL が `m_pendingRemove = true` + `task_need_retry` に変わる
- PORT_QOS_MAP 側の unbind (DEL または `dscp_to_fc_map` フィールド削除) が完了するまで待機

→ **DEL 順序: PORT_QOS_MAP の参照を先に外してから DSCP_TO_FC_MAP を DEL する**

### 依存関係 3: NhgMapOrch (CBF ネクストホップ) との関係

`NhgMapOrch` (cbf/nhgmaporch.cpp) が FC ベースのネクストホップグループマップを管理する。
DSCP_TO_FC_MAP の SAI オブジェクトが存在しないと CBF 転送が機能しない。
NhgMapOrch は直接 DSCP_TO_FC_MAP テーブルを購読しないが、FC 値の有効範囲を
`getMaxNumFcs()` (nhgmaporch.cpp:299-325) で取得する —— これは **SAI 初期化後に解決される**。

→ orchagent 起動順序 (SAI init → QosOrch init) は自動保証されており、ユーザーが意識する必要はない。

### 依存関係 4: config cbf reload の順序

`config cbf reload` は `sonic-cfggen` が `cbf.json.j2` から以下を順に書き込む:
1. `DSCP_TO_FC_MAP` エントリ
2. `EXP_TO_FC_MAP` エントリ
3. `PORT_QOS_MAP` の `dscp_to_fc_map` / `exp_to_fc_map` フィールド

この順序はテンプレートにより保証される。手動で `sonic-db-cli` を使って書く場合は同じ順序を守ること。

## Phase B ブロック (docs 挿入用)

```markdown
<!-- ordering -->
## 書込み順依存 (Phase B)

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DSCP_TO_FC_MAP` SET → `PORT_QOS_MAP` の `dscp_to_fc_map` 参照 | **先行必須**（未存在時は `task_need_retry` ループ） | `resolveFieldRefValue` が自動再試行 |
| 2 | `PORT_QOS_MAP` の `dscp_to_fc_map` 参照解除 → `DSCP_TO_FC_MAP` DEL | **先行必須**（参照中は `m_pendingRemove=true`・DEL 保留） | 参照解除後の次サイクルで自動 DEL 実行 |
| 3 | `config cbf reload` 内部順序 | CLI が 自動保証（DSCP_TO_FC_MAP → EXP_TO_FC_MAP → PORT_QOS_MAP） | 手動 DB 書き込みでは同順序を維持すること |

### 主要な制約詳細

**PORT_QOS_MAP 先行禁止 (依存 #1)**: `handlePortQosMapTable()` は `dscp_to_fc_map` フィールドを処理する際、`resolveFieldRefValue(m_qos_maps, "dscp_to_fc_map", CFG_DSCP_TO_FC_MAP_TABLE_NAME, ...)` でマップ名を解決する。対応する `DSCP_TO_FC_MAP` エントリが存在しない場合は `task_need_retry` を返し、ポートへの SAI バインドが行われない (qosorch.cpp:2124-2130)。`DSCP_TO_FC_MAP` を事前に作成しておくことで即座に処理される。

**参照中 DEL は自動保留 (依存 #2)**: `processWorkItem()` が `isObjectBeingReferenced()` を確認し、`PORT_QOS_MAP` のいずれかのポートエントリが当該マップを参照していれば `m_pendingRemove = true` を立てて `task_need_retry` を返す (qosorch.cpp:181-186)。DEL を成功させるには `PORT_QOS_MAP` エントリの `dscp_to_fc_map` フィールドを先に削除 (または `PORT_QOS_MAP` エントリ自体を DEL) する必要がある。

<!-- /ordering -->
```
