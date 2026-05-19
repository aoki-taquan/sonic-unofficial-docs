# neigh-platform.md — 調査メモ (Phase H)

## 調査対象ファイル

- `sonic-swss/cfgmgr/nbrmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/nbrmgrd.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/neighorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/orch.h` (VS_PLATFORM_SUBSTRING 定義)

---

## 1. VoQ (Virtual Output Queue) / Chassis 環境の分岐

### 1a. nbrmgrd の switch_type 判定

`nbrmgr.cpp:74-83`

```cpp
if(cfgDeviceMetaDataTable.hget("localhost", "switch_type", swtype))
{
    if(swtype == "voq")
    {
        // STATE_DB:STATE_SYSTEM_NEIGH_TABLE_NAME を追加購読
        m_cfgVoqInbandInterfaceTable = unique_ptr<Table>(...);
    }
}
```

- `DEVICE_METADATA.switch_type == "voq"` のときのみ `STATE_DB:STATE_SYSTEM_NEIGH_TABLE_NAME` を SubscriberStateTable で追加購読
- VoQ 以外では `doStateSystemNeighTask()` は登録されず、リモートシステムポート neighbor のカーネルプログラミング経路は非アクティブ

### 1b. doStateSystemNeighTask — VoQ inband 経由カーネルプログラミング

`nbrmgr.cpp:406-505`

VoQ 環境でリモートシステム neighbor が STATE_DB に現れた場合:
1. `getVoqInbandInterfaceName()` で `CFG_VOQ_INBAND_INTERFACE_TABLE_NAME` から inband IF 名と `inband_type` を取得
2. `inband_type == "port"` かつ `isIntfOperUp(nbr_odev)` が false の場合 → スキップ (次 tick 再試行)
3. `addKernelNeigh(inband_if, ip, mac)` → `addKernelRoute(inband_if, ip)` の順でカーネルに書き込み

IPv6 スタティックルートは metric 256 で追加 (`ip -6 route add ... metric 256`):
```
nbrmgr.cpp:572: cmd = IP_CMD + " -6 route add " + ip_str + "/128 dev " + odev + " metric 256";
```
> VoQ 環境では eBGP / iBGP と同一メトリックにして ECMP グループに混入させるため metric 256 を明示設定。v4 はデフォルト 0 なので不要。

### 1c. NeighOrch の isChassisDbInUse() 分岐

`neighorch.cpp:51-57`

```cpp
if(isChassisDbInUse())
{
    // CHASSIS_APP_DB:CHASSIS_APP_SYSTEM_NEIGH_TABLE_NAME を SubscriberStateTable で追加購読
    m_tableVoqSystemNeighTable = unique_ptr<Table>(...);
    // m_stateSystemNeighTable (STATE_DB) を初期化
}
```

- シャーシ DB が有効なときのみ `CHASSIS_APP_SYSTEM_NEIGH_TABLE_NAME` を購読
- addNeighbor 成功後に `voqSyncAddNeigh()` → `CHASSIS_APP_DB:CHASSIS_APP_SYSTEM_NEIGH_TABLE` へ書込み
- removeNeighbor 成功後に `voqSyncDelNeigh()` → 同テーブルから削除

### 1d. addVoqEncapIndex — リモートシステムポートへの ENCAP_INDEX 付与

`neighorch.cpp:2559-2585`

```cpp
if(gMySwitchType == "voq")
{
    if (!addVoqEncapIndex(alias, ip_address, neighbor_attrs))
        return false;
}
```

- `gMySwitchType == "voq"` のとき `addVoqEncapIndex()` を呼ぶ
- `isRemoteSystemPortIntf(alias)` が true のとき: `CHASSIS_APP_DB` から encap_index を取得
  - `SAI_NEIGHBOR_ENTRY_ATTR_ENCAP_INDEX` = 取得した encap_index を neighbor_attrs に追加
  - `SAI_NEIGHBOR_ENTRY_ATTR_IS_LOCAL` = `false` を追加
- encap_index 未到着の場合: `return false` → Consumer が再試行
- ローカルポートの neighbor: ENCAP_INDEX なし (`addVoqEncapIndex` は remote のみ処理)

### 1e. doVoqSystemNeighTask — inband port 状態ガード

`neighorch.cpp:2048-2068`

```cpp
if (ibif.m_type != Port::VLAN)
{
    if (ibif.m_admin_state_up != true || ibif.m_oper_status != SAI_PORT_OPER_STATUS_UP)
        return; // inband port 未 UP → 処理を defer
}
```

- `port` 型 inband: admin + oper どちらも UP でなければ VoQ system neigh 処理を skip
- `vlan` 型 inband: ポート UP チェックをしない

### 1f. VoQ ネイバーの MAC アドレス処理 — VS platform 分岐

`neighorch.cpp:2209-2218`

```cpp
if(ibif.m_type != Port::VLAN)
{
    original_mac_address = mac_address;
    mac_address = gMacAddress; // inband MAC を使用
    string platform = getenv("ASIC_VENDOR") ? getenv("ASIC_VENDOR") : "";
    if (platform == VS_PLATFORM_SUBSTRING)  // "vs"
    {
        mac_address = original_mac_address; // VS では元の MAC を使用
    }
}
```

- `port` 型 inband 環境で non-VLAN: STATE_DB に書く MAC は `gMacAddress`（スイッチ自身の MAC）に差し替え
- **VS platform (`ASIC_VENDOR=vs`) のみ**: 元の MAC アドレス（学習したリモート neighbor の MAC）を維持
- これは VS 環境では inband MAC が固定されていないため実 MAC を使う必要があるための例外

---

## 2. multi-asic 環境

`nbrmgrd` と `neighorch` は multi-asic 環境では namespace ごとに独立したプロセスとして起動する。
各 ASIC namespace の `nbrmgrd` が自分の CONFIG_DB `NEIGH` テーブルを購読し、各 `orchagent` が自分の APPL_DB を処理する。

ソースコード内に explicit な multi-asic 分岐は `nbrmgr.cpp` / `neighorch.cpp` では確認されなかった（namespace 分離は swss-common / supervisor レイヤーで行われる）。

---

## 3. インバンドインターフェース型 (port vs vlan) による挙動差

| inband_type | nbrmgrd 挙動 | NeighOrch 挙動 |
|-------------|-------------|---------------|
| `"port"` | oper UP 確認後にカーネルへ追加。UP 待ちで skip | port admin+oper UP 確認。未 UP で defer。STATE_DB MAC = gMacAddress (VS 除く) |
| `"vlan"` | UP チェックなし。即カーネルへ追加 | UP チェックなし。STATE_DB MAC = 元の MAC |

---

## 4. SAI_NEIGHBOR_ENTRY_ATTR_IS_LOCAL 設定条件

`neighorch.cpp:2572`

```cpp
attr.id = SAI_NEIGHBOR_ENTRY_ATTR_IS_LOCAL;
attr.value.booldata = false; // リモート neighbor は IS_LOCAL = false
```

`addVoqEncapIndex()` がリモートポートへの neighbor にのみ設定。ローカルポートの neighbor は `IS_LOCAL` 属性なし（SAI デフォルト = true）。

---

## 5. doTask() の VoQ 分岐点

`neighorch.cpp:887-891`

```cpp
if(table_name == CHASSIS_APP_SYSTEM_NEIGH_TABLE_NAME)
{
    doVoqSystemNeighTask(consumer);
    return;
}
```

Consumer が `CHASSIS_APP_SYSTEM_NEIGH_TABLE` を受け取った場合は通常の APPL_DB `NEIGH_TABLE` 処理に入らず `doVoqSystemNeighTask` に dispatch される。

---

## 6. inband port neigh の skip 条件 (NeighOrch)

`neighorch.cpp:918-931`

```cpp
if(gPortsOrch->isInbandPort(alias))
{
    Port ibport;
    gPortsOrch->getInbandPort(ibport);
    if(ibport.m_type != Port::VLAN)
    {
        // port 型 inband の neigh は remote neighbor のカーネルエントリ。Skip
        it = consumer.m_toSync.erase(it);
        continue;
    }
    // vlan 型 inband は通過
}
```

- `port` 型 inband インターフェイスに到着した `NEIGH_TABLE` エントリは、VoQ リモート neighbor のカーネルエントリと判断して処理をスキップ（SAI プログラムしない）

---

## まとめ: 主要プラットフォーム分岐

| 分岐条件 | ファイル | 箇所 | 挙動 |
|---------|---------|------|------|
| `switch_type == "voq"` (DEVICE_METADATA) | `nbrmgr.cpp:74-83` | NbrMgr コンストラクタ | STATE_DB SYSTEM_NEIGH 購読を追加 |
| `isChassisDbInUse()` | `neighorch.cpp:51-57` | NeighOrch コンストラクタ | CHASSIS_APP_DB SYSTEM_NEIGH 購読 + voqSyncAddNeigh/Del 有効化 |
| `gMySwitchType == "voq"` | `neighorch.cpp:1313-1318` | addNeighbor() | addVoqEncapIndex() 呼び出し |
| `isRemoteSystemPortIntf(alias)` | `neighorch.cpp:2564-2582` | addVoqEncapIndex() | ENCAP_INDEX / IS_LOCAL=false 設定 |
| `ibif.m_type == Port::VLAN` vs `port` | `neighorch.cpp:2060-2068, 2209-2218` | doVoqSystemNeighTask() | ポート UP ガード / MAC アドレス差替えの有無 |
| `ASIC_VENDOR == "vs"` | `neighorch.cpp:2213-2217` | doVoqSystemNeighTask() | VoQ 環境の STATE_DB MAC に元 MAC を維持 (VS 専用例外) |
| `isInbandPort(alias) && ibport.m_type != Port::VLAN` | `neighorch.cpp:918-929` | doTask() | inband port neigh は skip (SAI プログラムなし) |
| IPv6 static route metric | `nbrmgr.cpp:572` | addKernelRoute() | VoQ リモートの IPv6 に metric 256 付与 |
