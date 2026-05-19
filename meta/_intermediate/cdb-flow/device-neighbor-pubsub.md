# DEVICE_NEIGHBOR — Pub/Sub 調査メモ (Phase G)

## 調査対象

- `sonic-buildimage/dockers/docker-lldp/lldpmgrd`
- `sonic-utilities/pfcwd/main.py`
- `sonic-utilities/scripts/ecnconfig`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
- `sonic-swss/orchagent/` (全 .cpp)

## 結論

`DEVICE_NEIGHBOR` テーブルを **ConsumerStateTable / SubscriberStateTable で動的購読するデーモンは存在しない**。
すべてのコンシューマは起動時または CLI 実行時に `get_table('DEVICE_NEIGHBOR')` でバルク読み込みを行う。

### 各コンポーネントの参照方式

| コンポーネント | 参照方式 | 行番号 |
|-------------|---------|--------|
| `pfcwd start_default` | `config_db.get_table('DEVICE_NEIGHBOR')` (起動時バルク読み) | `pfcwd/main.py:413` |
| `pfcwd get_server_facing_ports()` | `db.get_table('DEVICE_NEIGHBOR')` (CLI 実行時バルク読み) | `pfcwd/main.py:98` |
| `ecnconfig` | `db.get_table('DEVICE_NEIGHBOR')` (CLI 実行時バルク読み) | `ecnconfig:282` |
| `lldpmgrd` | 参照なし（TODO コメントあり: "Also listen for changes in DEVICE_NEIGHBOR"） | `lldpmgrd:12` |
| `bgpcfgd` | `DEVICE_NEIGHBOR_METADATA` を subscribe するが `DEVICE_NEIGHBOR` 本体は参照しない | `main.py:76`, `managers_bgp.py:140` |
| orchagent (`sonic-swss`) | 参照なし | — |

### lldpmgrd の TODO

`lldpmgrd` のソース先頭に以下のコメントがある:

```
TODO: Also listen for changes in DEVICE_NEIGHBOR and PORT tables in
      Config DB and update LLDP config upon changes.
```

現時点では `lldpmgrd` は `SubscriberStateTable` で
`APP_PORT_TABLE`、`CFG_MGMT_INTERFACE_TABLE`、`CFG_DEVICE_METADATA_TABLE` を購読しているが、
`DEVICE_NEIGHBOR` は購読していない（`lldpmgrd:301-310`）。

### CONFIG_DB 書き込み側 (producer)

- `minigraph.py`: `get_neighbors()` / `get_device_neighbors()` が minigraph XML を解析してバルク書き込み
- 他のプロデューサなし（runtime での SET/DEL は `config` CLI 経由のみ）

## 通知チャンネルなし

`DEVICE_NEIGHBOR` に関連する Redis Pub/Sub チャンネル・Notification は存在しない。
テーブル変更は CONFIG_DB の KeySpace notification 経由でのみ観測可能だが、どのデーモンも購読していない。
