# PIM_GLOBALS / PIM_INTERFACE — Phase C: 暗黙参照テーブル調査

調査日: 2026-05-17
対象ファイル:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

---

## 1. frrcfgd における PIM 関連テーブルの購読構造

`BGPConfigDaemon` の `__init__()` 内で `table_handler_list` に登録されるテーブルと handler の対応 (frrcfgd.py L2293-2340):

```python
('VRF',                 self.vrf_handler),
('PIM_GLOBALS',         self.bgp_table_handler_common),
('PIM_INTERFACE',       self.bgp_table_handler_common),
('IGMP_INTERFACE',      self.bgp_table_handler_common),
('IGMP_INTERFACE_QUERY',self.bgp_table_handler_common),
```

起動時に `config_db.get_table_data()` で全テーブルの初期データを一括取得し、変更イベントは `config_db.subscribe()` で受信する (frrcfgd.py L2340-2361)。

## 2. PIM 処理ハンドラが暗黙参照するテーブル

### VRF テーブル (間接依存)

`PIM_GLOBALS` ハンドラ (frrcfgd.py L3805-3821) は `vrf = prefix` として抽出した VRF 名を `cmd_prefix = ['configure terminal', 'vrf {}'.format(vrf)]` に使用する。frrcfgd は `VRF` テーブルの存在を確認せずに直接 vtysh コマンドを発行するため、`VRF` エントリが CONFIG_DB に存在しない (≒ カーネル VRF が未作成) の場合、vtysh が失敗して LOG_ERR が出力される。

`VRF` テーブルは frrcfgd の `vrf_handler` が専用に処理し (frrcfgd.py L2294, L2415-2467)、VRF 作成/削除時に BGP インスタンスの設定を整合させる。PIM テーブルは `vrf_handler` には含まれないため、VRF 削除後も PIM_GLOBALS エントリが残る場合は孤立したキャッシュが残存し得る。

### IGMP_INTERFACE / IGMP_INTERFACE_QUERY テーブル (同一 pimd daemon)

`frrcfgd` daemon_table_map (frrcfgd.py L117-120):
```python
'PIM_GLOBALS':          ['pimd'],
'PIM_INTERFACE':        ['pimd'],
'IGMP_INTERFACE':       ['pimd'],
'IGMP_INTERFACE_QUERY': ['pimd'],
```

これら 4 テーブルはすべて同一の `pimd` デーモンへ設定を注入する。ただし frrcfgd は `bgp_table_handler_common` を通じて**独立したコマンドキューで**処理するため、相互の書き込み順序は非同期となる。IGMP は PIM sparse-mode が有効な (`mode = "sm"`) インタフェースで機能するため、`PIM_INTERFACE` の設定が先行していることが前提。

### DEVICE_METADATA (起動時のみ参照)

`BGPConfigDaemon.__init__()` (frrcfgd.py L2162) で `DEVICE_METADATA|localhost` の `bgp_asn` / `vrf_name` / `router_id` 等を読み出す。PIM ハンドラ自体はこれらを直接参照しないが、frrcfgd プロセス全体の初期化に影響する。

## 3. 読み出しのみ / 書き込みなし

PIM ハンドラは CONFIG_DB への書き込みを行わない。frrcfgd は受け取った CONFIG_DB イベントを vtysh コマンドに変換して FRR pimd に注入するのみである。APP_DB / STATE_DB への書き込みも行わない。

## 4. 範囲外テーブル (誤解されやすい)

- `PORTCHANNEL` / `INTERFACE` / `VLAN`: frrcfgd の PIM ハンドラはインタフェース存在確認を行わない。`PIM_INTERFACE` の key に含まれるインタフェース名は vtysh の `interface <if_name>` コンテキストとして直接使用されるのみ。
- `PREFIX_LIST`: `ssm-ranges` フィールドが参照する prefix-list は FRR pimd 内で評価される。frrcfgd は prefix-list 名の文字列を vtysh に渡すだけで、`PREFIX_SET` テーブルを読み出すことはない。
- `ROUTE_MAP`: PIM は route-map を使用しない。frrcfgd の PIM ハンドラは `ROUTE_MAP` テーブルを参照しない。

---

## サマリ

| テーブル | 参照タイミング | 用途 | evidence |
|---------|--------------|------|---------|
| `VRF` | 各イベント (間接) | vtysh `vrf {}` コンテキストの VRF 名として使用 | frrcfgd.py L3808 |
| `IGMP_INTERFACE` | 各イベント (同一 pimd) | PIM sparse-mode と連動する IGMP インタフェース設定 | frrcfgd.py L2132, L2333 |
| `IGMP_INTERFACE_QUERY` | 各イベント (同一 pimd) | IGMP クエリ設定 (query-interval 等) | frrcfgd.py L2133, L2334 |
| `DEVICE_METADATA` | 起動時のみ | frrcfgd 全体の初期化 (bgp_asn 等) | frrcfgd.py L2162 |
