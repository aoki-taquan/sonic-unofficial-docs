# ZMQ CONFIG_DB フィールド — プラットフォーム差 (Phase H) 調査ノート

対象: `DEVICE_METADATA|localhost.orch_northbond_dash_zmq_enabled` / `orch_northbond_route_zmq_enabled`、`DPU|<name>.orchagent_zmq_port`。

## 1. ASIC 種別差 — なし

ZMQ チャネルは orchagent の northbound 通信層（gNMI / fpmsyncd との経路選択）に関するもので SAI を経由しない。`get_feature_status()` と `get_zmq_port()` は ASIC ベンダー依存コードを含まない（`orch_zmq_config.cpp:35-79`）。Broadcom / Mellanox / Marvell / Innovium などの ASIC 種別で動作差なし。

## 2. Multi-ASIC / namespace — ZMQ ポート計算に影響あり

multi-ASIC 環境では各 ASIC namespace (`asic0`, `asic1`, ...) に独立した orchagent インスタンスが存在し、それぞれが異なる ZMQ ポートを使用する。

```cpp
// orch_zmq_config.cpp:35-52
int get_zmq_port() {
    auto zmq_port = ORCH_ZMQ_PORT;  // = 8100
    const char* nsid = std::getenv("NAMESPACE_ID");
    if (!nsid_str.empty()) {
        zmq_port += std::stoi(nsid) + 1;  // asic0: 8101, asic1: 8102, ...
    }
    return zmq_port;
}
```

- global namespace (NAMESPACE_ID 未設定): ポート `8100`
- `NAMESPACE_ID=0` (asic0): ポート `8101`
- `NAMESPACE_ID=1` (asic1): ポート `8102`

`orch_northbond_dash_zmq_enabled` / `orch_northbond_route_zmq_enabled` フィールドはグローバル CONFIG_DB の `DEVICE_METADATA|localhost` に一元管理され、各 namespace orchagent が共通して参照する（`get_feature_status()` はグローバル DB 接続を使用）。

## 3. SmartSwitch / DPU — 専用フィールドあり

`DPU|<name>.orchagent_zmq_port` は SmartSwitch プラットフォーム専用のフィールドである。通常のスイッチには `DPU` テーブル自体が存在しない。

SmartSwitch 固有の動作:
- `orchagent.sh` が `DEVICE_METADATA.subtype == "SmartSwitch"` のとき ZMQ アドレスを `tcp://eth0-midplane` または `tcp://127.0.0.1` に切り替える（`orchagent.sh:105-118`）。
- `DEVICE_METADATA.switch_type == "dpu"` のとき orchagent が `-z zmq_sync -k 65536` 付きで起動し、ZMQ 同期モードが強制される（`orchagent.sh:38-39`）。
- NPU 上の gnmi が `DPU|<name>.orchagent_zmq_port` を参照して DPU orchagent に接続する（`gnmi-native.sh`）。

## 4. VOQ chassis / supervisor + line card

VOQ chassis 環境での ZMQ フィールドへの特別な影響は確認されていない。各 line card の orchagent インスタンスが個別に ZMQ チャネルを管理する。

## 5. Evidence

- `sonic-swss/lib/orch_zmq_config.cpp:35-52` — `get_zmq_port()` NAMESPACE_ID 分岐
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh:38-39,105-118` — SmartSwitch / DPU 専用分岐
- `sonic-swss-common/common/zmqserver.h:16` — `ORCH_ZMQ_PORT = 8100`
