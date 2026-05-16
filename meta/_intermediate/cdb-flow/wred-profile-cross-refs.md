# WRED_PROFILE テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/wred-profile.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/qosorch.cpp`。`WRED_PROFILE` テーブルを名前で参照する CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -n "wred_profile_field_name\|wred_profile\|CFG_WRED_PROFILE_TABLE_NAME" \
    .cache/sonic-sources/sonic-swss/orchagent/qosorch.cpp
```

`qos_to_ref_table_map` (qosorch.cpp:99-117) に `{wred_profile_field_name, CFG_WRED_PROFILE_TABLE_NAME}` が登録されており、`resolveFieldRefValue()` を呼び出す全ハンドラが暗黙的に WRED_PROFILE テーブルへの名前解決を行う。

## 検出された被参照テーブル

### QUEUE テーブル (直接参照)

`QUEUE` テーブルの `wred_profile` フィールドが `WRED_PROFILE` テーブルを名前で参照する。

| 参照元テーブル | 参照フィールド | 参照タイミング | 効果 | evidence |
|---|---|---|---|---|
| `QUEUE` | `wred_profile` | `handleQueueTable()` 内 `resolveFieldRefValue()` | `WRED_PROFILE` エントリ未解決なら `task_need_retry`、解決後 `applyWredProfileToQueue()` で `SAI_QUEUE_ATTR_WRED_PROFILE_ID` を設定 | `qosorch.cpp:1856-1886` |
| `QUEUE` | `wred_profile` (DEL) | `handleQueueTable()` DEL パス | `sai_wred_profile = SAI_NULL_OBJECT_ID` で unbind | `qosorch.cpp:1889-1893` |

**参照解決フロー**:

1. `handleQueueTable(consumer, tuple)` (qosorch.cpp:1815-) 内で `resolveFieldRefValue(m_qos_maps, wred_profile_field_name, qos_to_ref_table_map.at(wred_profile_field_name), tuple, sai_wred_profile, wred_profile_name)` (L1857-1859) を呼び出す
2. `WRED_PROFILE` エントリが未作成の場合 → `ref_resolve_status::not_resolved` → `task_need_retry` (L1864-1867) — QUEUE は WRED_PROFILE の先行作成を待つ
3. 解決成功 → `setObjectReference(m_qos_maps, CFG_QUEUE_TABLE_NAME, key, wred_profile_field_name, wred_profile_name)` (L1886) で参照を登録
4. `applyWredProfileToQueue(port, queue_ind, sai_wred_profile)` (L1936) で `SAI_QUEUE_ATTR_WRED_PROFILE_ID` を SAI に設定

**VoQ スイッチの特殊分岐**: `gMySwitchType == "voq"` の場合、`applyWredProfileToQueue()` (qosorch.cpp:1708-1730) が物理キューではなく VoQ ID に対して WRED を適用する。

### PORT_QOS_MAP テーブル (間接参照なし)

`PORT_QOS_MAP` は `dscp_to_tc`、`tc_to_queue`、`pfc_to_queue` などのマップテーブルを参照するが、`wred_profile` フィールドを持たない。`qos_to_ref_table_map` (qosorch.cpp:99-117) のエントリおよび `handlePortQosMapTable()` (qosorch.cpp:1970-2140) のフィールドループに `wred_profile_field_name` は含まれない。

> **結論**: PORT_QOS_MAP から WRED_PROFILE への直接参照は**なし**。ただし `PORT_QOS_MAP → handlePortQosMapTable() → QUEUE → wred_profile` という間接チェーンは存在する（QUEUE の WRED_PROFILE 参照を通じて関連）。

### SCHEDULER テーブル (参照なし)

`SCHEDULER` テーブルは `QUEUE.scheduler` フィールドから参照されるが、`SCHEDULER` 自身は `WRED_PROFILE` を参照しない。`handleSchedulerTable()` (qosorch.cpp:1333-) および `SchedulerHandler` は WRED 属性を扱わない。

> **結論**: SCHEDULER から WRED_PROFILE への参照は**なし**。QUEUE テーブルが両者（`scheduler` フィールド + `wred_profile` フィールド）を並列参照する関係。

### qos_config.j2 自動生成 (build-time 参照)

`sonic-buildimage/files/build_templates/qos_config.j2:514-660` の QUEUE セクションで RoCE キュー (queue 3, 4 等) に `"wred_profile": "AZURE_LOSSLESS"` を静的設定する。これは build-time のテンプレート展開による参照であり、runtime の `resolveFieldRefValue()` 経由ではない。

| 参照元 | 参照内容 | evidence |
|---|---|---|
| `qos_config.j2` QUEUE セクション | `"wred_profile": "AZURE_LOSSLESS"` (RoCE queue 3,4) | `qos_config.j2:514-660` |

## オブジェクト参照管理 (`m_qos_maps`)

`QosOrch` は `m_qos_maps` (タイプ: `type_map`) で WRED_PROFILE の参照カウントを管理する:

- `CFG_WRED_PROFILE_TABLE_NAME` エントリは `QosOrch` コンストラクタ (qosorch.cpp:86) で `m_qos_maps` に登録
- `setObjectReference` / `removeMeFromObjsReferencedByMe` / `doesObjectExist` で QUEUE → WRED_PROFILE の参照を追跡
- WRED_PROFILE エントリ削除時、参照中の QUEUE が存在する場合の unbind 順序は SAI エラーを防ぐため要注意（`remove_wred()` 前に `SAI_QUEUE_ATTR_WRED_PROFILE_ID = SAI_NULL_OBJECT_ID` が必要）

## まとめ — `wred-profile.md` Phase C 記載対象

| カテゴリ | テーブル・参照元 | 参照フィールド |
|---|---|---|
| 直接名前参照 (runtime) | `QUEUE` | `wred_profile` |
| build-time 静的参照 | `qos_config.j2` QUEUE セクション | `"wred_profile": "AZURE_LOSSLESS"` |
| 参照なし (確認済み) | `PORT_QOS_MAP`、`SCHEDULER` | — |

## 検証コマンド

```bash
grep -n "wred_profile_field_name\|resolveFieldRefValue\|applyWredProfileToQueue" \
    .cache/sonic-sources/sonic-swss/orchagent/qosorch.cpp

grep -n "wred_profile" \
    .cache/sonic-sources/sonic-buildimage/files/build_templates/qos_config.j2
```

このスキャン結果から派生して `docs/reference/config-db/wred-profile.md` の `<!-- cross-refs -->` ブロックを生成する。
