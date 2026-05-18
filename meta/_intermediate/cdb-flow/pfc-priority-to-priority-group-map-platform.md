# PFC_PRIORITY_TO_PRIORITY_GROUP_MAP — Phase H: プラットフォーム差分

<!-- evidence: sonic-swss/orchagent/qosorch.cpp / sonic-buildimage/files/build_templates/qos_config.j2 -->

## 1. テーブル生成の ASIC 制限 (pfc_to_pg_map_supported_asics)

`qos_config.j2:163` に以下が定義されている:

```jinja
{%- set pfc_to_pg_map_supported_asics = ['mellanox', 'barefoot'] -%}
```

`config qos reload` 実行時に `sonic-cfggen` が `qos_config.j2` を展開し、`asic_type` がこのリストに含まれる場合のみ `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` テーブルが CONFIG_DB へ書き込まれる (`qos_config.j2:395-407`)。

| asic_type | テーブル生成 | 投入される map 名 |
|-----------|------------|-----------------|
| `mellanox` | **あり** | `AZURE` (lossless TC 3,4 のみ)、dualtor 時は `AZURE_DUALTOR` も追加 |
| `barefoot` (Intel Tofino) | **あり** | 同上 |
| `broadcom` | なし | — |
| `broadcom-dnx` | なし | — |
| `cisco-8000` | なし | — |
| `marvell-prestera` / `marvell-teralynx` | なし | — |
| `vs` (Virtual Switch) | なし | — |
| その他 | なし | — |

Broadcom / Cisco / Marvell / VS 等では `config qos reload` を実行しても本テーブルは生成されない。デバイス固有の `qos.json.j2` にも `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` の記述は確認されていない。

## 2. QosOrch 側の platform 分岐

`QosOrch::handlePfcPrioToPgTable()` (`qosorch.cpp:984-988`) と `PfcPrioToPgHandler::addQosItem()` (`qosorch.cpp:957-982`) はプラットフォーム識別文字列 (`platform` 環境変数) を一切参照しない。テーブルが CONFIG_DB に存在すれば ASIC 種別に関わらず同一コードパスで `SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP` を作成する。

`orchdaemon.cpp` の QosOrch 登録部 (L366-384) も `platform` 変数による条件分岐なし — `CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME` は無条件で `qos_tables` リストに含まれる。

## 3. multi-asic / VOQ chassis

- **multi-asic**: `QosOrch` は namespace ごとに独立起動するが、`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` の購読コードに namespace 固有の分岐はない。各 namespace のデフォルト QoS config が mellanox/barefoot か否かで生成有無が決まる。
- **VOQ chassis**: `PfcPrioToPgHandler` に VOQ 分岐なし。VOQ 用システムポートへの pfc_to_pg_map 適用は `PORT_QOS_MAP` 側の問題であり、本テーブルのマップオブジェクト作成コードは変わらない。

## 4. ASIC capability 動的照会

`PfcPrioToPgHandler::addQosItem()` は `sai_qos_map_api->create_qos_map()` を直接呼び出し、事前の `querySwitchCapability()` / `querySwitchAttribute()` による capability チェックを行わない。サポート有無は SAI 応答値 (`SAI_STATUS_SUCCESS` 以外) によってのみ判定される。

## 5. 結論

- テーブル生成自体が `asic_type in ['mellanox', 'barefoot']` 条件でゲートされており、それ以外の ASIC では CONFIG_DB に本テーブルが書き込まれることはない (`qos_config.j2:395`)。
- SAI マップ作成コード (QosOrch) は platform 非依存。テーブルが存在すれば全 ASIC で同一パス。
- multi-asic / VOQ chassis での追加分岐なし。
