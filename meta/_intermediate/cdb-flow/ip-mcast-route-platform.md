# ip-mcast-route — Phase H プラットフォーム差 調査メモ

調査日: 2026-05-19
対象ソース:
- sonic-buildimage/rules/config:205-206
- sonic-buildimage/slave.mk:222-242
- sonic-buildimage/rules/docker-p4rt.mk:27-30
- sonic-buildimage/files/build_templates/init_cfg.json.j2:83
- sonic-buildimage/files/build_templates/p4rt.service.j2
- sonic-swss/orchagent/p4orch/ip_multicast_manager.cpp
- sonic-swss/orchagent/p4orch/l3_multicast_manager.cpp
- sonic-swss/orchagent/orchdaemon.cpp:847-849

## 結論

`REPLICATION_IP_MULTICAST_TABLE` / `FIXED_IPV4_MULTICAST_TABLE` / `FIXED_IPV6_MULTICAST_TABLE` の処理ロジック（`IpMulticastManager` / `L3MulticastManager`）に **platform 固有のコードパスは存在しない**。ただし P4RT サービス自体がオプションコンポーネントであり、ビルド時フラグと CPU アーキテクチャ制約によって本テーブルが存在するかどうかが変わる。

## P4RT はビルドオプション (INCLUDE_P4RT)

- `rules/config:206`: デフォルト `INCLUDE_P4RT = n`
- `slave.mk:222-223`: `SONIC_INCLUDE_P4RT=y` 環境変数があれば有効化
- `slave.mk:226-241`: `armhf` および `arm64` では Bazel が利用不可のため **強制 n**（`override INCLUDE_P4RT = n`）
- `init_cfg.json.j2:83`: `INCLUDE_P4RT == "y"` のとき `p4rt` feature エントリ（`disabled, has_per_asic_scope=false`）を `FEATURE` テーブルに追加

実際に P4RT が有効なビルドは community master では Google P4-SDN (PINS) 対応ビルドのみ。device/ ディレクトリ内に `INCLUDE_P4RT = y` を指定している platform は確認されない（community upstream）。

## `p4rt` feature の per-asic スコープ: false

`init_cfg.json.j2:83` の feature タプル `("p4rt", "disabled", false, "enabled")` の第3要素 `false` が `has_per_asic_scope=False` を示す。multi-asic 環境でも p4rt コンテナは host namespace に 1 個のみ起動し、asic0..N には展開されない。

ZMQ エンドポイント `"ipc:///zmq_swss/p4orch_zmq_swss_ep"` も orchdaemon.h で host 固定。

## ip_multicast_manager.cpp / l3_multicast_manager.cpp の platform 分岐: なし

両ファイルを `platform|vendor|asic[0-9]|chassis|multi_asic|is_multi_npu|VS` で grep → 0 ヒット（C++ namespace の `namespace p4orch {}` を除く）。SAI API 呼び出し（`sai_ipmc_group_api->create_ipmc_group()` 等）はすべて platform 非依存の通常 SAI プリミティブ。

## SAI 対応 ASIC の要件

`SAI_OBJECT_TYPE_IPMC_GROUP` / `SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER` / `SAI_OBJECT_TYPE_IPMC_ENTRY` / `SAI_OBJECT_TYPE_RPF_GROUP` を実装した SAI アダプタが必要。VS (virtual switch) SAI はこれらを基本的にスタブ実装。ただしこれは SAI 実装の問題であり、swss 側のスキーマ・書込パスに platform 条件分岐はない。

## FabricOrchDaemon / DpuOrchDaemon での扱い

`orchdaemon.cpp:1292-1310` FabricOrchDaemon::init() には `gP4Orch` の初期化なし。
`orchdaemon.cpp:1322-1380` DpuOrchDaemon::init() には `OrchDaemon::init()` 継承経由で `gP4Orch` が生成される（基底クラス `OrchDaemon::init()` 内の L847-849 が実行される）。

Fabric ノード (LC/SC のファブリックポートのみ管理するノード) では P4Orch が起動しないため、IP マルチキャストテーブルは存在しない。
