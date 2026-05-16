# BREAKOUT_CFG — プラットフォーム差調査

Task F Phase H: `BREAKOUT_CFG` テーブルのプラットフォーム/ASIC/構成差を `sonic-utilities/config/main.py`、`sonic-swss/orchagent/portsorch.cpp`、`sonic-buildimage/src/sonic-config-engine/portconfig.py`、および `device/` 配下の `platform.json`/`hwsku.json`/`port_config.ini` から精読した結果。

## 結論

**プラットフォーム差あり (重大)**。DPB (Dynamic Port Breakout) は `platform.json` の有無と内容に強く依存する。主要な差異は次の 4 点:

1. **`platform.json` 未搭載プラットフォームでは DPB が無効** — CLI が即 Abort する
2. **ASIC ごとに利用可能な breakout モードが異なる** — `platform.json` の `breakout_modes` キーで定義
3. **lane 割当数がプラットフォームで異なる** — 4-lane / 8-lane 構成で使用可能モードが変わる
4. **multi-ASIC 構成では `asic_id` を介したパス解決** — `get_path_to_port_config_file(hwsku, asic_id)` で各 ASIC の設定ファイルを分離参照

---

## 1. `platform.json` 有無によるプラットフォーム分岐

### 1-A. `platform.json` 搭載プラットフォーム（DPB 有効）

`device_info.get_path_to_port_config_file()` が `.json` 拡張子のファイルを返す場合に DPB が利用可能:

```python
# sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py L491-497
if os.path.isfile(hwsku_json_file):
    if os.path.isfile(os.path.join(platform_path, PLATFORM_JSON_FILE)):
        json_file = os.path.join(platform_path, PLATFORM_JSON_FILE)
        platform_data = json.loads(open(json_file).read())
        interfaces = platform_data.get('interfaces', None)
        if interfaces is not None and len(interfaces) > 0:
            port_config_candidates.append(os.path.join(platform_path, PLATFORM_JSON_FILE))
```

条件:
- `hwsku.json` が `hwsku_path` に存在すること
- `platform.json` が `platform_path` に存在し、`interfaces` キーが空でないこと

### 1-B. `port_config.ini` のみのプラットフォーム（DPB 無効）

`platform.json` が存在しない、または `interfaces` が空の場合、`port_config_candidates` に `.ini` ファイルのみが入る。`config interface breakout` 実行時に:

```python
# sonic-utilities/config/main.py L5469-5471
if not os.path.isfile(breakout_cfg_file) or not breakout_cfg_file.endswith('.json'):
    click.secho("[ERROR] Breakout feature is not available without platform.json file", fg='red')
    raise click.Abort()
```

→ **即 Abort**。BREAKOUT_CFG テーブルは初期化されないため存在しない。

`get_breakout_mode()` も `port_config.ini` 環境では `None` を返す:

```python
# sonic-buildimage/src/sonic-config-engine/portconfig.py L464-465
else:
    return None  # .ini 使用時は BREAKOUT_CFG 非生成
```

**影響プラットフォーム例**: Arista 7260CX3 系 (Arista-7260CX3-64 など) は HWSKU 配下に `port_config.ini` のみを持ち、platform-level `platform.json` が未搭載の場合は DPB 不可。

---

## 2. ASIC/プラットフォームごとの breakout モード差異

`platform.json` の `interfaces.<port>.breakout_modes` がプラットフォームごとに異なる。代表例:

### 2-A. 8-lane 構成 (400G ポート、例: Celestica Silverstone)

```json
"Ethernet0": {
  "lanes": "33,34,35,36,37,38,39,40",
  "breakout_modes": {
    "1x400G": ["Eth1/1"],
    "2x200G": ["Eth1/1", "Eth1/5"],
    "2x100G": ["Eth1/1", "Eth1/5"],
    "4x100G": ["Eth1/1", "Eth1/3", "Eth1/5", "Eth1/7"],
    "4x25G(4)": ["Eth1/1", "Eth1/2", "Eth1/3", "Eth1/4"],
    "4x10G(4)": ["Eth1/1", "Eth1/2", "Eth1/3", "Eth1/4"]
  }
}
```

8-lane ポートは最大 `4x100G` や `8x` 構成が可能。lane 割当数が `(N)` 表記で指定される（例: `4x25G(4)` は 4 lane/port）。

### 2-B. 4-lane 構成 (100G ポート、例: Arista 7050CX3-32S)

```json
"Ethernet0": {
  "lanes": "65,66,67,68",
  "breakout_modes": {
    "1x100G[50G,40G,25G,10G]": ["Ethernet1/1"],
    "2x50G[40G,25G,10G]": ["Ethernet1/1", "Ethernet1/3"],
    "4x25G[10G]": ["Ethernet1/1", "Ethernet1/2", "Ethernet1/3", "Ethernet1/4"]
  }
}
```

4-lane ポートでは最大 `4x` 分割。`1x400G` や `8x` は不可。

### 2-C. Arista 風 `[fallback_speed]` 構文

Arista プラットフォームは `1x100G[50G,40G,25G,10G]` のように `[代替速度リスト]` をモード文字列内に埋め込む。これは `BreakoutCfg._re_group_to_entry()` の `supported_speed` グループに対応:

```python
# portconfig.py L329-334
groups_list = [re.match(BRKOUT_PATTERN, i).groups() for i in bmode.split("+")]
# BRKOUT_PATTERN は '(\d+)x(\d+[MGT])\[([^\]]+)\]' 等
```

Celestica / Accton 等は括弧 `(N)` 形式の lane 指定が主流。

### 2-D. ベンダー別 breakout_modes 一覧（代表値）

| ベンダー | lane 構成 | 代表 breakout モード |
|---------|---------|---------------------|
| Arista | 4-lane | `1x100G[50G,40G,25G,10G]`, `2x50G[40G,25G,10G]`, `4x25G[10G]` |
| Arista | 8-lane | `1x400G[200G,100G,50G,40G,25G,10G]`, `2x200G[100G]`, `4x100G[50G,40G,25G,10G]` |
| Celestica | 8-lane | `1x400G`, `2x200G`, `2x100G`, `4x100G`, `4x25G(4)`, `4x10G(4)` |
| Accton/Edge-core | 4-lane | `1x100G[40G]`, `2x50G`, `4x25G[10G]` |
| Mellanox/Nvidia | 4-lane | `1x100G[50G,40G,25G,10G,1G]`, `2x50G[40G,25G,10G]`, `4x25G[10G]` |
| Nokia | 4-lane + 8-lane | `1x100G`, `4x25G(4)`, `1x400G`, `4x100G(4)` |
| Marvell | 4-lane | `1x100G`, `1x400G`, `1x800G[400G,200G]` |

---

## 3. lane 割当と PORT テーブル派生の差異

`BreakoutCfg.get_config()` が platform.json の `lanes` フィールドを分割してチャイルドポートの PORT エントリを生成する際、以下がプラットフォーム依存となる:

### 3-A. `lanes_per_port` の計算

```python
# portconfig.py L367-372
lanes_per_port = entry.num_assigned_lanes // entry.num_ports
for port in range(entry.num_ports):
    interface_name = PORT_STR + str(self._interface_base_id + lane_id)
    lanes = self._lanes[lane_id:lane_id + lanes_per_port]
    port_config = {
        'lanes': ','.join(lanes),
        ...
    }
```

- 4-lane 構成で `4x25G` → 各チャイルドが 1 lane
- 8-lane 構成で `4x100G` → 各チャイルドが 2 lane
- 8-lane 構成で `4x25G(4)` → 各チャイルドが 1 lane (8 lane 中の前半 4 lane のみ使用)

### 3-B. FEC 自動付与のプラットフォーム依存

```python
# portconfig.py L387-388
if entry.default_speed // lanes_per_port >= 50000:
    port_config['fec'] = 'rs'
```

| プラットフォーム | breakout モード | lanes_per_port | default_speed | FEC 付与 |
|---|---|---|---|---|
| 4-lane Arista | `4x25G[10G]` | 1 | 25000 | **なし** (25G/1 lane = 25000 < 50000) |
| 4-lane Arista | `2x50G[40G]` | 2 | 50000 | **なし** (50000/2 lane = 25000 < 50000) |
| 4-lane Arista | `1x100G[50G]` | 4 | 100000 | **なし** (100000/4 lane = 25000 < 50000) |
| 8-lane Celestica | `4x100G` | 2 | 100000 | **あり** (100000/2 lane = 50000 >= 50000) |
| 8-lane Arista | `2x200G[100G]` | 4 | 200000 | **あり** (200000/4 lane = 50000 >= 50000) |

FEC 付与の境界は **50G/lane**。同じ `4x25G` でも lane 割当が異なると結果が変わる。

---

## 4. multi-ASIC 構成での差異

### 4-A. `asic_id` によるパス分岐

```python
# portconfig.py L187-193
if asic_name is not None:
    asic_id = str(get_asic_id_from_name(asic_name))
else:
    asic_id = None
port_config_file = device_info.get_path_to_port_config_file(hwsku, asic_id)
```

```python
# device_info.py L499-501
if asic:
    port_config_candidates.append(os.path.join(hwsku_path, asic, PORT_CONFIG_FILE))
else:
    port_config_candidates.append(os.path.join(hwsku_path, PORT_CONFIG_FILE))
```

multi-ASIC プラットフォームでは HWSKU ディレクトリ内の `asic0/`、`asic1/` サブディレクトリに各 ASIC 固有の `port_config.ini` が配置される。各 ASIC が独立した port 空間を持つ。

### 4-B. `config interface breakout` での multi-ASIC 対応状況

`config/main.py` の `breakout()` 関数は `get_path_to_port_config_file()` を **引数なし** で呼び出す:

```python
# config/main.py L5467
breakout_cfg_file = device_info.get_path_to_port_config_file()
```

`asic` 引数が渡されないため、multi-ASIC 構成での DPB は **host namespace の port 設定のみを参照** する。各 ASIC namespace 個別の DPB は現状の CLI では非対応。

### 4-C. portsorch.cpp での ASIC 固有処理

`portsorch.cpp` が実際の SAI 操作を行う際、`m_portListLaneMap`（ASIC が認識する lane → port_id マップ）を基準にバリデーションする:

```cpp
// portsorch.cpp L4026-4032
if (m_portListLaneMap.find(lane_set) == m_portListLaneMap.end())
{
    SWSS_LOG_ERROR("Failed to locate port lane combination alias:%s", alias.c_str());
    return false;
}
sai_object_id_t id = m_portListLaneMap[lane_set];
```

platform.json で定義された `lanes` が ASIC の物理 lane マップと一致しない場合、ここで失敗する。ASIC 固有の lane 番号体系はベンダー SAI 実装に依存し、`platform.json` の記述と整合している必要がある。

---

## 5. Mellanox/Nvidia 固有分岐

`portsorch.cpp` に `isMlnxPlatform()` が存在するが、これは breakout 処理ではなく **Flex Counter / Trim Stat** 計算に限定されている:

```cpp
// portsorch.cpp L858-863
if (isMlnxPlatform() &&
    isPortStatSupported(SAI_PORT_STAT_TRIM_PACKETS) &&
    isPortStatSupported(SAI_PORT_STAT_TX_TRIM_PACKETS) &&
    !isPortStatSupported(SAI_PORT_STAT_DROPPED_TRIM_PACKETS))
{
    portStatPlugins += "," + nvdaPortTrimSha;
}
```

**DPB 処理パス内に Mellanox 固有分岐はなし**。lane マップや SAI の port create/remove API 呼び出しにベンダー条件分岐なし。ただし Mellanox ASIC は `platform.json` の breakout_modes 定義が Arista/Celestica とは異なる（`1x100G[50G,40G,25G,10G,1G]` のように 1G fallback を含む）。

---

## ソース証跡

| ファイル | 行 | 内容 |
|---------|-----|------|
| `sonic-utilities/config/main.py` | L5467-5471 | `platform.json` 必須チェック・Abort |
| `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py` | L445-509 | `get_path_to_port_config_file()` パス解決ロジック |
| `sonic-buildimage/src/sonic-py-common/sonic_py_common/device_info.py` | L491-497 | `hwsku.json` + `platform.json` 存在確認と `interfaces` 空チェック |
| `sonic-buildimage/src/sonic-config-engine/portconfig.py` | L186-208 | `get_port_config()` での `platform.json` vs `port_config.ini` 分岐 |
| `sonic-buildimage/src/sonic-config-engine/portconfig.py` | L312-395 | `BreakoutCfg.get_config()` — lane 割当・FEC 自動付与 |
| `sonic-buildimage/src/sonic-config-engine/portconfig.py` | L387-388 | FEC 自動付与の 50G/lane 閾値 |
| `sonic-buildimage/src/sonic-config-engine/portconfig.py` | L461-465 | `get_breakout_mode()` — `port_config.ini` 時 `None` 返却 |
| `sonic-swss/orchagent/portsorch.cpp` | L4026-4032 | lane_set の ASIC バリデーション |
| `sonic-swss/orchagent/portsorch.cpp` | L858-863 | `isMlnxPlatform()` の限定的使用 |
| `device/celestica/x86_64-cel_silverstone-r0/platform.json` | — | 8-lane 400G ポートの breakout_modes 定義例 |
| `device/arista/x86_64-arista_7050cx3_32s/Arista-7050CX3-32S/hwsku.json` | — | `default_brkout_mode` 定義例 |
