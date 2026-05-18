# dpu-eni Phase B — ordering 調査メモ

## 対象ページ
docs/reference/config-db/dpu-eni.md

## 調査ソース
- sonic-swss/orchagent/dash/dashenifwdorch.cpp (DpuRegistry::populate, lazyInit, handleNeighUpdate, addAclTable)
- sonic-swss/orchagent/dash/dashenifwdorch.h (class DashEniFwdOrch, EniFwdCtx)
- sonic-swss/orchagent/orchdaemon.cpp (L613-618: SmartSwitch 条件分岐、orchList 追加)

## 発見した順序依存

1. DPU/REMOTE_DPU → VDPU (populate() 内固定順序)
2. DPU系テーブル → DASH_ENI_FORWARD_TABLE (lazyInit は初回ENI受信時)
3. NeighOrch Neighbor解決 → LOCAL ENI ACL ルールインストール
4. VIP_TABLE → addAclTable() (空なら SWSS_LOG_THROW)
5. VNetOrch VNET登録 → CLUSTER ENI ACL ルール生成
6. gMySwitchSubType==SmartSwitch → DashEniFwdOrch 生成 (前提条件)
