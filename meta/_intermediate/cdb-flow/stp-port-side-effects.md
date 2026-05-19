# stp-port — Phase F 副次 DB 書込み調査

## 調査対象

- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## CONFIG_DB 以外への副次書込み

`stpmgrd` は `STP_PORT` SET/DEL イベントを `doStpPortTask()` → `processStpPortAttr()` で処理する。
STATE_DB / APPL_DB / ASIC_DB への直接書き込みは発生しない。
副次効果は次の 2 種類のみ:

1. Unix ドメインソケット経由の stpd への IPC メッセージ送信
2. 内部フラグ `stpPortTask` の `true` への更新（後段テーブルのゲート解除）

## STP_PORT SET/DEL の副次効果

### 1. sendMsgStpd — stpd への IPC 送信

`processStpPortAttr()` (`stpmgr.cpp:624`):

```cpp
sendMsgStpd(STP_PORT_CONFIG, len, reinterpret_cast<void *>(msg));
```

| メッセージ型 | ソケットパス | 送信タイミング |
|---|---|---|
| `STP_PORT_CONFIG` | `/var/run/stpipc.sock` (STPD_SOCK_NAME) | SET/DEL いずれも calloc 成功後 |

stpd への IPC 送信はベストエフォートで、`sendto()` 失敗時はエラーログのみで再送なし。
CONFIG_DB エントリはすでに消費済みのため永久消失（Phase D 参照）。

### 2. stpPortTask フラグの true 化（ゲート解除）

`doStpPortTask()` (`stpmgr.cpp:637-638`):

```cpp
if (stpPortTask == false)
    stpPortTask = true;
```

`stpPortTask` が `true` になると後段の複数テーブルの処理が解禁される:

| 影響を受けるタスク | 参照箇所 | 効果 |
|---|---|---|
| `doStpVlanTask()` | `stpmgr.cpp:183` | `stpPortTask == false && !isStpPortEmpty()` の場合 defer → 解除 |
| `doStpVlanPortTask()` | `stpmgr.cpp:448` | `stpPortTask == false` の場合 defer → 解除 |
| `doStpMstInstPortTask()` | `stpmgr.cpp:1160` | `stpPortTask == false` の場合 defer → 解除 |

これらは `STP_VLAN`, `STP_VLAN_PORT`, `STP_MST_PORT` テーブルの処理であり、
`STP_PORT` が受信されることで初めて処理が開始される。

## STATE_DB との関係

`stpmgrd` は STATE_DB を **読み取り専用** で使用する:

| STATE_DB テーブル | 用途 |
|---|---|
| `STATE_VLAN_MEMBER_TABLE` | `getAllPortVlan()` — ポート所属 VLAN 一覧の取得（SET 処理時） |
| `STATE_VLAN_TABLE` | `isVlanStateOk()` — VLAN ready 確認 |
| `STATE_LAG_TABLE` | `isLagStateOk()` — LAG ready 確認 |
| `STATE_STP_TABLE` | `getStpMaxInstances()` — MST 最大インスタンス数取得 |

いずれも `get()` / `getKeys()` のみ。`set()` / `del()` の呼び出しはない。

## 副次書込みのまとめ

| 副次効果 | 対象 | DB/ストレージ種別 |
|---|---|---|
| stpd IPC (STP_PORT_CONFIG) | `/var/run/stpipc.sock` | Unix ドメインソケット（ファイルシステム外） |
| `stpPortTask = true` フラグ設定 | stpmgrd プロセスメモリ | インメモリ（後段テーブル処理のゲート解除） |

CONFIG_DB 以外の永続ストレージ（STATE_DB / APPL_DB / ASIC_DB）への書き込みは発生しない。

## ソース参照

- `stpmgr.cpp:519-628` — `processStpPortAttr()` 実装（IPC メッセージ構築・送信）
- `stpmgr.cpp:624` — `sendMsgStpd(STP_PORT_CONFIG, ...)` 呼び出し
- `stpmgr.cpp:630-681` — `doStpPortTask()` 実装
- `stpmgr.cpp:637-638` — `stpPortTask = true` フラグ設定
- `stpmgr.cpp:183` — `doStpVlanTask()` の `stpPortTask` ガード
- `stpmgr.cpp:448` — `doStpVlanPortTask()` の `stpPortTask` ガード
- `stpmgr.cpp:1160` — `doStpMstInstPortTask()` の `stpPortTask` ガード
- `stpmgr.cpp:1218-1255` — `sendMsgStpd()` 実装（Unix ドメインソケット sendto）
