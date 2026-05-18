# cluster フィールド — Phase H Platform 調査ノート

調査日: 2026-05-18
対象ファイル: sonic-buildimage/src/sonic-config-engine/minigraph.py
ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd

## 調査観点

`cluster` フィールドの書き込み経路はシングル ASIC 向け (`parse_png`) と
マルチ ASIC / チャーシス向け (`parse_asic_png`) の 2 本が存在する。
また `DEVICE_METADATA|localhost` への書き込みも存在する。
ASIC 種別・switch_type・VOQ 有無による差異を確認する。

## parse_png (シングル ASIC / 非チャーシス)

`minigraph.py:662-668`:
```python
(lo_prefix, lo_prefix_v6, mgmt_prefix, mgmt_prefix_v6, name, hwsku, d_type,
 deployment_id, cluster, d_subtype, slice_type) = parse_device(device)
device_data = {}
if cluster != None:
    device_data['cluster'] = cluster
```
`DEVICE_NEIGHBOR_METADATA|<device>.cluster` に書き込む。
条件は `if cluster != None:` のみ。ASIC 種別に依存しない。

## parse_asic_png (マルチ ASIC / チャーシス)

`minigraph.py:806-811`:
```python
(lo_prefix, lo_prefix_v6, mgmt_prefix, mgmt_prefix_v6, name, hwsku, d_type,
 deployment_id, cluster, _, slice_type) = parse_device(device)
device_data = {}
if cluster != None:
    device_data['cluster'] = cluster
```
マルチ ASIC 環境では ASIC-scope minigraph で `parse_asic_png` が呼ばれ、
各 ASIC namespace の `DEVICE_NEIGHBOR_METADATA` に書き込む。
書き込み条件・ロジックはシングル ASIC 版と完全に同一。

## DEVICE_METADATA|localhost への書き込み

`minigraph.py:2170-2172`:
```python
cluster = [devices[key] for key in devices
           if key.lower() == hostname.lower()][0].get('cluster', "")
if cluster:
    results['DEVICE_METADATA']['localhost']['cluster'] = cluster
```
シングル ASIC / マルチ ASIC / チャーシスのどの構成でも同一コードパスを通る。
hostname マッチングは大文字小文字を無視。

## VOQ / switch_type 依存の有無

`cluster` フィールドの読み書きパスに `gMySwitchType` / `switch_type` /
`is_voq_mode()` / `is_chassis_device()` 等のプラットフォーム条件分岐は存在しない。
minigraph.py 全体を grep した結果、`cluster` の近傍に switch_type チェックなし。

## SAI 経由の有無

`cluster` フィールドは SAI を経由しない (CONFIG_DB のみ)。
ASIC ベンダー (Broadcom / Mellanox / Marvell 等) の差異なし。

## 結論

| プラットフォーム観点 | 差異 |
|---|---|
| シングル ASIC vs マルチ ASIC | 書き込み関数が異なる (`parse_png` vs `parse_asic_png`) が、ロジック同一 |
| VOQ chassis | 差異なし。`switch_type` 条件分岐なし |
| ASIC ベンダー | 差異なし。SAI 非経由 |
| supervisor / linecard 分離 | 各 host で独立して `DEVICE_METADATA|localhost` に書き込む (cluster スコープは host 単位) |
