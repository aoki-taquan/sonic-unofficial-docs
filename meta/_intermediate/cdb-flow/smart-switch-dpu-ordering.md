# SmartSwitch DPU テーブル群 — Phase B 書込み順依存スキャンノート

対象テーブル: `MID_PLANE_BRIDGE` / `DPUS` / `DPU` / `REMOTE_DPU` / `VDPU` / `DASH_HA_GLOBAL_CONFIG`
Consumer: `dhcp_cfggen` (`dhcpservd`) / `dashhaorch` (orchagent)
スキャン範囲: `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py` 全行精読 + `dhcp_db_monitor.py:349-386`

---

## 検出した順序依存・タイミング依存

### 1. DEVICE_METADATA.subtype が先行必須 — SmartSwitch モード分岐

`dhcp_cfggen.generate()` (dhcp_cfggen.py:67) は最初に `is_smart_switch(device_metadata)` を呼ぶ:

```python
# dhcp_cfggen.py:67
smart_switch = is_smart_switch(device_metadata)
# dhcp_cfggen.py:76
mid_plane, dpus = self._parse_dpu(dpus_table, mid_plane_table) if smart_switch else ({}, {})
```

`is_smart_switch()` は `DEVICE_METADATA|localhost.subtype == "SmartSwitch"` を返す (utils.py:161)。

**順序依存**: `DEVICE_METADATA|localhost.subtype = "SmartSwitch"` が CONFIG_DB に存在しないまま
`MID_PLANE_BRIDGE` や `DPUS` を書いても、`dhcp_cfggen` はこれらを完全に無視する（`{}` で代替）。
`DEVICE_METADATA` 書込みを先に完了させること。

Evidence: `dhcp_cfggen.py:65-76`, `utils.py:153-161`

### 2. MID_PLANE_BRIDGE|GLOBAL が先行必須 — ブリッジ名・IP プレフィックスの存在チェック

`dhcp_cfggen.generate()` (dhcp_cfggen.py:84) は `MID_PLANE_BRIDGE|GLOBAL` の `bridge` および `ip_prefix`
フィールドの存在を明示的にチェックする:

```python
# dhcp_cfggen.py:84-90
if smart_switch and "bridge" in mid_plane and "ip_prefix" in mid_plane:
    mid_plane_name = mid_plane["bridge"]
    dhcp_interfaces[mid_plane_name] = [{
        "network": ipaddress.ip_network(mid_plane["ip_prefix"], strict=False),
        "ip": mid_plane["ip_prefix"]
    }]
    dpus = ["{}|{}".format(mid_plane_name, dpu) for dpu in dpus]
```

どちらか一方でも欠如すると `dhcp_interfaces` にミッドプレーンブリッジが登録されず、
DPUS エントリの処理もスキップされる。

**順序依存**: `DPUS` 書込みの前に `MID_PLANE_BRIDGE|GLOBAL` (`bridge` + `ip_prefix` 両フィールド) を
先に書き込むこと。ただし `config_samples.py` がこの順序を自動保証している（#3 参照）。

Evidence: `dhcp_cfggen.py:84-91`

### 3. config_samples.py が書込み順序を自動保証 — ビルド時生成の順序

`generate_t1_smartswitch_switch_sample_config()` (config_samples.py:81-151) は以下の順序で
CONFIG_DB に書き込む:

```
1. DEVICE_METADATA.subtype = "SmartSwitch"
2. MID_PLANE_BRIDGE|GLOBAL  (bridge + ip_prefix)
3. DPUS|<dpu_name>          (midplane_interface)
4. FEATURE|dhcp_server + FEATURE|dhcp_relay
5. DHCP_SERVER_IPV4|bridge-midplane
6. DHCP_SERVER_IPV4_PORT|bridge-midplane|<dpu>
```

この順序は DPU 追加数に関わらず維持される (`natsorted` による自然ソート順)。
手動で CONFIG_DB を操作する場合は同じ順序を守ること。

Evidence: `config_samples.py:81-151`

### 4. DASH_HA_GLOBAL_CONFIG — 独立。DPU テーブルとの依存なし

`dashhaorch` (orchagent) は `DASH_HA_GLOBAL_CONFIG` を独立して購読する。
`DPU` / `DPUS` / `MID_PLANE_BRIDGE` との書込み順序依存は検出されなかった。
`VNET` テーブルへの leafref (`dpu_vnet` フィールド) があるため、`VNET` エントリが先行している必要がある。

**順序依存**: `DASH_HA_GLOBAL_CONFIG|global.dpu_vnet` を書く前に対応 `VNET|<vnet_name>` を作成すること。

### 5. MidPlaneTableEventChecker — ランタイム変更の反映タイミング

`dhcp_db_monitor.py:349-368` の `MidPlaneTableEventChecker` は `MID_PLANE_BRIDGE` テーブルの変化を監視し、
`bridge` フィールドが `enabled_dhcp_interfaces` に含まれる場合のみ再生成をトリガーする。

- `dhcpservd` は変更検知 → `dhcp_cfggen.generate()` 全量再生成 → kea-dhcp4 SIGHUP の流れ。
- `DpusTableEventChecker` (dhcp_db_monitor.py:371-385) は `DPUS` の全変更を無条件にトリガーする。
- ランタイムで `DPUS` エントリを追加・削除した場合、次回 dhcpservd ポーリング（最大 5000 ms）後に自動反映される。

Evidence: `dhcp_db_monitor.py:349-386`, `dhcp_cfggen.py:97-99`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DEVICE_METADATA\|localhost.subtype = "SmartSwitch"` → `MID_PLANE_BRIDGE` / `DPUS` | **先行必須**（欠如時 dhcp_cfggen がテーブルを無視） | `config_samples.py` がビルド時に自動保証 |
| 2 | `MID_PLANE_BRIDGE\|GLOBAL` (`bridge` + `ip_prefix`) → `DPUS` | **先行必須**（欠如時 DPUS スキップ） | `config_samples.py` がビルド時に自動保証 |
| 3 | `VNET\|<vnet_name>` → `DASH_HA_GLOBAL_CONFIG\|global.dpu_vnet` | **先行必須**（YANG leafref 制約） | CLI が leafref を事前チェック |
| 4 | `DPU` / `REMOTE_DPU` / `VDPU` — 相互間の順序依存 | **なし**（独立エントリ、相互参照なし） | — |
| 5 | ランタイム `DPUS` 変更 → dhcpservd 反映 | 自動（最大 5000 ms ポーリング後） | `DpusTableEventChecker` が無条件トリガー |
