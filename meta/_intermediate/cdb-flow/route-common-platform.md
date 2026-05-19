# route-common Phase H 調査メモ — プラットフォーム差分

調査対象: `ROUTE_REDISTRIBUTE` テーブル (`sonic-route-common`)
調査ソース:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-common.yang`

## 調査方針

`frrcfgd.py` 全体を対象に、プラットフォーム・ASIC・hwsku・switch_type に依存した条件分岐を全行スキャン。
さらに `DEVICE_METADATA` 参照箇所を精読して挙動差を確認。

## スキャン結果

### docker_routing_config_mode (unified / separated)

`frrcfgd.py:2167-2170` で `DEVICE_METADATA.localhost.docker_routing_config_mode` を読み取る。

```python
if 'docker_routing_config_mode' in db_entry:
    self.config_mode = db_entry['docker_routing_config_mode']
else:
    self.config_mode = "separated"
```

`frrcfgd.py:2344-2357` でこの値を使う分岐:

```python
if self.config_mode == "unified":
    for table, _ in self.table_handler_list:
        table_list = self.config_db.get_table(table)
        for key, data in table_list.items():
            ...
            self.bgp_message.put((self.config_db.serialize_key(key), False, table, upd_data))
            ...
            self.__update_bgp(upd_data_list)
```

- **unified モード**: 起動時に全テーブル（`ROUTE_REDISTRIBUTE` を含む）を CONFIG_DB から読み込み、FRR へ一括リプレイする。SONiC T1/T2 以上では `unified` が標準となる場合がある。
- **separated モード** (デフォルト): 起動時の一括リプレイは行わない。その後の変更イベントのみを購読して処理する。

ROUTE_REDISTRIBUTE の **定常動作ロジック**（SET/DEL イベントの変換処理）は両モードで同一。差分は起動時の初期化シーケンスのみ。

### プラットフォーム固有コード (hwsku / asic_type / switch_type)

`frrcfgd.py` 内に `hwsku`、`asic_type`、`switch_type`、`platform` キーワードへの参照は存在しない。
DEVICE_METADATA から読むのは `bgp_asn` と `docker_routing_config_mode` のみ。

### VOQ Chassis

`frrcfgd.py` に VOQ chassis 固有の分岐コードなし。各 linecard は独自 namespace の CONFIG_DB を持ち、frrcfgd は linecard スコープで独立して動作する。`ChassisAppDbMgr` は `bgpcfgd` 側機能（`bgpcfgd/main.py`）であり、frrcfgd/frrcfgd.py には含まれない。ROUTE_REDISTRIBUTE 処理に VOQ 固有差分なし。

### SmartSwitch (DPU)

frrcfgd は NPU 側 host namespace で動作する。DPU 固有の BGP 設定やルーティングは別テーブル（`BGP_VOQ_CHASSIS_NEIGHBOR` 等）で管理され、frrcfgd.py の ROUTE_REDISTRIBUTE ハンドラに DPU 分岐コードなし。

### multi-asic

multi-asic 構成では frrcfgd が各 namespace（asic0/asic1 …）で独立して起動し、それぞれのホスト namespace CONFIG_DB を購読する。ROUTE_REDISTRIBUTE ロジックに namespace 間での差分コードなし。

### FRR バージョン差

`frrcfgd.py` に FRR バージョン検出・条件分岐コードは存在しない。vtysh コマンド文字列は固定。

## 結論

`docker_routing_config_mode` による**起動時リプレイ有無**が唯一の動作差分。
その他プラットフォーム（VOQ/SmartSwitch/multi-asic）・ASIC ベンダー・FRR バージョンによる差分はなし。
