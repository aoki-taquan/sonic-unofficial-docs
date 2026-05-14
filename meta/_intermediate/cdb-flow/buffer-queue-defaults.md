# Phase A — BUFFER_QUEUE コード由来暗黙デフォルト調査

## 対象フィールド

| フィールド | YANG default | 実装デフォルト | 備考 |
|-----------|-------------|--------------|------|
| `profile` | `0` (YANG leaf default) | なし (実質必須) | |

## field 詳細

### `profile`

**YANG default**: `0`（`sonic-buffer-queue.yang` L67 / L110）
- `BUFFER_QUEUE_LIST.profile` および `VOQ_BUFFER_QUEUE_LIST.profile` どちらも `default 0`。
- 型は `leafref` で `BUFFER_PROFILE.name` を参照。`0` という YANG default は実際には有効な BUFFER_PROFILE 名ではなく、YANG ツール上の書式的プレースホルダ相当。

**実装動作 (buffermgrdyn.cpp L3336–3341)**:
```
if (!successful)
{
    SWSS_LOG_ERROR("Invalid BUFFER_QUEUE configuration on %s: no profile configured", key.c_str());
    return task_process_status::task_failed;
}
```
- `profile` フィールドが SET tuple に含まれていない場合、`successful = false` のまま `task_failed` を返す。
- つまり **実装上 `profile` は必須**。YANG が `default 0` を宣言していても、buffermgrdyn は `profile` フィールドのない BUFFER_QUEUE エントリを `task_failed` で拒否する。
- YANG default と実装の **discrepancy**: YANG 上は省略可能（default 0）だが実装は profile 省略を fatal エラーとして扱う。

**方向チェック (buffermgrdyn.cpp L3318–3325)**:
- `checkBufferProfileDirection(fvValue(i), BUFFER_EGRESS)` を呼び出す。
- profile の方向が `BUFFER_EGRESS` でない場合 `task_failed`（ingress profile を queue に誤設定した場合に検出）。
- 方向属性は BUFFER_PROFILE テーブル自体が持つ（pool 経由で ingress/egress が決まる）。YANG には方向制約なし。

**プロファイル未登録 → retry (bufferorch.cpp L961–974)**:
- `resolveFieldRefValue` が `not_resolved` を返す場合 `task_need_retry`。
- BUFFER_PROFILE がまだ APPL_DB に存在しない場合（書き込み順の問題）、BufferOrch はリトライする。
- この間 BUFFER_QUEUE エントリは保留状態のまま。

**zero profile 名の特殊扱い (bufferorch.cpp L995, L1017)**:
- profile 名に `_zero_` を含む場合、flex counter の追加・削除をスキップ。
- これはトラフィックなし（ゼロ予約）を意味する zero profile の慣用命名規則で、YANG に制約なし。
- admin-down 時に `BufferMgrDynamic::reclaimReservedBufferForPort` が自動的に zero profile へ差し替え (silent substitution)。

### `port` (key)

YANG leafref `PORT.name`。key 部分のため YANG default なし。
- buffermgrd は port 存在を直接はチェックしないが orchagent が `gPortsOrch->getPort()` でチェック → 未存在時 `task_invalid_entry`。

### `qindex` (key)

YANG pattern `(1[0-5]|[0-9])((-)(1[0-5]|[0-9]))?`。key 部分のため default なし。
- 範囲上限を超えるインデックスは orchagent の `port.m_queue_ids.size() <= ind` チェックで `task_invalid_entry`。
- buffermgrdyn では `parseObjectNameFromKey(key, 1)` が空の場合（ids なし）`task_invalid_entry` を返す (L3520)。

## 暗黙デフォルト・乖離まとめ

| 種別 | フィールド | 内容 | evidence |
|------|-----------|------|----------|
| YANG-実装 discrepancy | `profile` | YANG `default 0` だが実装は省略を `task_failed` で拒否（実質必須） | `buffermgrdyn.cpp:3337-3341` |
| 方向制約（YANG になし） | `profile` | profile が ingress 方向の場合 `task_failed` | `buffermgrdyn.cpp:3318-3325` |
| silent substitution (admin-down) | `profile` | port admin-down 時、設定された profile を zero profile に自動差し替えて APPL_DB へ書込み | `buffermgrdyn.cpp:2888-`, `reclaimReservedBufferForPort` |
| dead field / 未サポート removal | `profile`（DEL） | `m_supportRemoving=false` の場合（プラットフォーム制限 `support_removing_buffer_items`）DEL が `task_failed` | `buffermgrdyn.cpp:3355-3358` |
| flexcounter 暗黙スキップ | `profile` | `_zero_` を含む名前 → counter 操作スキップ（YANG に規定なし） | `bufferorch.cpp:995,1017` |
| retry（書込み順依存） | `profile` | BUFFER_PROFILE が未登録の時点で BUFFER_QUEUE が先に届くと retry ループ | `bufferorch.cpp:961-974` |
| プラットフォーム依存 | platform | `queues_to_apply_zero_profile` / `egress_zero_profile` は vendor json ファイル次第。未設定の場合 admin-down で全 queue 削除 or zero profile なしで削除 | `buffermgrdyn.cpp:285-289`, `1332` |
