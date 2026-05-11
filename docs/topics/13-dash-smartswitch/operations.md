---
title: HA / PMON / reboot / upgrade の運用
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md
  - docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md
  - docs/platform/smartswitch-pmon-high-level-design.md
  - docs/system/smart-switch-reboot-high-level-design.md
  - docs/platform/smartswitch-dpu-graceful-shutdown.md
  - docs/system/independent-dpu-upgrade.md
---

# HA / PMON / reboot / upgrade の運用

SmartSwitch の運用観点は「どの障害をどの daemon が見て」「どの順序で再起動 / アップグレードするか」に集約されます。NPU / DPU で責務が分かれているため、コマンドを叩く前に経路を意識する必要があります。

## HA: DPU-scope, DPU-driven 構成

DASH-on-SmartSwitch の HA は **DPU 単位のペア（DPU-scope）** で組み、フェイルオーバー判定は **DPU 側のセッション状態を主入力（DPU-driven）** とするのが基本形です。NPU 側 HAMgrD は外側の actor として、DPU ペアの組み合わせ・global state・peer リンクの健全性を管理します。

運用時に押さえる流れは次の通りです。

1. コントローラが HA セット / HA グループを設定する。
2. HAMgrD が peer DPU 間のセッション確立を指示する。
3. DPU の `DashHaOrch` / `DashHaFlowOrch` がフロー単位で sync する。
4. 障害（DPU 単体・peer リンク・NPU 経路）を検知すると HAMgrD が active / standby 切替を駆動する。
5. 復旧後はフロー再同期と active 戻し（switchback）を行う。

実装上の細部は [HAMgrD 設計](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) と [DPU-Scope DPU-Driven HA HLD](../../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) を参照してください。

## PMON の境界

SmartSwitch の `pmon` は NPU 側で動き、DPU を含むハードウェア全体の電源 / 温度 / リセット / PCIe / link をまとめて見ます。DPU 側で個別に走らせるのは DPU 内部の thermal / sensor 程度で、上位の運用 view は NPU 側に集約されます。

確認ポイントは次の通りです。

- DPU の link state（midplane / PCIe / boot 完了）
- DPU の温度・電力
- DPU リセット要求（HAMgrD / 手動 reboot 経由）

詳細は [SmartSwitch PMON HLD](../../platform/smartswitch-pmon-high-level-design.md) を参照してください。

## Reboot 順序

SmartSwitch 全体を reboot する際は、**NPU と DPU を別々に・正しい順序で** 落とす必要があります。データプレーンを止めずに DPU だけ入れ替える運用も想定されているため、reboot path は次の階層に分かれます。

| 操作 | 影響範囲 | 主経路 |
|---|---|---|
| NPU reboot | NPU + 全 DPU | 通常の `reboot` |
| 全 DPU reboot | 全 DPU（NPU 維持） | DPU ごとに gNOI HALT → PCI detach → 個別 reboot |
| 個別 DPU reboot | 1 DPU のみ | gNOI HALT → PCI detach → 該当 DPU reboot |

順序の要点は次の通りです。

1. 対象 DPU に `gnoi.system.Reboot` (HALT) を送り、停止準備を促す。
2. DPU 上の `gnoi_reboot_daemon` が graceful shutdown を実行する。
3. NPU 側で PCI detach する。
4. 物理的に reboot し、戻ったら PCI attach → midplane 再接続 → DPU 側 SONiC 起動。
5. HAMgrD が当該 DPU を再度 HA セットに組み込む。

詳細は [SmartSwitch reboot 順序](../../system/smart-switch-reboot-high-level-design.md) と [DPU Graceful Shutdown](../../platform/smartswitch-dpu-graceful-shutdown.md) を参照してください。

## DPU の独立アップグレード

DPU 単体のソフトウェアアップグレードは「NPU を止めずに DPU だけ image 入替する」運用です。経路は gNOI 系で揃えられ、おおむね次の流れになります。

1. gNOI でターゲット DPU に新 image を転送する。
2. DPU 側で activate / install する。
3. graceful shutdown → reboot → 起動確認 → HA セット復帰。

複数 DPU を 1 台ずつ rolling で回すのが基本で、HA ペアの片側ずつ行うことでサービス継続を保ちます。詳細は [Smart Switch DPU 独立アップグレード](../../system/independent-dpu-upgrade.md) を参照してください。

## 障害ドメイン別の確認順

| 障害 | 最初に見る | 次に見る |
|---|---|---|
| DPU 個別がトラフィックを処理しない | NPU 側 `show platform` / PMON、midplane link、`redisdpuN` 接続 | DPU 側 `DashOrch` / SAI 状態、HAMgrD のセッション state |
| HA フェイルオーバーしない | HAMgrD ログ、`STATE_DB` の HA state | peer link、DPU 側 `DashHaFlowOrch` の sync 状況 |
| ACL が効かない | NPU 側 `ENI_REDIRECT` ACL、`DashEniFwdOrch` | DPU 側 `DASH_ACL_GROUP` / `DASH_ACL_RULE` 反映 |
| Upgrade 後に DPU が戻らない | gNOI ログ、PCI detach / attach、midplane DHCP | DPU 側 boot / `featured` |

## 関連ページ

- [HAMgrD 設計](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md)
- [DPU-Scope DPU-Driven HA HLD](../../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md)
- [SmartSwitch PMON HLD](../../platform/smartswitch-pmon-high-level-design.md)
- [SmartSwitch reboot 順序](../../system/smart-switch-reboot-high-level-design.md)
- [DPU Graceful Shutdown](../../platform/smartswitch-dpu-graceful-shutdown.md)
- [DPU 独立アップグレード](../../system/independent-dpu-upgrade.md)
