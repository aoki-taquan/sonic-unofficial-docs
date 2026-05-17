# smart-switch — Phase H: platform 依存・ハードウェア固有挙動

調査日: 2026-05-17  
対象ファイル:
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- `sonic-platform-common/sonic_platform_base/chassis_base.py`
- `sonic-platform-common/sonic_platform_base/module_base.py`

---

## 1. SmartSwitch 判定とデーモン分岐

`chassisd` の `main()` は起動時に `chassis.is_smartswitch()` と `chassis.is_dpu()` を呼び出し、
3 種類のデーモンに分岐する。

```python
# chassisd:1571-1583
chassis = get_chassis()
if chassis.is_smartswitch() and chassis.is_dpu():
    chassisd = DpuChassisdDaemon(SYSLOG_IDENTIFIER, chassis)
else:
    chassisd = ChassisdDaemon(SYSLOG_IDENTIFIER, chassis)
```

| 条件 | デーモンクラス | 役割 |
|---|---|---|
| `is_smartswitch() and is_dpu()` | `DpuChassisdDaemon` | DPU 上で動作。control/data plane 状態を CHASSIS_STATE_DB に更新 |
| `is_smartswitch() and not is_dpu()` | `ChassisdDaemon` (SmartSwitch モード) | NPU 上で動作。SmartSwitchModuleUpdater で全 DPU を管理 |
| `not is_smartswitch()` | `ChassisdDaemon` (通常モード) | スーパバイザ/ラインカード構成で動作 |

`chassis_base.py:317-325` のデフォルト実装は `is_smartswitch()` が `False` を返す。
SmartSwitch プラットフォームはこのメソッドをオーバーライドして `True` を返す必要がある。

---

## 2. プラットフォーム API と MID_PLANE_BRIDGE の関係

`MID_PLANE_BRIDGE|GLOBAL` の `bridge` フィールド（`"bridge-midplane"`）は CONFIG_DB の設定値だが、
実際のミッドプレーン L2 接続の初期化はプラットフォーム API で行われる。

### init_midplane_switch()

```python
# chassis_base.py:171-184
def init_midplane_switch(self):
    """
    Initializes the midplane functionality of the modular chassis.
    The expectation is that the required kernel modules, ip-address assignment
    etc are done before the pmon, database dockers are up.

    Returns:
        A bool value, should return True if the midplane initialized successfully.
    """
    return NotImplementedError
```

`SmartSwitchModuleUpdater.__init__()` (`chassisd:717`) はこのメソッドを呼び出して結果を
`self.midplane_initialized` に保存する。`False` の場合は `LOG_ERR` を出力して `check_midplane_reachability()` をスキップする。

**CONFIG_DB との関係**: `init_midplane_switch()` は CONFIG_DB を参照しない。カーネルモジュールや
プラットフォームドライバレベルで `bridge-midplane` インターフェースを作成することが期待される。
CONFIG_DB の `MID_PLANE_BRIDGE|GLOBAL.ip_prefix` は DHCP サーバ（`dhcpservd`）が参照するが、
ブリッジ自体のネットワーク設定はプラットフォーム側が担う。

---

## 3. DPU 再起動タイムアウトのプラットフォーム上書き

`SmartSwitchModuleUpdater` はデフォルトの DPU 再起動タイムアウト（`DEFAULT_DPU_REBOOT_TIMEOUT = 360` 秒）を
`/usr/share/sonic/platform/platform.json` で上書きできる。

```python
# chassisd:721-731
self.dpu_reboot_timeout = DEFAULT_DPU_REBOOT_TIMEOUT
if os.path.isfile(PLATFORM_JSON_FILE):
    try:
        with open(PLATFORM_JSON_FILE, 'r') as f:
            platform_cfg = json.load(f)
        self.dpu_reboot_timeout = int(platform_cfg.get("dpu_reboot_timeout",
                                                        DEFAULT_DPU_REBOOT_TIMEOUT))
    except (json.JSONDecodeError, ValueError) as e:
        self.log_error("Error parsing {}: {}".format(PLATFORM_JSON_FILE, e))
```

- デフォルト: `360` 秒（`DEFAULT_DPU_REBOOT_TIMEOUT`）
- 上限: `MAX_DPU_REBOOT_DURATION = 800` 秒（再起動判定の有効期間として使用）
- プラットフォーム固有値は `platform.json` の `dpu_reboot_timeout` キーで指定

これは YANG や CONFIG_DB フィールドではなく、ファイルシステム上のプラットフォーム構成ファイルによる制御。

---

## 4. midplane 到達性チェックと STATE_DB 書き込み

`SmartSwitchModuleUpdater.check_midplane_reachability()` (`chassisd:1074-1110`) は
`CHASSIS_INFO_UPDATE_PERIOD_SECS = 10` 秒ごとに呼び出される。

プラットフォーム API:
- `module.get_midplane_ip()` — DPU の midplane IP アドレスを返す（プラットフォーム実装）
- `module.is_midplane_reachable()` — midplane 到達可能性をチェック（プラットフォーム実装）

**STATE_DB への書き込み先**:

| DB | テーブル | キー | フィールド | 値 |
|---|---|---|---|---|
| STATE_DB | `CHASSIS_MIDPLANE_TABLE` | `<DPU名>` | `ip_address` | `module.get_midplane_ip()` の戻り値 |
| STATE_DB | `CHASSIS_MIDPLANE_TABLE` | `<DPU名>` | `access` | `str(module.is_midplane_reachable())` |
| CHASSIS_STATE_DB | `DPU_STATE` | `DPU_STATE\|<DPU名>` | `dpu_midplane_link_state` | `"up"` or `"down"` |
| CHASSIS_STATE_DB | `DPU_STATE` | `DPU_STATE\|<DPU名>` | `dpu_midplane_link_time` | 変化時刻 |

到達性が `True→False` に変化したとき、`update_dpu_state()` は `dpu_midplane_link_state` を `"down"` にするとともに
`dpu_control_plane_state` / `dpu_data_plane_state` も `"down"` に設定する（`chassisd:880-885`）。

---

## 5. MODULE_TYPE_DPU の名前制約

`module_base.py:37` で `MODULE_TYPE_DPU = "DPU"` と定義されている。

`SmartSwitchModuleConfigUpdater.module_config_update()` (`chassisd:236-239`) は
`CHASSIS_MODULE` テーブルのキーが `"DPU"` で始まらない場合に `LOG_ERR` を出力してスキップする。

```python
if not key.startswith(ModuleBase.MODULE_TYPE_DPU):
    self.log_error("Incorrect module-name {}. Should start with {}".format(key,
                                                ModuleBase.MODULE_TYPE_DPU))
    return
```

これは CONFIG_DB の `CHASSIS_MODULE` テーブルのキー制約であり、SmartSwitch では
`DPU0`, `DPU1`, ... の形式のみ有効。

---

## 6. CONFIG_DB CHASSIS_MODULE テーブルと管理状態

`SmartSwitchConfigManagerTask` は CONFIG_DB の `CHASSIS_MODULE` テーブルを `SubscriberStateTable` で購読し、
DPU の管理状態（`admin_status`）を監視する。

```python
# chassisd:1216-1228
if op == 'SET':
    fvs = dict(fvp)
    admin_status = fvs.get('admin_status')
    if admin_status == 'up':
        admin_state = MODULE_ADMIN_UP
    else:
        admin_state = MODULE_ADMIN_DOWN
elif op == 'DEL':
    admin_state = MODULE_ADMIN_DOWN
```

`admin_status = 'up'` → `MODULE_ADMIN_UP` (1) → `chassis.get_module(index).set_admin_state_gracefully(1)`
`admin_status != 'up'` または DEL → `MODULE_ADMIN_DOWN` (0) → `set_admin_state_gracefully(0)` を呼び出す。

**CONFIG_DB 読み取り（get_module_admin_status）**:
`SmartSwitchModuleUpdater.get_module_admin_status()` (`chassisd:748-756`) は CONFIG_DB の
`CHASSIS_MODULE|<dpu_name>.admin_status` を直接読み取る。SmartSwitch 起動時の初期状態設定に使用される。

---

## 7. CONFIG_DB を参照しないプラットフォーム依存項目

以下の動作は CONFIG_DB / YANG を経由せず、プラットフォーム API またはファイルシステムに直接依存する:

| 動作 | 依存先 | 説明 |
|---|---|---|
| ミッドプレーン初期化 | `chassis.init_midplane_switch()` | `bridge-midplane` カーネルインターフェースの作成 |
| DPU の midplane IP 取得 | `module.get_midplane_ip()` | プラットフォーム実装。CONFIG_DB 非経由 |
| midplane 到達性確認 | `module.is_midplane_reachable()` | ping/ARP 等のプラットフォーム実装 |
| DPU の再起動タイムアウト | `/usr/share/sonic/platform/platform.json` | `dpu_reboot_timeout` キー |
| DPU 再起動原因の永続化 | `/host/reboot-cause/module/<dpu>/` | ファイルシステム直接書き込み |
| SmartSwitch/DPU 判定 | `chassis.is_smartswitch()` / `chassis.is_dpu()` | プラットフォームオーバーライド必須 |

---

## Evidence

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:1571-1583` (main 分岐)
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:717-731` (dpu_reboot_timeout)
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:1074-1110` (check_midplane_reachability)
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:1180-1228` (SmartSwitchConfigManagerTask)
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:236-256` (module_config_update)
- `sonic-platform-common/sonic_platform_base/chassis_base.py:171-184,300-340` (platform API)
- `sonic-platform-common/sonic_platform_base/module_base.py:37,183` (MODULE_TYPE_DPU)
