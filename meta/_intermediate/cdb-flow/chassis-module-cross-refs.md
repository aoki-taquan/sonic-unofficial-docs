# CHASSIS_MODULE 暗黙参照調査 (Phase C)

対象ページ: `docs/reference/config-db/chassis-module.md`
調査日: 2026-05-16
調査ソース: `sonic-platform-daemons` (chassisd), `sonic-utilities` (config/chassis_modules.py, utilities_common/chassis.py), `sonic-buildimage` (sonic-py-common/device_info.py)

---

## 調査方法

1. `chassisd` (`sonic-platform-daemons/sonic-chassisd/scripts/chassisd`) の全 DB アクセスを grep
2. `is_smartswitch()` の実装遡り（`utilities_common/chassis.py` → `sonic_py_common/device_info.py`）
3. `config/chassis_modules.py` の DB 読み書きパターン精査
4. YANG スキーマ (`sonic-chassis-module.yang`) の import / leafref 確認

---

## 1. PORT テーブル（CONFIG_DB）への暗黙参照

### 参照コード

```python
# sonic-platform-daemons/sonic-chassisd/scripts/chassisd:1268-1273
def _get_data_plane_state_common(self):
    port_table = swsscommon.Table(self.app_db, 'PORT_TABLE')

    for port in self.config_db.get_table('PORT'):          # ← CONFIG_DB の PORT テーブルを全件読み取り
        status, oper_status = port_table.hget(port, 'oper_status')
        if not status or oper_status.lower() != 'up':
            return False

    return True
```

### 意味

- `SmartSwitchDpuStateUpdater` が DPU の **データプレーン状態** を判定するとき、`CONFIG_DB` の `PORT` テーブルで定義されているポート名を列挙し、`APPL_DB` の `PORT_TABLE` で各ポートの `oper_status` を確認する。
- つまり **PORT テーブルが存在しない（空）** 場合、全 DPU のデータプレーン状態が即時 `True`（全ポート up とみなす）になり、実態と乖離したデータプレーン状態が報告される可能性がある。
- CHASSIS_MODULE（ADMIN_STATUS）の `down` 操作が DPU に対して行われた後、PORT_TABLE の oper_status が down に変化するかの確認に使用される。

**方向**: `CHASSIS_MODULE` → `PORT` (暗黙参照、CONFIG_DB → APPL_DB のクロス検査)

---

## 2. DEVICE_METADATA テーブル（CONFIG_DB）への暗黙参照

### 参照コード（間接）

```python
# sonic-utilities/utilities_common/chassis.py:21-22
def is_smartswitch():
    return hasattr(device_info, 'is_smartswitch') and device_info.is_smartswitch()

# sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py:671-682
def is_smartswitch():
    platform = get_platform()
    if not platform:
        return False
    platform_data = get_platform_json_data()   # platform.json を読む
    if platform_data:
        return "DPUS" in platform_data         # "DPUS" キーの有無で SmartSwitch 判定
    return False
```

### 意味

- `config/chassis_modules.py` は `is_smartswitch()` の結果で `admin_status` デフォルト fallback を分岐させる（`down` vs `up`）。
- `is_smartswitch()` は **platform.json の "DPUS" キー** を参照するため、`DEVICE_METADATA` テーブルを直接読まない。
- ただし、`DEVICE_METADATA|localhost|switch_type = 'dpu'` / `subtype = 'SmartSwitch'` はシステムが SmartSwitch として初期化される際の CONFIG_DB 側の証跡であり、chassis モジュールの admin_status 挙動はこの設定と **間接的に連動** する。
- `sonic-cfggen` / minigraph.py は `DEVICE_METADATA.localhost.subtype = 'SmartSwitch'` を書き込む時点で SmartSwitch 向け CHASSIS_MODULE 設定を生成する (`config_samples.py:83,210`)。

**方向**: `CHASSIS_MODULE` → `DEVICE_METADATA` (間接参照: platform.json 経由。DEVICE_METADATA の `subtype` / `switch_type` が SmartSwitch 初期化の状態を反映)

---

## 3. SYSTEM_PORT テーブルへの参照なし

`chassisd` / `config/chassis_modules.py` のいずれも `SYSTEM_PORT` テーブルを直接参照しない。

VOQ 構成における `SYSTEM_PORT` は `sonic-swss` の `voqorch.cpp` が管理し、`CHASSIS_MODULE` テーブルとの直接的なコード上の依存は確認されない（間接的には同一チャシス上の VOQ 設定として共存する）。

---

## まとめ

| 参照先テーブル | 方向 | 機構 | 条件 |
|---|---|---|---|
| `PORT` (CONFIG_DB) | CHASSIS_MODULE → PORT | chassisd が `_get_data_plane_state_common()` で CONFIG_DB の PORT 全エントリを列挙。APPL_DB の `PORT_TABLE.oper_status` をクロスチェック | SmartSwitch の DPU 状態判定時のみ (chassisd:1268-1273) |
| `DEVICE_METADATA` (CONFIG_DB) | CHASSIS_MODULE → DEVICE_METADATA | `is_smartswitch()` が platform.json の "DPUS" を検査（直接の DB 参照ではない）。`subtype=SmartSwitch` が CONFIG_DB に書き込まれた環境と間接的に連動 | SmartSwitch 環境のみ |
| `SYSTEM_PORT` (CONFIG_DB) | — | 直接参照なし | — |

PORT テーブルへの参照は YANG leafref ではなく **コードレベルの暗黙参照** であるため、PORT エントリが存在しない場合でも YANG バリデーション違反にならない（chassisd が空テーブルを無条件 True と扱うサイレント挙動）。
