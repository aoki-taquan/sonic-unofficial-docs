# STP / STP_VLAN / STP_INTF (STP_PORT) — Phase A デフォルト調査メモ

## 調査対象テーブル

- `STP` (key: `GLOBAL`) — グローバル STP 設定
- `STP_VLAN` (key: `Vlan<vid>`) — VLAN ごとの STP 設定
- `STP_PORT` (key: `<intf_name>`) — インタフェースごとの STP 設定
- `STP_VLAN_PORT` (key: `Vlan<vid>|<intf>`) — VLAN + インタフェースの per-VLAN ポート設定

## 主要ソース

- `sonic-utilities/config/stp.py` (SHA: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
- `sonic-swss/cfgmgr/stpmgr.cpp` + `stpmgr.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 1. STP|GLOBAL テーブルのフィールドとデフォルト

`spanning_tree_enable()` (config/stp.py:520-528) で PVST 有効化時に以下が書き込まれる:

```python
fvs = {
    'mode': 'pvst',
    'rootguard_timeout': STP_DEFAULT_ROOT_GUARD_TIMEOUT,  # = 30
    'forward_delay': STP_DEFAULT_FORWARD_DELAY,           # = 15
    'hello_time': STP_DEFAULT_HELLO_INTERVAL,             # = 2
    'max_age': STP_DEFAULT_MAX_AGE,                       # = 20
    'priority': STP_DEFAULT_BRIDGE_PRIORITY               # = 32768
}
```

定数定義 (config/stp.py:116-134):
```python
STP_DEFAULT_ROOT_GUARD_TIMEOUT = 30   # range: 5-600
STP_DEFAULT_FORWARD_DELAY = 15        # range: 4-30
STP_DEFAULT_HELLO_INTERVAL = 2        # range: 1-10
STP_DEFAULT_MAX_AGE = 20              # range: 6-40
STP_DEFAULT_BRIDGE_PRIORITY = 32768   # range: 0-61440, 4096の倍数
```

MST 有効化時 (`mode == "mst"`) は `mode` のみ書き込まれ、タイマー類は `STP_MST` テーブルに保存される。

---

## 2. STP_VLAN テーブルのフィールドとデフォルト

`enable_stp_for_vlans()` (config/stp.py:251-266) / `vlan_enable_stp()` (config/stp.py:278-289) で書き込まれる:

```python
fvs = {
    'enabled': 'true',
    'forward_delay': get_global_stp_forward_delay(db),  # STP|GLOBAL の値を継承
    'hello_time': get_global_stp_hello_time(db),         # STP|GLOBAL の値を継承
    'max_age': get_global_stp_max_age(db),               # STP|GLOBAL の値を継承
    'priority': get_global_stp_priority(db)              # STP|GLOBAL の値を継承
}
```

**デフォルト値 (PVST グローバルデフォルトから継承)**:

| フィールド | デフォルト | 説明 |
|---|---|---|
| `enabled` | `"true"` | STP 有効/無効 |
| `forward_delay` | `15` | フォワード遅延 (秒) |
| `hello_time` | `2` | Hello 間隔 (秒) |
| `max_age` | `20` | 最大エージ (秒) |
| `priority` | `32768` | ブリッジプライオリティ |

PVST 有効化時に全 VLAN に自動適用される (最大 `PVST_MAX_INSTANCES=255` VLAN まで)。
VLAN のパラメータはグローバル変更時に `update_stp_vlan_parameter()` で同期される (グローバルと同値の場合のみ)。

---

## 3. STP_PORT テーブルのフィールドとデフォルト

`enable_stp_for_interfaces()` (config/stp.py:361-379) / `interface_enable_stp()` (config/stp.py:292-301) で書き込まれる:

**PVST モード時**:
```python
fvs = {
    'enabled': 'true',
    'root_guard': 'false',
    'bpdu_guard': 'false',
    'bpdu_guard_do_disable': 'false',
    'portfast': 'false',
    'uplink_fast': 'false'
}
```

**MST モード時** (`enable_mst_for_interfaces()`, config/stp.py:441-470):
```python
fvs_port = {
    'edge_port': 'false',
    'link_type': 'auto',
    'enabled': 'true',
    'bpdu_guard': 'false',
    'bpdu_guard_do': 'false',
    'root_guard': 'false',
    'path_cost': 1,      # MST_DEFAULT_PORT_PATH_COST
    'priority': 128      # MST_DEFAULT_PORT_PRIORITY
}
```

**フィールドまとめ**:

| フィールド | PVST デフォルト | MST デフォルト | 備考 |
|---|---|---|---|
| `enabled` | `"true"` | `"true"` | |
| `root_guard` | `"false"` | `"false"` | |
| `bpdu_guard` | `"false"` | `"false"` | |
| `bpdu_guard_do_disable` | `"false"` | `"false"` | MST では `bpdu_guard_do` |
| `portfast` | `"false"` | — (MST 非対応) | PVST のみ |
| `uplink_fast` | `"false"` | — (MST 非対応) | PVST のみ |
| `edge_port` | — (PVST 非対応) | `"false"` | MST のみ |
| `link_type` | — (PVST 非対応) | `"auto"` | MST のみ |
| `path_cost` | 未設定 | `1` | |
| `priority` | 未設定 | `128` | |

注: `path_cost` は PVST 時には STP_PORT 初期書き込み時には含まれず、後から `stp_interface_path_cost()` で設定可能 (range: 1-200000000)。

---

## 4. STP_VLAN_PORT テーブルのフィールドとデフォルト

`STP_VLAN_PORT` テーブルは `path_cost` と `priority` を per-VLAN per-port で管理する。

`doStpVlanPortTask()` (stpmgr.cpp) では:
- `path_cost` → `msg.path_cost`
- `priority` → `msg.priority` (デフォルト -1 = 未設定)

CLIによる設定:
- `stp_vlan_interface_priority()` (config/stp.py:1290-1301): `STP_VLAN_PORT|<Vlan>|<intf>` に `priority` 書き込み (range: 0-240)
- `stp_vlan_interface_cost()` (config/stp.py:1310-1321): `STP_VLAN_PORT|<Vlan>|<intf>` に `path_cost` 書き込み

初期値は書き込まれず、CLI 設定時のみ存在する。

---

## 5. タイマー整合性制約

STP タイマーは `2*(forward_delay-1) >= max_age >= 2*(hello_time+1)` の制約を満たす必要がある (config/stp.py:183-187)。

デフォルト値での検証: `2*(15-1)=28 >= 20 >= 2*(2+1)=6` → 満足

---

## 6. stpmgr の動作 (フィールド処理)

`processStpPortAttr()` (stpmgr.cpp:515-628):
- `enabled`, `root_guard`, `bpdu_guard`, `bpdu_guard_do_disable`: boolean → uint8_t
- `path_cost`, `priority`: int → msg フィールド
- `portfast`, `uplink_fast`: PVST (`L2_PVSTP`) 時のみ処理
- `edge_port`, `link_type`: MSTP (`L2_MSTP`) 時のみ処理
- 未知フィールドはサイレントに無視

`processStpVlanPortAttr()` (stpmgr.cpp:408-442):
- `path_cost`: int パース
- `priority`: int パース (SET 時のデフォルト -1 = 未設定)

---

## 7. 暗黙制約・注意点

1. **PVST 最大 VLAN 数**: `PVST_MAX_INSTANCES = 255` (stpmgr.h:38 で `STP_DEFAULT_MAX_INSTANCES = 255`)
2. **STP_PORT の path_cost**: PVST 時は書き込み時に含まれない (明示設定が必要)
3. **link_type 値**: stpmgr.h で `AUTO=0, POINT_TO_POINT=1, SHARED=2` の enum だが config/stp.py では文字列 `"auto"`, `"point-to-point"`, `"shared"` で書き込み
4. **STP グローバル有効化前に書かれたエントリ**: `stpGlobalTask==false` 中はスキップ (it++) — silent defer
5. **bpdu_guard_do_disable vs bpdu_guard_do**: PVST は `bpdu_guard_do_disable`、MST は `bpdu_guard_do` — フィールド名が異なる (潜在的な discrepancy)

---

## ソース証跡

| ファイル | 行番号 | 内容 |
|---|---|---|
| `config/stp.py` | 116-134 | STP 定数定義 |
| `config/stp.py` | 520-528 | PVST enable 時の STP|GLOBAL 書き込み |
| `config/stp.py` | 251-266 | enable_stp_for_vlans |
| `config/stp.py` | 292-301 | interface_enable_stp |
| `config/stp.py` | 361-379 | enable_stp_for_interfaces |
| `config/stp.py` | 441-470 | enable_mst_for_interfaces |
| `stpmgr.h` | 36-38 | MAX_VLANS, STP_DEFAULT_MAX_INSTANCES |
| `stpmgr.cpp` | 515-628 | processStpPortAttr |
| `stpmgr.cpp` | 408-442 | processStpVlanPortAttr |
