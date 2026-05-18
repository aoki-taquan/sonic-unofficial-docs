# MGMT_PORT — プラットフォーム差調査

Task F Phase H: `MGMT_PORT` テーブル適用時のプラットフォーム/構成差を `sonic-buildimage` および `sonic-host-services` から精読した結果。

## 結論

**ASIC 種別・multi-asic・VOQ chassis・SmartSwitch DPU による処理差はほぼなし**。ただし `speed` フィールドの有無は **HwSku 依存**（platform 依存）であり、`<ManagementInterface><Speed>` が定義されていない HwSku では `speed` フィールドが CONFIG_DB に投入されない。

## 根拠

### 1. SAI 非経由 — ASIC 種別の影響なし

`MGMT_PORT` は SAI を一切経由しない。eth0 (OOB 管理ポート) は Linux カーネルの netdev であり、ASIC ハードウェアとは独立している。`portmgrd` (`sonic-swss/cfgmgr/portmgrd.cpp`) は `CFG_PORT_TABLE_NAME`（= `"PORT"`、データポート）のみを購読し `MGMT_PORT` テーブルは処理しない（`portmgrd.cpp:28`）。よって Broadcom / Mellanox / Marvell / Innovium 等の ASIC 差は無関係。

### 2. speed フィールドは HwSku 依存（プラットフォーム差あり）

`minigraph.py:parse_deviceinfo()` (L1675-1711) が `<DeviceInfo><HwSku>` ブロックを解析し、`<ManagementInterfaces><ManagementInterface><Speed>` から速度値を `port_speeds_default[alias]` に格納する。

```python
# minigraph.py:2295-2296
if alias in port_speeds_default:
    results['MGMT_PORT'][name]['speed'] = port_speeds_default[alias]
```

`ManagementInterface` の `Speed` 要素が存在しない HwSku では `alias` が `port_speeds_default` に含まれないため、`speed` フィールドが `MGMT_PORT` エントリに挿入されない（完全省略）。

- chassis テスト (`test_chassis_cfggen.py:111-116`) では `{'eth0': {'alias': 'Management1/1', 'admin_status': 'up'}}` — `speed` なし。これは当該 HwSku の minigraph XML に `ManagementInterface/Speed` が未定義であることを示す。
- 通常の T0/T1 プラットフォームでは `1000`（1 Gbps）が一般的だが HwSku ファイル依存。

### 3. multi-asic — MGMT_PORT は host-scoped

`MGMT_PORT` は host 側の CONFIG_DB (namespace = "") に保存される。multi-asic 構成でも `asic0..N` の namespace に `MGMT_PORT` は存在しない。`mgmt_oper_status.py` は host CONFIG_DB の `MGMT_PORT|*` のみを参照し、asic namespace を iterate しない（`mgmt_oper_status.py:16-22`）。

### 4. VOQ chassis — 特別処理なし

`sonic-host-services/scripts/hostcfgd` は MGMT_PORT を直接購読しない（L600 の `MGMT_INTERFACE` のみを読む）。VOQ chassis での supervisor / line card 間の差異もない — 各ノードで独立した eth0 を持ち、各 host の CONFIG_DB に MGMT_PORT エントリが置かれる。chassis 構成でも `admin_status="up"` の固定注入は変わらない（`minigraph.py:2294`）。

### 5. SmartSwitch DPU — eth0 設定が抑制される可能性

`interfaces.j2` L144-158: `MGMT_INTERFACE` が存在しない場合に DHCP フォールバック生成を抑制する SmartSwitch DPU 条件分岐が存在するが、これは `MGMT_INTERFACE` テーブルの処理であり `MGMT_PORT` テーブル自体の処理には影響しない。SmartSwitch DPU でも `MGMT_PORT` エントリは通常通り CONFIG_DB に投入される（minigraph 由来）。

### 6. lldpd / SNMP — alias フィールドのみ参照

`lldpd.conf.j2:17-18` と `sonic-snmpagent/mibs/__init__.py:270` はプラットフォーム分岐なし。`alias` フィールドの有無だけに依存し、未設定時はフォールバック（SNMP は `if_name`、LLDP は `port_name`）を使用する。

## まとめ

| 観点 | 結果 | 根拠 |
|---|---|---|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | 影響なし | SAI 非経由。eth0 は Linux netdev |
| `speed` フィールドの存在 | **HwSku 依存** | minigraph.py が `ManagementInterface/Speed` 要素の有無で条件的に挿入 |
| multi-asic | 影響なし | MGMT_PORT は host CONFIG_DB のみ。asic namespace に存在しない |
| VOQ chassis (supervisor / line card) | 影響なし | 各 host に独立した eth0。chassis 集中管理機構なし |
| SmartSwitch DPU | MGMT_PORT エントリ自体は通常通り | DHCP 抑制は MGMT_INTERFACE の話 |
