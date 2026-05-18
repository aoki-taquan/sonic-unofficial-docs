# Phase D: APPL_DB LAG_TABLE portchannel-status 失敗挙動調査

## 対象ファイル

- `sonic-swss/teamsyncd/teamsync.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/teammgr.cpp` (同上)
- `sonic-swss/orchagent/portsorch.cpp` (同上)

## 失敗パス精読結果

### teammgrd — addLag() 失敗

- **根拠コード**: `teammgr.cpp:640-644`
- **失敗条件**: `teamd -r -t <alias> ...` コマンド実行失敗（exec の戻り値 != 0）
- **返り値**: `task_need_retry`
- **APPL_DB への影響**: APPL_DB `LAG_TABLE` への書き込みは `addLag()` を呼ぶ前に実行されない（`doLagTask` L303 は addLag 後にフィールドを書く）
- **STATE_DB への影響**: STATE_DB には書かれない（teamsyncd が RTM_NEWLINK を受信しないため）
- **後続処理**: `addLag()` が `task_need_retry` を返すと `doLagTask()` は `removeLag(alias)` を呼んでクリーンアップし (`teammgr.cpp:303-307`)、`it++; continue` で次のイテレーションに持ち越す（再試行）

### teammgrd — addLagMember() 失敗

- **根拠コード**: `teammgr.cpp:769-788`
- **失敗条件 (retry)**: `teamdctl port add` コマンド失敗 AND `checkPortIffUp(member) == true` → メンバーポートがまだ admin UP 状態
- **返り値**: `task_need_retry` → `it++; continue` で再試行
- **失敗条件 (fatal)**: `teamdctl port add` 失敗 AND `checkPortIffUp(member) == false` → APPL_DB には影響なし（内部コマンド失敗）
- **返り値**: `task_failed`
- **前提チェック失敗**: `isPortStateOk(member) == false` または `isLagStateOk(lag) == false` の場合は `it++; continue` で暗黙 retry（`teammgr.cpp:357`）

### teamsync — team_init() 失敗

- **根拠コード**: `teamsync.cpp:194-213`
- **失敗条件**: `TeamPortSync` コンストラクタが `std::system_error` をスロー（EADDRNOTAVAIL 等、`team_init()` の ifindex 不正時）
- **APPL_DB への影響**: `m_lagTable.set()` はすでに呼ばれている（L157）。APPL_DB には `admin_status` / `oper_status` / `mtu` が書かれているが STATE_DB への書き込みはスキップされる
- **STATE_DB への影響**: STATE_DB は書かれない（`m_stateLagTable.set()` が catch ブロックで到達しない）
- **中間状態**: APPL_DB `LAG_TABLE` にエントリが存在するが STATE_DB `LAG_TABLE` にエントリが存在しない状態が続く。teamd が teamdev を再作成して RTM_NEWLINK を再発火するまで継続
- **復旧**: 次の RTM_NEWLINK 受信で `addLag()` 再呼び出し → `TeamPortSync` 生成成功 → STATE_DB 書き込み

### orchagent PortsOrch — addLag() 失敗

- **根拠コード**: `portsorch.cpp:7994-8005`
- **失敗条件**: `sai_lag_api->create_lag()` 失敗（SAI_STATUS_SUCCESS 以外）
- **返り値**: `handleSaiCreateStatus()` の結果に依存。通常 `task_need_retry` または例外スロー
- **APPL_DB への影響**: `doLagTask()` の `it++; continue` (L6137-6139) で処理をリトライ。APPL_DB は書き換えない
- **ブリッジポート pending 削除**: LAG が `m_portList` に存在し `m_bridge_port_id != SAI_NULL_OBJECT_ID` の場合は `return false`（`portsorch.cpp:7952-7955`）。FDB エントリ削除完了まで LAG の SAI オブジェクト再作成が待機される

### orchagent PortsOrch — removeLag() 失敗（ref_count 制約）

- **根拠コード**: `portsorch.cpp:8047-8052`（推定）
- **失敗条件**: `m_port_ref_count[lag.m_alias] > 0`（INTF_TABLE / VLAN メンバーなどが LAG を参照中）
- **返り値**: `false`
- **APPL_DB への影響**: `doLagTask()` の `it++`（`portsorch.cpp:6228`）で再試行。APPL_DB `LAG_TABLE` のエントリは削除されない
- **復旧**: 参照を持つテーブル（INTF_TABLE / VLAN_MEMBER_TABLE 等）のエントリが先に削除されると ref_count が 0 に戻り、次の処理サイクルで SAI `remove_lag()` が呼ばれる

## 失敗パスまとめ表

| 失敗ケース | 発生箇所 | APPL_DB 影響 | STATE_DB 影響 | retry |
|-----------|---------|-------------|--------------|-------|
| teamd 起動失敗 (`exec` 失敗) | `teammgr.cpp:640-644` | なし | なし | 無制限 (task_need_retry) |
| teamd LAG member 追加失敗（port admin UP の競合） | `teammgr.cpp:779-781` | なし | なし | 無制限 |
| teamd LAG member 追加失敗（port admin DOWN のまま） | `teammgr.cpp:785-787` | なし | なし | なし (task_failed) |
| `isPortStateOk` / `isLagStateOk` 未ready | `teammgr.cpp:357` | なし | なし | 暗黙 retry (STATE_DB 準備待ち) |
| `team_init()` 失敗 (EADDRNOTAVAIL 等) | `teamsync.cpp:208-213` | APPL_DB にエントリ残留 | なし | 次の RTM_NEWLINK で自動復旧 |
| SAI `create_lag` 失敗 | `portsorch.cpp:7994-8005` | なし | なし | 無制限 |
| SAI `remove_lag` 拒否 (ref_count > 0) | `portsorch.cpp:8047-8052` | APPL_DB エントリ残留 | なし | 参照解放まで無制限 retry |
