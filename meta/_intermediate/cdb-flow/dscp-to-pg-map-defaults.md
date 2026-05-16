# Phase A — DSCP_TO_PG_MAP フィールドデフォルト調査

調査日: 2026-05-15

## 調査結論

**`DSCP_TO_PG_MAP` というテーブルは SONiC CONFIG_DB に存在しない。**

SONiC の QoS アーキテクチャでは、DSCP 値から Priority Group (PG) への経路は以下の 2 段マッピングで実現される:

```
DSCP (0-63)
  → Traffic Class (via DSCP_TO_TC_MAP)
  → Priority Group (via TC_TO_PRIORITY_GROUP_MAP)
```

### エビデンス

1. `sonic-swss/orchagent/qosorch.cpp:80-96` — `m_qos_maps` に登録されているテーブル名定数:
   - `CFG_DSCP_TO_TC_MAP_TABLE_NAME` = `"DSCP_TO_TC_MAP"` （存在）
   - `CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME` = `"TC_TO_PRIORITY_GROUP_MAP"` （存在）
   - `DSCP_TO_PG_MAP` に相当する定数は **存在しない**

2. `sonic-buildimage/src/sonic-yang-models/yang-models/` に `sonic-dscp-pg-map.yang` は存在しない。
   実在する YANG モデル（QoS 関連）:
   - `sonic-dscp-tc-map.yang`
   - `sonic-dscp-fc-map.yang`
   - `sonic-tc-priority-group-map.yang`
   - `sonic-port-qos-map.yang`

3. `qosorch.cpp:1329,1342` — handler 登録:
   ```cpp
   m_qos_handler_map.insert(qos_handler_pair(CFG_DSCP_TO_TC_MAP_TABLE_NAME, &QosOrch::handleDscpToTcTable));
   m_qos_handler_map.insert(qos_handler_pair(CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME, &QosOrch::handleTcToPgTable));
   // DSCP_TO_PG_MAP ハンドラは存在しない
   ```

4. `sonic-port-qos-map.yang` の PORT_QOS_MAP リーフ:
   - `dscp_to_tc_map` → `DSCP_TO_TC_MAP` テーブルへの leafref
   - `tc_to_pg_map` → `TC_TO_PRIORITY_GROUP_MAP` テーブルへの leafref
   - `dscp_to_pg_map` に相当するリーフは存在しない

## フィールドデフォルト調査

### `DSCP_TO_TC_MAP` テーブル（段階 1）

| フィールド | デフォルト | 根拠 |
|-----------|-----------|------|
| `name` | ビルド時のみ `AZURE` / `AZURE_UPLINK` | `qos_config.j2` が storage platform でのみ注入 |
| `dscp` (key) | なし（明示的設定必須） | YANG key, 0..63 |
| `tc` | なし（明示的設定必須） | `sonic-types:tc_type` (uint8 0..15; 実質 0..7) |

コード由来デフォルト（`qos_config.j2` フォールバック AZURE マップ）:
- dscp 3,4 → tc 3,4 (lossless)
- dscp 8 → tc 0 (best-effort)
- dscp 46 → tc 5 (EF)
- dscp 48 → tc 6 (CS6)
- その他 → tc 1 (低優先度)

### `TC_TO_PRIORITY_GROUP_MAP` テーブル（段階 2）

| フィールド | デフォルト | 根拠 |
|-----------|-----------|------|
| `name` | プラットフォーム依存 | `qos_config.j2` の `generate_tc_to_pg_map()` マクロ |
| `tc` (key) | なし（明示的設定必須） | `stypes:tc_type` (0..15, 実質 0..7) |
| `pg` | なし（明示的設定必須） | `pattern "[0-7]?"` |

`TC_TO_PRIORITY_GROUP_MAP` の PG 値は YANG で `"[0-7]?"` パターン（0 または空文字も合法）。
qosorch.cpp:895 で `(uint8_t)stoi(fvValue(*i))` と変換 — 例外処理なし、非整数で `std::invalid_argument` 伝播。

## ページ方針

`dscp-to-pg-map.md` は以下を説明するアーキテクチャ解説ページとして作成:
- テーブルが存在しない事実を明記
- 実際のアーキテクチャ（2 段マッピング）を解説
- `DSCP_TO_TC_MAP` と `TC_TO_PRIORITY_GROUP_MAP` へのクロスリファレンス
- `verification: discrepancy-found` でマークし、誤解を防ぐ

## 参照コード

- `sonic-swss/orchagent/qosorch.cpp:80-96` — `m_qos_maps` 登録テーブル一覧
- `sonic-swss/orchagent/qosorch.cpp:235-300` — `DscpToTcMapHandler` (DSCP → TC のみ)
- `sonic-swss/orchagent/qosorch.cpp:880-910` — `TcToPgMapHandler` (TC → PG)
- `sonic-swss/orchagent/qosorch.cpp:1329,1342` — handler 登録
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dscp-tc-map.yang` — DSCP_TO_TC_MAP YANG
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-tc-priority-group-map.yang` — TC_TO_PRIORITY_GROUP_MAP YANG
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port-qos-map.yang` — PORT_QOS_MAP YANG（leafref確認）
