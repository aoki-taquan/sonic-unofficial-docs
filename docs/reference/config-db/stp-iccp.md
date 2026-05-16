---
title: STP / ICCP 連携 — コード由来デフォルト詳細
description: "MCLAG 環境における STP と ICCP (iccpd) の連携メカニズム、STP ロール決定アルゴリズム、CONFIG_DB フィールドとの対応、および TLV_T_MLACP_STP_INFO 未サポート状況を詳細解説。Phase A 分析。"
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
