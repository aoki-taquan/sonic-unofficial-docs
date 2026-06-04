---
title: HA / PMON / reboot / upgrade の運用
description: SmartSwitch 上で HA / PMON / reboot / DPU 独立アップグレードを運用するための NPU / DPU 別経路と
  実 CLI・実 DB テーブルの早見。
area: topics
verification: code-verified
last_verified: 2026-06-03
sources:
- repo: sonic-net/sonic-swss-common
  path: common/schema.h
  ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- repo: sonic-net/sonic-swss
  path: orchagent/dash/dashhaorch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-utilities
  path: show/chassis_modules.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: config/chassis_modules.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: show/system_health.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-host-services
  path: scripts/gnoi_shutdown_daemon.py
  ref: c5bbbe8b07b96f078fa4b761316627404b01bd04
- repo: sonic-net/SONiC
  path: doc/smart-switch/high-availability/smart-switch-ha-hamgrd.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/SONiC
  path: doc/smart-switch/graceful-shutdown/graceful-shutdown.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
- repo: sonic-net/SONiC
  path: doc/smart-switch/upgrade/dpu-upgrade-hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  cli:
  - show chassis modules status
  - show chassis modules midplane-status
  - show system-health dpu
  - config chassis modules shutdown
  - config chassis modules startup
  config_db:
  - CHASSIS_MODULE
  - DASH_HA_GLOBAL_CONFIG
  yang:
  - sonic-chassis-module
---

# HA / PMON / reboot / upgrade の運用

[SmartSwitch](../../reference/glossary.md#term-smartswitch) の運用観点は「どの障害をどの daemon が見て」「どの順序で再起動 / アップグレードするか」に集約される。[NPU](../../reference/glossary.md#term-npu) / [DPU](../../reference/glossary.md#term-dpu) で責務が分かれているため、コマンドを叩く前に経路を意識する必要がある。

## 全体状態の入口

最初に NPU 側で全 DPU の admin/oper 状態と midplane 到達性を一覧する[^cli-chassis]。

```bash
admin@smartswitch:~$ show chassis modules status
       Name      Description    Physical-Slot   Oper-Status     Admin-Status    Serial
-----------  --------------  ---------------  ------------  ---------------  --------
DPU0          SmartSwitch-DPU            1            Online              up      ...
DPU1          SmartSwitch-DPU            2            Online              up      ...
DPU2          SmartSwitch-DPU            3           Offline            down      ...
DPU3          SmartSwitch-DPU            4            Online              up      ...

admin@smartswitch:~$ show chassis modules midplane-status
       Name        IP-Address    Reachability
-----------  ---------------  ---------------
DPU0           169.254.200.1            True
DPU1           169.254.200.2            True
DPU2           169.254.200.3           False
DPU3           169.254.200.4            True
```

`Reachability: False` は最も多い「DPU が動かない」事象の入口で、原因は (a) DPU 側 [SONiC](../../reference/glossary.md#term-sonic) が boot 途中、(b) midplane DHCP が走っていない、(c) PCI detach 中、のいずれか。NPU 側からは DPU ごとに別 redis インスタンス (`/var/run/redisdpu<N>/redis.sock`) が見えるので、`redis-cli -s /var/run/redisdpu2/redis.sock ping` で DPU 側 redis 到達性まで踏み込める[^redisdpu]。

[^cli-chassis]: `show chassis modules status` は `STATE_DB` の `CHASSIS_MODULE_TABLE` を、`midplane-status` は `CHASSIS_MIDPLANE_TABLE` を読む。`sonic-utilities/show/chassis_modules.py` L11–L122 を参照。
[^redisdpu]: NPU から見える DPU 側 redis の unix socket は `/var/run/redisdpu<N>/redis.sock`。`sonic-buildimage/dockers/docker-database/database_global.json.j2` および `SONiC/doc/smart-switch/smart-switch-database-architecture/smart-switch-database-design.md` を参照。

## HA: DPU-scope, DPU-driven 構成

[DASH](../../reference/glossary.md#term-dash)-on-SmartSwitch の HA は **DPU 単位のペア（DPU-scope）** で組み、フェイルオーバー判定は **DPU 側のセッション状態を主入力（DPU-driven）** とするのが基本形である。NPU 側 HAMgrD は外側の actor として、DPU ペアの組み合わせ・global state・peer リンクの健全性を管理する[^hamgrd-hld]。

運用時に押さえる流れは次の通り。

1. コントローラが HA セット / HA グループを設定する。
2. HAMgrD が peer DPU 間のセッション確立を指示する。
3. DPU の `DashHaOrch` / `DashHaFlowOrch` がフロー単位で sync する。
4. 障害（DPU 単体・peer リンク・NPU 経路）を検知すると HAMgrD が active / standby 切替を駆動する。
5. 復旧後はフロー再同期と active 戻し（switchback）を行う。

実装上の細部は [HAMgrD 設計](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) と [DPU-Scope DPU-Driven HA HLD](../../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) を参照。

[^hamgrd-hld]: HA actor / table の対応表は `SONiC/doc/smart-switch/high-availability/smart-switch-ha-hamgrd.md` L40–L60 に整理されており、Global Config (`DASH_HA_GLOBAL_CONFIG_TABLE` / `DASH_HA_GLOBAL_CONFIG_STATE`) / HA Set (`DASH_HA_SET_CONFIG_TABLE` / `DASH_HA_SET_STATE`) / HA Scope (`DASH_HA_SCOPE_CONFIG_TABLE` / `DASH_HA_SCOPE_STATE`) の三層構造を示す。

### HA 状態の確認

実 DB テーブルは `sonic-swss-common/common/schema.h` で次のように定義されている[^schema]。

- NPU `APPL_DB` (DB 0): `APP_DASH_HA_SET_CONFIG_TABLE_NAME = "DASH_HA_SET_CONFIG_TABLE"`, `APP_DASH_HA_SET_TABLE_NAME = "DASH_HA_SET_TABLE"`, `APP_DASH_HA_SCOPE_CONFIG_TABLE_NAME = "DASH_HA_SCOPE_CONFIG_TABLE"`, `APP_DASH_HA_SCOPE_TABLE_NAME = "DASH_HA_SCOPE_TABLE"`
- NPU `CONFIG_DB`: `CFG_DASH_HA_GLOBAL_CONFIG_TABLE_NAME = "DASH_HA_GLOBAL_CONFIG"`
- DPU `STATE_DB` (`DPU_STATE_DB`, DB 17): `STATE_DASH_HA_SET_STATE_TABLE_NAME = "DASH_HA_SET_STATE_TABLE"`, `STATE_DASH_HA_SCOPE_STATE_TABLE_NAME = "DASH_HA_SCOPE_STATE_TABLE"`

`DashHaOrch` は HA Set の APP/STATE と HA Scope の APP/STATE 双方を購読・書き戻しする[^dashhaorch]。

```bash
admin@smartswitch:~$ redis-cli -n 0 hgetall 'DASH_HA_SET_TABLE:hasetA'
admin@smartswitch:~$ redis-cli -n 0 hgetall 'DASH_HA_SCOPE_TABLE:hasetA'
admin@smartswitch:~$ redis-cli -s /var/run/redisdpu0/redis.sock hgetall 'DASH_HA_SCOPE_STATE_TABLE:hasetA'
admin@smartswitch:~$ docker logs hamgrd 2>&1 | tail -50
```

DPU 側 `STATE_DB` の `DASH_HA_SCOPE_STATE_TABLE` で `ha_role` が両側 `active` のままなら split-brain、両側 `standby` なら controller / peer link 障害である。実フィールド名（`ha_role`, `last_state_change_time` 等）の正規定義は HAMgrD [HLD](../../reference/glossary.md#term-hld) §「DASH HA Scope State」を参照（実装側のフィールド名は orch 経由でセットされるため、本ページでは具体値を例示しない）。

[^schema]: `sonic-swss-common/common/schema.h` L179–L182（APP_DB DASH HA テーブル）, L386（`CFG_CHASSIS_MODULE_TABLE = "CHASSIS_MODULE"`）, L391（`CFG_DASH_HA_GLOBAL_CONFIG_TABLE_NAME = "DASH_HA_GLOBAL_CONFIG"`）, L453–L454（`STATE_DASH_HA_SET_STATE_TABLE_NAME`, `STATE_DASH_HA_SCOPE_STATE_TABLE_NAME`）, L30（`DPU_STATE_DB = 17`）を参照。
[^dashhaorch]: `sonic-swss/orchagent/dash/dashhaorch.cpp` L70（`APP_DASH_HA_SET_TABLE_NAME` 用 result table）, L79（DPU [STATE_DB](../../reference/glossary.md#term-state_db) 側 `STATE_DASH_HA_SCOPE_STATE_TABLE_NAME` への接続）, L1073 周辺の consumer 振り分けを参照。

### HA 障害ドメインの DB 対応表

実 schema 名と対応する DB を示す。HLD 上で言及される「[ENI](../../reference/glossary.md#term-eni) 単位 state」「flow sync counters」は master の `schema.h` には個別テーブルとして登録されていないため、`DashHaFlowOrch` 内部状態 / カウンタは `COUNTERS_DB` の `DASH:*` カウンタ系から拾うか、`docker exec swssdpu<N> ...` で orchagent ログを直接見る運用になる。

| 対象 | DB | 実テーブル名 |
|---|---|---|
| HA グローバル設定 | NPU `CONFIG_DB` | `DASH_HA_GLOBAL_CONFIG` |
| HA セット定義 (config) | NPU `APPL_DB` (DB 0) | `DASH_HA_SET_CONFIG_TABLE` |
| HA セット result | NPU `APPL_DB` (DB 0) | `DASH_HA_SET_TABLE` |
| HA scope 設定 | NPU `APPL_DB` (DB 0) | `DASH_HA_SCOPE_CONFIG_TABLE` |
| HA scope result | NPU `APPL_DB` (DB 0) | `DASH_HA_SCOPE_TABLE` |
| HA set state | DPU `STATE_DB` (DB 17) | `DASH_HA_SET_STATE_TABLE` |
| HA scope state | DPU `STATE_DB` (DB 17) | `DASH_HA_SCOPE_STATE_TABLE` |

## PMON の境界

SmartSwitch の `pmon` は NPU 側で動き、`chassisd` を含むプラットフォームデーモン群で DPU の電源 / 温度 / リセット / midplane / PCIe をまとめて見る。DPU 側で個別に走らせるのは DPU 内部の thermal / sensor 程度で、上位の運用 view は NPU 側に集約される。

確認ポイントは次の通り。

- DPU の link state（midplane / PCIe / boot 完了）
- DPU の温度・電力
- DPU リセット要求（HAMgrD / 手動 reboot 経由）

詳細は [SmartSwitch PMON HLD](../../platform/smartswitch-pmon-high-level-design.md) を参照。

### DPU 個別の確認コマンド

`show system-health dpu <DPUx>` は DPU を 1 台引数で指定して `CHASSIS_STATE_DB` の `DPU_STATE|<DPUx>` を midplane / control / data の 3 plane に分解して表示する[^system-health]。

```bash
admin@smartswitch:~$ show system-health dpu DPU2
   Name        Oper-Status    State-Detail        State-Value    Time    Reason
-------  --------------------  ------------------  -------------  ------  --------
DPU2      Offline               dpu_midplane_state  down           ...     ...
                                dpu_control_state   down           ...     ...
                                dpu_data_state      down           ...     ...

admin@smartswitch:~$ redis-cli -h 127.0.0.1 -p 6380 -n <CHASSIS_STATE_DB index> hgetall 'DPU_STATE|DPU2'
```

`dpu_midplane_state` が `down` のまま戻らない場合は NPU 側 `chassisd` ログと、midplane DHCP の `journalctl -u dhclient@<midplane-intf>` を NPU 側で確認する。

[^system-health]: `sonic-utilities/show/system_health.py` L172–L222 (`show_dpu_state`), L239–L248 (`dpu` サブコマンド定義) を参照。引数 `module_name` は必須で、`CHASSIS_STATE_DB` の `DPU_STATE|*` を `_state` / `_time` / `_reason` サフィックスで分解し、midplane / control / data の 3 行に展開する。

## Reboot 順序

SmartSwitch 全体を reboot する際は、**NPU と DPU を別々に・正しい順序で** 落とす必要がある。データプレーンを止めずに DPU だけ入れ替える運用も想定されているため、reboot path は次の階層に分かれる[^graceful]。

| 操作 | 影響範囲 | 主経路 |
|---|---|---|
| NPU reboot | NPU + 全 DPU | 通常の `reboot` |
| 全 DPU reboot | 全 DPU（NPU 維持） | DPU ごとに `config chassis modules shutdown DPUx` |
| 個別 DPU reboot | 1 DPU のみ | `config chassis modules shutdown DPUx` → graceful shutdown → `startup DPUx` |

`config chassis modules shutdown DPUx` の動作は次の通り[^chassis-shutdown]。

1. `CONFIG_DB` の `CHASSIS_MODULE|DPUx` の `admin_status` を `down` に書き換える。
2. NPU の `gnoi_shutdown_daemon`（`sonic-host-services/scripts/gnoi_shutdown_daemon.py`）が `CHASSIS_MODULE_INFO_TABLE` の `state_transition_in_progress` を購読しており、`docker exec gnmi gnoi_client` 経由で DPU 側 sysmgr に [gNOI](../../reference/glossary.md#term-gnoi) `Reboot{method=HALT}` を発行する。
3. DPU 側でカーネル halt まで進んだ後、NPU 側で PCI detach する。
4. `startup DPUx` で逆の手順を踏み、midplane 再接続 → DPU 側 SONiC 起動 → HAMgrD が当該 DPU を再度 HA セットに組み込む。

詳細は [SmartSwitch reboot 順序](../../system/smart-switch-reboot-high-level-design.md) と [DPU Graceful Shutdown](../../platform/smartswitch-dpu-graceful-shutdown.md) を参照。

[^graceful]: `SONiC/doc/smart-switch/graceful-shutdown/graceful-shutdown.md` L31, L55, L63, L159 を参照。`gnoi_reboot_daemon.py` は HLD 上の名称で、master 実装では `gnoi_shutdown_daemon.py`（`sonic-host-services/scripts/`）として配置されている。
[^chassis-shutdown]: `sonic-utilities/config/chassis_modules.py` L136–L172 (`shutdown_chassis_module`) は `CHASSIS_MODULE` テーブルの `admin_status` を `down` に設定するのみで、graceful shutdown 自体は `gnoi_shutdown_daemon.py` が `CHASSIS_MODULE_INFO_TABLE` の `state_transition_in_progress` 変化を契機に gNOI `Reboot{HALT}` を投げる。

### Reboot コマンド例

```bash
admin@smartswitch:~$ sudo config chassis modules shutdown DPU2
admin@smartswitch:~$ show chassis modules status DPU2
admin@smartswitch:~$ sudo config chassis modules startup DPU2
```

外部 controller から直接 gNOI 経由で叩く場合、SONiC 同梱の `gnoi_client` を `gnmi` コンテナ内から実行する[^gnoi-client]。

```bash
admin@smartswitch:~$ docker exec gnmi gnoi_client \
    -module System -rpc Reboot \
    -jsonin '{"method":"HALT","subcomponents":[{"name":{"origin":"openconfig-platform","elem":[{"name":"DPU2"}]}}]}' \
    -insecure
```

`shutdown` を投げた DPU の HA ペアが正しく `active` 側だけ残っているかは、NPU 側 `APPL_DB` の `DASH_HA_SCOPE_TABLE` と DPU 側 `STATE_DB` の `DASH_HA_SCOPE_STATE_TABLE` で確認してから物理 reboot に進むのが安全な手順となる。

[^gnoi-client]: SONiC 同梱 CLI は `gnoi_client`（`gnoi_cli` ではない）。`SONiC/doc/mgmt/Management Framework.md` L716, L775, `gnoi_healthz_hld.md` L276 などで一貫して `gnoi_client` と表記される。`gnoi_shutdown_daemon.py` 内部でも `docker exec gnmi gnoi_client ...` の形で呼び出される（L240, L257）。

## DPU の独立アップグレード

DPU 単体のソフトウェアアップグレードは「NPU を止めずに DPU だけ image 入替する」運用である。経路は gNOI 系で揃えられ、おおむね次の流れ[^upgrade-hld]:

1. gNOI でターゲット DPU に新 image を転送する。
2. DPU 側で activate / install する。
3. `config chassis modules shutdown DPUx` で graceful shutdown → 物理 reboot → 起動確認 → HA セット復帰。

複数 DPU を 1 台ずつ rolling で回すのが基本で、HA ペアの片側ずつ行うことでサービス継続を保つ。詳細は [Smart Switch DPU 独立アップグレード](../../system/independent-dpu-upgrade.md) を参照。

なお、`config chassis modules upgrade` のような専用 CLI は master の `sonic-utilities` には実装されていない（2026-06-03 時点。外部コントローラから gNOI 経由で image 配布する設計）。

[^upgrade-hld]: `SONiC/doc/smart-switch/upgrade/dpu-upgrade-hld.md` 参照。NPU を維持したまま DPU だけを image 入替する rolling upgrade として定義されている。

### Upgrade 中の典型ログ

```text
gnoi_shutdown_daemon[DPU2]: state_transition_in_progress=True; sending gNOI Reboot HALT to DPU2
gnoi_shutdown_daemon[DPU2]: RebootStatus polling: active=True
chassisd: DPU2 admin_status=down, PCI detach successful
chassisd: DPU2 admin_status=up, PCI attach successful
swssdpu2#orchagent: SAI switch init done, ports up
hamgrd[hasetA]: peer DPU2 re-joined ha-set, starting bulk sync
hamgrd[hasetA]: bulk sync complete, restoring previous role distribution
```

bulk sync が完了しないまま次の DPU に進むと、HA ペアの両側が同時に standby に倒れる事故が起きる。HA scope state が両 DPU で `active`/`standby` の正規ペアに収束するまで待つのが運用上の鉄則。

## 障害ドメイン別の確認順

| 障害 | 最初に見る | 次に見る |
|---|---|---|
| DPU 個別がトラフィックを処理しない | NPU 側 `show chassis modules status` / `midplane-status`、`redisdpuN` socket 接続 | DPU 側 `DashOrch` / [SAI](../../reference/glossary.md#term-sai) 状態、HAMgrD のセッション state |
| HA フェイルオーバーしない | NPU 側 `hamgrd` ログ、`STATE_DB` の `DASH_HA_SCOPE_STATE_TABLE` | peer link、DPU 側 `DashHaFlowOrch` の sync 状況 |
| [ACL](../../reference/glossary.md#term-acl) が効かない | NPU 側 `ENI_REDIRECT` ACL、`DashEniFwdOrch` | DPU 側 `DASH_ACL_GROUP` / `DASH_ACL_RULE` 反映 |
| Upgrade 後に DPU が戻らない | `gnoi_shutdown_daemon` ログ、PCI detach / attach、midplane DHCP | DPU 側 boot / `featured` |

### 異常検出と典型ログ

| ログ片 | 意味 | 一次対応 |
|---|---|---|
| `chassisd: DPU<N> midplane unreachable` | DPU 側 SONiC 未起動 or DHCP 未取得 | DPU 側 boot 確認、midplane DHCP server ログ |
| `hamgrd: peer link down, declaring local active` | peer link 喪失 | 物理 link / inter-switch fabric 確認 |
| `dashorch: SAI_STATUS_INSUFFICIENT_RESOURCES` | DPU の ENI/ACL 表が満杯 | controller 側で不要 ENI を削除 |
| `gnoi_shutdown_daemon: HALT timeout` | DPU 側 graceful shutdown 不可 | 強制 reboot を検討、要因として flow sync の停止 |
| `swssdpu<N>: orchagent died` | DPU 側 [orchagent](../../reference/glossary.md#term-orchagent) クラッシュ | core dump 確認、DPU 単独 reboot |

### 復旧コマンドの目安

| 状況 | コマンド |
|---|---|
| DPU 単独再起動 | `sudo config chassis modules shutdown DPUx` → `startup DPUx` |
| DPU graceful shutdown を gNOI 直叩き | `docker exec gnmi gnoi_client -module System -rpc Reboot -jsonin '{"method":"HALT", ...}'` |
| DPU 状態確認 | `show chassis modules status DPUx` / `show system-health dpu DPUx` |
| DPU image 再投入 | 外部 gNOI client から DPU に image 配布 → `config chassis modules shutdown/startup` で再起動 |

破壊的操作は HA ペア片側に限定。両側に同時に shutdown / upgrade を投げないこと。

### 他章への誘導

- DASH の API モデルや SAI 経路は [internals](./internals.md) を参照。
- 初期 fabric / DPU プロビジョニングは [setup](./setup.md) を参照。
- [ASIC](../../reference/glossary.md#term-asic) リソースカウンタ全般は [Multi-ASIC / VOQ の運用](../12-multi-asic-voq/operations.md) と一部重複する。

## 関連ページ

- [HAMgrD 設計](../../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md)
- [DPU-Scope DPU-Driven HA HLD](../../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md)
- [SmartSwitch PMON HLD](../../platform/smartswitch-pmon-high-level-design.md)
- [SmartSwitch reboot 順序](../../system/smart-switch-reboot-high-level-design.md)
- [DPU Graceful Shutdown](../../platform/smartswitch-dpu-graceful-shutdown.md)
- [DPU 独立アップグレード](../../system/independent-dpu-upgrade.md)

<!-- glossary-links-injected: 31120287100e -->
