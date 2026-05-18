# DPU orchagent (DpuOrchDaemon) 書込み順依存調査メモ

調査日: 2026-05-18
対象: `DEVICE_METADATA|localhost` フィールドを起点とした DpuOrchDaemon 初期化順序

## 調査対象ファイル

- `sonic-swss/orchagent/main.cpp` (getCfgSwitchType, gMySwitchType, DpuOrchDaemon生成)
- `sonic-swss/orchagent/orchdaemon.cpp` (DpuOrchDaemon::init, OrchDaemon::init)
- `sonic-swss/lib/orch_zmq_config.cpp` (get_feature_status)
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh`

---

## 順序依存の概要

### 依存 #1: switch_type 読み取り → SAI 初期化

```cpp
// main.cpp:658
getCfgSwitchType(&config_db, gMySwitchType, gMySwitchSubType);
// → SAI sai_api_initialize() 等より先行
```

gMySwitchType はグローバル変数。以降プロセス再起動まで不変。

### 依存 #2: switch_type=dpu → DPU_APPL_DB 接続

```cpp
// main.cpp:990-994
if (gMySwitchType == "dpu")
{
    dpu_app_db = make_shared<DBConnector>("DPU_APPL_DB", 0, true);
    dpu_app_state_db = make_shared<DBConnector>("DPU_APPL_STATE_DB", 0, true);
    orchDaemon = make_shared<DpuOrchDaemon>(..., dpu_app_db.get(), dpu_app_state_db.get(), ...);
}
```

DPU_APPL_DB / DPU_APPL_STATE_DB は DpuOrchDaemon コンストラクタ引数として渡される。

### 依存 #3: OrchDaemon::init() → DpuOrchDaemon::init() の DASH Orch 初期化

```cpp
// orchdaemon.cpp:1322-1324
bool DpuOrchDaemon::init()
{
    SWSS_LOG_NOTICE("DpuOrchDaemon init...");
    OrchDaemon::init();  // ← 基底クラス先行必須
    // ...DASH Orch 初期化...
```

### 依存 #4: orch_northbond_dash_zmq_enabled 読み取り → dash_zmq_server 確定

```cpp
// orchdaemon.cpp:1327-1333
ZmqServer *dash_zmq_server = nullptr;
if (get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true))
{
    dash_zmq_server = m_zmqServer;
}
// → DashVnetOrch, DashOrch, DashHaOrch, DashRouteOrch, DashAclOrch,
//    DashTunnelOrch, DashMeterOrch, DashPortMapOrch, DashHaFlowOrch 全て dash_zmq_server を引数に取る
```

### 依存 #5: ZMQ サーバ生成 → DpuOrchDaemon コンストラクタ

orchagent.sh:
```bash
elif [[ x"$LOCALHOST_SWITCHTYPE" == x"dpu" ]]; then
    ORCHAGENT_ARGS+="-b 65536 "
fi
if [ "$LOCALHOST_SWITCHTYPE" == "dpu" ]; then
    ORCHAGENT_ARGS+="-z zmq_sync -k 65536 "
fi
```

ZMQ sync mode は起動前に確定。プロセス起動後は CONFIG_DB 変更で変えられない。

---

## 結論

| # | 依存関係 | 方向 | 備考 |
|---|----------|------|------|
| 1 | switch_type 読み取り → SAI 初期化 | 強制先行 | 起動後変更不可 |
| 2 | switch_type=dpu → DPU DB 接続 | 強制先行 | コンストラクタ引数として確定 |
| 3 | OrchDaemon::init() → DpuOrchDaemon DASH Orch 初期化 | 強制先行 | 基底クラス先行必須 |
| 4 | orch_northbond_dash_zmq_enabled → dash_zmq_server | 強制先行 | 全 DASH Orch コンストラクタに渡される |
| 5 | ZMQ サーバ生成 → DpuOrchDaemon コンストラクタ | 強制先行 | orchagent.sh で起動前確定 |
