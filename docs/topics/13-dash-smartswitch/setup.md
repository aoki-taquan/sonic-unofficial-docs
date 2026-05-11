---
title: DPU の IP 割当・gNMI 連携・KVM 検証
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/system/smart-switch-ip-address-assignment.md
  - docs/management/smart-switch-gnmi-feedback-design-omit-in-toc.md
  - docs/overlay/dash-sonic-kvm.md
  - docs/architecture/smart-switch-database-design.md
---

# DPU の IP 割当・gNMI 連携・KVM 検証

SmartSwitch / DASH の設定は「DPU の管理面をどう立ち上げるか」「コントローラに状態をどう返すか」「実機を持っていない開発者がどう検証するか」の 3 つに分けて考えると見通しが良くなります。

## DPU 管理 IP の払い出し

NPU と DPU は midplane bridge（通常 `169.254.200.0/24` 系の内部 L2）で繋がります。DPU の管理 IP は、NPU 上で動く DHCP server から払い出されます。手順としては次の流れになります。

1. NPU 起動時に midplane bridge を作成する。
2. NPU 側 DHCP server に DPU 数分のリースエントリを用意する。
3. 各 DPU は boot 時に midplane の DHCP discovery を打ち、IP を取る。
4. DPU は取得した IP で NPU 上の `redisdpuN` へ remote 接続する。

これにより、外部の管理ネットワーク設定なしで NPU が「DPU の親ルータ兼 DHCP サーバ」として完結します。midplane の運用や DPU 数の規模に応じて、bridge のサブネット設計とリース台数を合わせる必要があります。

詳細は [Smart Switch DPU IP アドレス割当](../../system/smart-switch-ip-address-assignment.md) を参照してください。

## コントローラへの gNMI フィードバック

DASH のコントローラは設定をプッシュした後、「DPU が実際に受理して反映できたか」を知る必要があります。SmartSwitch では DPU の `APPL_STATE_DB` に書かれた version_id を NPU 側 gNMI server が読み、コントローラへフィードバックします。

ポイントは次の通りです。

- コントローラは `version_id` を付けて設定を送る。
- DPU 側 orchagent は SAI 反映後、その `version_id` を `APPL_STATE_DB` に書く。
- NPU 側 gNMI server がそれを集約し、subscribe しているコントローラへ返す。
- これによりコントローラは「どの version までが DPU で active か」を確認できる。

この経路は HLD 範囲では `hld-only` の項目もあるため、最新の実装差分は [SmartSwitch gNMI フィードバック設計](../../management/smart-switch-gnmi-feedback-design-omit-in-toc.md) で確認してください。

## DASH SONiC KVM での検証

物理 SmartSwitch がなくても、DASH の動作確認は **BMv2 ベースの仮想 DPU** で行えます。`dash-sonic-kvm` は KVM 上で SONiC を動かし、DPU を BMv2（P4 ソフトウェアスイッチ）として接続することで、`DashOrch` 系 → SAI → BMv2 のループを再現します。

検証で確認できる主な観点は次の通りです。

- `DASH_VNET` / `DASH_ENI` / `DASH_ROUTE` を入れた時の APPL_DB / SAI / BMv2 までの伝搬
- ACL ルール（タグ含む）の挙動
- フロー単位の packet path（VxLAN encap / decap、Service Tunnel など）

実環境投入前のスモークテストと CI に使えますが、性能や HA の細部は実機特性に依存します。詳細は [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md) を参照してください。

## lab と production の違い

| 観点 | lab (KVM / 単機) | production (SmartSwitch 実機) |
|---|---|---|
| DPU | BMv2 仮想 DPU | SoC 実機 + SAI 実装 |
| midplane | 仮想 bridge | 物理 PCIe / midplane SerDes |
| HA | 単 DPU で擬似的に確認 | DPU ペア / 跨ぎ ENI |
| 性能 | データプレーンは BMv2 速度 | line-rate（DPU SAI 依存） |
| 上限 | ENI 数・rule 数は小さく | 規模パラメータは DPU 仕様 |

lab 検証はスキーマや状態遷移の確認に使い、性能・HA フェイルオーバー時間・障害シナリオは実機で確認するのが基本方針になります。

## 関連ページ

- [Smart Switch DPU IP アドレス割当](../../system/smart-switch-ip-address-assignment.md)
- [SmartSwitch gNMI フィードバック設計](../../management/smart-switch-gnmi-feedback-design-omit-in-toc.md)
- [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md)
- [Smart Switch のデータベース構成](../../architecture/smart-switch-database-design.md)
