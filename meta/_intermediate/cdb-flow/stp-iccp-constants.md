# stp-iccp ハードコード定数調査 (Phase E)

調査日: 2026-05-18
対象ページ: docs/reference/config-db/stp-iccp.md

## 調査対象ファイル

- `src/iccpd/include/scheduler.h`
- `src/iccpd/include/iccp_csm.h`
- `src/iccpd/include/msg_format.h`
- `src/sonic-yang-models/yang-models/sonic-mclag.yang`

## 調査結果

### scheduler.h 内の定数 (行 40-44)

```c
#define CONNECT_INTERVAL_SEC        1     // ICCP 接続リトライ間隔 (秒)
#define CONNECT_TIMEOUT_MSEC        100   // TCP connect タイムアウト (ミリ秒)
#define HEARTBEAT_TIMEOUT_SEC       15    // ハートビート無応答タイムアウト (秒)
#define TRANSIT_INTERVAL_SEC        1     // FSM 状態遷移チェック間隔 (秒)
#define EPOLL_TIMEOUT_MSEC          100   // epoll wait タイムアウト (ミリ秒)
```

`HEARTBEAT_TIMEOUT_SEC = 15` はコードハードコード値。
YANG モデルの `session_timeout` のデフォルトは `30` (秒) で別概念。
- `session_timeout` (YANG): ICCP メッセージ交換なしでセッション切断とみなすまでの秒数 (CONFIG_DB 経由で設定可)
- `HEARTBEAT_TIMEOUT_SEC` (C #define): コード内のデフォルト初期値。CONFIG_DB の `session_timeout` で上書き可能かを確認が必要。

mlacp_link_handler.c:3076 ログを見ると `cfg_info.session_timeout` が MCLAG_DOMAIN から読まれている。
scheduler.h の `HEARTBEAT_TIMEOUT_SEC = 15` は実際の初期値であり、YANG デフォルトの `session_timeout = 30` とは異なる。

### iccp_csm.h 内の定数

```c
#define ICCP_TCP_PORT 8888  // iccpd が listen する TCP ポート番号 (iccp_csm.h:53)
```

このポートは変更不可 (CONFIG_DB での設定なし)。

### msg_format.h 内の関連定数 (STP TLV)

```c
#define TLV_T_MLACP_STP_INFO    0x1037  // no support (msg_format.h:103)
```

STP TLV は定義されているが実装なし。

### YANG デフォルト vs コードハードコード

| 項目 | YANG デフォルト | コードハードコード | 備考 |
|------|----------------|-------------------|------|
| `keepalive_interval` | `1` 秒 (`sonic-mclag.yang:81`) | N/A | CONFIG_DB 経由でのみ設定 |
| `session_timeout` | `30` 秒 (`sonic-mclag.yang:91`) | `HEARTBEAT_TIMEOUT_SEC = 15` | 不一致: YANG デフォルト ≠ コード初期値 |
| ICCP TCP ポート | なし | `ICCP_TCP_PORT = 8888` | CONFIG_DB での変更不可 |
| TCP connect タイムアウト | なし | `CONNECT_TIMEOUT_MSEC = 100` | CONFIG_DB での変更不可 |
| 接続リトライ間隔 | なし | `CONNECT_INTERVAL_SEC = 1` | CONFIG_DB での変更不可 |
| epoll タイムアウト | なし | `EPOLL_TIMEOUT_MSEC = 100` | CONFIG_DB での変更不可 |

## discrepancy 発見

`session_timeout` YANG デフォルト (`30`) と `HEARTBEAT_TIMEOUT_SEC` (#define = `15`) の乖離:
- scheduler.c の実際の挙動を確認すると、`HEARTBEAT_TIMEOUT_SEC` は csm 初期化時の hb_timeout_sec として使われ、
  CONFIG_DB から `session_timeout` を受け取った後は CFG 値で上書きされる可能性がある。
- 初回 CONFIG_DB フェッチ前の短い時間、`15` 秒タイムアウトが適用されうる。
