# vlan-state failure behavior (Phase D)

## 調査対象

- `sonic-swss` `cfgmgr/vlanmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 失敗パターン

### 1. キー形式不正（"Vlan" プレフィックス欠如）

`doVlanTask()` L334:
```cpp
SWSS_LOG_ERROR("Invalid key format. No 'Vlan' prefix: %s", key.c_str());
it = consumer.m_toSync.erase(it);  // 即廃棄
```
STATE_DB への書き込みなし。エラーログのみ。リトライなし。

### 2. VLAN ID が数値でない

`doVlanTask()` L346:
```cpp
SWSS_LOG_ERROR("Invalid key format. Not a number after 'Vlan' prefix: %s", key.c_str());
it = consumer.m_toSync.erase(it);  // 即廃棄
```
同上。

### 3. `addHostVlan()` 失敗 — Linux bridge 作成失敗

`addHostVlan()` は `EXEC_WITH_ERROR_THROW` マクロを使う (L136)。
`/sbin/bridge vlan add` または `/sbin/ip link add` が失敗した場合 `std::runtime_error` が throw される。
`doVlanTask()` の呼び出し側はこの例外を catch していない → プロセス全体が例外終了。
systemd が `vlanmgrd` を再起動する。
STATE_DB `VLAN_TABLE` へは書き込みなし（最後の手順のため）。

### 4. `gMacAddress` 未確定

`doVlanTask()` L318-321:
```cpp
if (!isVlanMacOk())
{
    SWSS_LOG_DEBUG("VLAN mac not ready, delaying VLAN task");
    return;
}
```
タスクをキューに残して即 return。STATE_DB 書き込みは発生しない。
syncd が Switch MAC を確定するまで全 VLAN 処理が保留される。
これは失敗ではなく「待機」だが、STATE_DB が長時間空のまま下流を滞留させる。

### 5. DEL: VLAN が `m_vlans` に未登録

`doVlanTask()` L467:
```cpp
SWSS_LOG_ERROR("%s doesn't exist", key.c_str());
```
`removeHostVlan` を呼ばずエラーログのみ。`stateVlanTable.del()` も呼ばれない（既に存在しないため実害なし）。
エントリは `m_toSync.erase` で破棄。リトライなし。

### 6. VLAN_MEMBER タスクが DEL 後に孤立

VLAN DEL 時に `m_stateVlanTable.del(key)` が即実行される (L463)。
この後に VLAN_MEMBER の SET タスクが `doVlanMemberTask()` で処理されると、
`isVlanStateOk()` が false を返し続け、タスクがキューに永久残留する。
STATE_DB に書き込みはなく、症状は VLAN_MEMBER 設定の無言の滞留として現れる。

### 7. addHostVlanMember() — PortChannel のレースコンディション

`addHostVlanMember()` L258-265:
LAG (`portchannel` プレフィックス) の場合、bridge コマンド失敗時に `return false` でリトライ可。
物理ポートの場合は例外を再 throw → vlanmgrd プロセス終了。

## STATE_DB 書き込み失敗時の挙動まとめ

| 失敗ケース | STATE_DB 書込み | リトライ | プロセス影響 |
|----------|----------------|---------|------------|
| キー形式不正 | なし | なし | なし（エントリ廃棄） |
| `addHostVlan` 例外 | なし | なし（プロセス再起動後に再処理） | vlanmgrd 再起動 |
| gMacAddress 未確定 | なし | 自動（次回ループ） | なし |
| DEL: VLAN 未登録 | なし | なし | なし |
| VLAN_MEMBER 孤立 | なし | なし（永久滞留） | なし（機能停止） |
