# appl-port-table — 失敗挙動 (Phase D)

> Task F Phase D intermediate. APPL_DB `PORT_TABLE` を購読する `PortsOrch::doPortTask()`
> および `setPort*()` 系メソッドの失敗・retry 分岐を `sonic-swss/orchagent/portsorch.cpp`
> (`4305596156d70e9797e8a881b3d19b46de0bce0d`) から精読したもの。

## サマリ

PortsOrch では失敗時の挙動が **3 系統** に分かれる。`task_process_status` の意味は
`saihelper.cpp:623-668` `handleSaiSetStatus()` のコメント由来:

| 戻り値 | 意味 | doPortTask() 内挙動 |
|--------|------|----------------------|
| `task_success` | 成功 / 無視扱い (`SAI_STATUS_OBJECT_IN_USE` / `ITEM_NOT_FOUND` 等もここに丸める) | 次の attribute に進む |
| `task_need_retry` | リソース枯渇 (`INSUFFICIENT_RESOURCES` / `TABLE_FULL` / `NO_MEMORY` / `NV_STORAGE_FULL`) | `it++` でタスクを残し、次の `doTask()` で再試行 |
| `task_failed` | 復旧不能 / 入力不正 | `it = taskMap.erase(it)` でタスクを削除し永久放棄 |

## 永久失敗 (retry しない) 分岐

### 1. 未対応 speed

`portsorch.cpp:5019-5032`:

```cpp
if (pCfg.speed.is_set)
{
    if (p.m_speed != pCfg.speed.value)
    {
        if (!isSpeedSupported(p.m_alias, p.m_port_id, pCfg.speed.value))
        {
            SWSS_LOG_ERROR("Unsupported port %s speed %u", ...);
            // Speed not supported, dont retry
            it = taskMap.erase(it);
            continue;
        }
```

`isSpeedSupported()` (`portsorch.cpp:3085-3100`) は STATE_DB `supported_speeds` に
含まれない speed を弾く。ただしリストが空のとき (=platform が
`SAI_PORT_ATTR_SUPPORTED_SPEED` を返さない) は `true` を返して通す。

### 2. 未対応 FEC モード

`portsorch.cpp:5312-5332`:

```cpp
if (!pCfg.fec.override_fec && !fec_override_sup)
{
    SWSS_LOG_ERROR("Auto FEC mode is not supported");
    it = taskMap.erase(it);
    continue;
}
if (!isFecModeSupported(p, pCfg.fec.value))
{
    SWSS_LOG_ERROR("Unsupported port %s FEC mode %s", ...);
    // FEC mode is not supported, don't retry
    it = taskMap.erase(it);
    continue;
}
```

`isFecModeSupported()` (`portsorch.cpp:3205-3222`) は SAI が
`SAI_PORT_ATTR_SUPPORTED_FEC_MODE` を返した場合のみ厳密チェック。
未取得時 (`obj.supported == false`) は `true` を返して通す。

### 3. `setPortLinkTraining` 非 PHY ポート

`portsorch.cpp:3709-3716`:

```cpp
task_process_status PortsOrch::setPortLinkTraining(const Port &port, bool state)
{
    if (port.m_type != Port::PHY)
    {
        return task_failed;
    }
```

LAG / VLAN / sub-port などに対する LT 設定は即 `task_failed`。
`doPortTask()` で `it = taskMap.erase(it)` 扱いになる (LT 該当の continue 分岐は
`portsorch.cpp` の LT セクションで `task_need_retry` のみ retry 扱い)。

## 一時失敗 (retry する) 分岐

### 4. SAI リソース枯渇による `task_need_retry`

`setPortSpeed` / `setPortAdvSpeeds` / `setPortInterfaceType` / `setPortAdvInterfaceTypes`
/ `setPortAutoNeg` / `setPortLinkTraining` 等の `set_port_attribute()` 失敗時、
`handleSaiSetStatus()` で SAI status を判定:

- `SAI_STATUS_INSUFFICIENT_RESOURCES` / `SAI_STATUS_TABLE_FULL` /
  `SAI_STATUS_NO_MEMORY` / `SAI_STATUS_NV_STORAGE_FULL` → `task_need_retry`

`doPortTask()` 側 (`portsorch.cpp:5052-5067`, 5103-5118, 5153-5168, 5224-5239 等)
ではこれを受けて:

```cpp
if (status != task_success)
{
    SWSS_LOG_ERROR("Failed to set port %s speed from %u to %u", ...);
    if (status == task_need_retry)
    {
        it++;  // タスクを残し再試行
    }
    else
    {
        it = taskMap.erase(it);  // 永久放棄
    }
    continue;
}
```

### 5. admin DOWN への transition 失敗

speed / fec / interface_type / adv_speeds / adv_interface_types を変更する際、
ポートが admin up かつ条件 (autoneg off 等) を満たすと一度 admin を DOWN に落とす。
ここで `setPortAdminStatus(p, false)` が失敗するとタスクは **erase されず `it++` で残る**
(`portsorch.cpp:5036-5050`, 5084-5099, 5136-5151, 5207-5222, 5339-5354 等)。
これは事実上 retry に該当するが、`setPortAdminStatus()` は `bool` を返すため
`task_need_retry` / `task_failed` の区別を持たない点に注意。

### 6. `setPortFec()` の SAI 失敗

`portsorch.cpp:5356-5364` だけは特殊で、`setPortFec()` (`portsorch.cpp:2386-2412`) が
`bool` を返すため doPortTask 側では:

```cpp
if (!setPortFec(p, pCfg.fec.value, pCfg.fec.override_fec))
{
    SWSS_LOG_ERROR("Failed to set port %s FEC mode %s", ...);
    it++;
    continue;
}
```

erase せず `it++` で残るため、SAI が一過性のエラーを返した場合は次の `doTask()`
で再試行される。`setPortFec()` 内部の `handleSaiSetStatus()` の戻り値は捨てられ、
SAI が失敗した時点で `setPortFec()` は `false` を返す。

## APPL_DB への影響

- 永久失敗 (`erase`) になった場合: APPL_DB `PORT_TABLE:<alias>` 上のフィールドは
  そのまま残るが、SAI / Port struct (`m_speed` / `m_fec_mode` 等) には反映されない。
  すなわち **APPL_DB と SAI の値が乖離する** 状態が発生し得る。
- retry (`it++`) になった場合: 次の `doTask()` で同じ FieldValueTuple セットが
  再処理される。`Consumer` がエントリを保持し続けるため、`m_toSync` には常時
  該当キーが残る。
- `setPortAdminStatus()` 失敗時は `host_tx_ready` も STATE_DB に書かれないため、
  STATE_DB `PORT_TABLE:<alias>` の `host_tx_ready` は古い値のままになる
  (`portsorch.cpp:2208-2275`)。
- `oper_status` / `flap_count` 等の orchagent 書き戻し系は `set_port_attribute`
  失敗とは独立に SAI notification で更新される (`updateDbPortOperStatus()` /
  `updateDbPortFlapCount()`)。すなわち管理面の SET が失敗してもデータ面の
  oper 表示は最新値を反映し続ける。

## 検出した「retry しない」分岐一覧

| 行 | 条件 | 動作 |
|---|------|------|
| `portsorch.cpp:5023` | `isSpeedSupported()==false` | erase, no retry |
| `portsorch.cpp:5317` | auto FEC 指定 + `fec_override_sup==false` | erase, no retry |
| `portsorch.cpp:5323` | `isFecModeSupported()==false` | erase, no retry |
| `portsorch.cpp:3715` | LT 設定で `port.m_type != PHY` | `task_failed` → erase |
| `setPort*()` の `handleSaiSetStatus` が `task_failed` を返す全ケース | SAI が `INSUFFICIENT_RESOURCES` 系以外で失敗 | erase, no retry |

## 検出した「retry する」分岐一覧

| 行 | 条件 | 動作 |
|---|------|------|
| `portsorch.cpp:5038` | speed 変更前の admin DOWN 失敗 | `it++`, retry |
| `portsorch.cpp:5087` | adv_speeds 変更前の admin DOWN 失敗 | `it++`, retry |
| `portsorch.cpp:5139` | interface_type 変更前の admin DOWN 失敗 | `it++`, retry |
| `portsorch.cpp:5210` | adv_interface_types 変更前の admin DOWN 失敗 | `it++`, retry |
| `portsorch.cpp:5342` | fec mode 変更前の admin DOWN 失敗 | `it++`, retry |
| `portsorch.cpp:5362` | `setPortFec()` SAI 失敗 | `it++`, retry |
| `setPort*` で `handleSaiSetStatus`→`task_need_retry` | SAI が `INSUFFICIENT_RESOURCES` 系で失敗 | `it++`, retry |

## 出典

- `sonic-net/sonic-swss` `orchagent/portsorch.cpp` rev
  `4305596156d70e9797e8a881b3d19b46de0bce0d`: <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/portsorch.cpp>
- `sonic-net/sonic-swss` `orchagent/saihelper.cpp` 同 rev (`handleSaiSetStatus()`):
  <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/saihelper.cpp>
