# Phase A — DOT1P_TO_PG_MAP フィールドデフォルト調査

調査日: 2026-05-14

## 調査結論

**`DOT1P_TO_PG_MAP` というテーブルは SONiC CONFIG_DB に存在しない。**

SONiC の QoS アーキテクチャでは、dot1p (802.1p PCP) から Priority Group (PG) への経路は以下の 2 段マッピングで実現される:

```
dot1p (0-7)
  → Traffic Class (via DOT1P_TO_TC_MAP)
  → Priority Group (via TC_TO_PRIORITY_GROUP_MAP)
```

### エビデンス

1. `sonic-swss/orchagent/qosorch.h` — `m_qos_maps` に登録されているテーブル名定数:
   - `CFG_DOT1P_TO_TC_MAP_TABLE_NAME` = `"DOT1P_TO_TC_MAP"` （存在）
   - `CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME` = `"TC_TO_PRIORITY_GROUP_MAP"` （存在）
   - `DOT1P_TO_PG_MAP` に相当する定数は **存在しない**

2. `sonic-buildimage/src/sonic-yang-models/yang-models/` に `sonic-dot1p-pg-map.yang` は存在しない。

3. `qos_config.j2` に `DOT1P_TO_PG_MAP` セクションは存在しない。

4. `sonic-swss-common/common/schema.h` に `CFG_DOT1P_TO_PG_MAP_TABLE_NAME` 定数は存在しない。

## フィールドデフォルト（DOT1P_TO_TC_MAP との比較参照）

### `DOT1P_TO_TC_MAP` テーブル（実在、doc 済み）

| フィールド | デフォルト | 根拠 |
|-----------|-----------|------|
| `name` | ビルド時のみ `AZURE` | `qos_config.j2` がストレージバックエンド platform でのみ注入 |
| `dot1p` | なし（明示的設定必須） | YANG pattern `[0-7]?` |
| `tc` | なし（明示的設定必須） | `sonic-types:tc_type` (uint8 0..15) |

ストレージバックエンドプラットフォームのデフォルト値（`qos_config.j2`）:
```
{"0":"1","1":"0","2":"2","3":"3","4":"4","5":"5","6":"6","7":"7"}
```

### `TC_TO_PRIORITY_GROUP_MAP` テーブル（実在、別 doc）

dot1p → PG の第 2 段。`qos_config.j2` の `generate_tc_to_pg_map()` マクロで platform 別に生成。

## ページ方針

`dot1p-to-pg-map.md` は以下を説明するアーキテクチャ解説ページとして作成:
- テーブルが存在しない事実を明記
- 実際のアーキテクチャ（2 段マッピング）を解説
- `DOT1P_TO_TC_MAP` と `TC_TO_PRIORITY_GROUP_MAP` へのクロスリファレンス
- `verification: discrepancy-found` でマークし、誤解を防ぐ

## 参照コード

- `sonic-swss/orchagent/qosorch.cpp:360-427` — `Dot1pToTcMapHandler` (dot1p → TC のみ)
- `sonic-swss/orchagent/qosorch.h:13,18` — フィールド名定数
- `sonic-swss/orchagent/qosorch.cpp:80-96` — `m_qos_maps` 登録テーブル一覧
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dot1p-tc-map.yang` — DOT1P_TO_TC_MAP YANG
