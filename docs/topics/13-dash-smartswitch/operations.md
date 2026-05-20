---
title: HA / PMON / reboot / upgrade の運用
description: HA / PMON / reboot / upgrade の運用 — SmartSwitch の運用観点は「どの障害をどの daemon
  が見て」「どの順序で再起動 / アップグレードするか」に集約されます。NPU / DPU で責務が分かれているため、コマンドを叩く前に経路を意識する必要があります。
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
related:
  cli:
  - show platform
  - show acl
  - config acl
  config_db:
  - ACL_RULE
  - ACL_TABLE
  - CHASSIS_MODULE
  - MID_PLANE_BRIDGE
  - DPU
  - DPUS
  - VOQ_INBAND_INTERFACE
  yang:
  - sonic-crm
---

# HA / PMON / reboot / upgrade の運用

[SmartSwitch](../../reference/glossary.md#term-smartswitch) の運用観点は「どの障害をどの daemon が見て」「どの順序で再起動 / アップグレードするか」に集約されます。[NPU](../../reference/glossary.md#term-npu) / [DPU](../../reference/glossary.md#term-dpu) で責務が分かれているため、コマンドを叩く前に経路を意識する必要があります。

## 全体状態の入口

最初に NPU 側で全 DPU の存在と up/down を一覧します。

```bash
admin@smartswitch:~$ show chassis modules status
       Name      Description    Physical-Slot   Oper-Status     Admin-Status
-----------  --------------  ---------------  ------------  ---------------
DPU0          SmartSwitch-DPU            1            Online              up
DPU1          SmartSwitch-DPU            2            Online              up
DPU2          SmartSwitch-DPU            3        Offline              up
DPU3          SmartSwitch-DPU            4            Online              up

admin@smartswitch:~$ show chassis modules midplane-status
       Name        IP-Address    Reachability
-----------  ---------------  ---------------
DPU0           169.254.200.1            True
DPU1           169.254.200.2            True
DPU2           169.254.200.3           False
DPU3           169.254.200.4            True
```

`midplane-status: False` は最も多い「DPU が動かない」事象の入口で、原因は (a) DPU 側 SONiC が boot 途中、(b) midplane DHCP が走っていない、(c) PCI detach 中、のいずれかです。`docker ps | grep redisdpu` と NPU 側 `redis-cli -h redisdpu2 ping` を続けて叩いて、DPU 側 redis 到達性まで踏み込みます。

## HA: DPU-scope, DPU-driven 構成

[DASH](../../reference/glossary.md#term-dash)-on-SmartSwitch の HA は **DPU 単位のペア（DPU-scope）** で組み、フェイルオーバー判定は **DPU 側のセッション状態を主入力（DPU-driven）** とするのが基本形です。NPU 側 HAMgrD は外側の actor として、DPU ペアの組み合わせ・global state・peer リンクの健全性を管理します。

運用時に押さえる流れは次の通りです。

1. コントローラが HA セット / HA グループを設定する。
2. HAMgrD が peer DPU 間のセッション確立を指示する。
3. DPU の `DashHaOrch` / `DashHaFlowOrch` がフロー単位で sync する。
4. 障害（DPU 単体・peer リンク・NPU 経路）を検知すると HAMgrD が active / standby 切替を駆動する。
5. 復旧後はフロー再同期と active 戻し（switchback）を行う。

実装上の細部は [HAMgrD 設計](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) と [DPU-Scope DPU-Driven HA HLD](../../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) を参照してください。

### HA 状態の確認

```bash
admin@smartswitch:~$ redis-cli -n 0 hgetall 'DASH_HA_SET_TABLE:hasetA'
1) "version"
2) "1"
3) "vip_v4"
4) "10.1.0.100"
5) "owner"
6) "switch"
7) "scope"
8) "dpu"
9) "local_ip"
10) "10.1.0.1"
11) "peer_ip"
12) "10.1.0.2"

admin@smartswitch:~$ redis-cli -n 6 hgetall 'DASH_HA_SCOPE_STATE_TABLE:hasetA'
1) "ha_role"
2) "active"
3) "last_state_change_time"
4) "1715200001"
5) "flow_sync_session_count"
6) "1"

admin@smartswitch:~$ docker logs hamgrd 2>&1 | tail -20
2026-05-10T03:21:01.123 INFO hamgrd[hasetA]: peer link healthy, local=active peer=standby
2026-05-10T03:21:11.500 WARN hamgrd[hasetA]: bulk sync timeout, retrying
```

`ha_role` が両側 `active` のままなら split-brain、両側 `standby` なら controller / peer link 障害です。`STATE_DB` の `DPU_STATE` も併せて確認します。

DPU 側にログインして見るときは `redis-cli -h redisdpu0 -n 0` で DPU 側 [APPL_DB](../../reference/glossary.md#term-appl_db) に直接アタッチします（`docker exec -it database bash` 経由）。

### HA 障害ドメインの DB 対応表

| 対象 | DB | テーブル |
|---|---|---|
| HA セット定義 | NPU `APPL_DB` (DB 0) | `DASH_HA_SET_TABLE` |
| HA グループ | NPU `APPL_DB` | `DASH_HA_GLOBAL_TABLE` |
| HA scope state | NPU `STATE_DB` (DB 6) | `DASH_HA_SCOPE_STATE_TABLE` |
| [ENI](../../reference/glossary.md#term-eni) 単位 state | DPU `STATE_DB` | `DASH_ENI_STATE_TABLE` |
| flow sync 状況 | DPU `COUNTERS_DB` | `DASH_HA_FLOW_SYNC_COUNTERS` |

## PMON の境界

SmartSwitch の `pmon` は NPU 側で動き、DPU を含むハードウェア全体の電源 / 温度 / リセット / PCIe / link をまとめて見ます。DPU 側で個別に走らせるのは DPU 内部の thermal / sensor 程度で、上位の運用 view は NPU 側に集約されます。

確認ポイントは次の通りです。

- DPU の link state（midplane / PCIe / boot 完了）
- DPU の温度・電力
- DPU リセット要求（HAMgrD / 手動 reboot 経由）

詳細は [SmartSwitch PMON HLD](../../platform/smartswitch-pmon-high-level-design.md) を参照してください。

### DPU 個別の確認コマンド

```bash
admin@smartswitch:~$ show system-health dpu
   DPU      State    PCI       Midplane    Boot   ASIC-Temp    Power
------  -----------  --------  --------  ------  ----------  --------
DPU0       up        attached  up         done    65 C         55 W
DPU1       up        attached  up         done    63 C         53 W
DPU2       down      detached  down       boot     -            -
DPU3       up        attached  up         done    64 C         54 W

admin@smartswitch:~$ redis-cli -n 6 hgetall 'DPU_STATE|DPU2'
1) "id"
2) "2"
3) "state"
4) "rebooting"
5) "midplane_link"
6) "down"
7) "pcie_link"
8) "detached"
9) "boot_progress"
10) "kernel"
```

`state=rebooting` が数分で `up` に戻らないときは、NPU `pmon` の `chassisd` ログと、midplane に対する DPU 側 DHCP の `journalctl -u dhclient` を NPU 側で確認します。

## Reboot 順序

SmartSwitch 全体を reboot する際は、**NPU と DPU を別々に・正しい順序で** 落とす必要があります。データプレーンを止めずに DPU だけ入れ替える運用も想定されているため、reboot path は次の階層に分かれます。

| 操作 | 影響範囲 | 主経路 |
|---|---|---|
| NPU reboot | NPU + 全 DPU | 通常の `reboot` |
| 全 DPU reboot | 全 DPU（NPU 維持） | DPU ごとに [gNOI](../../reference/glossary.md#term-gnoi) HALT → PCI detach → 個別 reboot |
| 個別 DPU reboot | 1 DPU のみ | gNOI HALT → PCI detach → 該当 DPU reboot |

順序の要点は次の通りです。

1. 対象 DPU に `gnoi.system.Reboot` (HALT) を送り、停止準備を促す。
2. DPU 上の `gnoi_reboot_daemon` が graceful shutdown を実行する。
3. NPU 側で PCI detach する。
4. 物理的に reboot し、戻ったら PCI attach → midplane 再接続 → DPU 側 SONiC 起動。
5. HAMgrD が当該 DPU を再度 HA セットに組み込む。

詳細は [SmartSwitch reboot 順序](../../system/smart-switch-reboot-high-level-design.md) と [DPU Graceful Shutdown](../../platform/smartswitch-dpu-graceful-shutdown.md) を参照してください。

### Reboot コマンド例

```bash
admin@smartswitch:~$ sudo config chassis modules shutdown DPU2
admin@smartswitch:~$ show chassis modules status DPU2
       Name      Description    Physical-Slot   Oper-Status     Admin-Status
-----------  --------------  ---------------  ------------  ---------------
DPU2          SmartSwitch-DPU            3        Offline             down

admin@smartswitch:~$ sudo config chassis modules startup DPU2
```

直接 gNOI 経由で操作する場合（外部 controller から）:

```bash
$ gnoi_cli -target smartswitch:8080 -rpc Reboot \
    -jsonin '{"method":"COLD","subcomponents":[{"name":"DPU2"}]}'
```

`shutdown` を投げた DPU の HA ペアが正しく `active` 側だけ残っているか、`DASH_HA_SCOPE_STATE_TABLE` で確認してから物理 reboot に進むのが安全な手順です。

## DPU の独立アップグレード

DPU 単体のソフトウェアアップグレードは「NPU を止めずに DPU だけ image 入替する」運用です。経路は gNOI 系で揃えられ、おおむね次の流れになります。

1. gNOI でターゲット DPU に新 image を転送する。
2. DPU 側で activate / install する。
3. graceful shutdown → reboot → 起動確認 → HA セット復帰。

複数 DPU を 1 台ずつ rolling で回すのが基本で、HA ペアの片側ずつ行うことでサービス継続を保ちます。詳細は [Smart Switch DPU 独立アップグレード](../../system/independent-dpu-upgrade.md) を参照してください。

### Upgrade 中の典型ログ

```yaml
hamgrd[hasetA]: switching local=active -> standby for upgrade of DPU2
gnoi_reboot_daemon[DPU2]: received HALT, draining flows
chassisd: DPU2 PCI detach successful
chassisd: DPU2 PCI attach successful
swssdpu2#orchagent: SAI switch init done, ports up
hamgrd[hasetA]: peer DPU2 re-joined ha-set, starting bulk sync
hamgrd[hasetA]: bulk sync complete, restoring previous role distribution
```

bulk sync が完了しないまま次の DPU に進むと、HA ペアの両側が同時に standby に倒れる事故が起きます。`flow_sync_session_count` が peer の総 flow と一致するまで待つのが運用上の鉄則です。

## 障害ドメイン別の確認順

| 障害 | 最初に見る | 次に見る |
|---|---|---|
| DPU 個別がトラフィックを処理しない | NPU 側 `show platform` / PMON、midplane link、`redisdpuN` 接続 | DPU 側 `DashOrch` / [SAI](../../reference/glossary.md#term-sai) 状態、HAMgrD のセッション state |
| HA フェイルオーバーしない | HAMgrD ログ、`STATE_DB` の HA state | peer link、DPU 側 `DashHaFlowOrch` の sync 状況 |
| [ACL](../../reference/glossary.md#term-acl) が効かない | NPU 側 `ENI_REDIRECT` ACL、`DashEniFwdOrch` | DPU 側 `DASH_ACL_GROUP` / `DASH_ACL_RULE` 反映 |
| Upgrade 後に DPU が戻らない | gNOI ログ、PCI detach / attach、midplane DHCP | DPU 側 boot / `featured` |

### 異常検出と典型ログ

| ログ片 | 意味 | 一次対応 |
|---|---|---|
| `chassisd: DPU<N> midplane unreachable` | DPU 側 SONiC 未起動 or DHCP 未取得 | DPU 側 boot 確認、midplane DHCP server ログ |
| `hamgrd: peer link down, declaring local active` | peer link 喪失 | 物理 link / inter-switch fabric 確認 |
| `dashorch: SAI_STATUS_INSUFFICIENT_RESOURCES` | DPU の ENI/ACL 表が満杯 | controller 側で不要 ENI を削除 |
| `gnoi_reboot_daemon: HALT timeout` | DPU 側 graceful shutdown 不可 | 強制 reboot を検討、要因として flow sync の停止 |
| `swssdpu<N>: orchagent died` | DPU 側 [orchagent](../../reference/glossary.md#term-orchagent) クラッシュ | core dump 確認、DPU 単独 reboot |

### 復旧コマンドの目安

| 状況 | コマンド |
|---|---|
| DPU 単独再起動 | `sudo config chassis modules shutdown DPUx` → `startup DPUx` |
| HA active 強制切替 | `sudo config dash ha switchover hasetA` （controller 推奨） |
| HA ペアから一時除外 | `sudo config dash ha exclude hasetA DPUx` |
| DPU image 再投入 | `sudo config chassis modules upgrade DPUx <image-url>` |

破壊的操作は HA ペア片側に限定。両側に同時に shutdown / upgrade を投げないこと。

### 他章への誘導

- DASH の API モデルや SAI 経路は [internals](./internals.md) を参照。
- 初期 fabric / DPU プロビジョニングは [setup](./setup.md) を参照。
- ASIC リソースカウンタ全般は [Multi-ASIC / VOQ の運用](../12-multi-asic-voq/operations.md) と一部重複します。

## 関連ページ

- [HAMgrD 設計](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md)
- [DPU-Scope DPU-Driven HA HLD](../../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md)
- [SmartSwitch PMON HLD](../../platform/smartswitch-pmon-high-level-design.md)
- [SmartSwitch reboot 順序](../../system/smart-switch-reboot-high-level-design.md)
- [DPU Graceful Shutdown](../../platform/smartswitch-dpu-graceful-shutdown.md)
- [DPU 独立アップグレード](../../system/independent-dpu-upgrade.md)

<!-- glossary-links-injected: 302d7ca006cb -->
