# DOT1P_TO_PG_MAP — 暗黙参照調査 (Phase C)

## 調査概要

本ページは `DOT1P_TO_PG_MAP` という実在しないテーブルを扱うが、dot1p → PG の 2 段マッピングを実現する
`DOT1P_TO_TC_MAP` / `TC_TO_PRIORITY_GROUP_MAP` / `PORT_QOS_MAP` 3 テーブルを処理する
`qosorch.cpp` `handlePortQosMapTable()` が読み出す関連テーブルを調査した。

## 調査対象ファイル

- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/qosorch.h`

## grep ログ

```
grep -n "PORT_TABLE\|getPort\|gPortsOrch\|BUFFER_PG\|BUFFER_QUEUE\|DEVICE_METADATA" qosorch.cpp
```

該当行 (抜粋):
- L28: `extern PortsOrch *gPortsOrch;`
- L2068: `if (!gPortsOrch->getPort(port_name, port))` — SET パス、ポート解決
- L2068 (DEL パス L2068 も同): 未登録ポートはエラーログ + `continue` でスキップ
- BUFFER_PG / BUFFER_QUEUE / DEVICE_METADATA への直接参照: 0 hit

## 抽出結果

### qosorch が参照する外部テーブル / リソース

| 参照先テーブル / リソース | 参照方向 | 条件 | evidence |
|--------------------------|---------|------|---------|
| `DOT1P_TO_TC_MAP\|<name>` (CONFIG_DB) | 被参照 (resolveFieldRefValue) | `PORT_QOS_MAP` エントリ SET 時に `dot1p_to_tc_map` フィールドが存在する場合 | `qosorch.cpp:102,2124` |
| `TC_TO_PRIORITY_GROUP_MAP\|<name>` (CONFIG_DB) | 被参照 (resolveFieldRefValue) | `PORT_QOS_MAP` エントリ SET 時に `tc_to_pg_map` フィールドが存在する場合 | `qosorch.cpp:106,2124` |
| `PORT_QOS_MAP\|<port_name>` (CONFIG_DB) | 参照元 (最終適用対象) | 常時。`dot1p_to_tc_map` / `tc_to_pg_map` フィールドを通じて 2 段マップを参照 | `qosorch.cpp:2046-2156` |
| `PORT` (PortsOrch `gPortsOrch->getPort()`) | ポート存在チェック | `PORT_QOS_MAP` SET / DEL 時、key が `global` でない場合 | `qosorch.cpp:2068` |
| `PORT_QOS_MAP\|global` (CONFIG_DB) | グローバル QoS 適用 | `handleGlobalQosMap()` 経路。dot1p 関連属性は global 経路では SAI SWITCH 直接適用なし（DSCP_TO_TC のみ対象） | `qosorch.cpp:1956-2044` |

### 非参照（調査で除外済み）

| テーブル / リソース | 除外理由 |
|-------------------|---------|
| `BUFFER_PG` / `BUFFER_QUEUE` | qosorch.cpp に直接参照なし。BufferOrch が管理 |
| `DEVICE_METADATA` | qosorch.cpp で DOT1P / TC_TO_PG 処理に `DEVICE_METADATA` 参照なし |
| `DSCP_TO_TC_MAP` | `handlePortQosMapTable` 経路では処理されるが DOT1P_TO_PG_MAP ページ対象外 |
