# CHASSIS_MODULE プラットフォーム差異調査メモ (Phase H)

調査日: 2026-05-16  
対象テーブル: CONFIG_DB `CHASSIS_MODULE`  
フェーズ: H（プラットフォーム差分抽出）

## 調査対象ファイル

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- `sonic-platform-common/sonic_platform_base/module_base.py`
- `sonic-utilities/config/chassis_modules.py`

---

## プラットフォーム種別判定

### is_smartswitch() による分岐点

`ChassisDaemon.__init__()` (chassisd:1412-1416) で `chassis.is_smartswitch()` を呼び出し、`True` の場合に SmartSwitch 系クラスを選択する。

```python
# chassisd:1412-1416
self.smartswitch = self.platform_chassis.is_smartswitch()
if self.smartswitch:
    self.module_updater = SmartSwitchModuleUpdater(...)
else:
    self.module_updater = ModuleUpdater(...)
```

---

## カード種別 (card type) による分岐

### MODULE_TYPE_* 定数 (module_base.py:34-37)

| 定数 | 値 | 対象 |
|------|---|------|
| `MODULE_TYPE_SUPERVISOR` | `"SUPERVISOR"` | スーパーバイザカード |
| `MODULE_TYPE_LINE` | `"LINE-CARD"` | ラインカード |
| `MODULE_TYPE_FABRIC` | `"FABRIC-CARD"` | ファブリックカード |
| `MODULE_TYPE_DPU` | `"DPU"` | SmartSwitch の DPU |

### VOQ チャシス: 許容 key prefix (chassisd:193-199)

`ModuleConfigUpdater.module_config_update()` は `SUPERVISOR` / `LINE-CARD` / `FABRIC-CARD` のいずれかで始まるキーのみ処理する。他のキーはエラーログを出力してスキップ。

### SmartSwitch: 許容 key prefix (chassisd:236-239)

`SmartSwitchModuleConfigUpdater.module_config_update()` は `DPU` で始まるキーのみ処理する。`LINE-CARD` / `FABRIC-CARD` / `SUPERVISOR` キーはエラーログを出力してスキップ。

---

## Midplane 監視のプラットフォーム差異

### FABRIC-CARD の除外 (VOQ チャシス, chassisd:549)

`ModuleUpdater.check_midplane_reachability()` はループ内で `MODULE_TYPE_FABRIC` を skip する。FABRIC-CARD は midplane 監視対象外。

### Supervisor/Linecard 観点の差異 (chassisd:552-559)

- Supervisor として動作: 自己 slot を除外し全 LINE-CARD を監視
- LINE-CARD として動作: supervisor slot のみを監視

### SmartSwitch の独立実装

`SmartSwitchModuleUpdater` は `ModuleUpdater` を継承するが、midplane 監視ロジックは DPU 向けに独立実装されており、上記の FABRIC-CARD skip は適用されない。

---

## Chassis App DB クリーンアップの card type 分岐 (chassisd:677-681)

`_check_and_clean_chassis_app_db()` は `LINE-CARD` prefix のモジュールが 30 分以上 down 状態のときのみ `_cleanup_chassis_app_db()` を呼び出す。FABRIC-CARD / SUPERVISOR は対象外。

---

## SmartSwitch 固有機能

### DPU_STATE テーブル監視 (chassisd:1482, 1506-1521)

`SmartSwitchModuleUpdater` は `chassisStateDB` の `DPU_STATE` テーブルを `SubscriberStateTable` で監視し、DPU state 変化を検知して `CHASSIS_MODULE_TABLE` 状態を更新する。VOQ チャシスの `ModuleUpdater` にはこの仕組みはない。

### DPU reboot タイムアウト (chassisd:721-731)

SmartSwitch 専用の `DEFAULT_DPU_REBOOT_TIMEOUT = 360` 秒。`/usr/share/sonic/platform/platform.json` の `"dpu_reboot_timeout"` フィールドで上書き可能。VOQ チャシスは `DEFAULT_LINECARD_REBOOT_TIMEOUT = 180` 秒を使用 (`platform_env.conf` で上書き可)。

### MAX_DPU_REBOOT_DURATION (chassisd:84)

`MAX_DPU_REBOOT_DURATION = 800` 秒はハードコード固定値。DPU の reboot cause を同一 reboot として判定する最大時間窓。

---

## 要約表

| 分岐ポイント | VOQ チャシス | SmartSwitch |
|------------|-------------|------------|
| Updater クラス | `ModuleConfigUpdater` / `ModuleUpdater` | `SmartSwitchModuleConfigUpdater` / `SmartSwitchModuleUpdater` |
| 許容 key prefix | `SUPERVISOR`, `LINE-CARD`, `FABRIC-CARD` | `DPU` のみ |
| midplane 監視 | LINE-CARD + SUPERVISOR 間（FABRIC-CARD 除外） | DPU 独立実装 |
| DB クリーンアップ対象 | `LINE-CARD` のみ（30 分 down 後） | 独立実装（LINE-CARD ロジック非適用） |
| DPU_STATE 連携 | なし | あり（`chassisStateDB.DPU_STATE` 監視） |
| reboot タイムアウト | `linecard_reboot_timeout` 180 秒（`platform_env.conf`） | `dpu_reboot_timeout` 360 秒（`platform.json`）|

---

## 証拠リンク

- `chassisd:193-199` — `ModuleConfigUpdater.module_config_update()` key prefix チェック
- `chassisd:236-239` — `SmartSwitchModuleConfigUpdater.module_config_update()` key prefix チェック
- `chassisd:549` — FABRIC-CARD skip in midplane reachability check
- `chassisd:552-559` — supervisor/linecard 観点での監視対象フィルタ
- `chassisd:677-681` — LINE-CARD 限定の DB クリーンアップ
- `chassisd:721-731` — `dpu_reboot_timeout` 読み込み
- `chassisd:1412-1416` — `is_smartswitch()` によるクラス選択
- `chassisd:1482,1506-1521` — `DPU_STATE` テーブル監視
- `module_base.py:34-37` — MODULE_TYPE_* 定数定義
