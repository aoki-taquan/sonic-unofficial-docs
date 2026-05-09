---
title: Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）
area: platform
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/smart-switch/graceful-shutdown/graceful-shutdown.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli:
    - config chassis module shutdown
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    HLD は v0.1 (2025-12) Initial Proposal。`gnoi_reboot_daemon.py` / `module_base.py` の graceful 経路、`CHASSIS_MODULE_INFO_TABLE` の `state_transition_in_progress` / `transition_type` フィールド、PMON 制限下での gNOI HALT 起動経路は未裏取り。priority=high で queue 登録。

# Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）

## 概要

SmartSwitch では DPU の graceful reboot に続き **graceful shutdown** をサポートする[^1]。"reboot の前半" に見えるが、CLI 起動経路、コードパス、PMON container の制限（`docker` / `bash` / `hostexec` 不可）から実装が分離される。chassisd が NPU 側で動き、各 DPU には gNOI Reboot RPC (`HALT`) を発行する `gnoi_reboot_daemon.py` 経由で並列に shutdown を投げる構成。

## 動作仕様

### コンポーネント関係

```mermaid
flowchart LR
    CLI["config chassis module shutdown DPUx"] --> CD[chassisd]
    CD --> MB[module_base.py]
    MB -->|set_admin_state(down) /<br/>graceful_shutdown_handler| ST[(STATE_DB<br/>CHASSIS_MODULE_INFO_TABLE)]
    ST -- watch --> GD[gnoi_reboot_daemon.py]
    GD -->|gNOI Reboot HALT| DPU[DPUx sysmgr]
    DPU -->|DBUS reboot -p| KERN[DPU kernel]
    GD -->|RebootStatus poll| DPU
    GD --> ST
    MB -->|poll until False| ST
    MB --> MOD[module.py]
    MOD --> PAPI[Platform API power_down]
```

### Sequence

1. `gnoi_reboot_daemon.py` 起動時に `CHASSIS_MODULE_INFO_TABLE` を subscribe（startup 系の遷移は no-op）[^1]
2. ユーザが `config chassis module shutdown DPUx` を発行
3. `chassisd` → `module_base.set_admin_state(down)` を呼出
4. `module_base.py` は **DEVICE_METADATA の `subtype="SmartSwitch"` かつ `switch_type != dpu`** を確認。条件成立で `graceful_shutdown_handler()` 経路へ。それ以外は通常の `module.set_admin_state(down)`
5. `graceful_shutdown_handler()` が STATE_DB の `CHASSIS_MODULE_INFO_TABLE|DPUx` に `state_transition_in_progress=True`, `transition_type=shutdown` を書き込む
6. `gnoi_reboot_daemon` は変化を検出し DPUx の sysmgr に **gNOI Reboot RPC `HALT`** を送る。sysmgr は DBUS で `reboot -p` を発行
7. daemon が `gnoi_client -rpc RebootStatus` で polling
8. DPU が kernel shutdown 完了後、daemon が `state_transition_in_progress=False` に戻す（タイムアウト時は失敗結果を書く）
9. `module_base.py` は 5 秒間隔で polling し False を確認、ログ出力
10. 最後に `module.py.set_admin_state(down)` で platform API による power-down

### CHASSIS_MODULE_INFO_TABLE スキーマ（STATE_DB）

key: `CHASSIS_MODULE_INFO_TABLE|<MODULE>`

| Field | 説明 |
|-------|------|
| `state_transition_in_progress` | `"True"` で遷移中、`"False"`/不在で停止中 |
| `transition_start_time` | UTC 文字列 |
| `transition_type` | `"shutdown"` / `"none"`（reboot/startup は `none`）|

| 種別 | 設定者 | 解除者 |
|------|--------|--------|
| Startup | CLI / config load | online 到達時 |
| Shutdown | CLI / config load | `gnoi_reboot_daemon` が platform API 完了時 |
| Reboot | `smartswitch_reboot_helper` | 同左 |

### 並列実行と race condition

複数 DPU の graceful shutdown は並列に実行される[^1]。`module_base.py` と `smartswitch_reboot_helper` が同 module の `state_transition_in_progress` に書き込みを競った場合、**先に True に書いた側が勝つ**。負け側は失敗扱いで再投を要求される。

主要シナリオ（HLD 抜粋）[^1]:

| Scenario | 結果 |
|----------|------|
| reboot 進行中に shutdown/startup | 後者が失敗。reboot 完了後再投 |
| graceful shutdown 進行中に reboot 要求 | reboot 失敗。shutdown 完走で目的達成のため reboot 不要 |
| startup 進行中に reboot | reboot 失敗 |
| switch-level reboot 進行中 | 全 module の `True` を一括取得。module-level 操作は失敗 |
| switch-level reboot が module-level 進行中に発行 | 進行中 module は skip、他は switch reboot で処理 |

### Constraints の妙味

- PMON container には `docker`, `hostexec`, `bash` が無い → gNOI 呼び出しを **PMON 内 daemon** に閉じる必要があった[^1]
- gNOI 自体は host 側で `docker exec` ベースに実行される設計だが、PMON は host に直接命令できないため **STATE_DB IPC** を介する pub/sub 経由で実行を委譲する形を採る

<!-- evidence:
source: sonic-net/SONiC/doc/smart-switch/graceful-shutdown/graceful-shutdown.md#L93-L103 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  This design enables the chassisd process running in the PMON container to invoke a gNOI-based reboot
  when it triggers the "set_admin_state(down)" API of a DPU module, without relying on docker, bash,
  or hostexec within the container.
reasoning: PMON 制限下での実装方針と Redis pub/sub への分離の根拠。
-->

## CLI / CONFIG_DB / YANG

- CLI: `config chassis module shutdown DPUx`（既存 chassis CLI 流用）[^1]
- CONFIG_DB は本 HLD では追加なし。STATE_DB の `CHASSIS_MODULE_INFO_TABLE` のフィールドが拡張される

## 制限事項

- module-level と switch-level の reboot/shutdown が衝突した場合、明示的な失敗で再投が必要
- `module_base.py` は 5 秒 poll で完了確認
- DPU 側の sysmgr が gNOI HALT を受け DBUS → `reboot -p` で完了する経路に依存
- v0.1 (2025-12) Initial で master 取り込み未確認

## 干渉する機能

- **Smart Switch Reboot (`smartswitch_reboot_helper`)**: 同じ STATE_DB フィールドで race
- **smartswitch-pmon HLD**: chassisd / pmon の親設計
- **Independent DPU Upgrade**: shutdown 経路を再利用する可能性
- **gNOI / gNMI**: HALT を含む reboot RPC の依存

## 引用元

[^1]: `sonic-net/SONiC` `doc/smart-switch/graceful-shutdown/graceful-shutdown.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- gnoi_reboot_daemon.py の sonic-platform-daemons / sonic-pmon 取り込み確認
- module_base.py の graceful_shutdown_handler 実装と subtype/switch_type 判定確認
- CHASSIS_MODULE_INFO_TABLE の state_transition_in_progress / transition_type フィールド sonic-yang-models 反映確認
- smartswitch_reboot_helper との STATE_DB 排他ロジックの実装一致確認
- DPU sysmgr の gNOI HALT 受信 → DBUS → reboot -p 経路の実装確認
- v0.1 2025-12 Initial Proposal、master への取り込み・採否未確認
-->
