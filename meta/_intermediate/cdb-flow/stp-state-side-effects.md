# stp-state — side-effects 証跡

調査日: 2026-05-19
対象ファイル:
- sonic-net/sonic-swss cfgmgr/stpmgrd.cpp (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-net/sonic-swss cfgmgr/stpmgr.cpp (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- sonic-net/sonic-swss cfgmgr/stpmgr.h (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 主な副作用

### 1. STP_INIT_READY IPC メッセージ → stpd

`stpmgrd.cpp:77-78`:
```cpp
msg.max_stp_instances = stpmgr.getStpMaxInstances();
stpmgr.sendMsgStpd(STP_INIT_READY, sizeof(msg), (void *)&msg);
```

`getStpMaxInstances()` が `STP_TABLE|GLOBAL` の `max_stp_inst` を読み取り、
その値を `STP_INIT_READY_MSG.max_stp_instances` にセットして
Unix Domain Socket (`STPD_SOCK_NAME`) 経由で `stpd` に送信する。

`stpd` はこの `max_stp_instances` を使って内部の STP インスタンスプールを初期化する。
`STP_TABLE|GLOBAL` の値が変わることで `stpd` が初期化するインスタンス上限数が変わる。

### 2. IPC ソケット確立 (ipcInitStpd) との順序

`stpmgrd.cpp:71-78`:
```
stpmgr.ipcInitStpd();       // Unix socket bind
stpmgr.isPortInitDone(...); // APPL_DB guard
msg.max_stp_instances = stpmgr.getStpMaxInstances();  // STATE_DB 読み取り
stpmgr.sendMsgStpd(STP_INIT_READY, ...);              // IPC 送信
```

`STP_TABLE|GLOBAL` の読み取りは必ず `ipcInitStpd()` と `isPortInitDone()` の後に行われる。
IPC ソケット (`stpd_fd`) が確立されてから STATE_DB 読み取り → `stpd` 送信が行われる。

### 3. stpd の内部ステートへの影響

`sendMsgStpd()` (`stpmgr.cpp:1218-1248`) は `AF_UNIX SOCK_DGRAM` で
`STPD_SOCK_NAME` 宛に `STP_IPC_MSG` を送信する。
`stpd` はこのメッセージを受信してインスタンスプールを初期化し、
その後の `STP_BRIDGE_CONFIG` / `STP_VLAN_CONFIG` 等の設定処理が有効になる。

### 副作用まとめ

| 副作用先 | 副作用の種別 | トリガー | evidence |
|---|---|---|---|
| `stpd` (STP daemon) | IPC 送信 (`STP_INIT_READY` メッセージ) | stpmgrd が `STP_TABLE\|GLOBAL` の `max_stp_inst` を読み取った直後 | `stpmgrd.cpp:74-78` |
| `stpd` 内インスタンスプール | `max_stp_instances` 上限の初期化 | `STP_INIT_READY` 受信 | `stpmgrd.cpp:77` |
