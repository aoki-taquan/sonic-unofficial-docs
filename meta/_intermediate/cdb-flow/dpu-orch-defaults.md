# DPU orchagent (DpuOrchDaemon) CONFIG_DB フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `DEVICE_METADATA|localhost` — DpuOrchDaemon が参照するフィールド

## 調査対象ファイル

- `sonic-swss/orchagent/orchdaemon.h` (DpuOrchDaemon クラス定義)
- `sonic-swss/orchagent/orchdaemon.cpp` (DpuOrchDaemon::init / OrchDaemon::init)
- `sonic-swss/orchagent/main.cpp` (switch_type=dpu 判定・DpuOrchDaemon インスタンス生成)
- `sonic-swss/lib/orch_zmq_config.h` (ORCH_NORTHBOND_DASH_ZMQ_ENABLED 定数)
- `sonic-swss/lib/orch_zmq_config.cpp` (get_feature_status 実装)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang`
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh`

---

## grep エントリポイント

```
grep -n "DpuOrchDaemon\|gMySwitchType.*dpu\|ORCH_NORTHBOND_DASH_ZMQ_ENABLED" \
  sonic-swss/orchagent/main.cpp sonic-swss/orchagent/orchdaemon.cpp \
  sonic-swss/lib/orch_zmq_config.h
```

主要定数 (orch_zmq_config.h):
- `ORCH_NORTHBOND_DASH_ZMQ_ENABLED = "orch_northbond_dash_zmq_enabled"`
- `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED = "orch_northbond_route_zmq_enabled"`

---

## DpuOrchDaemon 起動条件

```cpp
// main.cpp:990-994
if (gMySwitchType == "dpu")
{
    dpu_app_db = make_shared<DBConnector>("DPU_APPL_DB", 0, true);
    dpu_app_state_db = make_shared<DBConnector>("DPU_APPL_STATE_DB", 0, true);
    orchDaemon = make_shared<DpuOrchDaemon>(...);
}
```

`switch_type` は `DEVICE_METADATA|localhost` から `getCfgSwitchType()` で読み出す:

```cpp
// main.cpp:244-257
void getCfgSwitchType(DBConnector *cfgDb, string &switch_type, ...)
{
    Table cfgDeviceMetaDataTable(cfgDb, CFG_DEVICE_METADATA_TABLE_NAME);
    if (!cfgDeviceMetaDataTable.hget("localhost", "switch_type", switch_type))
        switch_type = "switch"; // fallback デフォルト
    // 不正値の場合も "switch" にリセット
}
```

**YANG に default 文なし** → 欠如時コードが `"switch"` (NPU モード) にフォールバック。

---

## フィールド別 暗黙デフォルト

### `switch_type`

**デフォルト: `"switch"` (コード fallback)**

```cpp
// main.cpp:248-251
if (!cfgDeviceMetaDataTable.hget("localhost", "switch_type", switch_type))
    switch_type = "switch";
```

YANG 定義 (sonic-device_metadata.yang:217-224):
- 型: string pattern `chassis-packet|fabric|npu|voq|dpu|dummy-sup`
- YANG `default` 文: **なし**
- コード fallback: `"switch"` (= NPU モード)

`"dpu"` のとき:
- `DpuOrchDaemon` が選択される
- `orchagent.sh:27-39` で `-b 65536 -z zmq_sync -k 65536` が付与される (pop batch 65536、ZMQ sync モード強制)

---

### `orch_northbond_dash_zmq_enabled`

**YANG default: `true`**

```yang
// sonic-device_metadata.yang:340-344
leaf orch_northbond_dash_zmq_enabled {
    type boolean;
    description "Enable ZMQ feature on APPL_DB DASH tables.";
    default "true";
}
```

```cpp
// orchdaemon.cpp:1329-1333
if (get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true))
{
    dash_zmq_server = m_zmqServer;
}
```

`get_feature_status` 実装 (orch_zmq_config.cpp:81-104):
- `CONFIG_DB.hget("DEVICE_METADATA|localhost", "orch_northbond_dash_zmq_enabled")` を読む
- 欠如時は `default_value = true` を返す
- `"true"` 文字列のとき `true` を返す (それ以外は `false`)

効果: `true` → gNMI サービスが ZMQ チャネルで DASH イベントを orchagent に送信。
      `false` → ZMQ 無効。APPL_DB ProducerStateTable 経由のみ。

---

### `orch_northbond_route_zmq_enabled`

**YANG default: `false`**

```yang
// sonic-device_metadata.yang:346-350
leaf orch_northbond_route_zmq_enabled {
    type boolean;
    description "Enable ZMQ feature on APPL_DB ROUTE tables.";
    default "false";
}
```

DpuOrchDaemon では直接参照されないが、`OrchDaemon::init()` の RouteOrch 初期化で参照される:

```cpp
// orchdaemon.cpp:334-335
auto enable_route_zmq = get_feature_status(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false);
auto route_zmq_sever = enable_route_zmq ? m_zmqServer : nullptr;
```

DPU モードでは RouteOrch は `OrchDaemon::init()` 経由で初期化されるが、DPU 上では通常 Route テーブルへのフロー制御に使わない。

---

### orchagent.sh: DPU 固有パラメータ

```bash
# orchagent.sh:27-39
elif [[ x"$LOCALHOST_SWITCHTYPE" == x"dpu" ]]; then
    ORCHAGENT_ARGS+="-b 65536 "  # pop batch size (DPU high-volume 対応)
fi

if [ "$LOCALHOST_SWITCHTYPE" == "dpu" ]; then
    ORCHAGENT_ARGS+="-z zmq_sync -k 65536 "  # ZMQ sync mode + bulk limit
fi
```

`-b` (batch size): 65536 (DPU高ボリューム) vs 1024 (通常NPU) vs 128 (chassis-packet)
`-z zmq_sync`: synchronous_mode フィールド値に関わらず強制 ZMQ sync mode
`-k 65536`: ZMQ max bulk limit

---

## 結論

| フィールド | YANG default | コード由来デフォルト | 区分 |
|-----------|-------------|-------------------|------|
| `switch_type` | なし | `"switch"` (getCfgSwitchType fallback) | 実質必須 (DPU 起動要) |
| `orch_northbond_dash_zmq_enabled` | `"true"` | `true` (get_feature_status default_value) | 省略可 (default 有効) |
| `orch_northbond_route_zmq_enabled` | `"false"` | `false` (get_feature_status default_value) | 省略可 (default 無効) |

DPU orchagent 固有の CONFIG_DB テーブルは存在しない。
`DEVICE_METADATA|localhost` の `switch_type=dpu` が DpuOrchDaemon 選択の唯一の条件。
