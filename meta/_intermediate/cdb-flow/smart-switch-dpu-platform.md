# SmartSwitch DPU — プラットフォーム差調査 (Phase H)

Task F Phase H: SmartSwitch DPU テーブル群 (`MID_PLANE_BRIDGE` / `DPUS` / `DPU` / `REMOTE_DPU` / `VDPU` / `DASH_HA_GLOBAL_CONFIG`) のプラットフォーム・ベンダー依存を調査した。

## 主要調査ソース

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:82-85,144-146,302-311,717-729,1412-1420,1532-1579`
- `sonic-buildimage/platform/mellanox/mlnx-platform-api/sonic_platform/module.py:261-514`
- `sonic-buildimage/platform/mellanox/mlnx-platform-api/sonic_platform/device_data.py:32-378`
- `sonic-buildimage/platform/mellanox/mlnx-platform-api/sonic_platform/dpuctlplat.py:87-134`
- `sonic-buildimage/platform/mellanox/mlnx-platform-api/tests/dpuctl_inputs/platform.json`

## 結論

**Mellanox (NVIDIA) 固有実装あり**。主に以下の 3 点で platform API 依存が存在する:
1. `get_midplane_ip()` — IP 計算式がハードコード（Mellanox 固有）
2. `platform.json` — ミッドプレーンインターフェース名を platform ごとに定義
3. `get_oper_status()` — Mellanox `BootProgEnum.OS_RUN` による online/offline 判定
4. `get_reboot_cause()` — Mellanox `mlxreg` コマンド + `/var/run/hw-management/` sysfs パスへの依存

## 詳細

### 1. chassisd — `is_smartswitch()` による分岐

`ChassisdDaemon.run()` (chassisd:1412) で `platform_chassis.is_smartswitch()` を呼び出し:

```python
# chassisd:1412-1420
self.smartswitch = self.platform_chassis.is_smartswitch()
if self.smartswitch:
    self.module_updater = SmartSwitchModuleUpdater(...)
else:
    self.module_updater = ModuleUpdater(...)  # 標準 chassis
```

エントリポイント `main()` (chassisd:1576) では `is_dpu()` も評価して DPU 側の `DpuChassisdDaemon` と NPU 側の `ChassisdDaemon` を分岐する:

```python
# chassisd:1576-1579
if chassis.is_smartswitch() and chassis.is_dpu():
    chassisd = DpuChassisdDaemon(...)
else:
    chassisd = ChassisdDaemon(...)
```

`is_smartswitch()` / `is_dpu()` は `sonic_platform.platform.Platform().get_chassis()` から得られるオブジェクトのメソッドであり、platform プラグイン実装に依存する。

### 2. PLATFORM_JSON_FILE による `dpu_reboot_timeout` 上書き

`SmartSwitchModuleUpdater.__init__()` (chassisd:722-727) は `/usr/share/sonic/platform/platform.json` を読み、`dpu_reboot_timeout` キーが存在すれば `DEFAULT_DPU_REBOOT_TIMEOUT=360` 秒を上書きする:

```python
# chassisd:722-727
if os.path.isfile(PLATFORM_JSON_FILE):
    with open(PLATFORM_JSON_FILE, 'r') as f:
        platform_cfg = json.load(f)
    self.dpu_reboot_timeout = int(
        platform_cfg.get("dpu_reboot_timeout", DEFAULT_DPU_REBOOT_TIMEOUT)
    )
```

これは **platform ごとに DPU リブートタイムアウトが異なる** ことを明示する。Mellanox 搭載プラットフォームのテスト `platform.json` には `dpu_reboot_timeout` キーが含まれていないため、デフォルト 360 秒が使用される。

### 3. Mellanox `DpuModule.get_midplane_ip()` — IP 計算式がハードコード

Mellanox の `module.py:478-490`:

```python
def get_midplane_ip(self):
    return f"169.254.200.{int(self.dpu_id) + 1}"
```

この `169.254.200.x` アドレス体系は Mellanox プラットフォームに固有のハードコードである。他ベンダーの platform 実装は異なる IP 計算式またはアドレスレンジを使用する可能性がある。chassisd はこのメソッドを抽象インタフェース経由で呼ぶため、CONFIG_DB の `MID_PLANE_BRIDGE.ip_prefix` が `169.254.200.254/24` 固定なのは Mellanox 実装の前提を反映したものである。

### 4. `platform.json[DPUS]` によるインターフェース解決 (Mellanox 固有)

Mellanox `device_data.py:358-370` は `/usr/share/sonic/platform/platform.json` の `DPUS` セクションからミッドプレーンインターフェース名を読み取る:

```python
# device_data.py:358-370
def get_platform_dpus_data(cls):
    platform_json_path = os.path.join(platform_path, 'platform.json')
    json_data = utils.load_json_file(platform_json_path)
    return json_data.get('DPUS', None)

def get_dpu_interface(cls, dpu, interface):
    dpu_data = cls.get_platform_dpus_data()
    return dpu_data.get(dpu, {}).get(interface)
```

Mellanox テスト用 `platform.json`:

```json
{
    "DPUS": {
        "dpu0": { "midplane_interface": "dpu0" },
        "dpu1": { "midplane_interface": "dpu1" },
        "dpu2": { "midplane_interface": "dpu2" },
        "dpu3": { "midplane_interface": "dpu3" }
    }
}
```

`platform.json[DPUS]` が存在しない場合、`get_midplane_interface()` が `RuntimeError` を送出し、`_is_midplane_up()` → `is_midplane_reachable()` が常に `False` を返す。

### 5. `get_oper_status()` — `BootProgEnum.OS_RUN` (Mellanox 固有 sysfs)

Mellanox `module.py:417-420`:

```python
def get_oper_status(self):
    boot_prog = self.dpuctl_obj.read_boot_prog()
    if boot_prog == BootProgEnum.OS_RUN.value:
        return ModuleBase.MODULE_STATUS_ONLINE
    return ModuleBase.MODULE_STATUS_OFFLINE
```

`BootProgEnum.OS_RUN.value = 5` (dpuctlplat.py:93)。`read_boot_prog()` は Mellanox `hw-management` が提供する sysfs ファイル `/var/run/hw-management/dpu{N}/system/boot_progress` を読む。このファイルは Mellanox 固有のカーネルドライバにより書き込まれる。他ベンダーは異なる online 判定手段を実装する。

### 6. `get_reboot_cause()` — Mellanox `mlxreg` 依存

Mellanox `module.py:437-476` は Watchdog リブート原因取得のために `mlxreg` コマンドを直接呼び出す:

```python
op = subprocess.check_output(
    ['mlxreg', '-d', pcie_dev_id, '--reg_name', 'MRSI', '-g', '-indexes', 'device=1']
)
```

`mlxreg` は Mellanox ハードウェア固有のレジスタアクセスツール。その他のリブート原因は `/var/run/hw-management/{dpu}/system/reset_*` sysfs ファイルで判定する。これらは Mellanox `hw-management` ドライバ依存であり、他ベンダープラットフォームでは利用不可。

### 7. PLATFORM_ENV_CONF_FILE

`chassisd:84,302-303` で `/usr/share/sonic/platform/platform_env.conf` を参照しているが、SmartSwitch / DPU テーブルの挙動には直接影響しない（ModuleUpdater 基底クラスの環境変数読み込みのみ）。

## まとめ

| 差分ポイント | 影響するテーブル | 内容 |
|---|---|---|
| `get_midplane_ip()` IP 計算式 | `MID_PLANE_BRIDGE`, `DPUS` | Mellanox 固有: `169.254.200.(dpu_id+1)`. 他ベンダーは異なる可能性 |
| `platform.json[DPUS]` | `DPUS` | ミッドプレーンインターフェース名解決。Mellanox 必須。欠落で RuntimeError |
| `platform.json[dpu_reboot_timeout]` | `CHASSIS_MODULE` 間接 | デフォルト 360 秒。プラットフォームごとに変更可能 |
| `BootProgEnum.OS_RUN` sysfs | `CHASSIS_MODULE` 間接 | Mellanox hw-management 固有。online 判定方法 |
| `mlxreg` Watchdog 判定 | `CHASSIS_STATE_DB.REBOOT_CAUSE` 間接 | Mellanox 固有コマンド。他ベンダーは代替手段 |
| `DASH_HA_GLOBAL_CONFIG` / `DPU` / `REMOTE_DPU` / `VDPU` | 上記全て | SAI 実装は DASH ハードウェア依存だが CONFIG_DB テーブル構造はプラットフォーム非依存 |
