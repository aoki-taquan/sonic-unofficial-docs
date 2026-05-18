# DEVICE_NEIGHBOR — Phase C 暗黙参照テーブル調査ノート

対象テーブル: `DEVICE_NEIGHBOR`
スキャン範囲:
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_neighbor.yang`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:741,1749,1776,2631-2641`
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd:12-14`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:140,219-224`
- `sonic-utilities/pfcwd/main.py:98,413-416`
- `sonic-utilities/scripts/ecnconfig:282-287`
- `sonic-utilities/show/interfaces/__init__.py:316-344`
- `sonic-utilities/scripts/db_migrator.py:765-766`

---

## 結論

`DEVICE_NEIGHBOR` テーブルは以下のテーブル / リソースを暗黙的に参照する（または参照される）。

---

## YANG leafref: local_port → PORT_LIST.name

`sonic-device_neighbor.yang` の `local_port` フィールドは `sonic-port` モジュールへの leafref を持つ:

```yang
leaf local_port {
    type leafref {
        path /port:sonic-port/port:PORT/port:PORT_LIST/port:name;
    }
}
```

YANG バリデーション時に `PORT_LIST.name` に存在しないポート名は reject される。これは **書き込み時の強制先行参照** であり、`PORT` テーブルがなければ `local_port` を含む DEVICE_NEIGHBOR エントリを書くことができない。

Evidence: `sonic-device_neighbor.yang:52-55`

---

## minigraph.py: DEVICE_NEIGHBOR → port_config.ini (PORT)

`minigraph.py:2631-2636` は `port_config.ini` に存在しないインターフェイス名のエントリを `DEVICE_NEIGHBOR` から除外する:

```python
for nghbr in list(neighbors.keys()):
    if nghbr not in ports:
        print("Warning: ignore interface '%s' in DEVICE_NEIGHBOR...", file=sys.stderr)
        del neighbors[nghbr]
```

つまり minigraph 経由では `PORT` キー空間がフィルタとして機能する。`port_config.ini` に存在するポートのみが `DEVICE_NEIGHBOR` に残る。

---

## minigraph.py: DEVICE_NEIGHBOR → devices dict (DEVICE_METADATA/topology)

`minigraph.py:1749,1776` では `results['DEVICE_NEIGHBOR'][intf]['name']` を使って対向機器タイプを `devices` dict から参照する。

```python
neighbor_router = results['DEVICE_NEIGHBOR'][intf]['name']
if devices[neighbor_router]['type'] != chassis_backend_role:
    phyport_intfs[intf] = {'vnet_name': chassis_vnet}
```

この参照は DEVICE_NEIGHBOR の `name` フィールドが topology `devices` dict のキーと一致することを暗黙的に要求する。

---

## minigraph.py: DEVICE_NEIGHBOR → DEVICE_NEIGHBOR_METADATA 派生

`minigraph.py:2638-2641` では `DEVICE_NEIGHBOR.values()` から `name` フィールドを収集して `DEVICE_NEIGHBOR_METADATA` の対象機器セットを決定する（multi-ASIC 環境）。`DEVICE_NEIGHBOR` の `name` 集合が `DEVICE_NEIGHBOR_METADATA` のエントリ集合の源泉。

---

## bgpcfgd: DEVICE_NEIGHBOR_METADATA 参照（name フィールド経由の間接参照）

`bgpcfgd/managers_bgp.py:219-224` では BGP neighbor 追加時に `DEVICE_NEIGHBOR_METADATA` を参照するが、`DEVICE_NEIGHBOR.name` フィールドが DEVICE_NEIGHBOR_METADATA のキーと一致することを前提としている:

```python
neigmeta = self.directory.get_slot("CONFIG_DB", swsscommon.CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME)
if data['name'] not in neigmeta:
    log_info("DEVICE_NEIGHBOR_METADATA is not ready for neighbor '%s'..." % (nbr, data['name']))
    return False
```

`DEVICE_NEIGHBOR.name` が `DEVICE_NEIGHBOR_METADATA` に未登録の場合、BGP neighbor 確立が silent に失敗する。

---

## pfcwd: DEVICE_NEIGHBOR をポート一覧として参照

`pfcwd/main.py:98` では `get_table('DEVICE_NEIGHBOR')` の返り値をサーバ向きポート候補として使用する。`pfcwd/main.py:413` では `get_table('DEVICE_NEIGHBOR').keys()` を外部ポート一覧として使用する。DEVICE_NEIGHBOR が空の場合、外部ポートが 0 件とみなされる。

---

## ecnconfig: DEVICE_NEIGHBOR をポート一覧として参照

`scripts/ecnconfig:282-287` (非 multi-ASIC 環境) では `get_table('DEVICE_NEIGHBOR')` でポート一覧を取得し、空の場合は `Exception("No active ports detected...")` を raise する。

---

## show interfaces: DEVICE_NEIGHBOR + DEVICE_NEIGHBOR_METADATA を結合参照

`show/interfaces/__init__.py:316-344` では `get_table('DEVICE_NEIGHBOR')` と `get_table('DEVICE_NEIGHBOR_METADATA')` を両方取得して expected neighbor 情報を表示する。

---

## まとめ表

| 参照先テーブル / リソース | 参照方向 | 条件 | evidence |
|--------------------------|---------|------|----------|
| `PORT`（CONFIG_DB） | `local_port` leafref による書き込み時バリデーション | YANG バリデーション有効時は常時 | `sonic-device_neighbor.yang:52-55` |
| `port_config.ini`（ファイルシステム） | minigraph 生成時のフィルタ参照 | minigraph.py 経由での書き込み時 | `minigraph.py:2631-2636` |
| `DEVICE_NEIGHBOR_METADATA`（CONFIG_DB） | `name` フィールドからの派生生成（minigraph）、bgpcfgd での存在チェック | minigraph 経由の初期投入時・BGP neighbor 追加時 | `minigraph.py:2638-2641`, `managers_bgp.py:219-224` |
| `VLAN_MEMBER`（CONFIG_DB） | pfcwd が DEVICE_NEIGHBOR 空時の fallback として参照 | `get_server_facing_ports()` でテーブル空の場合 | `pfcwd/main.py:104-105` |
