# CHASSIS_MODULE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `CHASSIS_MODULE`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-chassis-module.yang`
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` (ModuleUpdater / SmartSwitchModuleUpdater / ModuleConfigUpdater)
- `sonic-utilities/config/chassis_modules.py` (CLI 書き込み)
- `sonic-utilities/show/chassis_modules.py` (show コマンド)
- `sonic-platform-common/sonic_platform_base/module_base.py` (定数定義)

---

## フィールド別 暗黙デフォルト

### `name` (key フィールド)

**YANG パターン**: `LINE-CARD[0-9]+|FABRIC-CARD[0-9]+|DPU[0-9]+`

**YANG-実装乖離**: YANG は `SUPERVISOR*` を key として許可していないが、CLI (`config/chassis_modules.py:148,189`) は `startswith("SUPERVISOR", ...)` を許容する。`SUPERVISOR-CARD0` 等のエントリは YANG バリデーション通過不可だが実装上は設定・読み取りされる。

**大文字小文字制約**: `MODULE_TYPE_SUPERVISOR="SUPERVISOR"`, `MODULE_TYPE_LINE="LINE-CARD"`, `MODULE_TYPE_FABRIC="FABRIC-CARD"`, `MODULE_TYPE_DPU="DPU"` (module_base.py:34-37)。これらは完全一致の prefix チェック (`key.startswith(...)`) で判定されるため大文字小文字は厳密。

---

### `admin_status` (唯一の設定フィールド)

**YANG デフォルト**: `up`

**コード由来デフォルト（エントリ不在時）**: **プラットフォーム依存の分岐あり**

#### 標準チャシス (non-SmartSwitch)

```python
# config/chassis_modules.py:57-66
def get_config_module_state(db, chassis_module_name):
    config_db = db.cfgdb
    fvs = config_db.get_entry('CHASSIS_MODULE', chassis_module_name)
    if not fvs:
        if is_smartswitch():
            return 'down'
        else:
            return 'up'     # <-- エントリ不在 → 'up' を返す
    else:
        return fvs['admin_status']
```

標準チャシスではエントリが存在しない場合 `'up'` として扱われる。これは YANG default `up` と一致する。

#### SmartSwitch (DPU 搭載機)

エントリ不在時のデフォルトは `'down'`。`is_smartswitch()` が `True` の場合:
- `get_config_module_state()` → `'down'` を返す
- show コマンド (`show/chassis_modules.py:70-76`) → `admin_status = 'down'` をデフォルトとして表示

YANG の `default up` と実装の SmartSwitch fallback `down` は**乖離**している。

#### chassisd (ModuleUpdater) のデフォルト

```python
# chassisd:354-362  ModuleUpdater.get_module_admin_status()
def get_module_admin_status(self, chassis_module_name):
    config_db = daemon_base.db_connect("CONFIG_DB")
    vtable = swsscommon.Table(config_db, CHASSIS_CFG_TABLE)
    fvs = vtable.get(chassis_module_name)
    if isinstance(fvs, list) and fvs[0] is True:
        fvs = dict(fvs[-1])
        return fvs[CHASSIS_MODULE_ADMIN_STATUS]
    else:
        return 'up'   # <-- エントリ不在 → 'up'
```

非-SmartSwitch chassisd は `'up'` を fallback とする。

#### SmartSwitchModuleUpdater のデフォルト

```python
# chassisd:748-756  SmartSwitchModuleUpdater.get_module_admin_status()
def get_module_admin_status(self, chassis_module_name):
    ...
    if isinstance(fvs, list) and fvs[0] is True:
        ...
        return fvs[CHASSIS_MODULE_ADMIN_STATUS]
    else:
        return ModuleBase.MODULE_STATUS_EMPTY  # 'Empty'
```

SmartSwitch chassisd はエントリ不在時に `'Empty'` を返す。これは `'up'` でも `'down'` でもなく、`module_cfg_status != 'down'` の条件 (chassisd:447) では `'up'` と同様に扱われる（ASIC テーブル更新が実行される）。

---

### `startup` コマンドの silent deletion (書き込み時 vs 実行時 乖離)

```python
# config/chassis_modules.py:210
config_db.set_entry('CHASSIS_MODULE', chassis_module_name, None)
```

非-SmartSwitch における `config chassis_modules startup <name>` は `admin_status: up` を明示的に書き込まず、エントリを**削除**する。エントリ不在 = `'up'` として扱われる慣用的パターン。

SmartSwitch では `{'admin_status': 'up'}` を明示的に書き込む (config/chassis_modules.py:204-207)。

**書き込み順依存**: startup → shutdown → startup の操作で non-SmartSwitch はエントリが削除→作成(`down`)→削除の変化をたどる。

---

## プラットフォーム依存デフォルト (chassisd 内部)

### `linecard_reboot_timeout` (PLATFORM_ENV_CONF_FILE)

```python
# chassisd:81,301-307
DEFAULT_LINECARD_REBOOT_TIMEOUT = 180  # 秒

self.linecard_reboot_timeout = DEFAULT_LINECARD_REBOOT_TIMEOUT
if os.path.isfile(PLATFORM_ENV_CONF_FILE):
    with open(PLATFORM_ENV_CONF_FILE, 'r') as file:
        for line in file:
            field = line.split('=')[0].strip()
            if field == "linecard_reboot_timeout":
                self.linecard_reboot_timeout = int(line.split('=')[1].strip())
```

`/usr/share/sonic/platform/platform_env.conf` で `linecard_reboot_timeout=<N>` が定義されていない場合、**180 秒** がハードコードデフォルト。ミッドプレーン再接続タイムアウト判定に使用。

### `dpu_reboot_timeout` (PLATFORM_JSON_FILE, SmartSwitch のみ)

```python
# chassisd:83,721-731
DEFAULT_DPU_REBOOT_TIMEOUT = 360  # 秒

self.dpu_reboot_timeout = DEFAULT_DPU_REBOOT_TIMEOUT
if os.path.isfile(PLATFORM_JSON_FILE):
    ...
    self.dpu_reboot_timeout = int(platform_cfg.get("dpu_reboot_timeout", DEFAULT_DPU_REBOOT_TIMEOUT))
```

`/usr/share/sonic/platform/platform.json` で `dpu_reboot_timeout` が未定義の場合、**360 秒** がハードコードデフォルト。DPU の midplane 再接続タイムアウト判定に使用。

### `MAX_DPU_REBOOT_DURATION`

```python
# chassisd:84
MAX_DPU_REBOOT_DURATION = 800  # 秒 (ハードコード固定値)
```

DPU の reboot cause を同一 reboot として判定する最大時間窓。変更不可のハードコード定数。

---

## try_get fallback (STATE_DB 書き込み時)

chassisd が platform API から情報取得できない場合の fallback 値:

| フィールド | Platform API メソッド | fallback 値 |
|---|---|---|
| `name` | `get_name()` | `'N/A'` |
| `desc` | `get_description()` | `'N/A'` |
| `slot` | `get_slot()` | `MODULE_INVALID_SLOT` = `-1` |
| `oper_status` | `get_oper_status()` | `MODULE_STATUS_OFFLINE` = `"Offline"` |
| `serial` | `get_serial()` | `'N/A'` |
| `model` | `get_model()` | `'N/A'` |
| `presence` | `get_presence()` | `'N/A'` |
| `is_replaceable` | `is_replaceable()` | `'N/A'` |
| `asics` | `get_all_asics()` | `[]` (空リスト) |
| `midplane_ip` | `get_midplane_ip()` | `'0.0.0.0'` |
| `midplane_access` | `is_midplane_reachable()` | `False` |

これらは CONFIG_DB フィールドではなく STATE_DB の `CHASSIS_MODULE_TABLE` に書き込まれる値。ただし `oper_status` の fallback `"Offline"` は slot が `down` 状態であるかのように扱われ、ASIC テーブル更新がスキップされる。

---

## 複合必須制約 (FABRIC-CARD 操作の前提条件)

`config chassis_modules shutdown FABRIC-CARD*` の実行時:
1. `admin_status: down` を CONFIG_DB に書き込み
2. `check_config_module_state_with_timeout()` (最大 10 秒) で chassisd の反映を待機
3. タイムアウト後に `fabric_module_set_admin_status(db, name, 'down')` で ASIC サービス停止

→ chassisd が起動していない場合、timeout 後に強制実行される。timeout は **TIMEOUT_SECS = 10 秒** (config/chassis_modules.py:12) ハードコード。

---

## 要約表

| フィールド | YANG default | コード由来デフォルト | 条件 |
|-----------|-------------|-------------------|------|
| `admin_status` (非 SmartSwitch) | `up` | `'up'` (エントリ不在時) | chassisd:362, config:64 |
| `admin_status` (SmartSwitch) | `up` | `'down'` (エントリ不在時) | config:62 — **YANG と乖離** |
| `admin_status` (SmartSwitch chassisd) | `up` | `'Empty'` (エントリ不在時) | chassisd:756 — 実質 up 扱い |
| `name` key パターン (YANG) | — | `LINE-CARD[0-9]+|FABRIC-CARD[0-9]+|DPU[0-9]+` のみ | YANG バリデーション |
| `name` key (CLI) | — | `SUPERVISOR*` も許可 | **YANG-実装 discrepancy** |
| `linecard_reboot_timeout` | — | `180` 秒 | `platform_env.conf` 未設定時 |
| `dpu_reboot_timeout` | — | `360` 秒 | `platform.json` 未設定時 |
| `MAX_DPU_REBOOT_DURATION` | — | `800` 秒 (固定) | ハードコード、変更不可 |

---

## 証拠リンク

- `sonic-chassis-module.yang` — YANG スキーマ (key pattern, admin_status default)
- `chassisd:57-66` — `config/chassis_modules.py:get_config_module_state()` (プラットフォーム分岐)
- `chassisd:192-212` — `ModuleConfigUpdater.module_config_update()` (admin_state 適用)
- `chassisd:354-362` — `ModuleUpdater.get_module_admin_status()` (fallback `'up'`)
- `chassisd:748-756` — `SmartSwitchModuleUpdater.get_module_admin_status()` (fallback `'Empty'`)
- `chassisd:81-84` — ハードコード timeout 定数
- `chassisd:301-307` — `linecard_reboot_timeout` platform_env.conf 読み込み
- `chassisd:721-731` — `dpu_reboot_timeout` platform.json 読み込み
- `module_base.py:34-57` — MODULE_TYPE_* / MODULE_STATUS_* 定数
- `show/chassis_modules.py:63-76` — show 表示時の fallback
