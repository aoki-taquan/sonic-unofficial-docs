# STP failure behavior — Phase D intermediate

Source: sonic-swss/cfgmgr/stpmgr.cpp (ref 4305596156d70e9797e8a881b3d19b46de0bce0d)

## A. ipcInitStpd — UDS ソケット初期化失敗

`ipcInitStpd()` (stpmgr.cpp:859-884) は起動時に Unix Domain Socket を作成・bind する。
- `socket()` 失敗: `SWSS_LOG_ERROR` + `return`。`stpd_fd` は 0 のまま。その後の `sendMsgStpd()` 呼出しは `sendto(0, ...)` として実行されるため、実質的に全 IPC が無効になる。systemd が stpmgrd プロセスをリスタートするまで STP 設定はデーモンに届かない。
- `bind()` 失敗: `SWSS_LOG_ERROR` + `close(stpd_fd)` + `return`。socket は閉じられるが `stpd_fd` は更新されないため同上。

## B. sendMsgStpd — IPC 送信失敗

`sendMsgStpd()` (stpmgr.cpp:1218-1255):
- `calloc` 失敗: `SWSS_LOG_ERROR` + `return -1`
- `sendto` 失敗: `SWSS_LOG_ERROR` + `rc == -1` を返す

**全呼出し元 (doStpGlobalTask, doStpVlanTask, doStpPortTask, doStpVlanPortTask, doVlanMemUpdateTask, doLagMemUpdateTask) は sendMsgStpd の戻り値を検査しない**。
IPC 送信失敗後もそのエントリは `consumer.m_toSync.erase(it)` で消費されるため、**リトライなし・設定がデーモンに届かない状態で silent discard** となる。

## C. doStpGlobalTask — ebtables / 不正モード

- `ebtables` ADD 失敗 (PVST 有効化時): `SWSS_LOG_ERROR("ebtables add failed for PVST %d", ret)` のみ。処理は続行し IPC は送信される (stpmgr.cpp:116-119)
- `ebtables` DEL 失敗 (STP|GLOBAL DEL 時): 同上 (stpmgr.cpp:164-165)
- `mode` フィールドが `pvst`/`mst` 以外: `SWSS_LOG_ERROR("Error: Invalid mode %s")` のみ。`msg.stp_mode` は未設定 (0) のまま IPC が送信される (stpmgr.cpp:136)

## D. doStpVlanTask — インスタンス枯渇 / メモリ不足

- PVST インスタンス枯渇 (`allocL2Instance` が -1 を返す場合): `SWSS_LOG_ERROR("Couldnt allocate instance to VLAN %d")` + `erase(it)` + `continue`。**恒久スキップ**。当該 VLAN への STP 設定はそのセッション中適用されない (stpmgr.cpp:264-269)
- `calloc` 失敗 (STP_VLAN_CONFIG_MSG): `SWSS_LOG_ERROR("mem failed for vlan %d")` + `return`。タスク関数全体が中断され、残キューエントリは次回 SELECT ループに持ち越し (stpmgr.cpp:278-283, 319-324)
- `l2ProtoEnabled == L2_NONE` または `!isVlanStateOk()`: `it++`（silent defer）。エラーログなし (stpmgr.cpp:210-214)
- STP 無効で DEL 操作 (`l2ProtoEnabled == L2_NONE`): `erase(it)` で silent discard (stpmgr.cpp:246-250)

## E. doStpPortTask — STP 未設定 / LAG 空

- `stpGlobalTask == false`: 関数先頭で `return`（silent defer）(stpmgr.cpp:634)
- `isLagEmpty(key)` が true: `erase(it)` + `continue`。LAG に最初のメンバーが追加されると `doLagMemUpdateTask` が `processStpPortAttr` を再実行する設計 (stpmgr.cpp:648-652)
- `l2ProtoEnabled == L2_NONE` + SET: `it++`（silent defer）(stpmgr.cpp:656-661)
- `l2ProtoEnabled == L2_NONE` + DEL: `erase(it)` で silent discard (stpmgr.cpp:664-669)
- `processStpPortAttr` 内の `calloc` 失敗: `SWSS_LOG_ERROR` + `return`。呼出し元 `doStpPortTask` は戻り値を確認しないまま `erase(it)` するため silent discard (stpmgr.cpp:536-539)

## F. doStpVlanPortTask — 前提条件未達 / LAG 空

- 前提フラグ未達 (`stpGlobalTask==false || stpVlanTask==false || stpPortTask==false`): 関数先頭で `return`（silent defer）(stpmgr.cpp:448-449)
- `l2ProtoEnabled == L2_NONE` または `m_vlanInstMap[vlan_id] == INVALID_INSTANCE` + SET: `it++`（silent defer）(stpmgr.cpp:486-491)
- 同条件 + DEL: `erase(it)` で silent discard (stpmgr.cpp:494-498)
- `isLagEmpty(intfName)`: `erase(it)` で silent discard (stpmgr.cpp:502-507)
- 不正キー形式: `SWSS_LOG_ERROR("Invalid key format %s")` + `erase(it)` (stpmgr.cpp:477-479)

## G. doLagMemUpdateTask — LAG State 未確立

- SET で `isLagStateOk(po_name)` が false: `it++`（silent defer）(stpmgr.cpp:791-795)
- DEL で LAG が `m_lagMap` に存在しない: `SWSS_LOG_ERROR("PO not found %s")` のみ、処理継続 (stpmgr.cpp:824)
- 不正キー: `SWSS_LOG_ERROR` + `erase(it)` (stpmgr.cpp:784-786)

## 失敗分類まとめ

| 失敗種別 | 処理 | リトライ可否 |
|---|---|---|
| IPC ソケット初期化失敗 | return (プロセス継続、全 IPC 無効) | プロセス再起動のみ |
| IPC sendto 失敗 | ERROR ログのみ、エントリ消費 | なし (silent discard) |
| PVST インスタンス枯渇 | ERROR + erase | なし (恒久スキップ) |
| calloc 失敗 (MSG 構造体) | ERROR + return (タスク中断) | 次回 SELECT ループ |
| ebtables 失敗 | ERROR のみ、IPC 送信続行 | なし |
| 不正 mode フィールド | ERROR のみ、0 値 IPC 送信 | なし |
| STATE_DB 未確立 (VLAN/LAG) | it++ (silent defer) | 次回 SELECT ループ |
| L2_NONE 状態での SET | it++ (silent defer) | 次回 SELECT ループ |
| L2_NONE 状態での DEL | erase (silent discard) | なし |
| LAG empty (PORT/VLAN_PORT) | erase (LAGメンバー追加時に再実行) | doLagMemUpdateTask 経由 |
| 不正キー形式 | ERROR + erase | なし |
