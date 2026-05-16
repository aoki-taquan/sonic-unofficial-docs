# STP / ICCP (MCLAG) 連携 — Phase A デフォルト調査メモ

## 調査対象

STP (Spanning Tree Protocol) と ICCP (Inter-Chassis Control Protocol) の連携に関する CONFIG_DB フィールドおよびコード由来デフォルト。
ICCP は MCLAG (Multi-Chassis Link Aggregation) の制御プロトコルであり、`iccpd` デーモン (`docker-iccpd`) が実装する。

## 主要ソース

- `sonic-buildimage/src/iccpd/src/iccp_csm.c` — STP ロール決定ロジック
- `sonic-buildimage/src/iccpd/src/mlacp_link_handler.c` — ロール通知送信 (`mlacp_link_set_iccp_role`)
- `sonic-buildimage/src/iccpd/src/mlacp_fsm.c` — STP TLV 受信ハンドラ
- `sonic-buildimage/src/iccpd/src/scheduler.c` — STP ロール決定呼び出し
- `sonic-buildimage/src/iccpd/src/iccp_netlink.c` — STP ロール依存ネットワーク処理
- `sonic-buildimage/src/iccpd/include/iccp_csm.h` — `stp_role_type_et` 列挙型・`CSM.role_type` フィールド
- `sonic-buildimage/src/iccpd/include/mlacp_fsm.h` — ICCP デバッグカウンタ (STP 関連)
- `sonic-buildimage/src/iccpd/include/msg_format.h` — STP TLV type 定義
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-spanning-tree.yang` — YANG デフォルト値
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mclag.yang` — MCLAG YANG デフォルト値

---

## 1. STP ロール型 (`stp_role_type_et`) — iccpd 内部のみ使用

`iccp_csm.h` にて定義:

```c
typedef enum stp_role_type_e
{
    STP_ROLE_NONE,      /* mstp do nothing */
    STP_ROLE_ACTIVE,    /* mstp report port state */
    STP_ROLE_STANDBY    /* mstp fwd bpdu & set port state */
} stp_role_type_et;
```

- `CSM` 構造体の `role_type` フィールド (初期値: `STP_ROLE_NONE`) がこの型を持つ
- **CONFIG_DB への書き込みなし** — ロールは iccpd 内部メモリのみで管理される

---

## 2. STP ロール決定ロジック — `iccp_csm_stp_role_count()`

`iccp_csm.c:845-871`:

```c
void iccp_csm_stp_role_count(struct CSM *csm)
{
    if (csm->role_type == STP_ROLE_NONE)
    {
        if (inet_addr(csm->sender_ip) < inet_addr(csm->peer_ip))
        {
            /* Active */
            csm->role_type = STP_ROLE_ACTIVE;
            mlacp_link_set_iccp_role(csm->mlag_id, true, MLACP(csm).system_id);
        }
        else
        {
            /* Standby */
            csm->role_type = STP_ROLE_STANDBY;
            mlacp_link_set_iccp_role(csm->mlag_id, false, NULL);
            mlacp_fix_bridge_mac(csm);
        }
    }
}
```

**ロール決定アルゴリズム**:
- `sender_ip` (自ノード IP) < `peer_ip` (相手ノード IP) → **Active**
- `sender_ip` >= `peer_ip` → **Standby**
- これは `MCLAG_DOMAIN.source_ip` と `MCLAG_DOMAIN.peer_ip` の IP アドレス数値比較
- `scheduler.c:805-806` で ICCP セッション確立後に 1 回呼び出し (以後変更なし)

**Standby の副作用**:
- `mlacp_fix_bridge_mac(csm)` を呼び出し、Standby ノードのブリッジ MAC をピアの system_id (Active の MAC) に書き換える
- LACP system-id を両ノードで統一し、MC-LAG が正常動作するための必須ステップ

---

## 3. ICCP ロール通知 — `mlacp_link_set_iccp_role()`

`mlacp_link_handler.c:654-716`:

- mclagsyncd (`MCLAG_MSG_TYPE_SET_ICCP_ROLE`) にロールを通知する
- Active ロール時は `system_id` (MLACP system MAC) も送信
- Standby ロール時は `system_id` 送信なし (`NULL`)
- `sys->sync_fd` が有効な場合のみ送信 (接続未確立時は送信スキップ)

この通知は **CONFIG_DB フィールドとは直接対応しない** — mclagsyncd がカーネル/SAI へ反映する

---

## 4. STP TLV (ICCP プロトコル拡張) — 未サポート

`msg_format.h:103`:
```c
#define TLV_T_MLACP_STP_INFO    0x1037  //no support
```

`mlacp_fsm.c:729-733`:
```c
static void mlacp_sync_recv_stpInfo(struct CSM* csm, struct Msg* msg)
{
    /*Don't support currently*/
    return;
}
```

- ICCP プロトコルには STP 情報交換用 TLV (`TLV_T_MLACP_STP_INFO = 0x1037`) が定義されているが、**現在の実装では未サポート** (関数本体が空)
- `mlacp_fsm.h:109-123` で STP_CONNECT / STP_DISCONNECT / STP_SYSTEM_CONFIG 等のデバッグカウンタが定義されているが、これらも現状では使用されない

---

## 5. MCLAG_DOMAIN の関連フィールド (CONFIG_DB に実在するもの)

STP ロール決定に使用される `source_ip` と `peer_ip` は CONFIG_DB の `MCLAG_DOMAIN` テーブルに保存される:

| フィールド | YANG デフォルト | 役割 |
|---|---|---|
| `source_ip` | (必須・なし) | 自ノードのケアライブ IP → `csm->sender_ip` へ展開 |
| `peer_ip` | (必須・なし) | 相手ノードの IP → `csm->peer_ip` へ展開、STP ロール比較対象 |
| `keepalive_interval` | `1` (秒) | ICCP keepalive 間隔。タイムアウト前に STP ロールが確定する必要がある |
| `session_timeout` | `30` (秒) | ICCP セッションタイムアウト |

`source_ip < peer_ip` (数値) の場合に Active (STP ロール的に優位) となる設計。

---

## 6. STP YANG デフォルト (sonic-spanning-tree.yang) — 参考

STP テーブル自体のデフォルト値は既存の `stp-defaults.md` に記載済み。
YANG モデル (`sonic-spanning-tree.yang`) で定義されるデフォルト値:

| YANG リーフ | YANG デフォルト | テーブル |
|---|---|---|
| `rootguard_timeout` | `30` 秒 | `STP\|GLOBAL` |
| `forward_delay` | `15` 秒 | `STP\|GLOBAL` / `STP_VLAN` |
| `hello_time` | `2` 秒 | `STP\|GLOBAL` / `STP_VLAN` |
| `max_age` | `20` 秒 | `STP\|GLOBAL` / `STP_VLAN` |
| `priority` (bridge) | `32768` | `STP\|GLOBAL` / `STP_VLAN` |
| `path_cost` (port) | `200` | `STP_VLAN_PORT` grouping |
| `priority` (port) | `128` | `STP_VLAN_PORT` grouping |
| `root_guard` | `false` | `STP_PORT` |
| `bpdu_guard` | `false` | `STP_PORT` |
| `bpdu_guard_do_disable` | `false` | `STP_PORT` |
| `uplink_fast` | `false` | `STP_PORT` |
| `portfast` | `false` | `STP_PORT` (PVST のみ) |
| `edge_port` | `false` | `STP_PORT` (MST のみ) |
| `max_hops` | `20` | `STP_MST\|GLOBAL` |
| `max_age` (MST) | `20` 秒 | `STP_MST\|GLOBAL` |
| `hello_time` (MST) | `2` 秒 | `STP_MST\|GLOBAL` |
| `forward_delay` (MST) | `15` 秒 | `STP_MST\|GLOBAL` |
| `bridge_priority` (inst) | `32768` | `STP_MST_INST` |

**注**: YANG の `path_cost` デフォルト `200` と、CLI の `MST_DEFAULT_PORT_PATH_COST = 1` で値が異なる (YANG-CLI discrepancy)。

---

## 7. STP_ROLE_STANDBY の動作影響 (iccp_netlink.c)

Standby ロールは以下の動作を制御する (CONFIG_DB とは直接無関係だが重要な暗黙挙動):

- `iccp_netlink.c:643-646`: `role_type != STP_ROLE_STANDBY` の場合は MAC 書き換えをスキップ
- `iccp_netlink.c:753-755`, `2307-2309`, `2399-2401`: 各種ネットリンク処理で Standby 判定を使用
- Standby ノードは BPDU 転送・ポート状態設定を行い、Active ノードは port state をレポートする

---

## 結論 / discrepancy まとめ

1. **iccpd の STP ロールは CONFIG_DB フィールドに存在しない** — `CSM.role_type` は iccpd 内部メモリ変数のみ
2. **TLV_T_MLACP_STP_INFO は未サポート** — 将来の STP ピア間同期機能のプレースホルダ
3. **YANG `path_cost` デフォルト 200 vs CLI `MST_DEFAULT_PORT_PATH_COST = 1`** — discrepancy (YANG が誤っているか、PVST 用の別値か不明)
4. **STP ロール決定 (IP 比較) は MCLAG_DOMAIN.source_ip / peer_ip に依存** — これらフィールドが CONFIG_DB の唯一の STP/ICCP 連携ポイント
