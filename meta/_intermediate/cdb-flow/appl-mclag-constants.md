# APPL_DB MCLAG/ICCP — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/mclagsyncd/mclag.h`
- `sonic-swss/mclagsyncd/mclaglink.h`
- `sonic-swss/mclagsyncd/mclaglink.cpp`
- `sonic-buildimage/src/iccpd/include/scheduler.h`
- `sonic-buildimage/src/iccpd/include/iccp_csm.h`
- `sonic-buildimage/src/iccpd/include/mlacp_fsm.h`
- `sonic-buildimage/src/iccpd/include/system.h`
- `sonic-buildimage/src/iccpd/include/iccp_cli.h`
- `sonic-buildimage/src/iccpd/include/mlacp_link_handler.h`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mclag.yang`

---

## 1. MCLAG ドメイン ID / タイマー範囲（YANG）

| 定数 / 制約 | 値 | ソース |
|---|---|---|
| `MCLAG_DOMAIN.domain_id` 範囲 | `1..4095` (uint16) | `sonic-mclag.yang:48` |
| `MCLAG_DOMAIN.keepalive_interval` 範囲 | `1..60` 秒、default `1` | `sonic-mclag.yang:76,81` |
| `MCLAG_DOMAIN.session_timeout` 範囲 | `1..3600` 秒、default `30` | `sonic-mclag.yang:86,91` |
| must 制約 | `(keepalive_interval * 3) <= session_timeout` | `sonic-mclag.yang:93` |

注: YANG default は `keepalive_interval=1` / `session_timeout=30`。CONFIG_DB に値が無い場合は mclagsyncd が `-1` を iccpd に送信し、iccpd 側で `CONNECT_INTERVAL_SEC=1` / `HEARTBEAT_TIMEOUT_SEC=15` にフォールバックする（下記 §3）。YANG default (30) と iccpd 内部 fallback (15) は一致しないが、通常経路では YANG/CLI が default を CONFIG_DB に書き込むため、iccpd 内 fallback は CLI 経由でない経路（CONFIG_DB 直書きで空）のときのみ発火する。

---

## 2. mclag.h — IPC プロトコル定数

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `MCLAG_DEFAULT_IP` | `0x7f000006` (`127.0.0.6`) | mclagsyncd IPC listen アドレス | `mclag.h:23` |
| `MCLAG_DEFAULT_PORT` | `2626` | iccpd ↔ mclagsyncd TCP/UNIX ポート | `mclag.h:56` |
| `MCLAG_MAX_MSG_LEN` | `4096` | IPC メッセージ最大バイト | `mclag.h:61` |
| `MCLAG_MAX_SEND_MSG_LEN` | `4096` | 同上（送信側） | `mclag.h:62` |
| `MCLAG_PROTO_VERSION` | `1` | IPC プロトコルバージョン | `mclag.h:81` |

---

## 3. iccpd タイマー定数（scheduler.h）

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `CONNECT_INTERVAL_SEC` | `1` 秒 | `keepalive_interval` 空時の iccpd 内 fallback | `scheduler.h:40` |
| `CONNECT_TIMEOUT_MSEC` | `100` ms | ピア接続 socket connect タイムアウト | `scheduler.h:41` |
| `HEARTBEAT_TIMEOUT_SEC` | `15` 秒 | `session_timeout` 空時の iccpd 内 fallback | `scheduler.h:42` |
| `TRANSIT_INTERVAL_SEC` | `1` 秒 | 状態遷移ポーリング間隔 | `scheduler.h:43` |
| `EPOLL_TIMEOUT_MSEC` | `100` ms | iccpd メインループ epoll タイムアウト | `scheduler.h:44` |
| `MLACP_LOCAL_IF_DOWN_TIMER` | `600` 秒 | ローカル IF down 後の保持タイマー | `mlacp_fsm.h:33` |

---

## 4. iccpd ソケット・接続定数

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `ICCP_TCP_PORT` | `8888` | iccpd ↔ ピア iccpd 間 TCP セッションポート | `iccp_csm.h:53` |
| `MAX_ACCEPT_CONNETIONS` | `20` (sic) | listen backlog 上限 | `iccp_csm.h:54` |
| `ICCPD_TO_MCLAGSYNCD_HDR_VERSION` | `1` | IPC ヘッダバージョン | `msg_format.h:35` |
| `ICCP_MLAGSYNCD_SEND_MSG_BUFFER_SIZE` | `4096` (= `MCLAG_MAX_MSG_LEN`) | 送信バッファ | `mlacp_link_handler.h:33` |
| `ICCP_MLAGSYNCD_RECV_MSG_BUFFER_SIZE` | `1048576` (= 4096 × 256) | 受信バッファ | `mlacp_link_handler.h:34` |
| `MCLAG_MEMBER_NAME_STR_LEN` | `2048` | MEMBERS カンマ区切り文字列上限 | `mlacp_link_handler.h:31` |

---

## 5. ポート名・文字列長定数

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `MAX_L_PORT_NAME` (swss側) | `20` | mclagsyncd 内ポート名バッファ長 | `mclaglink.h:52` |
| `MAX_L_PORT_NAME` (iccpd側) | `20` | iccpd 内ポート名バッファ長 | `iccpd/include/port.h:46` |
| `ICCP_MAX_PORT_NAME` | `20` | show 表示用ポート名長 | `iccp_cmd_show.h:27` |
| `ICCP_MAX_IP_STR_LEN` | `16` | IPv4 文字列長（`INET_ADDRSTRLEN`） | `iccp_cmd_show.h:28` |
| `INET_ADDRSTRLEN` | `16` | mclagsyncd 内再定義 | `mclaglink.h:49` |
| `MAX_L_ICC_SENDER_NAME` | `80` | ICC TLV sender 名長 | `msg_format.h:77` |
| `MAX_BUFSIZE` | `4096` | 汎用バッファ | `system.h:54` |
| `PORTCHANNEL_PREFIX` | `"PortChannel"` | ポート名識別プレフィクス（PortChannel 判定） | `system.h:42` |
| `VLAN_PREFIX` | `"Vlan"` | VLAN インタフェース名プレフィクス | `system.h:43` |

`mclaglink.cpp` の MEMBERS フィルタは `Ethernet` プレフィクスを除外し、PortChannel のみを ISOLATION_GROUP_TABLE.MEMBERS に積む（`mclaglink.cpp` L200 付近）。

---

## 6. プラットフォーム識別文字列（ISOLATION_GROUP 対応プラットフォーム）

`mclaglink.h` で定義され、`isPlatformSupportIsolationGroup()` で `gMySwitchType` と部分一致比較される。

| 定数 | 値 | ソース |
|---|---|---|
| `BRCM_PLATFORM_SUBSTRING` | `"broadcom"` | `mclaglink.h:54` |
| `BFN_PLATFORM_SUBSTRING` | `"barefoot"` | `mclaglink.h:55` |
| `CTC_PLATFORM_SUBSTRING` | `"centec"` | `mclaglink.h:56` |
| `CLX_PLATFORM_SUBSTRING` | `"clounix"` | `mclaglink.h:57` |
| `MRVL_PRST_PLATFORM_SUBSTRING` | `"marvell-prestera"` | `mclaglink.h:58` |
| `MRVL_TL_PLATFORM_SUBSTRING` | `"marvell-teralynx"` | `mclaglink.h:59` |

これ以外のプラットフォームは ACL フォールバック経路（`ACL_TABLE_TABLE` / `ACL_RULE_TABLE`）。

---

## 7. ロール / 状態文字列リテラル（mclaglink.cpp）

STATE_DB / APPL_DB に書き込まれる固定文字列。

| 文字列 | 用途 | ソース |
|---|---|---|
| `"active"` / `"standby"` | `STATE_MCLAG_TABLE.role`（`mclagsyncdSetIccpRole()`） | `mclaglink.cpp:1395,1414` |
| `"up"` / `"down"` | `oper_status`（ICCP セッション・remote IF） | `mclaglink.cpp:1344,1359,1571,1586` |
| `"hardware"` / `"disable"` | `LAG_TABLE.learn_mode` / `PORT_TABLE.learn_mode` | `mclaglink.cpp:393,397` |
| `"true"` / `"false"` | `LAG_TABLE.traffic_disable` | `mclaglink.cpp:1308,1310` |
| `"static"` / `"dynamic"` / `"dynamic_local"` | `MCLAG_FDB_TABLE.type` | `mclaglink.cpp` (Phase A 既掲) |
| `"MCLAG_ISO_GRP"` | `ISOLATION_GROUP_TABLE` 唯一の key（固定 1 エントリ） | `mclaglink.cpp:239,244,277` |
| `"Isolation group for MCLAG"` | `ISOLATION_GROUP_TABLE.DESCRIPTION` 固定値 | `mclaglink.cpp:235,272` |
| `"bridge-port"` | `ISOLATION_GROUP_TABLE.TYPE` 固定値 | `mclaglink.cpp:236,273` |
| `"Mclag egress port isolate acl"` | ACL フォールバック時 `ACL_TABLE.policy_desc` | `mclaglink.cpp` (Phase A 既掲) |
| `"L3"` | フォールバック ACL の `type` | `mclaglink.cpp` (Phase A 既掲) |
| `"mclag"` | フォールバック `ACL_TABLE_TABLE` key | `mclaglink.cpp` (Phase A 既掲) |
| `"mclag:mclag"` | フォールバック `ACL_RULE_TABLE` key | `mclaglink.cpp` (Phase A 既掲) |
| `"ANY"` | ACL_RULE.IP_TYPE | `mclaglink.cpp` (Phase A 既掲) |
| `"DROP"` | ACL_RULE.PACKET_ACTION | `mclaglink.cpp` (Phase A 既掲) |

---

## 8. CLI / CONFIG キーワード（iccp_cli.h）

| 定数 | 値 | 用途 |
|---|---|---|
| `MCLAG_ID_STR` | `"mclag_id"` | CLI 引数名 |
| `MCLAG_INTF_STR` | `"mclag_interface"` | CLI 引数名 |
| `PEER_LINK_STR` | `"peer_link"` | CLI 引数名 |

---

## 9. エラーコード

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `MCLAG_ERROR` | `-1` | 汎用エラー | `system.h:48` |
| `MCLAG_ERROR_INVALID_TLV` | `-2` | TLV パース失敗 | `system.h:49` |
| `ICCP_NLE_SEQ_MISMATCH` | `-16` | netlink seq mismatch | `iccp_netlink.h:38` |

---

## 10. mlacp ノード ID マスク（mlacp_tlv.h）

| 定数 | 値 | 用途 |
|---|---|---|
| `MLACP_SYSCONF_NODEID_MSB_MASK` | `0x80` | SysConf TLV ノード ID MSB |
| `MLACP_SYSCONF_NODEID_NODEID_MASK` | `0x70` | ノード ID 3bit フィールド |
| `MLACP_SYSCONF_NODEID_FREE_MASK` | `0x0F` | 予約ビット |

---

## 特記事項

1. **MCLAG ドメインは 1 個のみ**: YANG `MCLAG_DOMAIN_LIST` に `max-elements 1` 制約があり、コミュニティ SONiC では同時に 1 ドメインしか設定できない。
2. **IPC は `127.0.0.6:2626` 固定**: mclagsyncd の listen アドレス／ポートは `MCLAG_DEFAULT_IP` / `MCLAG_DEFAULT_PORT` ハードコード。設定不可。
3. **IPC メッセージ最大 4096 バイト** (`MCLAG_MAX_MSG_LEN`)。MEMBERS 等のリストはこの上限内で送る必要があり、`MCLAG_MEMBER_NAME_STR_LEN=2048` がカンマ区切り文字列長の上限。
4. **iccpd 内 fallback の二段構え**: CONFIG_DB の `keepalive_interval` / `session_timeout` が空文字列のときのみ `CONNECT_INTERVAL_SEC=1` / `HEARTBEAT_TIMEOUT_SEC=15` にフォールバック。CLI 経由なら YANG default の `1` / `30` が CONFIG_DB に書かれるので fallback は発火しない。
5. **ポート名長 20 文字制限**: `MAX_L_PORT_NAME=20` は `Ethernet1XX` / `PortChannel9999` 等の最長想定。これを超えるカスタム命名は IPC で truncate される可能性あり。
6. **`MCLAG_ISO_GRP` は唯一のキー**: ISOLATION_GROUP_TABLE は 1 エントリのみで、複数の分離グループは持てない。
7. **ICCP TCP ポートは 8888 固定** (`ICCP_TCP_PORT`)。ピア iccpd 間セッションのソケットポート。mclagsyncd IPC ポート (2626) とは別物。

---

## 出典

- `sonic-swss/mclagsyncd/mclag.h` lines 23, 49-50, 56, 61-62, 81-82
- `sonic-swss/mclagsyncd/mclaglink.h` lines 49, 52, 54-59
- `sonic-swss/mclagsyncd/mclaglink.cpp` lines 235-244, 272-277, 393-397, 1308-1316, 1344-1414, 1571-1586
- `sonic-buildimage/src/iccpd/include/scheduler.h` lines 40-44
- `sonic-buildimage/src/iccpd/include/iccp_csm.h` lines 53-54
- `sonic-buildimage/src/iccpd/include/mlacp_fsm.h` line 33
- `sonic-buildimage/src/iccpd/include/system.h` lines 42-43, 48-49, 54
- `sonic-buildimage/src/iccpd/include/iccp_cli.h` lines 46, 49-50
- `sonic-buildimage/src/iccpd/include/mlacp_link_handler.h` lines 30-34
- `sonic-buildimage/src/iccpd/include/mlacp_tlv.h` lines 35-37
- `sonic-buildimage/src/iccpd/include/msg_format.h` lines 35, 77
- `sonic-buildimage/src/iccpd/include/port.h` line 46
- `sonic-buildimage/src/iccpd/include/iccp_cmd_show.h` lines 27-28
- `sonic-buildimage/src/iccpd/include/iccp_netlink.h` line 38
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mclag.yang` lines 48, 76, 81, 86, 91, 93
