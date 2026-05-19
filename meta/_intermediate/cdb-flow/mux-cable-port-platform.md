# MUX_CABLE — Phase H プラットフォーム差異調査

## 調査元

- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py` (master)
- `sonic-linkmgrd/src/DbInterface.cpp` (master)

## 概要

MUX_CABLE の per-port 処理には以下の明示的なプラットフォーム差異がある:

1. **`cable_type` フィールド** (`active-standby` vs `active-active`): 経路が完全に分岐
2. **VS (Virtual Switch) / Mux Simulator** モード: 物理 Y-cable の代わりにソフトウェアシミュレーション
3. **ベンダー固有 Y-cable ドライバ**: `y_cable_vendor_mapping` で manufacturer + model ごとに異なる API モジュールを動的ロード

## `cable_type` による処理分岐

`check_mux_cable_port_type()` (`y_cable_helper.py:309-317`) が `MUX_CABLE|<port>.cable_type` を読んで分岐:

| `cable_type` 値 | 処理経路 |
|---|---|
| `"active-active"` | `active-active` 専用 API (`get_muxcable_info_for_active_active()`) を使用。gRPC チャンネル (`grpc_client`) 経由でケーブル制御 |
| `"active-standby"` (デフォルト) | 従来の Y-cable API 経由でケーブル制御 |
| `None` (フィールド不在) | `DbInterface.cpp:827` で `"active-standby"` にフォールバック |

`active-active` は Grpc ベースの制御を必要とし、追加の gRPC チャンネル設定 (`setup_grpc_channel_for_port()`) が呼ばれる。

## VS (Virtual Switch) / Mux Simulator モード

`y_cable_is_platform_vs = True` の場合:

- `y_cable_wrapper_get_presence()` (`y_cable_helper.py:178`) が常に `True` を返す（物理 SFP 不在でも存在扱い）
- `y_cable_wrapper_get_transceiver_info()` (`y_cable_helper.py:222`) が VS 用ダミー情報を返す
- `/etc/sonic/mux_simulator.json` が存在する場合、`manufacturer = "microsoft"`、`model = "simulated"` で上書き (`y_cable_helper.py:200-207`)。これにより `y_cable_vendor_mapping` で Microsoft の mux simulator モジュールがロードされる

`init_ports_status_for_y_cable(is_vs=True)` で VS モードが有効化される (`y_cable_helper.py:1359,1369`)。

## ベンダー固有 Y-cable ドライバの動的ロード

`y_cable_helper.py:1203-1232` の初期化フロー:

1. トランシーバー情報から `manufacturer` と `model` を取得
2. `y_cable_vendor_mapping.mapping[vendor][model]` でベンダー固有モジュール名を解決
3. `importlib.import_module()` でモジュールを動的ロードし `y_cable_port_instances[physical_port]` に格納
4. API 呼び出しは全てこのインスタンス経由で行われる

`manufacturer` が `"microsoft"` かつ `/etc/sonic/mux_simulator.json` 存在時は Microsoft の Mux Simulator API が使用される（VS/testbed 用）。

## `pseudo-cable` 処理

物理ポートが存在しない場合 (`y_cable_wrapper_get_presence()` = False) や
`cable_type == 'pseudo-cable'` の場合、`post_port_mux_info_to_db()` は
mux_info_dict への書き込みをスキップする (`y_cable_helper.py:2200`)。

## まとめ

| プラットフォーム条件 | 挙動の差 |
|---|---|
| `cable_type = "active-active"` | gRPC 経由制御、専用 API 使用 |
| `cable_type = "active-standby"` (デフォルト) | Y-cable ベンダー API 使用 |
| `is_vs = True` または mux_simulator.json 存在 | SFP 存在偽装、microsoft/simulated ドライバ使用 |
| `pseudo-cable` | mux_info_dict 書き込みスキップ |
| ベンダー固有 (manufacturer/model) | y_cable_vendor_mapping で動的モジュール切り替え |
