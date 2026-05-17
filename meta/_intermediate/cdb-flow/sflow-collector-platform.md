# SFLOW_COLLECTOR テーブル — プラットフォーム差異 (Phase H) 解析メモ

対象: CONFIG_DB の `SFLOW_COLLECTOR` テーブル。

ソース確認: `sonic-swss/cfgmgr/sflowmgrd.cpp`、`sonic-swss/cfgmgr/sflowmgr.cpp`、`sonic-swss/cfgmgr/sflowmgr.h`、`sonic-swss/orchagent/sfloworch.cpp`、`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang`、`sonic-utilities/config/main.py`。

## 1. SAI 非経由 → ASIC 種別の影響なし

`SFLOW_COLLECTOR` テーブルは orchagent / sfloworch には読まれない。`sfloworch.cpp` の全内容を精読したが、`SFLOW_COLLECTOR` / `collector_ip` / `collector_port` / `collector_vrf` への参照は 0 件。`sfloworch` が扱うのは `APP_SFLOW_TABLE` と `APP_SFLOW_SESSION_TABLE` のみ（orchagent → SAI `sai_samplepacket_api`）。

SFLOW_COLLECTOR のデータ経路:
```
CLI / gNMI → CONFIG_DB[SFLOW_COLLECTOR] → (sflowmgrd 非購読) → hsflowd 再起動時に conf 再生成
```
SAI 経路はない。したがって Broadcom / Mellanox / Marvell / Innovium / その他のいずれの ASIC を使用しても、SFLOW_COLLECTOR の書き込み・読み取り挙動は変わらない。

## 2. Multi-ASIC 環境

`sflowmgrd.cpp` は namespace / asic_id の概念を一切持たない。`DBConnector("CONFIG_DB", 0)` で単一の CONFIG_DB（namespace 0）に接続する（`sflowmgrd.cpp:28-31`）。multi-ASIC 環境でも `SFLOW_COLLECTOR` は host-scope の CONFIG_DB に 1 か所だけ存在し、asicN namespace の CONFIG_DB にはコピーされない。

hsflowd は `docker-sflow` コンテナで 1 プロセスとして稼働し、host-scope CONFIG_DB から SFLOW_COLLECTOR を読んで sFlow パケットを外部コレクタに送出する。multi-ASIC では各 ASIC のサンプルパケットが psample/netlink 経由で host に集約され hsflowd が扱う設計（HLD参照）。SFLOW_COLLECTOR 自体の挙動に multi-ASIC 差異はない。

## 3. VOQ chassis

`sflowmgr.cpp` / `sflowmgrd.cpp` に VOQ chassis 固有のコードパスは存在しない。SFLOW_COLLECTOR は supervisor / line-card どちらの CONFIG_DB に書くかを区別するコードもない。community master では VOQ chassis での sFlow 集中コレクタ管理機構は実装されていない。

## 4. collector_vrf = 'mgmt' のプラットフォーム依存性

`sonic-utilities/config/main.py:9327-9329`: CLI は `vrf_name` が `'default'` または `'mgmt'` 以外を拒否する。これはソフトウェア制約であり ASIC 非依存。

`collector_vrf = 'mgmt'` の有効化条件は `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled = 'true'` であり、YANG `must` 制約で保護されている（`sonic-sflow.yang`）。mgmt VRF 機能自体は kernel routing table の設定であり ASIC SAI とは無関係。プラットフォーム（ASIC 種別）に依らず同一挙動。

## 5. IPv6 コレクタ

YANG `sonic-sflow.yang` で `collector_ip` の型は `inet:ip-address` であり IPv4 / IPv6 両対応。hsflowd の IPv6 コレクタ接続可否は hsflowd 実装（ライブラリ）に依存するが、CONFIG_DB 書き込み・読み取り経路はプラットフォーム非依存。

## 結論

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | 影響なし | SAI 非経由。SFLOW_COLLECTOR は CONFIG_DB 書き込み→hsflowd conf 再生成のみ |
| Multi-ASIC | 影響なし | sflowmgrd は host-scope CONFIG_DB のみ接続。namespace 分岐なし (`sflowmgrd.cpp:28-31`) |
| VOQ chassis | 影響なし | VOQ 固有コードなし。chassis 集中管理機構は未実装 |
| collector_vrf = 'mgmt' | mgmt VRF 有効化が前提 | ソフトウェア制約（kernel routing table）。ASIC 非依存 |
| IPv6 コレクタ | CONFIG_DB 経路は同一 | hsflowd 実装依存だが DB 経路は ASIC 非依存 |

ソース証跡: `sonic-swss/cfgmgr/sflowmgrd.cpp:28-41`（DB 接続・TableConnector）、`sonic-swss/orchagent/sfloworch.cpp`（COLLECTOR 参照なし）、`sonic-utilities/config/main.py:9314-9331`（CLI VRF 制約）、`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang`（YANG must / max-elements）。
