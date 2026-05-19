# ipv6-link-local — Phase H プラットフォーム差調査ノート

調査日: 2026-05-19
対象ページ: docs/reference/config-db/ipv6-link-local.md

## 調査方法

- `sonic-swss/cfgmgr/intfmgr.cpp` を `platform|multi_asic|chassis|is_multi_npu|namespace|asic[0-9]|vendor|VOQ|voq|per.asic` で全文 grep
- `sonic-swss/cfgmgr/intfmgrd.cpp` 全体確認
- `sonic-buildimage/files/build_templates/per_namespace/swss.service.j2` 存在確認（per-asic scope 確認）
- `sonic-utilities/config/main.py` の `ipv6` / `enable_use_link_local_only` / `disable_use_link_local_only` の namespace 分岐を確認

## 結論

### ASIC 種別差: なし

`intfmgr.cpp` の `ipv6_use_link_local_only` 処理（L817-926）に Broadcom / Mellanox / Marvell / Innovium などの ASIC 固有コードは存在しない。SAI API も呼ばない（orchagent は dead consumer）ため、ASIC 抽象化レイヤは無関係。

### multi-asic / per-asic namespace: intfmgrd は per-asic 実行

`sonic-buildimage/files/build_templates/per_namespace/swss.service.j2` が存在することから、`swss`（= `intfmgrd` を含む）は multi-asic 環境で asic0, asic1 … 各 namespace で独立インスタンスとして起動する。各インスタンスは対応する namespace の CONFIG_DB / APP_DB / STATE_DB のみを参照する。`intfmgrd.cpp` の `DBConnector` 接続は引数なし（デフォルト namespace）のため、namespace 分離はコンテナ起動時の環境変数 `SONIC_ASIC_ID` で処理される。

### VOQ chassis: link-local 処理への影響なし

`intfmgr.cpp:L103` の `mySwitchType == "voq"` 分岐は IPv6 アドレス付与時の metric 設定専用であり、`ipv6_use_link_local_only` フィールド処理（L817-926）とは独立している。VOQ inband interface (`CFG_VOQ_INBAND_INTERFACE_TABLE_NAME`) もテーブルリストには含まれるが、link-local 処理はインターフェース名プレフィクスで振り分けるため、voq inband (`Ethernet`/`PortChannel` プレフィクス以外のケース) は neighsyncd の `isLinkLocalEnabled()` で false 返却となる。

### CLI の multi-asic namespace 対応

`config ipv6 enable/disable link-local` は `multi_asic.connect_config_db_for_ns(namespace)` を使用し、`-n/--namespace` オプションで対象 namespace を指定できる（multi-asic 環境では必須）。`config interface ipv6 enable/disable use-link-local-only` は `interface` グループの `config_db` を引き継ぐため、`interface` グループの namespace 処理に従う。

### supervisor / line card: 各 host で独立適用

VOQ chassis では supervisor と line card それぞれに独立した `intfmgrd` が稼働し、INTERFACE テーブルは host-local。chassis 全体の集中管理機構はない。

## evidence

- `intfmgr.cpp` grep 結果: platform/multi_asic/namespace 系ヒット 0 件（`using namespace std/swss` のみ）
- `intfmgr.cpp:103`: `mySwitchType == "voq"` は `setIntfIp()` 内の IPv6 アドレス metric 設定のみ
- `intfmgrd.cpp`: `DBConnector("CONFIG_DB", 0)` / `DBConnector("APPL_DB", 0)` / `DBConnector("STATE_DB", 0)` — namespace は環境変数依存
- `per_namespace/swss.service.j2` 存在: swss は per-asic scope = True
- `config/main.py:9495-9506`: `ipv6` グループに `-n/--namespace` オプション、`multi_asic.connect_config_db_for_ns(namespace)` 使用
