# DEVICE_NEIGHBOR_METADATA — Phase F 副次 DB 書込み調査ノート

対象テーブル: `CONFIG_DB DEVICE_NEIGHBOR_METADATA`
調査日: 2026-05-19

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | bgpcfgd — DEVICE_NEIGHBOR_METADATA を参照して BGP ピア設定を FRR へ適用し、STATE_DB に書き込む |
| `sonic-utilities/scripts/db_migrator.py` | db_migrator — `update_edgezone_aggregator_config()` で CABLE_LENGTH テーブルを更新 |
| `sonic-buildimage/files/build_templates/buffers_config.j2` | sonic-cfggen — `type` フィールドでケーブル長を決定し CABLE_LENGTH テーブルへ出力 |
| `sonic-buildimage/files/build_templates/qos_config.j2` | sonic-cfggen — `type` フィールドで PORT_UPLINK/PORT_DOWNLINK を分類し QoS テーブルへ出力 |

---

## 1. bgpcfgd → STATE_DB BGP_PEER_CONFIGURED_TABLE 書き込み

`BGPPeerMgrBase.add_peer()` (`managers_bgp.py:172-243`) は DEVICE_NEIGHBOR_METADATA を参照して BGP ピアのテンプレートを展開する。テンプレート展開成功後に `update_state_db(vrf, nbr, data, "SET")` (`managers_bgp.py:239`) を呼び出し、STATE_DB の `BGP_PEER_CONFIGURED_TABLE` へ書き込む。

```python
# managers_bgp.py:288-289
state_peer_table.set(key, list(sorted(data.items())))
```

- **副次書き込み先**: `STATE_DB BGP_PEER_CONFIGURED_TABLE|<vrf>|<neighbor_ip>`
- **条件**: `constants.bgp.use_neighbors_meta == True` かつ `DEVICE_NEIGHBOR_METADATA` に対応エントリが存在する場合のみ
- **タイミング**: BGP ピアテンプレート展開成功直後（同期）
- **DEL 時**: `update_state_db(vrf, nbr, data, "DEL")` で同エントリを削除 (`managers_bgp.py:293-294`)

## 2. db_migrator → CABLE_LENGTH テーブル更新

`update_edgezone_aggregator_config()` (`db_migrator.py:757-799`) は DB マイグレーション時に DEVICE_NEIGHBOR_METADATA の `type == "EdgeZoneAggregator"` エントリを検索し、対応するインタフェースの `CABLE_LENGTH|AZURE` を `"40m"` に更新する。

- **副次書き込み先**: `CONFIG_DB CABLE_LENGTH|AZURE` の EdgeZoneAggregator 接続ポートフィールド
- **条件**: `type == "EdgeZoneAggregator"` エントリが存在し、かつ CABLE_LENGTH テーブルに不均一な値がある場合
- **タイミング**: DB マイグレーション実行時（1 回限り）
- **冪等性**: 全 cable length が同一の場合は early return（変更なし）

## 3. sonic-cfggen (buffers_config.j2) → CABLE_LENGTH テーブル生成

`buffers_config.j2` は `sonic-cfggen -d -t` 実行時に DEVICE_NEIGHBOR_METADATA の `type` フィールドを参照し、ポートの cable_length を決定して CONFIG_DB に出力する。

- **副次書き込み先**: `CONFIG_DB CABLE_LENGTH|AZURE` 全ポート値
- **条件**: `DEVICE_NEIGHBOR_METADATA` が定義済みで対応エントリが存在する場合
- **タイミング**: `sonic-cfggen -m` / `sonic-cfggen -d -t buffers_config.j2` 実行時（minigraph ロード・設定再生成）

## 4. sonic-cfggen (qos_config.j2) → PORT_UPLINK / PORT_DOWNLINK マップ生成

`qos_config.j2` は DEVICE_NEIGHBOR_METADATA の `type` フィールドを参照し、各ポートを `PORT_UPLINK` / `PORT_DOWNLINK` に分類して QoS 設定テーブルへ出力する。

- **副次書き込み先**: QoS 設定テーブル（QUEUE / SCHEDULER 等）の PORT_UPLINK/PORT_DOWNLINK リスト
- **条件**: `DEVICE_METADATA.localhost.type` が `LeafRouter` または `ToRRouter` で、対応 DEVICE_NEIGHBOR_METADATA エントリが存在する場合
- **タイミング**: `sonic-cfggen -d -t qos_config.j2` 実行時

## 副次書き込みが発生しないケース

| ケース | 理由 |
|--------|------|
| `use_neighbors_meta == False` | bgpcfgd が DEVICE_NEIGHBOR_METADATA を依存として登録せず参照しない → STATE_DB 書き込みなし |
| EdgeZoneAggregator エントリなし | `update_edgezone_aggregator_config()` が早期 return → CABLE_LENGTH 変更なし |
| CABLE_LENGTH テーブルに不均一値なし | db_migrator が冪等判定で終了 → CABLE_LENGTH 変更なし |
| APPL_DB / COUNTERS_DB / FLEX_COUNTER_DB | DEVICE_NEIGHBOR_METADATA は orchagent に到達しないため SAI レイヤ副次書き込みなし |
