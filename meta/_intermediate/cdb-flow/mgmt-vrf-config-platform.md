# MGMT_VRF_CONFIG — Phase H: プラットフォーム差調査

Task F Phase H: `MGMT_VRF_CONFIG` テーブル適用時のプラットフォーム / 構成差を `sonic-swss` (`vrfmgr.cpp`)、`sonic-host-services` (`hostcfgd`)、`sonic-buildimage` (`interfaces.j2`、`supervisord.conf.j2`) から精読した結果。

## 調査対象ソース

- `sonic-net/sonic-swss` — `cfgmgr/vrfmgr.cpp`
- `sonic-net/sonic-host-services` — `scripts/hostcfgd`
- `sonic-net/sonic-buildimage` — `files/image_config/interfaces/interfaces.j2`
- `sonic-net/sonic-buildimage` — `dockers/docker-orchagent/supervisord.conf.j2`

---

## 差異 1: SmartSwitch DPU — eth0 DHCP 設定がスキップされる

`interfaces.j2` L143–158

```jinja
{% if (DEVICE_METADATA is not defined)
      or (DEVICE_METADATA['localhost']['subtype'] is not defined)
      or (DEVICE_METADATA['localhost']['switch_type'] is not defined)
      or not (DEVICE_METADATA['localhost']['subtype'] == 'SmartSwitch'
              and DEVICE_METADATA['localhost']['switch_type'] == 'dpu') %}
auto eth0
iface eth0 inet dhcp
    metric 202
{% if (MGMT_VRF_CONFIG) and (MGMT_VRF_CONFIG['vrf_global']['mgmtVrfEnabled'] == "true") %}
    vrf mgmt
{% endif %}
```

**SmartSwitch の DPU ノード** (`subtype == "SmartSwitch"` かつ `switch_type == "dpu"`) では `MGMT_INTERFACE` エントリが存在しない状態でも `eth0` の DHCP 設定が **生成されない**。
DPU は管理 IF を持たない前提のため、`mgmtVrfEnabled=true` の場合でも `vrf mgmt` 行が `/etc/network/interfaces` に追加されず、DPU 上では管理 VRF への eth0 アサインが行われない。

| 条件 | eth0 DHCP ブロック生成 | mgmt VRF アサイン |
|------|----------------------|-------------------|
| 通常スイッチ (T0 / T1 等) で MGMT_INTERFACE なし | `auto eth0` + `iface eth0 inet dhcp metric 202` | `mgmtVrfEnabled=true` のとき `vrf mgmt` を付加 |
| SmartSwitch DPU (`subtype=SmartSwitch` + `switch_type=dpu`) | **生成なし** | **アサインなし** |

---

## 差異 2: Fabric ASIC — vrfmgrd が起動しない

`dockers/docker-orchagent/supervisord.conf.j2` L247–262

```jinja
{% if is_fabric_asic == 0 %}
[program:vrfmgrd]
command=/usr/bin/vrfmgrd
...
{%- endif %}
```

**Fabric ASIC** ノード (`is_fabric_asic == 1`) では `supervisord.conf` に `vrfmgrd` セクションが **生成されない**。
その結果、Fabric ASIC では `MGMT_VRF_CONFIG` テーブルへの書き込みがあっても `vrfmgrd` が CONFIG_DB を購読しないため、カーネル管理 VRF テーブルマップへの登録が発生しない。

| ASIC 種別 | vrfmgrd 起動 | MGMT_VRF_CONFIG 反映 |
|-----------|-------------|----------------------|
| 通常 ASIC (`is_fabric_asic == 0`) | あり | vrfmgr が VRF テーブルマップを管理する |
| Fabric ASIC (`is_fabric_asic == 1`) | **なし** | 反映されない（supervisord セクション欠如） |

---

## 差異 3: mgmt VRF table ID ハードコード — 全プラットフォーム共通固定値

`cfgmgr/vrfmgr.cpp` L15

```cpp
#define MGMT_VRF_TABLE_ID 6000
```

通常 VRF のルーティングテーブル ID は `VRF_TABLE_START (1001)` ～ `VRF_TABLE_END (5097)` の動的割当。mgmt VRF のみ **全プラットフォームでコンパイル時定数 6000 番** で固定。ASIC ベンダー・ARM / x86 アーキテクチャによらず変更不可。

---

## 差異 4: ARM / x86 アーキテクチャ差

vrfmgr は Linux `ip` コマンド経由でカーネル VRF netdev を操作し、ASIC SDK / SAI を経由しない。ARM（`aarch64` / `armhf`）と x86_64 の間で処理の差異は **なし**。

---

## 差異 5: multi-asic — MGMT_VRF_CONFIG は host CONFIG_DB のみ対象

`hostcfgd` は引数なし `ConfigDBConnector()` で host namespace の CONFIG_DB に接続し、`asicN` namespace は参照しない。multi-asic 環境でも `MGMT_VRF_CONFIG` は host 単位のシングルトンであり、各 ASIC namespace の CONFIG_DB には複製されない。

| 構成 | MGMT_VRF_CONFIG の配置 | hostcfgd の参照先 |
|------|----------------------|-------------------|
| single-asic | host CONFIG_DB のみ | host CONFIG_DB |
| multi-asic | host CONFIG_DB のみ | host CONFIG_DB（`asicN` namespace は参照しない） |
| VOQ chassis | 各 host (supervisor / line card) で独立 | 各 host の CONFIG_DB |

---

## スキャン証跡

- `interfaces.j2` L8–20 (mgmt VRF block)、L143–158 (SmartSwitch DPU 分岐) 確認
- `supervisord.conf.j2` L247–262 (`is_fabric_asic` 条件) 確認
- `vrfmgr.cpp` L15 (`MGMT_VRF_TABLE_ID` 定数)、L74–79 (mgmt 保護)、L176–183 (setLink mgmt 特殊処理) 確認
- `hostcfgd` L2249, 2268 (ConfigDBConnector 引数なし) 確認
- ARM / x86 分岐: `vrfmgr.cpp` 全行 grep `aarch64|armhf|ARM|x86` → 0 ヒット
- SmartSwitch + mgmt VRF: `minigraph.py` grep → SmartSwitch 条件と MGMT_VRF_CONFIG の交差なし
