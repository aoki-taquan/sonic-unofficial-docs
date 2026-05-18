# stp-mst — Phase F 副次 DB 書込み調査

## 調査対象

- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgrd.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## CONFIG_DB 以外への副次書込み

`stpmgrd` は `STP_MST_INST` / `STP_MST_PORT` のイベントを受け取った際、
STATE_DB / APPL_DB / ASIC_DB には直接書き込まない。
唯一の副次効果は Unix ドメインソケット経由の stpd への IPC メッセージ送信と、
インメモリの `m_vlanInstMap[]` 更新である。

## STP_MST_INST SET/DEL の副次効果

### 1. sendMsgStpd — stpd への IPC 送信

`doStpMstInstTask()` (stpmgr.cpp:1108):

```cpp
sendMsgStpd(STP_MST_INST_CONFIG, len, (void *)msg);
```

| メッセージ型 | ソケットパス | 送信タイミング |
|---|---|---|
| `STP_MST_INST_CONFIG` | `/var/run/stpipc.sock` (STPD_SOCK_NAME) | SET/DEL いずれも成功時 |

stpd への IPC 送信はベストエフォートで、失敗時（calloc エラー・sendto エラー）は
CONFIG_DB エントリが消費された後でも再送されない（Phase D #3/#4 参照）。

### 2. m_vlanInstMap[] 更新 (インメモリ)

`updateVlanInstanceMap()` (stpmgr.cpp:1454) が `m_vlanInstMap[4096]` を更新する:

| 操作 | 処理内容 |
|---|---|
| SET (`bridge_priority` / `vlan_list` フィールド更新) | `vlan_list` に含まれる VLAN ID を `m_vlanInstMap[vlan_id] = instance_id` でマッピング。旧リストから外れた VLAN は `0` (デフォルトインスタンス) にリセット |
| DEL | 当該インスタンスにマップされていた全 VLAN を `0` にリセット |

このマップは DB テーブルではなくプロセスメモリに存在し、**stpmgrd 再起動で揮発する**。
再起動後は CONFIG_DB の再処理によって再構築される。

### 3. m_vlanInstMap 更新による STATE_VLAN_MEMBER 処理への連鎖

`doVlanMemUpdateTask()` (stpmgr.cpp:711) は `m_vlanInstMap[vlan_id]` を参照して
stpd へ `STP_VLAN_MEM_CONFIG` を送信するかどうかを判定する:

```cpp
if (m_vlanInstMap[vlan_id] != INVALID_INSTANCE && !isLagEmpty(intfName))
{
    sendMsgStpd(STP_VLAN_MEM_CONFIG, sizeof(msg), (void *)&msg);
}
```

STP_MST_INST の SET/DEL で `m_vlanInstMap` が更新されると、
それ以降の `STATE_VLAN_MEMBER` イベント処理で stpd への通知対象 VLAN が変化する。
ただし **既に処理済みの STATE_VLAN_MEMBER イベントは再処理されない**。

## STP_MST_PORT SET/DEL の副次効果

### 4. sendMsgStpd — stpd への IPC 送信

`processStpMstInstPortAttr()` (stpmgr.cpp:1152):

```cpp
sendMsgStpd(STP_MST_INST_PORT_CONFIG, sizeof(msg), (void *)&msg);
```

| メッセージ型 | 送信タイミング |
|---|---|
| `STP_MST_INST_PORT_CONFIG` | `processStpMstInstPortAttr()` 完了後 |

STP_MST_PORT は `m_vlanInstMap[]` を更新しない。
per-port の path_cost / priority を stpd に転送するのみ。

## STATE_DB との関係

`stpmgrd` は STATE_DB を **読み取り専用** で使用する:

| STATE_DB テーブル | 用途 |
|---|---|
| `STATE_VLAN_TABLE` | `isVlanStateOk()` — VLAN が STATE_DB で ready かを確認 |
| `STATE_LAG_TABLE` | `isLagStateOk()` — LAG が STATE_DB で ready かを確認 |
| `STATE_STP_TABLE` | `getStpMaxInstances()` — MST 最大インスタンス数を取得 (60秒ポーリング) |
| `STATE_VLAN_MEMBER_TABLE` | `doVlanMemUpdateTask()` / `isLagEmpty()` — VLAN メンバ情報の参照 |

いずれも `get()` / `getKeys()` のみ。`set()` / `del()` の呼び出しはない。

## 副次書込みのまとめ

| 副次効果 | 対象 | DB/ストレージ種別 |
|---|---|---|
| stpd IPC (STP_MST_INST_CONFIG) | `/var/run/stpipc.sock` | Unix ドメインソケット (ファイルシステム外) |
| stpd IPC (STP_MST_INST_PORT_CONFIG) | `/var/run/stpipc.sock` | Unix ドメインソケット |
| `m_vlanInstMap[]` 更新 | stpmgrd プロセスメモリ | インメモリ（揮発）|
| STATE_VLAN_MEMBER → STP_VLAN_MEM_CONFIG 連鎖 | `/var/run/stpipc.sock` | 間接効果（m_vlanInstMap 変化時） |

CONFIG_DB 以外の永続ストレージ（STATE_DB / APPL_DB / ASIC_DB）への書き込みは発生しない。

## ソース参照

- `stpmgr.cpp:1067` — `updateVlanInstanceMap()` 呼び出し (SET)
- `stpmgr.cpp:1105` — `updateVlanInstanceMap()` 呼び出し (DEL)
- `stpmgr.cpp:1108` — `sendMsgStpd(STP_MST_INST_CONFIG, ...)` 呼び出し
- `stpmgr.cpp:1152` — `sendMsgStpd(STP_MST_INST_PORT_CONFIG, ...)` 呼び出し
- `stpmgr.cpp:1218-1255` — `sendMsgStpd()` 実装 (Unix ドメインソケット sendto)
- `stpmgr.cpp:1454-1484` — `updateVlanInstanceMap()` 実装
- `stpmgr.cpp:711-753` — `doVlanMemUpdateTask()` — m_vlanInstMap 依存の連鎖効果
