# chassis-state — Phase H: プラットフォーム差調査

Task F Phase H: `CHASSIS_STATE_DB` テーブル群の動作に対するプラットフォーム依存性を `chassisd` ソースから精読した結果。

## 調査対象ファイル

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- `sonic-buildimage/files/scripts/asic_status.py`

## 結論

**プラットフォーム差あり（2 点）**:

1. **タイムアウト値のプラットフォームファイル上書き**: `linecard_reboot_timeout` と `dpu_reboot_timeout` はプラットフォーム固有ファイルで変更可能
2. **midplane API の実装有無**: `chassis.init_midplane_switch()` が `NotImplementedError` を返すプラットフォームでは midplane 監視が無効化される

ASIC 種別（Broadcom / Mellanox / Marvell 等）や multi-asic 構成による差は存在しない。

---

## 詳細根拠

### 1. `linecard_reboot_timeout` — `platform_env.conf` で上書き可能

```python
# chassisd:84,301-307 (ModuleUpdater.__init__)
PLATFORM_ENV_CONF_FILE = "/usr/share/sonic/platform/platform_env.conf"
DEFAULT_LINECARD_REBOOT_TIMEOUT = 180  # 秒

self.linecard_reboot_timeout = DEFAULT_LINECARD_REBOOT_TIMEOUT
if os.path.isfile(PLATFORM_ENV_CONF_FILE):
    with open(PLATFORM_ENV_CONF_FILE, 'r') as file:
        for line in file:
            field = line.split('=')[0].strip()
            if field == "linecard_reboot_timeout":
                self.linecard_reboot_timeout = int(line.split('=')[1].strip())
```

- デフォルト: **180 秒**
- 上書き: `/usr/share/sonic/platform/platform_env.conf` に `linecard_reboot_timeout=<N>` を記述
- 効果: `CHASSIS_MODULE_REBOOT_INFO_TABLE` のタイムスタンプエントリ削除タイミングと「midplane 接続が `<N>` 秒以内に復旧しない場合の警告ログ出力」タイミングが変わる (chassisd:529-539,584-586)
- 影響テーブル: `CHASSIS_MODULE_REBOOT_INFO_TABLE`

### 2. `dpu_reboot_timeout` — `platform.json` で上書き可能

```python
# chassisd:85,721-731 (SmartSwitchModuleUpdater.__init__)
PLATFORM_JSON_FILE = "/usr/share/sonic/platform/platform.json"
DEFAULT_DPU_REBOOT_TIMEOUT = 360  # 秒

self.dpu_reboot_timeout = DEFAULT_DPU_REBOOT_TIMEOUT
if os.path.isfile(PLATFORM_JSON_FILE):
    try:
        with open(PLATFORM_JSON_FILE, 'r') as f:
            platform_cfg = json.load(f)
        self.dpu_reboot_timeout = int(
            platform_cfg.get("dpu_reboot_timeout", DEFAULT_DPU_REBOOT_TIMEOUT)
        )
    except (json.JSONDecodeError, ValueError) as e:
        self.log_error("Error parsing {}: {}".format(PLATFORM_JSON_FILE, e))
```

- デフォルト: **360 秒**
- 上書き: `/usr/share/sonic/platform/platform.json` の `"dpu_reboot_timeout"` キー
- 効果: DPU が offline → online 遷移した際の「再起動原因が同一かどうかを判定する時間窓」に使用 (chassisd:830)。`REBOOT_CAUSE` テーブルに書き込む原因が前回と同一と判定される上限秒数
- 影響テーブル: `REBOOT_CAUSE` (SmartSwitch 専用)

### 3. `chassis.init_midplane_switch()` — platform API 実装有無で midplane 監視が有効/無効

```python
# chassisd:309-311 (ModuleUpdater.__init__)
self.midplane_initialized = try_get(chassis.init_midplane_switch, default=False)
if not self.midplane_initialized:
    self.log_error("Chassisd midplane intialization failed")
```

```python
# chassisd:541-543 (check_midplane_reachability)
def check_midplane_reachability(self):
    if not self.midplane_initialized:
        return  # midplane 監視を完全スキップ
```

- `init_midplane_switch()` が `NotImplementedError` → `try_get()` fallback で `False` → `CHASSIS_MIDPLANE_TABLE` は更新されない
- `CHASSIS_MODULE_REBOOT_INFO_TABLE` への書き込みもスキップされる（midplane 喪失検知ができないため）
- 実装済みプラットフォームのみ midplane 経由の LINE-CARD ↔ SUPERVISOR 疎通を監視する

### 4. `is_smartswitch()` — SmartSwitch vs モジュラーチャシスで書き込みテーブルが変わる

```python
# chassisd:1412-1420 (ChassisdDaemon.run)
self.smartswitch = self.platform_chassis.is_smartswitch()
if self.smartswitch:
    self.module_updater = SmartSwitchModuleUpdater(...)
else:
    self.module_updater = ModuleUpdater(...)
```

- SmartSwitch: `DPU_STATE`, `REBOOT_CAUSE` テーブルを書き込む。`CHASSIS_ASIC_TABLE`, `CHASSIS_FABRIC_ASIC_TABLE` は書き込まない
- モジュラーチャシス: `CHASSIS_MODULE_TABLE`, `CHASSIS_ASIC_TABLE` / `CHASSIS_FABRIC_ASIC_TABLE` を書き込む。`DPU_STATE`, `REBOOT_CAUSE` は書き込まない

### 5. ASIC 種別・multi-asic による差なし

`chassisd` は SAI を直接呼ばず、platform API (`get_oper_status`, `get_all_asics` 等) のみを経由する。ASIC ベンダー固有コードは platform adapter (platform plugin) 側に隠蔽されており、`chassisd` 本体には ASIC 種別条件分岐が存在しない。multi-asic (`is_multi_npu()`) の参照もない。

## まとめ

| 観点 | 結果 | 根拠 |
|------|------|------|
| `linecard_reboot_timeout` | プラットフォームで変更可 | `platform_env.conf` キー (chassisd:84,301-307) |
| `dpu_reboot_timeout` | プラットフォームで変更可 | `platform.json` キー (chassisd:85,721-731) |
| `init_midplane_switch()` 未実装 | midplane 監視・REBOOT_INFO 書き込みなし | `try_get()` fallback=False → `check_midplane_reachability()` early return (chassisd:309-311,541-543) |
| SmartSwitch vs モジュラーチャシス | 書き込みテーブルが異なる | `is_smartswitch()` 分岐 (chassisd:1412-1420) |
| ASIC 種別 (Broadcom / Mellanox 等) | 影響なし | platform adapter が吸収; `chassisd` 本体に ASIC 条件分岐なし |
| multi-asic | 影響なし | `is_multi_npu()` 参照なし |
