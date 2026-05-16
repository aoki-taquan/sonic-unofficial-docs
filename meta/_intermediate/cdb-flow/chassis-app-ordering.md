# CHASSIS_APP_DB — 書込み順依存調査 (Phase B)

調査日: 2026-05-16  
調査者: Claude (batch q67-f)

## 調査対象ファイル

- `sonic-swss/orchagent/main.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-swss/orchagent/neighorch.cpp`
- `sonic-swss/orchagent/chassisorch.cpp`
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py`

## 起動シーケンス

### 1. gMultiAsicVoq フラグの確定 (main.cpp:694-730)

```
CONFIG_DB.DEVICE_METADATA.localhost.switch_type == "voq"
  → getSystemPortConfigList() 成功
    → isChassisAppDbPresent() が true
      → gMultiAsicVoq = true
      → chassis_app_db = DBConnector("CHASSIS_APP_DB", 0, true)
```

`isChassisDbInUse()` は `gMultiAsicVoq` を返すだけ。接続失敗時は standalone VOQ モードとして扱われ、CHASSIS_APP_DB への書き込みは一切行われない。

### 2. OrchDaemon::init() 内の Orch 初期化順序 (orchdaemon.cpp:232-500)

```
PortsOrch(chassisAppDb)      # SYSTEM_LAG_TABLE / SYSTEM_LAG_MEMBER_TABLE 購読+書き込みテーブル設定
  ↓
IntfsOrch(chassisAppDb)      # SYSTEM_INTERFACE 購読+書き込みテーブル設定
  ↓
NeighOrch(chassisAppDb)      # SYSTEM_NEIGH 書き込みテーブル設定
```

m_orchList は `gSwitchOrch, gCrmOrch, gPortsOrch, ..., gIntfsOrch, gNeighOrch, ...` の順で定義。
doTask() ループはこの順で実行される。

### 3. PortInitDone ゲート (portsorch.cpp:4613-4622)

```
portsyncd → APP_DB:"PORT|PortConfigDone" → APP_DB:"PORT|PortInitDone"
  → PortsOrch::doTask() で key == "PortInitDone" を検出
    → addSystemPorts()   # APPL_DB.APP_SYSTEM_PORT_TABLE からシステムポートを登録
    → m_initDone = true  # allPortsReady() のゲートが開く
```

**SYSTEM_INTERFACE の書き込み (`voqSyncAddIntf`) は PortInitDone 後にのみ呼ばれる**:
- `IntfsOrch::doTask()` → `addIntf()` → `voqSyncAddIntf()` の流れは `gPortsOrch->getPort()` が成功する前提
- getPort() はシステムポートが `m_portList` に登録済みであることを要求 (addSystemPorts() 後)

### 4. SYSTEM_INTERFACE 書き込み条件

```
isChassisDbInUse() == true
  AND PortInitDone 受信済み (addSystemPorts() 完了)
  AND port.m_system_port_info.type != SAI_SYSTEM_PORT_TYPE_REMOTE (ローカルポートのみ)
  AND port.m_type == Port::LAG の場合は port.m_system_lag_info.switch_id == gVoqMySwitchId
```

書き込みトリガー: `IntfsOrch::addIntf()` → `voqSyncAddIntf()` (intfsorch.cpp:1316-1317)

### 5. SYSTEM_LAG_TABLE 書き込み条件

```
gMultiAsicVoq == true
  AND lag.m_system_lag_info.switch_id == gVoqMySwitchId (ローカル LAG のみ)
  AND SYSTEM_LAG_ID_TABLE にフリー ID が存在 (LagIdAllocator による払い出し成功)
```

書き込みトリガー: `PortsOrch::doLagTask()` → LAG CREATE 成功 → `voqSyncAddLag()` (portsorch.cpp:8039)

LAG ID は `SYSTEM_LAG_ID_START` / `SYSTEM_LAG_ID_END` が先に chassis_app_db に書き込まれている必要がある。これらは初期化スクリプト（lagids.lua）が担保する。

### 6. SYSTEM_NEIGH 書き込み条件

```
isChassisDbInUse() == true
  AND NeighOrch::doTask() 内で SAI neighbor entry 作成成功
  AND SAI get_neighbor_entry_attribute(SAI_NEIGHBOR_ENTRY_ATTR_ENCAP_INDEX) の返り値 != 0
```

encap_index == 0 は無効値としてエントリ書き込みをスキップ (neighorch.cpp:2608-2612)。
NeighOrch は IntfsOrch に依存 (インタフェース RIF 存在が前提)。

### 7. BGP_DEVICE_GLOBAL|STATE 書き込み条件

```
bgpcfgd が supervisor の CHASSIS_APP_DB を購読
  → ChassisAppDbMgr.set_handler() が "tsa_enabled" フィールドを受け取る
    → lc_tsa (LC 側 TSA 状態) == "false" の場合のみ
      → DeviceGlobalCfgMgr.isolate_unisolate_device(data["tsa_enabled"])
```

bgpcfgd は CONFIG_DB.BGP_DEVICE_GLOBAL.localhost.tsa_enabled の変化を購読し、LC TSA 状態が優先される。

## warm-reboot での挙動

### OrchDaemon::warmRestoreAndSyncUp() (orchdaemon.cpp:1093-1169)

```
WarmStart::setWarmStartState("orchagent", INITIALIZED)
  → 全 Orch::bake()    # 既存 APP_DB データを m_toSync に投入
  → 3回ループ doTask()  # 既存データを処理してメモリ状態を復元
    - 1st: SwitchOrch, PortsOrch (port init / hostif)
    - 2nd: port config (speed/mtu/fec等) + 他 orch
    - 3rd: 残余データのドレイン
  → warmRestoreValidation() # pending task なし確認
  → syncd_apply_view()
  → 全 Orch::onWarmBootEnd()
WarmStart::setWarmStartState("orchagent", RECONCILED)
```

### PortsOrch::bake() での warm-reboot 条件 (portsorch.cpp:4338-4393)

```
APP_DB:"PORT|PortConfigDone" が存在 AND "PORT|PortInitDone" が存在
  → true (warm-reboot 復元モード)
  → 既存 PORT / LAG / LAG_MEMBER / VLAN / VLAN_MEMBER を m_pendingPortSet に投入
```

PortConfigDone / PortInitDone が存在しない場合は `false` を返しコールドスタートに fallback。

### warm-reboot 時の CHASSIS_APP_DB 書き込み

CHASSIS_APP_DB (redis_chassis) は **warm-reboot をまたいでも supervisor 側で保持される**。
ラインカード側の orchagent が再起動しても supervisor の redis_chassis は停止しないため、
既存エントリは残存する。orchagent の warm-reboot 復元フロー (bake → doTask 3回ループ) では、
既存エントリと同一内容を SET しても冪等に上書きされる（ProducerStateTable の既存 key 上書き）。

`m_isWarmRestoreStage == true` の間は `PortsOrch::initializePorts()` 内で `postPortInit()` をスキップし、
ポート速度等の再設定を遅延させる。`onWarmBootEnd()` で `m_isWarmRestoreStage = false` になり
`refreshPortStatus()` が動いて oper_status が更新される。oper_status 変化は
`voqSyncIntfState()` 経由で SYSTEM_INTERFACE の `oper_status` フィールドを再書き込みする。

### chassisd 側のクリーンアップタイマー

ラインカードが down した場合、supervisor 上の `chassisd` は `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30` 分待機後に `_cleanup_chassis_app_db()` を呼び出す。  
warm-reboot の場合はラインカードが down → up を 30 分以内に完了するため、クリーンアップは**実行されない**（`down_modules[module]['cleaned']` が True にならない）。

## 依存グラフ（SET 時）

```
CONFIG_DB.DEVICE_METADATA (switch_type=voq)
  └─ gMultiAsicVoq = true
       └─ chassis_app_db 接続確立
            ├─ SYSTEM_LAG_ID_START / SYSTEM_LAG_ID_END (初期化スクリプトが先行書き込み)
            │    └─ SYSTEM_LAG_TABLE (voqSyncAddLag: PortInitDone 後 LAG CREATE 時)
            │         └─ SYSTEM_LAG_MEMBER_TABLE (voqSyncAddLagMember: LAG MEMBER ADD 時)
            ├─ SYSTEM_INTERFACE (voqSyncAddIntf: PortInitDone 後 intfsorch ADD 時)
            └─ SYSTEM_NEIGH (voqSyncNeigh: neighbor 作成 + encap_index != 0 確認後)
```

BGP_DEVICE_GLOBAL|STATE は orchagent 経由ではなく bgpcfgd が直接書き込む（独立経路）。
