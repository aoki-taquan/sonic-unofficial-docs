# NVGRE_TUNNEL / NVGRE_TUNNEL_MAP — Phase H: プラットフォーム差

調査日: 2026-05-19
ソース: sonic-swss/orchagent/nvgreorch.cpp, sonic-swss/orchagent/orchdaemon.cpp

## 結論

`NvgreTunnelOrch` / `NvgreTunnelMapOrch` は **全プラットフォームで同一の動作**をする。`orchdaemon.cpp:361-364` で無条件に両 Orch がインスタンス化され、platform 変数や SAI capability 照会による条件分岐はゼロ。

## 証跡

- `nvgreorch.cpp` 全 582 行を `platform|BRCM|MLNX|broadcom|mellanox|barefoot|cisco|namespace|multi_asic` でスキャン → ヒット 0 件
- `nvgreorch.h` 全行同様スキャン → ヒット 0 件
- `orchdaemon.cpp:190` で `platform = getenv("platform")` を読み込むが、その後 NVGRE orch 生成 (L361-364) は無条件ブロック内にある
- L503 以降の `if (platform == BFN_PLATFORM_SUBSTRING || ...)` ブロックは DTEL / FlexCounter / QoS 等を制御するもので、NVGRE には関与しない

## multi-asic / VOQ chassis

orchdaemon はシングルインスタンスで動作し、NVGRE orch は per-asic 分割されない。multi-asic 構成では orchagent が `asic0`/`asic1`/... ごとに起動するが、各 orchagent インスタンスが同じ無条件インスタンス化経路を通るため挙動差なし。

## SAI 実装依存性

`NvgreTunnelOrch` は SAI capability 照会 (`sai_query_attribute_enum_values_capability` 等) を行わない。SAI `create_tunnel(SAI_TUNNEL_TYPE_NVGRE)` が成功するかどうかはハードウェア実装依存だが、orchagent コードレベルでは ASIC 種別を事前チェックしない。非サポート ASIC では SAI が `SAI_STATUS_NOT_SUPPORTED` 等を返し、orchagent が `std::runtime_error` をスローして abort する（Phase D シナリオ 2-4 参照）。
