---
title: STP / ICCP 連携 — コード由来デフォルト詳細
description: "MCLAG 環境における STP と ICCP (iccpd) の連携メカニズム、STP ロール決定アルゴリズム、CONFIG_DB フィールドとの対応、および TLV_T_MLACP_STP_INFO 未サポート状況を詳細解説。Phase A + Phase B + Phase C 分析。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/iccpd/src/iccp_csm.c
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/iccpd/src/mlacp_link_handler.c
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/iccpd/src/mlacp_fsm.c
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/iccpd/include/iccp_csm.h
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/iccpd/include/msg_format.h
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-spanning-tree.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mclag.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/iccpd/src/scheduler.c
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss
    path: mclagsyncd/mclagsyncd.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: mclagsyncd/mclaglink.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - STP
    - STP_VLAN
    - STP_PORT
    - STP_VLAN_PORT
    - STP_MST
    - STP_MST_INST
    - STP_MST_PORT
    - MCLAG_DOMAIN
---

# STP / ICCP 連携 — コード由来デフォルト詳細

!!! info "ページの位置付け"
    このページは MCLAG 環境における **STP (Spanning Tree Protocol) と ICCP (Inter-Chassis Control Protocol) の連携** を詳述する Phase A 分析ページ。
    `iccpd` (`docker-iccpd`) が担うロール決定アルゴリズム・CONFIG_DB フィールドとの対応・ICCP STP TLV の実装状況を解説する。

## 概要

SONiC の MCLAG (Multi-Chassis Link Aggregation) 環境では、2 台のノードが ICCP セッションを確立して制御プレーン情報を同期する。
STP との連携は主に以下の 2 つの側面で存在する:

1. **STP ロール決定** — iccpd が `MCLAG_DOMAIN.source_ip` と `peer_ip` を比較してノードの Active/Standby を決定し、STP デーモンへ通知する
2. **ICCP STP TLV** — ICCP プロトコル仕様には STP 情報同期 TLV (`TLV_T_MLACP_STP_INFO = 0x1037`) が定義されているが、現在の実装では **未サポート**

!!! note "CONFIG_DB テーブル構成"
    STP/ICCP 連携専用の CONFIG_DB テーブルは存在しない。
    連携は `MCLAG_DOMAIN` テーブルの `source_ip` / `peer_ip` フィールドを入力として iccpd 内部で処理される。

<!-- ordering -->
## 書込み順序依存 (Phase B)

<!-- evidence: meta/_intermediate/cdb-flow/stp-iccp-ordering.md -->

### ICCP セッション確立と STP ロール決定の順序

STP ロール (`STP_ROLE_ACTIVE` / `STP_ROLE_STANDBY`) は ICCP セッション確立のタイミングで 1 回だけ決定される。
以下の前提条件がすべて満たされた後に初めてロールが確定する。

#### 設定前提条件（ICCP 接続拒否を防ぐ）

1. **`MCLAG_DOMAIN.source_ip` と `peer_ip` が CONFIG_DB に書かれていること**
   - `scheduler_check_csm_config()` (`scheduler.c:780-784`) が両フィールドの空文字をチェックし、いずれかが空なら `MCLAG_ERROR` を返して ICCP 接続を拒否する。
   - iccpd は接続拒否中は STP ロール決定処理に到達しない。

2. **`MCLAG_DOMAIN.peer_link` に指定したインターフェースが Linux カーネルに存在すること**
   - `peer_itf_name` が設定されているのにインターフェースが未存在 (`local_if_find_by_name()` = NULL) の場合も接続拒否 (`scheduler.c:791-798`)。
   - PortChannel を peer_link とする場合は PortChannel の作成が先行必須。

3. **mclagsyncd が iccpd と接続済みであること (`sync_fd > 0`)**
   - `mlacp_link_set_iccp_role()` は `sys->sync_fd <= 0` のときロール通知をサイレントスキップする (`mlacp_link_handler.c:654-660`)。
   - mclagsyncd は起動後に iccpd のサーバーソケットに接続し、完了してから `mclagsyncdFetchMclagConfigFromConfigdb()` を実行する (`mclagsyncd.cpp:51-58`)。

#### 起動・処理順序

| ステップ | 処理 | 依存 |
|---------|------|------|
| 1 | iccpd 起動・サーバーソケット listen | なし |
| 2 | mclagsyncd 起動 → iccpd ソケット接続 (`sync_fd` 確立) | iccpd が先に起動していること |
| 3 | mclagsyncd が CONFIG_DB から `MCLAG_DOMAIN` をフェッチして iccpd へ送信 | `sync_fd` 確立済み |
| 4 | iccpd が `source_ip` / `peer_ip` を CSM に格納 | ステップ 3 完了 |
| 5 | ICCP セッション確立 (TCP connect / accept) | `source_ip`, `peer_ip`, `peer_link` IF が揃っていること |
| 6 | `scheduler_check_csm_config()` → `iccp_csm_stp_role_count()` でロール決定 (1 回のみ) | ステップ 5 完了 |
| 7 | `mlacp_link_set_iccp_role()` → mclagsyncd へ `MCLAG_MSG_TYPE_SET_ICCP_ROLE` 送信 | `sync_fd > 0` (ステップ 2 完了) |

#### TCP クライアント/サーバー役の決定

ICCP セッションの TCP 接続方向は `source_ip` と `peer_ip` の数値大小で決まる:

| 条件 | 役割 | 動作 |
|------|------|------|
| `source_ip` < `peer_ip` | TCP クライアント | `session_client_conn_handler()` で相手に connect |
| `source_ip` > `peer_ip` | TCP サーバー | `accept()` で待機 |
| `source_ip` == `peer_ip` | 異常 | WARN ログのみ・セッション未確立 |

`scheduler_prepare_session()` (`scheduler.c:682-700`) でこの判定を行う。TCP クライアント側ノードが接続を開始するため、**小さい IP のノードが先にセッション確立を試みる**。

#### 再起動時の注意点

- `iccp_csm_stp_role_count()` は `role_type == STP_ROLE_NONE` のときのみ実行される (1 回ガード, `iccp_csm.c:846`)。
- iccpd の**プロセス再起動**なしにセッションが切断・再接続しても `role_type` はリセットされない。
- `MCLAG_DOMAIN.source_ip` を変更してもプロセス再起動なしにはロールが更新されない。

#### 順序依存サマリ

| # | 依存関係 | 強制度 | 備考 |
|---|----------|--------|------|
| 1 | `MCLAG_DOMAIN.source_ip` / `peer_ip` が存在 → ICCP 接続許可 | 必須 | 空だと接続拒否 |
| 2 | `peer_link` IF が Linux に存在 → ICCP 接続許可 | 必須 | PortChannel 作成が先行必要 |
| 3 | iccpd 起動 → mclagsyncd 起動 | 実質必須 | mclagsyncd の accept() 先行順序 |
| 4 | `sync_fd` 確立 → STP ロール通知到達 | 必須 | sync_fd=0 ではロール通知スキップ |
| 5 | ICCP セッション確立 → STP ロール決定 | 必須 | セッション確立時に 1 回のみ |
| 6 | `source_ip` < `peer_ip` ノード → TCP connect 発信 | 実装固定 | 変更不可 |

<!-- /ordering -->

<!-- cross-refs -->
## テーブル間・DB 間参照 (Phase C)

<!-- evidence: meta/_intermediate/cdb-flow/stp-iccp-cross-refs.md -->

### CONFIG_DB 内テーブル依存

#### MCLAG_DOMAIN → STP ロール決定

`MCLAG_DOMAIN.source_ip` / `peer_ip` フィールドが iccpd 内部の STP ロール決定アルゴリズムの
直接入力となる。CONFIG_DB から直接的な leafref はないが、機能上の依存関係が存在する:

| 参照元 | 参照先 | 依存の性質 |
|--------|--------|----------|
| `MCLAG_DOMAIN.source_ip` | iccpd `csm->sender_ip` | ICCP セッション確立 + STP ロール比較の左辺 |
| `MCLAG_DOMAIN.peer_ip` | iccpd `csm->peer_ip` | ICCP セッション確立 + STP ロール比較の右辺 |
| `MCLAG_DOMAIN.peer_link` | Linux IF (`local_if_find_by_name()`) | ICCP 接続許可の前提 |

証跡: `scheduler.c:768-807`, `iccp_csm.c:845-871`

#### STP YANG 内 leafref（STP テーブル間）

`sonic-spanning-tree.yang` で定義される CONFIG_DB テーブル間の leafref:

| 参照元テーブル | フィールド | 参照先テーブル | YANG 行 |
|---|---|---|---|
| `STP_VLAN_PORT` | `vlan-name` | `STP_VLAN.name` | L216 |
| `STP_VLAN_PORT` | `ifname` | `STP_PORT.ifname` | L224 |
| `STP_MST_PORT` | `ifname` | `STP_PORT.ifname` | L491 |

`STP_VLAN_PORT` エントリを作成するには `STP_VLAN` と `STP_PORT` が先行して存在する必要がある。

#### STP mode must 制約（STP → STP_PORT）

`STP.mode` の値が `STP_PORT` 内フィールドの must 制約に影響する:

| フィールド | 制約 | エラーメッセージ |
|---|---|---|
| `STP_PORT.portfast` | `STP.mode == 'pvst'` が必須 | "Mode must be PVST, and PortFast must be enabled..." |
| `STP_PORT.edge_port` | `STP.mode == 'mst'` が必須 | "Mode must be MST, and EdgePort must be enabled..." |
| `STP_PORT.link_type` | `STP.mode == 'mst'` が必須 | "Configuration allowed in MST mode only" |
| `STP_MST_LIST.*` | `STP.mode == 'mst'` が必須 (全フィールド) | `sonic-spanning-tree.yang:362-426` |

証跡: `sonic-spanning-tree.yang:289-304, 327, 362-426`

### APPL_DB 参照

`stpmgrd` (STP マネージャ) が CONFIG_DB の STP テーブルを読んで以下の APPL_DB テーブルに書き込み、
`stporch` が消費して SAI へ設定する:

| APPL_DB テーブル | 書き込み元 | 消費者 |
|---|---|---|
| `STP_VLAN_INSTANCE_TABLE` | `stpmgrd` | `StpOrch::updateVlanToStpInstance()` |
| `STP_PORT_STATE_TABLE` | `stpmgrd` | `StpOrch::updateStpPortState()` |
| `STP_FASTAGEING_FLUSH_TABLE` | `stpmgrd` | `StpOrch` (高速エージング flush) |
| `STP_INST_PORT_FLUSH_TABLE` | `stpmgrd` | `StpOrch` (インスタンスポート flush) |

証跡: `sonic-swss/orchagent/stporch.cpp:584-597`, `sonic-swss-common/common/schema.h:111-124`

### STATE_DB 参照

| 書き込み元 | STATE_DB テーブル | 参照者 |
|---|---|---|
| `stporch` | `STATE_STP_TABLE` | `show spanning_tree` CLI |
| `mclagsyncd` | `STATE_MCLAG_TABLE` (role / system_mac) | `show mclag brief` CLI |

証跡: `stporch.cpp:26` (`STATE_STP_TABLE_NAME`), `mclaglink.cpp:1412`

### iccpd ↔ STP デーモン間の直接インタフェース

iccpd は `stpmgrd` と **直接通信しない**。ICCP プロトコルに定義される STP TLV
(`TLV_T_MLACP_STP_INFO = 0x1037`) は現在の実装で未サポート（`mlacp_fsm.c:729-733`）。
ピア間の STP 設定一貫性はユーザーが手動で維持する必要がある。

証跡: `msg_format.h:103`, `mlacp_fsm.c:729-733`
<!-- /cross-refs -->

<!-- defaults -->
## 暗黙デフォルトとハードコード挙動

<!-- evidence: meta/_intermediate/cdb-flow/stp-iccp-defaults.md -->

### 1. STP ロール型 — iccpd 内部定義

`iccp_csm.h` で定義される STP ロール列挙型:

```c
typedef enum stp_role_type_e
{
    STP_ROLE_NONE,      /* 未決定 (セッション確立前) */
    STP_ROLE_ACTIVE,    /* Active: port state をレポート */
    STP_ROLE_STANDBY    /* Standby: BPDU 転送・port state 設定 */
} stp_role_type_et;
```

`CSM` (Connection State Machine) 構造体の `role_type` フィールドがこの型を持ち、**初期値は `STP_ROLE_NONE`** (`iccp_csm.c:149`)。

| 値 | 意味 | iccpd 動作 |
|---|---|---|
| `STP_ROLE_NONE` | 初期状態・セッション未確立 | STP 処理なし |
| `STP_ROLE_ACTIVE` | 自ノード IP < ピア IP | port state レポート、system_id を mclagsyncd へ送信 |
| `STP_ROLE_STANDBY` | 自ノード IP >= ピア IP | BPDU 転送、ブリッジ MAC をピアの system_id に書き換え |

**CONFIG_DB への書き込みなし** — ロールは iccpd 内部メモリのみで管理される。`MCLAG_DOMAIN` テーブルにロールフィールドは存在しない。

証跡: `iccp_csm.h:95-100, 128-129`, `iccp_csm.c:149`

---

### 2. STP ロール決定アルゴリズム — IP アドレス数値比較

`iccp_csm_stp_role_count()` (`iccp_csm.c:845-871`) が ICCP セッション確立後に `scheduler.c:806` から 1 回呼び出される:

```c
void iccp_csm_stp_role_count(struct CSM *csm)
{
    if (csm->role_type == STP_ROLE_NONE)
    {
        if (inet_addr(csm->sender_ip) < inet_addr(csm->peer_ip))
        {
            /* Active: 自ノード IP が小さい方が Active */
            csm->role_type = STP_ROLE_ACTIVE;
            mlacp_link_set_iccp_role(csm->mlag_id, true, MLACP(csm).system_id);
        }
        else
        {
            /* Standby: 自ノード IP が大きい (または同値) */
            csm->role_type = STP_ROLE_STANDBY;
            mlacp_link_set_iccp_role(csm->mlag_id, false, NULL);
            mlacp_fix_bridge_mac(csm);  /* Standby MAC をピア system_id に書き換え */
        }
    }
}
```

**アルゴリズム詳細**:

| 条件 | ロール | mclagsyncd 通知 | 副作用 |
|---|---|---|---|
| `source_ip` < `peer_ip` (数値) | `STP_ROLE_ACTIVE` | `is_active_role=true` + `system_id` | なし |
| `source_ip` >= `peer_ip` (数値) | `STP_ROLE_STANDBY` | `is_active_role=false` | `mlacp_fix_bridge_mac()` でブリッジ MAC 書き換え |

- `csm->sender_ip` は `MCLAG_DOMAIN.source_ip` から展開
- `csm->peer_ip` は `MCLAG_DOMAIN.peer_ip` から展開
- `role_type != STP_ROLE_NONE` の場合は関数全体をスキップ (1 回のみ実行)

証跡: `iccp_csm.c:845-871`, `scheduler.c:805-806`

---

### 3. Standby ノードのブリッジ MAC 書き換え — `mlacp_fix_bridge_mac()`

Standby ロールが決定した直後に `mlacp_fix_bridge_mac(csm)` が呼ばれる。
この関数は Standby ノードの PortChannel の MAC を Active ノードの `system_id` (MAC アドレス) に書き換える:

- `iccp_netlink.c:643-676`: `role_type == STP_ROLE_STANDBY` の場合のみ MAC 書き換えを実施
- `iccp_netlink_if_hwaddr_set()` で Linux カーネルの hw_addr を設定
- 書き換え後に `iccp_netlink_if_shutdown_set()` → `iccp_netlink_if_startup_set()` でリンクを再起動して link-local アドレスを更新

**目的**: LACP system-id を両ノードで統一し、接続先スイッチが 2 台を 1 台として認識するため。これにより STP の Bridge ID も Active ノードの MAC で統一される。

証跡: `iccp_netlink.c:640-677`

---

### 4. ICCP ロール通知 — `mlacp_link_set_iccp_role()`

ロール決定後に mclagsyncd (`MCLAG_MSG_TYPE_SET_ICCP_ROLE`) へ通知する:

```c
msg_hdr->type = MCLAG_MSG_TYPE_SET_ICCP_ROLE;
/* Sub-message: MLAG ID */
sub_msg->op_type = MCLAG_SUB_OPTION_TYPE_MCLAG_ID;
/* Sub-message: Active/Standby ロール */
sub_msg->op_type = MCLAG_SUB_OPTION_TYPE_ICCP_ROLE;
/* Sub-message: system_id (Active のみ) */
sub_msg->op_type = MCLAG_SUB_OPTION_TYPE_SYSTEM_ID;  /* Active 時のみ */
```

| パラメータ | Active 時 | Standby 時 |
|---|---|---|
| `is_active_role` | `true` | `false` |
| `system_id` | MLACP system MAC を送信 | 送信しない (`NULL`) |

`sys->sync_fd` が 0 (接続未確立) の場合は送信をスキップする (エラーログなし)。

証跡: `mlacp_link_handler.c:654-716`

---

### 5. ICCP STP TLV — 未サポート

ICCP プロトコルには STP 情報を交換する TLV が定義されているが、現在の実装では使用されない:

```c
/* msg_format.h:103 */
#define TLV_T_MLACP_STP_INFO    0x1037  //no support

/* mlacp_fsm.c:729-733 */
static void mlacp_sync_recv_stpInfo(struct CSM* csm, struct Msg* msg)
{
    /*Don't support currently*/
    return;
}
```

`mlacp_fsm.h:109-123` では以下のデバッグカウンタが定義されているが、対応する処理は実装されていない:

| カウンタ | 値 | 意味 |
|---|---|---|
| `ICCP_DBG_CNTR_MSG_STP_CONNECT` | 14 | STP 接続メッセージ |
| `ICCP_DBG_CNTR_MSG_STP_DISCONNECT` | 15 | STP 切断メッセージ |
| `ICCP_DBG_CNTR_MSG_STP_SYSTEM_CONFIG` | 16 | STP システム設定 |
| `ICCP_DBG_CNTR_MSG_STP_REGION_NAME` | 17 | MST リージョン名 |
| `ICCP_DBG_CNTR_MSG_STP_REVISION_LEVEL` | 18 | MST リビジョンレベル |
| `ICCP_DBG_CNTR_MSG_STP_INSTANCE_PRIORITY` | 19 | MST インスタンスプライオリティ |
| `ICCP_DBG_CNTR_MSG_STP_CONFIGURATION_DIGEST` | 20 | MST 設定ダイジェスト |
| `ICCP_DBG_CNTR_MSG_STP_TC_INSTANCES` | 21 | TC 対象インスタンス |
| `ICCP_DBG_CNTR_MSG_STP_ROOT_TIME_PARAM` | 22 | ルートタイマーパラメータ |
| `ICCP_DBG_CNTR_MSG_STP_SYNC_REQ` | 24 | STP 同期要求 |
| `ICCP_DBG_CNTR_MSG_STP_SYNC_DATA` | 25 | STP 同期データ |
| `ICCP_DBG_CNTR_MSG_STP_PO_PORT_MAP` | 26 | PortChannel ポートマップ |

これらは将来の STP ピア間情報同期機能のプレースホルダであり、現在 MCLAG 環境での STP 設定の一貫性はユーザーが手動で維持する必要がある。

証跡: `msg_format.h:103, 185-186`, `mlacp_fsm.c:729-733`, `mlacp_fsm.h:109-123`

---

### 6. MCLAG_DOMAIN フィールドと STP ロールの関係

STP ロール決定に直接使用される CONFIG_DB フィールド:

| テーブル | フィールド | YANG デフォルト | STP ロールへの影響 |
|---|---|---|---|
| `MCLAG_DOMAIN` | `source_ip` | (必須・省略不可) | `csm->sender_ip` へ展開、ロール比較の左辺 |
| `MCLAG_DOMAIN` | `peer_ip` | (必須・省略不可) | `csm->peer_ip` へ展開、ロール比較の右辺 |
| `MCLAG_DOMAIN` | `keepalive_interval` | `1` (秒) | セッション確立速度に影響 (ロール決定タイミング) |
| `MCLAG_DOMAIN` | `session_timeout` | `30` (秒) | セッション維持期間 |

`source_ip` と `peer_ip` に同一 IP を設定した場合: `inet_addr(same) < inet_addr(same)` = false → 両ノードとも Standby になる異常状態 (ガードなし)。

証跡: `sonic-mclag.yang:81, 91`, `iccp_csm.c:852`

---

### 7. STP YANG デフォルト値一覧 (`sonic-spanning-tree.yang`)

STP 設定テーブルの YANG 定義デフォルト値:

| フィールド | YANG デフォルト | テーブル | PVST/MST |
|---|---|---|---|
| `rootguard_timeout` | `30` 秒 | `STP\|GLOBAL` | PVST のみ |
| `forward_delay` | `15` 秒 | `STP\|GLOBAL`, `STP_VLAN`, `STP_MST\|GLOBAL` | 両方 |
| `hello_time` | `2` 秒 | `STP\|GLOBAL`, `STP_VLAN`, `STP_MST\|GLOBAL` | 両方 |
| `max_age` | `20` 秒 | `STP\|GLOBAL`, `STP_VLAN`, `STP_MST\|GLOBAL` | 両方 |
| `priority` (bridge) | `32768` | `STP\|GLOBAL`, `STP_VLAN` | PVST |
| `max_hops` | `20` | `STP_MST\|GLOBAL` | MST のみ |
| `bridge_priority` | `32768` | `STP_MST_INST` | MST のみ |
| `path_cost` (port) | `200` | `STP_VLAN_PORT` / `STP_MST_PORT` grouping | 両方 |
| `priority` (port) | `128` | `STP_VLAN_PORT` / `STP_MST_PORT` grouping | 両方 |
| `root_guard` | `false` | `STP_PORT` | 両方 |
| `bpdu_guard` | `false` | `STP_PORT` | 両方 |
| `bpdu_guard_do_disable` | `false` | `STP_PORT` | PVST |
| `uplink_fast` | `false` | `STP_PORT` | PVST のみ |
| `portfast` | `false` | `STP_PORT` | PVST のみ |
| `edge_port` | `false` | `STP_PORT` | MST のみ |

!!! warning "YANG-CLI discrepancy: path_cost デフォルト値"
    YANG モデルの `path_cost` デフォルトは `200` だが、CLI (`config/stp.py`) の `MST_DEFAULT_PORT_PATH_COST = 1` と異なる。
    MST 有効化時に CLI が書き込む実際の値は `1` であり、YANG デフォルトの `200` は未使用となる。

証跡: `sonic-spanning-tree.yang:86-105, 150-165, 380-432`

<!-- /defaults -->

<!-- ordering -->
## 書込み順序依存 (Phase B)

<!-- evidence: meta/_intermediate/cdb-flow/stp-iccp-ordering.md -->

STP/ICCP 連携において iccpd が STP ロールを正しく決定するためには、以下の順序依存がある。

### 追加順序

1. **`MCLAG_DOMAIN` の `source_ip` / `peer_ip` / `peer_link` を先に CONFIG_DB に書く**
   - `scheduler_check_csm_config()` が `sender_ip` と `peer_ip` の空文字チェックを行い、空であれば `MCLAG_ERROR` を返して ICCP セッション接続を拒否する。
   - `peer_link` が設定済みでも対応するインターフェースが存在しない場合も接続を拒否する（`"peer connection can not establish"` ログ）。
   - evidence: `scheduler.c:780-792`

2. **mclagsyncd が iccpd の `accept()` に接続してから STP ロール通知が届く**
   - `mlacp_link_set_iccp_role()` は `sys->sync_fd <= 0` の場合にサイレントスキップする。
   - mclagsyncd は iccpd が listen 状態になった後に接続するため、iccpd を先に起動する。
   - evidence: `mlacp_link_handler.c:654-660`

3. **クライアント/サーバー役は `source_ip` と `peer_ip` の大小比較で決定する**
   - `scheduler_prepare_session()` で `inet_addr(sender_ip) < inet_addr(peer_ip)` の場合のみ TCP client として connect を試みる。
   - `source_ip > peer_ip` のノードは TCP server として LISTEN で待つ。
   - `source_ip == peer_ip` の場合は WARN ログを出してスキップし、セッションが確立されない。
   - evidence: `scheduler.c:686-697`

4. **STP ロール決定は ICCP セッション確立直後に 1 回だけ実行される**
   - `iccp_csm_stp_role_count()` は `role_type == STP_ROLE_NONE` の場合のみ実行される（ガード条件）。
   - セッション切断・再接続後も `role_type` はリセットされないため、再起動しないとロール変更は反映されない。
   - STP デーモンへの通知はロール決定直後に行われ、その後の CONFIG_DB 変更は反映されない。
   - evidence: `iccp_csm.c:845-871`, `scheduler.c:806`

### 削除順序

| ステップ | 操作 | 理由 |
|---------|------|------|
| 1 | `MCLAG_DOMAIN` を DEL する前に ICCP セッションを停止 | `scheduler_session_disconnect_handler()` が呼ばれ CSM がクリアされる |
| 2 | `MCLAG_DOMAIN` の `peer_link` を unset | `unset_peer_link()` でピアリンク解除 |
| 3 | `MCLAG_DOMAIN` を DEL | `unset_mc_lag_by_id()` で CSM 解放 |

### 順序依存サマリ

| # | 依存関係 | 強制度 | 緩和策 |
|---|----------|--------|--------|
| 1 | `MCLAG_DOMAIN`（`source_ip` / `peer_ip` / `peer_link`）→ ICCP セッション確立 | 強制 | CONFIG_DB 書込み後に iccpd が自動リトライ (`CONNECT_INTERVAL_SEC` ごと) |
| 2 | iccpd 起動 → mclagsyncd 起動 | 推奨 | `sync_fd` 未確立の場合 STP ロール通知がサイレントスキップ |
| 3 | `source_ip != peer_ip` | WARN のみ・ICCP 未確立 | 同一 IP 設定はサポート外 |
| 4 | ICCP セッション確立 → STP ロール決定（1 回限り） | 強制 | ロール変更には iccpd 再起動が必要 |

<!-- /ordering -->

## 発見された discrepancy / 暗黙デフォルト サマリー

| # | 種別 | 対象 | 内容 |
|---|---|---|---|
| 1 | 未サポート機能 | `TLV_T_MLACP_STP_INFO` | ICCP STP 情報同期 TLV (`0x1037`) は `//no support` のままで将来実装待ち |
| 2 | 実装 discrepancy | `path_cost` | YANG デフォルト `200` vs CLI `MST_DEFAULT_PORT_PATH_COST = 1` — 実行時は `1` が使用される |
| 3 | 暗黙ロール | `STP_ROLE_NONE` | iccpd 起動時の初期ロール。セッション確立前は STP 処理が一切行われない |
| 4 | 同一 IP ガードなし | `MCLAG_DOMAIN.source_ip == peer_ip` | 両ノードが Standby になる異常状態を検出しない |
| 5 | CONFIG_DB 非書き込み | `STP_ROLE_ACTIVE/STANDBY` | ICCP ロールは CONFIG_DB に保存されない (iccpd 再起動時に再決定) |
| 6 | カウンタのみ | STP デバッグカウンタ群 | `mlacp_fsm.h` で定義されるが対応コードが存在しない |

## 引用元

[^1]: ICCP CSM 実装: `iccp_csm.c`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/iccpd/src/iccp_csm.c>
[^2]: MCLAG リンクハンドラ: `mlacp_link_handler.c`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/iccpd/src/mlacp_link_handler.c>
[^3]: MCLAG FSM: `mlacp_fsm.c`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/iccpd/src/mlacp_fsm.c>
[^4]: ICCP CSM ヘッダ: `iccp_csm.h`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/iccpd/include/iccp_csm.h>
[^5]: ICCP メッセージフォーマット: `msg_format.h`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/iccpd/include/msg_format.h>
[^6]: STP YANG モデル: `sonic-spanning-tree.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-spanning-tree.yang>
[^7]: MCLAG YANG モデル: `sonic-mclag.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mclag.yang>

## 関連ページ

- [CONFIG_DB: STP](stp.md)
- [CONFIG_DB: STP_MST](stp-mst.md)
- [CONFIG_DB: MCLAG_DOMAIN](mclag-domain.md)
- [CONFIG_DB: PORTCHANNEL](portchannel.md)
