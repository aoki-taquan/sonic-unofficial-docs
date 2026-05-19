# MCLAG_UNIQUE_IP — ハードコード定数調査 (Phase E)

調査対象: iccpd (`sonic-buildimage/src/iccpd`) / mclagsyncd (`sonic-swss/mclagsyncd`)

## mclagsyncd 側の定数

### IPC メッセージ長上限

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `MCLAG_MAX_SEND_MSG_LEN` | 4096 バイト | mclagsyncd → iccpd 送信バッファ上限。UNIQUE_IP エントリが多くてバッファが溢れると中間フラッシュを行う | `mclag.h:62` |
| `MCLAG_MAX_MSG_LEN` | 4096 バイト | iccpd 受信バッファ 1 メッセージ最大長 | `mclag.h:61` |

### IPC プロトコルバージョン・ポート

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `MCLAG_PROTO_VERSION` | 1 | `mclag_msg_hdr_t.version` にセットされるプロトコルバージョン。`mclagsyncdSendMclagUniqueIpCfg()` で `cfg_msg_hdr->version = 1` とハードコード | `mclag.h:81`, `mclaglink.cpp:1141,1166` |
| `MCLAG_DEFAULT_PORT` | 2626 | mclagsyncd が iccpd からの接続を待ち受ける TCP ポート番号。`MclagLink` コンストラクタのデフォルト引数 | `mclag.h:56`, `mclaglink.h:292` |
| `MCLAG_DEFAULT_IP` | `0x7f000006` (= 127.0.0.6) | mclagsyncd IPC listen アドレス（localhost の別エイリアス） | `mclag.h:23` |

### メッセージタイプ enum

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `MCLAG_SYNCD_MSG_TYPE_CFG_MCLAG_UNIQUE_IP` | 5 | mclagsyncd → iccpd の UNIQUE_IP 設定通知メッセージ種別 | `mclag.h:91` |

### IPC 構造体フィールド長

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `MAX_L_PORT_NAME` | 20 バイト | `struct mclag_unique_ip_cfg_info.mclag_unique_ip_ifname[]` のバッファサイズ。VLAN IF 名 (`Vlan<id>`) のコピー先 | `mclaglink.h:52`, `mclaglink.h:97` |

`MAX_L_PORT_NAME = 20` バイトは YANG パターンで許容される最長 VLAN IF 名 `Vlan4094` (8 文字) を十分収容できるが、将来的に長い名前のインターフェース型を対象にする場合は上限に注意。

## iccpd 側の定数

### IPC 受信バッファ

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `ICCP_MLAGSYNCD_RECV_MSG_BUFFER_SIZE` | `MCLAG_MAX_MSG_LEN * 256` = 1,048,576 バイト (1 MiB) | iccpd が mclagsyncd から受信するバッファの総サイズ。UNIQUE_IP メッセージはこのバッファに読み込まれる | `mlacp_link_handler.h:34` |
| `MCLAG_MAX_MSG_LEN` | 4096 バイト | 個別メッセージ最大長（iccpd 側の定義） | `mlacp_link_handler.h:30` |

### UNIQUE_IP 関連の iccpd 内部定数

iccpd の `iccp_mclagsyncd_mclag_unique_ip_cfg_handler()` は以下の定数を参照する:

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `MAX_L_PORT_NAME` | 20 バイト | `Unq_ip_If_info.name[]` のサイズ。iccpd 内部リスト要素への if_name コピー先 | `port.h:46`, `mlacp_link_handler.c:3222` |
| `MCLAG_CFG_OPER_ADD` | 1 | UNIQUE_IP の追加操作 op_type | `mclag.h` (iccpd 側 enum) |
| `MCLAG_CFG_OPER_DEL` | 2 | UNIQUE_IP の削除操作 op_type | `mclag.h` (iccpd 側 enum) |

## YANG パターン制約（実質的定数）

`sonic-mclag.yang:150-152` の `if_name` type パターンは以下の VLAN ID 範囲を許容する:

| パターン区分 | 範囲 | 説明 |
|---|---|---|
| `[0-9]{1,3}` | Vlan0 〜 Vlan999 | 1〜3 桁の VLAN ID |
| `[1-3][0-9]{3}` | Vlan1000 〜 Vlan3999 | 4 桁で 1000〜3999 |
| `[4][0][0-8][0-9]` | Vlan4000 〜 Vlan4089 | 4000〜4089 |
| `[4][0][9][0-4]` | Vlan4090 〜 Vlan4094 | 4090〜4094 |

有効 VLAN ID 上限は実質 **4094**（IEEE 802.1Q 標準上限）。パターン展開による最長文字列 `Vlan4094` = 8 文字で `MAX_L_PORT_NAME=20` の制約内に収まる。

## 注記

- `CFG_MCLAG_UNIQUE_IP_TABLE_NAME` マクロは `sonic-swss-common/common/schema.h`（v4305596 時点）に定義が存在しない。`mclaglink.cpp:921` で参照されているが、ソースツリーに `#define` が見当たらない。インストール済みパッケージから提供されるか、ビルド生成ファイルに含まれる可能性がある。実効値は `"MCLAG_UNIQUE_IP"` と推定される（YANG テーブル名との一致から）。
- mclagsyncd → iccpd の IPC に **再送機能はない**（Phase D 参照）。バッファサイズ上限（4096 バイト）を超えた場合は中間フラッシュを行うが、`::write()` 失敗時の補償はなし。
