# PORT_STORM_CONTROL — Phase H プラットフォーム差異 中間ファイル

生成日: 2026-05-16

## 調査対象ソース

- `sonic-swss/orchagent/policerorch.cpp`
- `sonic-utilities/config/main.py` (is_storm_control_supported 関数)
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/schema.h`

---

## SAI Capability チェック — orchagent 側は非実施

`policerorch.cpp` の `handlePortStormControlTable()` には `sai_query_attribute_capability()` 呼び出しは一切存在しない。

storm control policer は capability チェックなしに SAI へ push される。SAI / ASIC 側が非対応の場合、`sai_policer_api->create_policer()` または `sai_port_api->set_port_attribute()` が `SAI_STATUS_NOT_SUPPORTED` 等を返し、orchagent が `SWSS_LOG_ERROR` を記録して `task_need_retry` または `task_failed` を返す。

## BUM_STORM_CAPABILITY — STATE_DB エントリ

`STATE_DB:BUM_STORM_CAPABILITY|<storm_type>` の `supported` フィールドは **CLI のみ** が参照する。

- CLI (`config/main.py:806-814`): `is_storm_control_supported()` が `STATE_DB` を直接読み、`supported == 0` なら CONFIG_DB への書き込みをスキップし `"Storm-control is not supported on this namespace"` を表示する。
- orchagent: `BUM_STORM_CAPABILITY` エントリを `TableConnector` でサブスクライブしている (`orchdaemon.cpp:401`) が、`policerorch.cpp` 内でその値を参照してロジックを分岐させるコードは存在しない。つまり orchestagent は capability をチェックせずに SAI API を呼ぶ。

## 結論: プラットフォーム差異の実態

| 項目 | 内容 |
|---|---|
| SAI capability query | orchagent は storm control に対して `sai_query_attribute_capability()` を呼ばない |
| ASIC 非対応時の挙動 | SAI が `SAI_STATUS_NOT_SUPPORTED` を返す → orchagent が `task_need_retry` または `task_failed` でログ記録 |
| capability ガード経路 | CLI のみ: `STATE_DB:BUM_STORM_CAPABILITY|<type>` の `supported` フィールドで判定 |
| orchagent 側ガード | なし — 直接 push、SAI エラー任せ |
| CBS / Green / Yellow action | SAI/HW デフォルト依存。YANG・CLI 非公開。プラットフォームにより挙動が異なる可能性 |
| kbps=0 の扱い | YANG 上は 0 を許容するが、SAI/HW 側が 0 を無制限と解釈するかはプラットフォーム依存 |

証跡:
- `policerorch.cpp:121-372` (handlePortStormControlTable 全体)
- `orchdaemon.cpp:395-407`
- `sonic-utilities/config/main.py:806-824`
- `sonic-swss-common/common/schema.h:446`
