# PORT_QOS_MAP 順序依存分析 (Phase B)

ソース: `sonic-swss/orchagent/qosorch.cpp`

## 1. MAP 先行必須（各 QoS map table が先に存在しなければならない）

`handlePortQosMapTable` → `resolveFieldRefValue` でフィールド値（map 名）を解決する。
解決失敗（参照先 map が未作成）時は即座に `task_need_retry` を返し、イベントループで再試行される。

対象フィールドと SAI 属性の対応（`qosorch.cpp:61-72`）:

| フィールド | 参照先 CONFIG_DB テーブル | SAI 属性 |
|---|---|---|
| `dscp_to_tc_map` | `DSCP_TO_TC_MAP` | `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` |
| `mpls_tc_to_tc_map` | `TC_TO_TC_MAP` | `SAI_PORT_ATTR_QOS_MPLS_EXP_TO_TC_MAP` |
| `dot1p_to_tc_map` | `DOT1P_TO_TC_MAP` | `SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP` |
| `tc_to_queue_map` | `TC_TO_QUEUE_MAP` | `SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` |
| `tc_to_dot1p_map` | `TC_TO_DOT1P_MAP` | `SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DOT1P_MAP` |
| `tc_to_dscp_map` | `TC_TO_DSCP_MAP` | `SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP` |
| `tc_to_pg_map` | `TC_TO_PRIORITY_GROUP_MAP` | `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` |
| `pfc_to_pg_map` | `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` | `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` |
| `pfc_to_queue_map` | `MAP_PFC_PRIORITY_TO_QUEUE` | `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP` |
| `scheduler` | `SCHEDULER` | `SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID` |

**根拠**: `qosorch.cpp:2118-2130` — `resolveFieldRefValue` が失敗すると `task_need_retry`。

## 2. PORT 先行（ポートが gPortsOrch に登録されていなければならない）

`handlePortQosMapTable` の SET パスでは `gPortsOrch->getPort(port_name, port)` を呼び出す (`qosorch.cpp:2180`)。
ポートが未登録の場合は `SWSS_LOG_ERROR` + `continue`（スキップ）。DEL パスも同様 (`qosorch.cpp:2068`)。

さらに `doTask(Consumer)` の冒頭で `gPortsOrch->allPortsReady()` を確認し (`qosorch.cpp:2258`)、
false であれば全処理をスキップする（初期化段階では PORT_QOS_MAP 処理を一切行わない）。

**順序**: PORT テーブルのすべての対象ポートが `PortsOrch` に登録済みになってから PORT_QOS_MAP を SET する。

## 3. global vs per-port 順序

`key == PORT_NAME_GLOBAL` の場合は専用ハンドラ `handleGlobalQosMap` を呼び出す (`qosorch.cpp:2053-2056`)。

- `global` エントリは `dscp_to_tc_map` **のみ** サポート。他フィールドは `SWSS_LOG_WARN` でスキップ (`qosorch.cpp:2011-2014`)。
- `global` の dscp_to_tc_map は `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` で Switch レベルに適用（ポート属性ではない）。
- per-port エントリは全フィールドを `sai_port_api->set_port_attribute()` で個別ポートに適用。

**順序依存**: `global` エントリと per-port エントリは独立して処理される（相互ブロックなし）。
ただし per-port で同じフィールドを設定した場合、ポートは global の Switch レベル設定を上書きする形になる（SAI の仕様上、port 属性が switch 属性より優先）。

## 4. doTask() 内 SAI bind 順序

`QosOrch::doTask()` (`qosorch.cpp:2231-2251`) は以下の順で drain する:

1. **MAP 系テーブル（DSCP_TO_TC_MAP / TC_TO_QUEUE_MAP / SCHEDULER 等）を先に drain**
   - `port_qos_map_cfg_exec` と `queue_exec` 以外の executor を先に処理
2. **PORT_QOS_MAP を後に drain** (`port_qos_map_cfg_exec->drain()`)
3. **QUEUE テーブルを最後に drain** (`queue_exec->drain()`)

これにより「MAP が作られてから PORT_QOS_MAP が適用される」というイベントループ内の自然な順序が保証される。
1 イベントループで全テーブルが同時投入された場合でも、MAP 系の処理が PORT_QOS_MAP より先になる。

## 5. DEL 時の逆順序

`handlePortQosMapTable` DEL パスでは、PORT_QOS_MAP エントリを削除する際に対応 SAI 属性を `SAI_NULL_OBJECT_ID` に設定してから reference を除去する (`qosorch.cpp:2082-2108`)。

**DEL 順序原則**: 
- PORT_QOS_MAP を先に DEL → SAI reference を解除
- その後で参照先 MAP テーブル（DSCP_TO_TC_MAP 等）を DEL

逆順（MAP を先に DEL）すると SAI reference カウントが残り、SAI ドライバ側で削除エラーが発生する可能性がある。

## 6. pfc_enable / pfcwd_sw_enable の処理順序

SET パス内で map フィールドを全て `update_list` に収集後、以下の順でポートに適用する (`qosorch.cpp:2187-2224`):

1. `update_list` の SAI 属性（map 系）を `set_port_attribute` で全て適用
2. `getPortPfc` で現在の PFC bitmask を取得
3. `pfc_enable || old_pfc_enable` が true の場合のみ `setPortPfc` を呼び出し
4. `pfcwd_sw_enable` は **無条件に** `setPortPfcWatchdogStatus` を呼び出し（0 も適用）

**非対称点**: `pfc_enable` は現在値との OR チェックで呼び出しをスキップできるが、`pfcwd_sw_enable` は省略しても 0 として適用される。

## 証跡まとめ

| 順序ルール | ソース行 |
|---|---|
| MAP 先行必須 (task_need_retry) | `qosorch.cpp:2126-2129` |
| PORT 先行 (allPortsReady) | `qosorch.cpp:2258` |
| PORT 先行 (getPort skip) | `qosorch.cpp:2068, 2180` |
| global は dscp_to_tc_map のみ | `qosorch.cpp:2011-2014` |
| global → switch level SAI bind | `qosorch.cpp:2030` |
| doTask drain 順序 | `qosorch.cpp:2238-2251` |
| DEL で SAI_NULL_OBJECT_ID | `qosorch.cpp:2082-2097` |
| pfc_enable 条件付きスキップ | `qosorch.cpp:2213` |
| pfcwd_sw_enable 無条件適用 | `qosorch.cpp:2224` |
