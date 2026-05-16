# dhcp-server-ipv4 — Phase H: プラットフォーム差異

> 調査日: 2026-05-16  
> ソース: `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py`、`dhcpservd.py`、`common/utils.py`、`dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py`

## 1. kea-dhcp4 vs dnsmasq

`sonic-dhcp-server` は **kea-dhcp4 のみ**を DHCP バックエンドとして使用する。dnsmasq は使用されていない（コード内に参照なし）。

- `dhcpservd.py` が `/etc/kea/kea-dhcp4.conf` を生成・SIGHUP で再読込させる
- `dhcp_cfggen.py` が Jinja2 テンプレート (`kea-dhcp4.conf.j2`) をレンダリング
- `wait_for_dhcpservd.sh` が dhcpservd readiness フラグ (`/tmp/dhcpservd_ready`) を確認してから kea-dhcp4 を起動するゲート構造

dnsmasq は SONiC の DHCP relay 側 (`dhcprelayd`) にも登場しない。**kea-dhcp4 一択であり、プラットフォームによる切替は存在しない。**

## 2. SmartSwitch DPU 差異

`DEVICE_METADATA.localhost.subtype == "SmartSwitch"` を `is_smart_switch()` で判定し、以下の挙動が分岐する。

### 2.1 インタフェース対象の拡張

| 条件 | 挙動 |
|---|---|
| 通常 SONiC | `VLAN` / `VLAN_INTERFACE` ベースのインタフェースのみを DHCP 対象とする |
| SmartSwitch | 上記に加えて `MID_PLANE_BRIDGE.GLOBAL.bridge` で定義された mid-plane bridge インタフェースを DHCP 対象に追加。`DPUS` テーブルから `midplane_interface` フィールドを持つ DPU エントリをポートとして扱う |

**コード証跡** (`dhcp_cfggen.py:76,84-91`):
```python
mid_plane, dpus = self._parse_dpu(dpus_table, mid_plane_table) if smart_switch else ({}, {})
...
if smart_switch and "bridge" in mid_plane and "ip_prefix" in mid_plane:
    mid_plane_name = mid_plane["bridge"]
    dhcp_interfaces[mid_plane_name] = [{"network": ..., "ip": mid_plane["ip_prefix"]}]
    dpus = ["{}|{}".format(mid_plane_name, dpu) for dpu in dpus]
dhcp_members = vlan_members | set(dpus)
```

### 2.2 kea-dhcp4 subnet ID の固定

| 条件 | subnet ID |
|---|---|
| 通常 SONiC (`VlanXXX`) | VLAN 番号を整数変換 (例: `Vlan100` → `100`) |
| SmartSwitch (mid-plane bridge) | `MID_PLANE_BRIDGE_SUBNET_ID = 10000` にハードコード |

**コード証跡** (`dhcp_cfggen.py:19,251`):
```python
MID_PLANE_BRIDGE_SUBNET_ID = 10000
"id": MID_PLANE_BRIDGE_SUBNET_ID if smart_switch else dhcp_interface_name.replace("Vlan", "")
```

### 2.3 DB 購読テーブルの追加

SmartSwitch 判定時は通常の `PORT_MODE_CHECKER` に加えて `SMART_SWITCH_CHECKER` を追加購読する。

| 種別 | 購読テーブル |
|---|---|
| 通常 SONiC | `DHCP_SERVER_IPV4`, `DHCP_SERVER_IPV4_PORT`, `DHCP_SERVER_IPV4_RANGE`, `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS`, `VLAN`, `VLAN_INTERFACE`, `VLAN_MEMBER` |
| SmartSwitch 追加分 | `DPUS`, `MID_PLANE_BRIDGE` |

**コード証跡** (`dhcp_cfggen.py:23,97-98`):
```python
SMART_SWITCH_CHECKER = ["DpusTableEventChecker", "MidPlaneTableEventChecker"]
if smart_switch:
    subscribe_table |= set(SMART_SWITCH_CHECKER)
```

### 2.4 key 構造の差異

| 条件 | `DHCP_SERVER_IPV4` key 形式 |
|---|---|
| 通常 SONiC | `DHCP_SERVER_IPV4|Vlan<id>` |
| SmartSwitch | `DHCP_SERVER_IPV4|<MID_PLANE_BRIDGE.GLOBAL.bridge>` (例: `DHCP_SERVER_IPV4|bridge-midplane`) |

YANG の `name` フィールドは `union { Vlan<id>; bridge-name }` として定義されているため、SmartSwitch の bridge 名も YANG バリデーションを通過する。

## 3. FEATURE 有効化差異

`sonic-dhcp-server` 機能は `FEATURE|dhcp_server` テーブルで制御される。この制御はすべてのプラットフォームで共通だが、SmartSwitch と通常プラットフォームで有効化パスに実装上の差異がある。

### 3.1 CLI ガード (全プラットフォーム共通)

`config dhcp_server` グループ入口で `FEATURE|dhcp_server.state == "enabled"` を確認する。未有効化時は全サブコマンドが `ctx.fail()` で終了する (`dhcp_server.py:54`)。

### 3.2 `DEVICE_METADATA.localhost.dhcp_server` (全プラットフォーム共通)

`dhcp_server` フィールドが `enabled` でなければ dhcpservd が起動しない。SmartSwitch でも同様。

### 3.3 SmartSwitch での追加前提条件

SmartSwitch 環境では `FEATURE|dhcp_server` の有効化に加えて:

1. `MID_PLANE_BRIDGE.GLOBAL.bridge` フィールドが設定されていること
2. `MID_PLANE_BRIDGE.GLOBAL.ip_prefix` が設定されていること
3. `DPUS` テーブルに `midplane_interface` フィールドを持つエントリが存在すること

上記のいずれかが欠けると、SmartSwitch 固有の DHCP 提供 (DPU への IP 配布) が無効化される（ただし dhcpservd は起動を継続し、通常 VLAN の DHCP は機能する）。

## 4. 非対応プラットフォーム / スコープ外

- **arm / aarch64 / x86 アーキテクチャ差**: コード上の条件分岐なし。kea-dhcp4 バイナリのアーキテクチャ差はパッケージ管理レイヤーで吸収
- **dnsmasq**: 使用なし
- **ベンダー固有**: スコープ外 (コミュニティ版 master のみ対象)

## 引用

- `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py:8,17-23,67,76,84-98,190-270`
- `src/sonic-dhcp-utilities/dhcp_utilities/common/utils.py:153-163`
- `dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py:54`
