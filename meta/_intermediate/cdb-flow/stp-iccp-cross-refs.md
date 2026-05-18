# stp-iccp — Cross-Reference 調査 (Phase C)

調査日: 2026-05-18  
対象: `docs/reference/config-db/stp-iccp.md`

## 調査範囲

STP/ICCP 連携に関わる CONFIG_DB テーブル間・APPL_DB・STATE_DB の参照関係を
ソースコードから列挙する。

---

## 1. MCLAG_DOMAIN → STP ロール決定（主要 cross-ref）

`MCLAG_DOMAIN.source_ip` / `peer_ip` の 2 フィールドが iccpd の STP ロール決定に
直接使用される。

- `iccp_csm_stp_role_count()` (`iccp_csm.c:845-871`): `csm->sender_ip` (= `source_ip`)
  と `csm->peer_ip` の数値比較により `STP_ROLE_ACTIVE` / `STP_ROLE_STANDBY` を決定。
- `scheduler_check_csm_config()` (`scheduler.c:768-807`): `source_ip` / `peer_ip` が
  空のとき MCLAG_ERROR を返して ICCP 接続を阻止し STP ロール決定が行われない。

依存方向: `MCLAG_DOMAIN` → (iccpd 内部) → STP ロール

---

## 2. STP YANG 内 leafref (CONFIG_DB 内テーブル間)

`sonic-spanning-tree.yang` に定義された leafref による依存関係:

| 参照元テーブル | フィールド | 参照先 | 行番号 |
|---|---|---|---|
| `STP_VLAN_PORT` | `vlan-name` | `STP_VLAN.name` | L216 |
| `STP_VLAN_PORT` | `ifname` | `STP_PORT.ifname` | L224 |
| `STP_MST_PORT` | `ifname` | `STP_PORT.ifname` | L491 |

`STP_VLAN_PORT` エントリを作成するには `STP_VLAN` と `STP_PORT` が先行して存在する必要がある。

---

## 3. STP mode must 制約 (CONFIG_DB 内 cross-ref)

`STP_PORT` 内フィールドが `STP.mode` 値に依存する must 制約:

| フィールド | must 条件 | エラーメッセージ |
|---|---|---|
| `portfast` | `STP.mode == 'pvst'` | "Mode must be PVST, and PortFast must be enabled..." |
| `edge_port` | `STP.mode == 'mst'` | "Mode must be MST, and EdgePort must be enabled..." |
| `link_type` | `STP.mode == 'mst'` | "Configuration allowed in MST mode only" |

`STP_MST_LIST` 内の `forward_delay` / `hello_time` / `max_age` / `max_hops` /
`bridge_priority` / `revision_level` / `name` もすべて `STP.mode == 'mst'` 制約あり
(`sonic-spanning-tree.yang:362-426`)。

---

## 4. APPL_DB テーブル (stporch 消費)

`stporch` (`sonic-swss/orchagent/stporch.cpp`) が APPL_DB の以下のテーブルを消費する:

| APPL_DB テーブル | 定数 (`schema.h`) | stporch メソッド |
|---|---|---|
| `STP_VLAN_INSTANCE_TABLE` | `APP_STP_VLAN_INSTANCE_TABLE_NAME` | `updateVlanToStpInstance()` |
| `STP_PORT_STATE_TABLE` | `APP_STP_PORT_STATE_TABLE_NAME` | `updateStpPortState()` |
| `STP_FASTAGEING_FLUSH_TABLE` | `APP_STP_FASTAGEING_FLUSH_TABLE_NAME` | 高速エージング flush |
| `STP_INST_PORT_FLUSH_TABLE` | `APP_STP_INST_PORT_FLUSH_TABLE_NAME` | インスタンスポート flush |

これらは `stpmgrd` (STP マネージャデーモン) が CONFIG_DB の `STP_VLAN` / `STP_PORT` /
`STP_MST` 等を読んで APPL_DB へ書き込むフロー。stporch は APPL_DB 側を消費して SAI へ設定する。

---

## 5. STATE_DB テーブル (stporch 書込)

`stporch.cpp:26`: `m_stpTable = unique_ptr<Table>(new Table(stateDb, STATE_STP_TABLE_NAME))`

stporch は SAI 適用後に `STATE_STP_TABLE` (= `"STP_TABLE"`) へ結果を書き込む。
この STATE_DB テーブルは `show spanning_tree` CLI の情報源となる。

---

## 6. iccpd と STP デーモン間の直接インタフェース

iccpd は STP デーモン (`stpmgrd`) とは **直接通信しない**。

- `TLV_T_MLACP_STP_INFO` (`msg_format.h:103`) で定義される ICCP STP TLV は
  `mlacp_sync_recv_stpInfo()` で `/*Don't support currently*/` のまま無視される。
- iccpd の STP ロール決定結果は `MCLAG_MSG_TYPE_SET_ICCP_ROLE` 経由で
  `mclagsyncd` → STATE_DB `STATE_MCLAG_TABLE` に書き込まれ、CLI が参照する。

---

## grep カバレッジ

| 項目 | ソース | 確認結果 |
|---|---|---|
| `STP_VLAN_PORT` leafref | `sonic-spanning-tree.yang:215-224` | `STP_VLAN.name` / `STP_PORT.ifname` へ依存 |
| `STP_MST_PORT` leafref | `sonic-spanning-tree.yang:482-491` | `STP_PORT.ifname` へ依存 |
| `portfast` must | `sonic-spanning-tree.yang:289-290` | `STP.mode='pvst'` 必須 |
| `edge_port` must | `sonic-spanning-tree.yang:303-304` | `STP.mode='mst'` 必須 |
| stporch APPL_DB 消費 | `stporch.cpp:584-597` | 4 テーブル確認 |
| stporch STATE_DB 書込 | `stporch.cpp:26` | `STATE_STP_TABLE_NAME` |
| iccpd STP TLV 無視 | `mlacp_fsm.c:729-733` | 未サポート確認 |
