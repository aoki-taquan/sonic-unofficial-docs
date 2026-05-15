# Phase A: VOQ_INBAND_INTERFACE / SYSTEM_PORT — コード由来デフォルト調査

**調査日**: 2026-05-14
**対象ページ**: `docs/reference/config-db/voq-inband-interface.md`

---

## VOQ_INBAND_INTERFACE テーブル

### ソース
- YANG: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-voq-inband-interface.yang`
- 書き込み元: `sonic-buildimage/src/sonic-config-engine/minigraph.py`
- Consumer: `sonic-swss/cfgmgr/intfmgr.cpp`

### VOQ_INBAND_INTERFACE_LIST フィールド別デフォルト

| フィールド | YANG default | コード由来デフォルト | 備考 |
|-----------|-------------|---------------------|------|
| `name` (key) | なし | なし | `pattern "Ethernet-IB[0-9]+"` 必須 |
| `inband_type` | `"port"` (YANG `default "port"`) | なし | YANG 補完のみ。minigraph.py は当フィールドを明示投入しない |

### VOQ_INBAND_INTERFACE_IPPREFIX_LIST フィールド別デフォルト

| フィールド | YANG default | コード由来デフォルト | 備考 |
|-----------|-------------|---------------------|------|
| `name` (key) | なし (leafref) | なし | 親エントリへの leafref 参照 |
| `ip-prefix` (key) | なし | なし | minigraph.py から直接投入 |

### intfmgrd の挙動
`intfmgr.cpp:1195` — `VOQ_INBAND_INTERFACE` の 1-key エントリは `inband_type` フィールドを参照せず、そのまま APP_DB `INTF_TABLE` にリレーする。YANG デフォルト `"port"` は DB 書き込み時点で既に補完されている想定。

---

## SYSTEM_PORT テーブル

### ソース
- YANG: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-port.yang`
- 書き込み元: `sonic-buildimage/src/sonic-config-engine/minigraph.py` (2系統)
  - `parse_chassis_deviceinfo_intf_metadata()` (InterfaceMetadata XML → auto-assign)
  - `parse_spine_chassis_fe()` 経由の SystemPort XML 直接パース (lines 1694-1709)
- Consumer: `sonic-swss/orchagent/main.cpp` `getSystemPortConfigList()`

### SYSTEM_PORT_LIST フィールド別デフォルト

| フィールド | YANG default | YANG 制約 | コード由来デフォルト | 備考 |
|-----------|-------------|-----------|---------------------|------|
| `hostname` (key) | なし | `stypes:hostname` | minigraph `chassis_linecards_info[slot]['hostname']` | VOQ chassis の LC hostname |
| `asic_name` (key) | なし | `stypes:asic_name` | minigraph `"ASIC{asic_id}"` (例: `ASIC0`) | スロット内 ASIC 番号から生成 |
| `ifname` (key) | なし | length 1..128 | minigraph `intf_sonic_name` | chassis intf map から取得 |
| `system_port_id` | なし | なし | minigraph がソート後に `1` 始まりで自動採番 (`system_port_id++`) | テスト config では `"1"` 始まり |
| `switch_id` | なし | uint16 | `get_asic_switch_id(slot_index, asic_name)` で計算 | グローバル ASIC ID |
| `core_index` | なし | uint8 0..7 | XML `CoreId` または VOQ IB IF は `voq_intf_attributes['inb']['core_id']` | |
| `core_port_index` | なし | uint16 | XML `AsicInterfaceIndex` または VOQ IB IF は `voq_intf_attributes['inb']['core_port_index']` | |
| `num_voq` | なし | uint8 1..8 | minigraph の `num_voq` 引数（XML `NumVoq` or chassis-wide パラメタ）| テスト config に `num_voq` フィールドなし → orchagent は設定値必須 |
| `speed` | なし | uint32 1..800000 | intf map の `speed` フィールド（Mbps 整数文字列）。テスト値 `"40000"` | |

### orchagent main.cpp でのフィールドマッピング
```
switch_id        → sai_system_port_config_t.attached_switch_id
core_index       → .attached_core_index
core_port_index  → .attached_core_port_index
speed            → .speed
system_port_id   → .port_id
num_voq          → .num_voq
```
全フィールドが必須扱い（デフォルト補完なし）。欠損時は `stoi()` 例外が発生する。

---

## hard=0 制約チェック

- VOQ_INBAND_INTERFACE の `inband_type` デフォルト `"port"` は YANG による宣言的デフォルト（コードハードコードではない）→ hard=0 適合
- SYSTEM_PORT の全フィールドはデフォルトなし、minigraph XML から全量投入 → hard=0 適合（ハードコードデフォルト記載対象なし）
- `system_port_id` 採番ロジック (`system_port_id = 1` 初期値) はコード由来だが「デフォルト値」ではなく「採番アルゴリズム」なのでデフォルト扱い外

---

## <!-- defaults --> ブロック草案

```markdown
<!-- defaults -->
## フィールドデフォルト一覧

### VOQ_INBAND_INTERFACE_LIST

| フィールド | デフォルト | 由来 |
|-----------|-----------|------|
| `inband_type` | `"port"` | YANG `default "port"` ([sonic-voq-inband-interface.yang](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-voq-inband-interface.yang)) |

### SYSTEM_PORT_LIST

SYSTEM_PORT の全フィールドはデフォルトなし。minigraph.py が minigraph XML / InterfaceMetadata から全量生成して CONFIG_DB に投入する。`system_port_id` は投入時にソート順で `1` から自動採番される (`minigraph.py` `parse_chassis_deviceinfo_intf_metadata()`)。

<!-- /defaults -->
```
