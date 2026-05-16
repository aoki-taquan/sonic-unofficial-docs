# STP_MST_INST / STP_MST_PORT — Phase A デフォルト調査メモ

## 調査対象テーブル

- `STP_MST` (key: `GLOBAL`) — MST グローバル設定（タイマー・リージョン）
- `STP_MST_INST` (key: `MST_INSTANCE|<id>`) — MST インスタンスごとの設定
- `STP_MST_PORT` (key: `MST_INSTANCE|<id>|<intf>`) — MST インスタンス per-port 設定

## 主要ソース

- `sonic-utilities/config/stp.py` (SHA: 39732bceb8bdefe706518ab40623bbbba6ff33b9)

---

## 1. MST 定数定義 (config/stp.py:68-110)

```python
MST_DEFAULT_HOPS              = 20     # range: 1–40
MST_DEFAULT_HELLO_TIME        = 2      # range: 1–10
MST_DEFAULT_MAX_AGE           = 20     # range: 6–40
MST_DEFAULT_REVISION          = 0      # range: 0–65535
MST_DEFAULT_BRIDGE_PRIORITY   = 32768  # range: 0–61440, 4096の倍数
MST_DEFAULT_PORT_PRIORITY     = 128    # range: 0–240
MST_DEFAULT_FORWARD_DELAY     = 15     # range: 4–30
MST_DEFAULT_PORT_PATH_COST    = 1      # range: 1–200,000,000
MST_MAX_INSTANCES             = 63
MST_AUTO_LINK_TYPE            = 'auto'
```

---

## 2. STP_MST|GLOBAL テーブル — MST 有効化時の書き込み

`spanning_tree_enable()` (config/stp.py:533-539) でMST 有効化時:

```python
fvs = {'mode': 'mst'}
db.set_entry('STP', "GLOBAL", fvs)
```

`STP_MST|GLOBAL` には **MST 有効化時点では何も書き込まれない**。
タイマー・リージョン名・リビジョン番号は個別 CLI コマンドで初めて書き込まれる。

各フィールドの CLI 書き込みパス:

| フィールド | CLI コマンド | 書き込み関数 | 行番号 |
|---|---|---|---|
| `forward_delay` | `config spanning-tree forward_delay <4-30>` | `stp_global_forward_delay()` | 613–615 |
| `hello_time` | `config spanning-tree hello <1-10>` | `stp_global_hello_interval()` | 642–644 |
| `max_age` | `config spanning-tree max_age <6-40>` | `stp_global_max_age()` | 673–676 |
| `max_hops` | `config spanning-tree max_hops <1-40>` | `stp_global_max_hops()` | 702–705 |
| `name` | `config spanning-tree mst region-name <name>` | `stp_mst_region_name()` | 763–767 |
| `revision` | `config spanning-tree mst revision <0-65535>` | `stp_global_revision()` | 789–793 |

**初期デフォルト**: CLI 設定前は `STP_MST|GLOBAL` にエントリが存在しない（未設定 = デーモン側デフォルト依存）。

---

## 3. STP_MST_INST テーブル — インスタンス 0 の自動作成

`enable_mst_instance0()` (config/stp.py:433-438) が MST 有効化時に呼ばれる:

```python
mst_inst_fvs = {
    'bridge_priority': MST_DEFAULT_BRIDGE_PRIORITY  # = 32768
}
instance_id = 0
db.set_entry('STP_MST_INST', f"MST_INSTANCE:INSTANCE{instance_id}", mst_inst_fvs)
```

注意: キー形式が `MST_INSTANCE:INSTANCE0`（コロン区切り）になっている。
インスタンス優先度変更時 (mst_instance_priority) では `MST_INSTANCE|{instance_id}` (パイプ区切り) を使用 (行1786)。
**コロンとパイプの不一致は既知の潜在的 discrepancy**。

| フィールド | デフォルト値 | 有効範囲 | 備考 |
|---|---|---|---|
| `bridge_priority` | `32768` | 0–61440 (4096 倍数) | MST 有効化時に自動書き込み |
| `vlan_list` | 未設定 | カンマ区切り VLAN ID 文字列 | VLAN マッピング CLI で追加 |

インスタンス 1–62 は `config spanning-tree mst instance <id> priority <value>` で作成される（存在確認後に `mod_entry`）。
インスタンス 0 への VLAN マッピングは禁止（CLI で拒否）。

---

## 4. STP_MST_PORT テーブル — MST 有効化時の一括書き込み

`enable_mst_for_interfaces()` (config/stp.py:441-470):

```python
fvs_mst_port = {
    'path_cost': MST_DEFAULT_PORT_PATH_COST,  # = 1
    'priority': MST_DEFAULT_PORT_PRIORITY      # = 128
}
db.set_entry('STP_MST_PORT', f"MST_INSTANCE|0|{port_key}", fvs_mst_port)
```

書き込み対象: VLAN_MEMBER テーブルに存在するポート (Ethernet + PortChannel)。
VLAN_MEMBER に属していないポートへの書き込みはない。

| フィールド | デフォルト値 | 有効範囲 | 備考 |
|---|---|---|---|
| `path_cost` | `1` | 1–200,000,000 | MST 有効化時にインスタンス 0 の全ポートへ書き込み |
| `priority` | `128` | 0–240 | MST 有効化時にインスタンス 0 の全ポートへ書き込み |

インスタンス別 port 設定は CLI で個別に `mod_entry`:
- `config spanning-tree mst instance <id> interface <intf> priority <0-240>`
  → `db.mod_entry('STP_MST_PORT', "MST_INSTANCE|{id}|{intf}", {'priority': str(priority)})`
- `config spanning-tree mst instance <id> interface <intf> cost <1-200000000>`
  → `db.mod_entry('STP_MST_PORT', "MST_INSTANCE|{id}|{intf}", {'path_cost': str(cost)})`

---

## 5. STP_PORT テーブル (MST モード時)

`enable_mst_for_interfaces()` (config/stp.py:441-470) では `STP_MST_PORT` と同時に `STP_PORT` も書き込まれる:

```python
fvs_port = {
    'edge_port': 'false',
    'link_type': 'auto',      # MST_AUTO_LINK_TYPE
    'enabled': 'true',
    'bpdu_guard': 'false',
    'bpdu_guard_do': 'false',
    'root_guard': 'false',
    'path_cost': 1,            # MST_DEFAULT_PORT_PATH_COST
    'priority': 128            # MST_DEFAULT_PORT_PRIORITY
}
db.set_entry('STP_PORT', port_key, fvs_port)
```

`STP_PORT` は PVST/MST 共通テーブルだが、MST 時のみ `edge_port`/`link_type` が書き込まれる。
PVST では `portfast`/`uplink_fast` が書き込まれ、`edge_port`/`link_type` は存在しない。

---

## 6. MST インスタンス範囲制約

- インスタンス ID: 0–62 (`MST_MAX_INSTANCES = 63`、range は 0 以上 63 未満)
- bridge_priority: 0–61440、4096 の倍数のみ有効
- インスタンス 0 はデフォルトインスタンス (MST 有効化時に自動作成)
- インスタンス 0 への VLAN マッピングは CLI で拒否

---

## 7. discrepancy 候補

1. **キー形式の不一致**: `enable_mst_instance0()` は `MST_INSTANCE:INSTANCE0` (コロン) を使用するが、
   `mst_instance_priority()` / `mst_instance_vlan_add()` は `MST_INSTANCE|{id}` (パイプ) を使用。
   同じテーブルの同じインスタンスを別キー形式で参照している可能性がある。

2. **STP_MST|GLOBAL の暗黙デフォルト**: `STP_MST|GLOBAL` のタイマーフィールドは
   MST 有効化時に書き込まれない。デーモン (stpmgrd) 側のデフォルト動作に依存。

---

## ソース証跡

| ファイル | 行番号 | 内容 |
|---|---|---|
| `config/stp.py` | 68–110 | MST 定数定義 |
| `config/stp.py` | 433–438 | enable_mst_instance0 (STP_MST_INST 書き込み) |
| `config/stp.py` | 441–470 | enable_mst_for_interfaces (STP_MST_PORT + STP_PORT 書き込み) |
| `config/stp.py` | 533–539 | spanning_tree_enable (MST 有効化時の STP|GLOBAL 書き込み) |
| `config/stp.py` | 613–615 | forward_delay → STP_MST|GLOBAL 書き込み |
| `config/stp.py` | 642–644 | hello_time → STP_MST|GLOBAL 書き込み |
| `config/stp.py` | 673–676 | max_age → STP_MST|GLOBAL 書き込み |
| `config/stp.py` | 702–705 | max_hops → STP_MST|GLOBAL 書き込み |
| `config/stp.py` | 763–767 | region name → STP_MST|GLOBAL 書き込み |
| `config/stp.py` | 789–793 | revision → STP_MST|GLOBAL 書き込み |
| `config/stp.py` | 1697–1724 | mst_instance_interface_priority |
| `config/stp.py` | 1734–1765 | mst_instance_interface_cost |
| `config/stp.py` | 1770–1798 | mst_instance_priority |
| `config/stp.py` | 1808–1850 | mst_instance_vlan_add |
| `config/stp.py` | 1859–1892 | mst_instance_vlan_del |
