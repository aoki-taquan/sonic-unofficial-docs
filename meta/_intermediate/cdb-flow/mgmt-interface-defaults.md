# Phase A デフォルト解析: MGMT_INTERFACE

## 1. フィールド列挙

| フィールド | YANG 型 | role |
|-----------|---------|------|
| `name` (key) | leafref MGMT_PORT.name | 管理 IF 名 (例: eth0) |
| `ip_prefix` (key) | sonic-ip-prefix | IPv4/IPv6 アドレス+プレフィクス長 |
| `gwaddr` | inet:ip-address | デフォルト GW |
| `forced_mgmt_routes` | leaf-list (prefix or address) | 追加強制ルート |

## 2. YANG default 宣言

YANG モデル (`sonic-mgmt_interface.yang`) に `default` 文は一切なし。
すべてのフィールドは任意 (optional) または key (必須)。

## 3. コードレベルのデフォルト・暗黙挙動

### 3.1 `gwaddr` — 省略時は DHCP フォールバック

`interfaces.j2` L75-158 の分岐:

```
{% if MGMT_INTERFACE %}
    ...# static 設定 (gwaddr 直接展開)
{% else %}
    # MGMT_INTERFACE エントリが存在しない場合のフォールバック
    iface eth0 inet dhcp
        metric 202
    iface eth0 inet6 dhcp
        up sysctl net.ipv6.conf.eth0.accept_ra=1
{% endif %}
```

- **MGMT_INTERFACE エントリが存在する** かつ `gwaddr` が空 → L96 の `via {{ MGMT_INTERFACE[(name, prefix)]['gwaddr'] }}` がキー未存在で空文字展開 → `ip route add default via  dev eth0` → kernel がエラー (ルート未設定)
- **MGMT_INTERFACE エントリが存在しない** → `iface eth0 inet dhcp metric 202` にフォールバック

ただし SmartSwitch DPU (`subtype=SmartSwitch` かつ `switch_type=dpu`) は DHCP フォールバックも生成されない (L144-158)。

### 3.2 `gwaddr` — ハードコードメトリック

`interfaces.j2` L96:
```
up ip -4 route add default via <gwaddr> dev <name> table <vrf_table> metric 201
```
静的設定時のデフォルトルートは **metric 201** ハードコード。

DHCP フォールバック (L151):
```
iface eth0 inet dhcp
    metric 202
```
DHCP 経由のデフォルトルートは **metric 202** ハードコード。

### 3.3 `forced_mgmt_routes` — 省略時は空リスト (no-op)

`interfaces.j2` L98:
```
{% for route in MGMT_INTERFACE[(name, prefix)]['forced_mgmt_routes'] %}
```
Jinja2 の for ループは空リストで何も生成しない → silent drop (エラーなし)。

### 3.4 `forced_mgmt_routes` — 暗黙の SYSLOG_SERVER ルート注入

`interfaces.j2` L101-113:
```
{% if SYSLOG_SERVER is defined and SYSLOG_SERVER %}
    # syslog サーバ IP への policy routing rule を自動追加
{% else %}
    # SYSLOG_SERVER 未設定時は 10.20.6.16/32 をハードコードで追加
    up ip rule add pref 32764 to 10.20.6.16/32 table <vrf_table>
{% endif %}
```
**`SYSLOG_SERVER` が未設定の場合、`10.20.6.16/32` が mgmt table に暗黙注入される。**
これは `forced_mgmt_routes` に書かれていない暗黙追加であり、ユーザー不可視。

### 3.5 `forced_mgmt_routes` — IPv6 デフォルトテーブル参照ルール

`interfaces.j2` L114-117:
```
{% if prefix | ipv6 and vrf_table == 'default' %}
    up ip -6 rule add pref 32767 lookup default
{% endif %}
```
mgmt VRF 無効かつ IPv6 prefix を設定した場合、`pref 32767 lookup default` ルールが自動追加される。

### 3.6 `vrf_table` — mgmtVrfEnabled による暗黙切り替え

`interfaces.j2` L87-91:
```
{%     set vrf_table = 'default' %}
{% if (MGMT_VRF_CONFIG) and (MGMT_VRF_CONFIG['vrf_global']['mgmtVrfEnabled'] == "true") %}
{%     set vrf_table = '6000' %}
    vrf mgmt
{% endif %}
```
- `mgmtVrfEnabled=true` → VRF table ID **6000**、インターフェース `vrf mgmt` 所属
- それ以外 → VRF table ID **`default`** (kernel default table)

### 3.7 `name` (key) — minigraph 由来の自動連番

`minigraph.py` L2291-2297:
```python
name = 'eth' + str(mgmt_intf_count)
mgmt_intf_count += 1
```
管理 IF 名は `eth0`, `eth1`, ... と自動連番。YANG leafref は `MGMT_PORT.name` を指すが、
CLI (`config/main.py` L5710) は `"eth0"` をハードコードで使用:
```python
config_db.set_entry("MGMT_INTERFACE", ("eth0", key[1]), None)
```

### 3.8 `gwaddr` — minigraph の暗黙 GW 計算

`minigraph.py` L2873-2874:
```python
gwaddr = ipaddress.ip_address((next(mgmtipn.hosts())))
results['MGMT_INTERFACE'].update({('eth0', mgmt_prefix): {'gwaddr': gwaddr}})
```
minigraph.py は指定プレフィクスの **第1 ホストアドレス** を gwaddr として自動算出する。
例: `10.0.0.1/24` → `gwaddr = 10.0.0.1`。

## 4. Dead field / Dead consumer 検出

- `forced_mgmt_routes` は hostcfgd に直接触れられない。`interfaces-config` サービス経由で `interfaces.j2` が展開するだけ。hostcfgd は SET/DEL を検知して `systemctl restart interfaces-config` を発行するのみ (MgmtIfaceCfg.update_mgmt_iface)。
- intfmgr.cpp は MGMT_INTERFACE を購読しない (`VRF_MGMT = "mgmt"` 定数があるのみ)。

## 5. プラットフォーム依存

- **SmartSwitch DPU** (`DEVICE_METADATA.localhost.subtype == 'SmartSwitch'` かつ `switch_type == 'dpu'`): `interfaces.j2` L144-158 で DHCP フォールバックが生成されない。MGMT_INTERFACE 未設定の DPU では `eth0` の設定が一切生成されない。
- **USB 管理 IF**: `config/main.py reset_mgmt_interface_if_usb_not_running()` が `config save / config reload` 時に USB IF の operstate を確認し、未稼働なら link down/up する。MGMT_INTERFACE エントリ削除は行わない（誤記あり、旧バージョンとの差異）。

## 6. 書き込み順依存

CLI (`config/main.py` L5700-5716):
1. 既存の同 IP family エントリを `set_entry(... None)` で削除
2. 新エントリを `set_entry(... {"gwaddr": gw})` または `{"NULL": "NULL"}` で書き込む

`gwaddr` 省略時は `{"NULL": "NULL"}` で書き込まれる → `interfaces.j2` で `gwaddr` キーが存在しないことになり、L96 のルートが壊れる。

## 7. YANG-実装 discrepancy

| 項目 | YANG | 実装 |
|------|------|------|
| `ip_prefix` must 制約 | `gwaddr` との family 一致が必須 | CLI は `{"NULL": "NULL"}` 書き込みで `gwaddr` なしエントリを許容 → must が通らない状態でも DB に書ける |
| `forced_mgmt_routes` 説明 | "default VRF or mgmt VRF" | 実際は SYSLOG_SERVER の有無で第三の暗黙ルートも挿入される |

## ソース証跡

| ソース | 行番号 | 内容 |
|--------|--------|------|
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mgmt_interface.yang` | 46-68 | YANG 定義全体、must 制約 |
| `sonic-buildimage/files/image_config/interfaces/interfaces.j2` | 75-164 | eth0 設定生成ロジック |
| `sonic-host-services/scripts/hostcfgd` | 1605-1693 | MgmtIfaceCfg クラス |
| `sonic-host-services/scripts/hostcfgd` | 2345-2350 | mgmt_intf_handler |
| `sonic-utilities/config/main.py` | 5700-5716 | `config interface ip add` 実装 |
| `sonic-utilities/config/main.py` | 1117-1142 | `reset_mgmt_interface_if_usb_not_running` |
| `sonic-buildimage/src/sonic-config-engine/minigraph.py` | 2281-2297 | minigraph MGMT_INTERFACE 生成 |
| `sonic-buildimage/src/sonic-config-engine/minigraph.py` | 2869-2880 | device_desc.xml の GW 自動算出 |
