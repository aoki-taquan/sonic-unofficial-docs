# INTERFACE テーブル — プラットフォーム差 (Phase H)

調査日: 2026-05-14
調査対象:
- sonic-swss/orchagent/intfsorch.cpp
- sonic-swss/orchagent/main.cpp (orchdaemon 含む)
- sonic-swss/cfgmgr/intfmgr.cpp
- sonic-buildimage/device/mellanox/ (sai.profile 群)
- sonic-buildimage/device/broadcom/ (sai.profile)

---

## 検出したプラットフォーム差

### 1. NAT (`nat_zone`) — SAI capability query

**検出箇所**: `main.cpp:936-948`, `intfsorch.cpp:1287-1294`

```cpp
// main.cpp
attr.id = SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY;
status = sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr);
if (status == SAI_STATUS_SUCCESS && attr.value.u32 != 0) {
    gIsNatSupported = true;
}
```

- `gIsNatSupported == false` の場合: `nat_zone` フィールドは CONFIG_DB に設定されていても SAI には送られない
- `gIsNatSupported` は `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` が 0 より大きい値を返した場合のみ `true`
- VS (virtual switch) SAI は `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY = 100` を返す (既知)
- 実 Broadcom SAI (TD3, TH2 等) / Mellanox SAI でも返すが、ハードウェア実装差あり
- **結果**: NAT ハードウェアオフロード非対応 ASIC では `nat_zone` 設定は黙殺される

### 2. Mellanox SAI プロファイル — `SAI_NOT_DROP_SIP_DIP_LINK_LOCAL=1`

**検出箇所**: 全 Mellanox/NVIDIA SKU の `sai.profile`

例:
- `device/mellanox/x86_64-mlnx_msn2700-r0/Mellanox-SN2700/sai.profile`
- `device/mellanox/x86_64-mlnx_msn4700-r0/Mellanox-SN4700-C128/sai.profile`
- `device/mellanox/x86_64-nvidia_sn4280-r0/Mellanox-SN4280-O28/sai.profile`

```
SAI_NOT_DROP_SIP_DIP_LINK_LOCAL=1
```

- **意味**: Mellanox/NVIDIA ASIC はデフォルトで SIP/DIP が link-local アドレス (169.254.x.x / fe80::/10) のパケットをハードウェアでドロップする。このフラグを `1` に設定することで L3 インタフェース経由でのリンクローカルパケット転送を許可する
- Broadcom, Marvell, Barefoot の `sai.profile` にはこのキーが存在しない
- INTERFACE + `ipv6_use_link_local_only` の動作に Mellanox と他 ASIC で差が生じる可能性

### 3. `loopback_action` — SAI プラットフォームデフォルト依存

**検出箇所**: `intfsorch.cpp:1187-1195`, `intfsorch.cpp:431-459`

- `loopback_action` 未設定時 → `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` 属性を SAI に渡さない
- SAI プラットフォームデフォルトに委ねられるため、ASIC ベンダーによって挙動が異なる
- `drop` / `forward` のみサポート。その他の値は `SWSS_LOG_WARN` → 設定スキップ

### 4. Proxy ARP + VLAN — VLAN type 限定

**検出箇所**: `intfsorch.cpp:409-425`

```cpp
if (port.m_type == Port::VLAN)
{
    // SAI_VLAN_ATTR_BROADCAST_FLOOD_CONTROL_TYPE を制御
    // SAI_VLAN_ATTR_UNKNOWN_MULTICAST_FLOOD_CONTROL_TYPE も制御
}
// PHY/LAG/SUBPORT に対しては何もしない (SAI 操作なし)
```

- `proxy_arp` は VLAN IF にのみ SAI 変更が走る
- 物理 IF (Ethernet) / LAG での `proxy_arp` 設定は OS 層のみ (SAI 側無変更)
- VLAN flood control の SAI 実装差が結果に影響する可能性 (ベンダー差)

### 5. VS (Virtual Switch) プラットフォーム — MAC アドレス特例

**検出箇所**: `neighorch.cpp:2213-2218`

```cpp
string platform = getenv("ASIC_VENDOR") ? getenv("ASIC_VENDOR") : "";
if (platform == VS_PLATFORM_SUBSTRING)  // "vs"
{
    mac_address = original_mac_address;
}
```

- VS プラットフォームでは近傍プログラミング時に MAC をそのまま使用
- 実 ASIC では `gMacAddress` (switch global MAC) に置き換え
- `INTERFACE|<port>|mac_addr` 設定は orchagent で `gMacAddress` にフォールバックするが、VS では近傍経路は除外

### 6. SAI 初期化ファイル — Mellanox XML / Broadcom config.bcm

**検出箇所**: 各 sai.profile

Mellanox SKU 例:
```
SAI_INIT_CONFIG_FILE=/usr/share/sonic/hwsku/sai_2700.xml
```

Broadcom SKU 例 (Arista 7260):
```
SAI_INIT_CONFIG_FILE=/usr/share/sonic/hwsku/th-a7260cx3-64-flex.config.bcm
```

- L3 インタフェースの RIF 数上限・ECMP メンバ数 (`SAI_NUM_ECMP_MEMBERS`) はこれらファイルで決定
- `SAI_NUM_ECMP_MEMBERS=64` は Broadcom Arista SKU に多い設定 (Mellanox はデフォルト値)
- Mellanox: XML ベース SAI 設定、RIF 上限はチップ世代依存 (SN2700 vs SN4700 等)

### 7. VOQ Chassis — システムインタフェース同期

**検出箇所**: `intfsorch.cpp:1316-1317`, `intfsorch.cpp:1369-1370`, `intfsorch.cpp:586-593`, `intfmgr.cpp:103-106`

```cpp
// intfsorch.cpp:1316-1317  RIF 作成直後
voqSyncAddIntf(port.m_alias);
// intfsorch.cpp:1369-1370  RIF 削除直後
voqSyncDelIntf(port.m_alias);
```

- `switch_type=voq` のシャーシ環境では、ローカルポートの `INTERFACE` SET/DEL が `CHASSIS_APP_DB::SYSTEM_INTERFACE_TABLE` への書き込み/削除を引き起こす
- `voqSyncAddIntf` はポートが `SAI_SYSTEM_PORT_TYPE_REMOTE` でないことを確認してからのみ同期する
- inband ポート (`isInbandPort(alias)` が真) への IP 追加/削除時は `addInbandNeighbor` / `delInbandNeighbor` を呼び出してリモート ASIC にネイバー情報を伝播する
- リモートポートの IF 状態変化は `CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME` への通知として届き、`ifChangeInformRemoteNextHop` でネクストホップを更新する
- IPv6 アドレス追加時に `metric 256` を付与 (`intfmgr.cpp:103-106`) して connected ルートと static ルートのメトリクスを一致させる（通常シングルスイッチでは metric 指定なし）

**通常シングルスイッチとの差分**:

| 操作 | 通常シングルスイッチ | VOQ Chassis |
|------|---------------------|------------|
| `INTERFACE` SET (local port) | RIF 作成のみ | RIF 作成 + CHASSIS_APP_DB 同期 |
| `INTERFACE` DEL (local port) | RIF 削除のみ | RIF 削除 + CHASSIS_APP_DB 削除 |
| `INTERFACE\|<port>\|<ip>` (inband) | IP2me ルート追加 | IP2me ルート + inband neighbor 追加 |
| IPv6 アドレス追加 | `ip -6 address add <ip>` | `ip -6 address add <ip> metric 256` |

### 8. SmartSwitch DPU — コード差なし (2026-05-16 時点)

**検出箇所**: `intfsorch.cpp` 全体、`intfmgr.cpp` 全体

`sonic-swss/orchagent/intfsorch.cpp` および `cfgmgr/intfmgr.cpp` には SmartSwitch / DPU 固有の条件分岐は存在しない。DPU 上の `INTERFACE` テーブル処理は通常の物理ポートと同一経路をたどる。SmartSwitch 固有のインタフェース管理は `dpuorch` / `midplaneorch` に委譲されており、本テーブルには影響しない。

---

## 結論

| フィールド / 構成 | 差の性質 | 影響 ASIC / 環境 |
|-----------------|---------|----------------|
| `nat_zone` | SAI capability query で有効/無効決定 | NAT 非対応 ASIC では黙殺 |
| `ipv6_use_link_local_only` | Mellanox SAI プロファイルキー `SAI_NOT_DROP_SIP_DIP_LINK_LOCAL` で転送可否変化 | Mellanox/NVIDIA のみ sai.profile 設定あり |
| `loopback_action` | 未設定時は SAI プラットフォームデフォルト依存 | ベンダー差あり |
| `mac_addr` | VS ではそのまま、実 ASIC では switch global MAC | VS vs 実 HW |
| `proxy_arp` | VLAN IF のみ SAI flood control 変更、物理 IF では SAI 無変更 | VLAN flood 実装がベンダー依存 |
| VOQ Chassis | CHASSIS_APP_DB 同期・inband neighbor・IPv6 metric 256 が追加される | `switch_type=voq` のシャーシのみ |
| SmartSwitch DPU | コード差なし。DPU 固有処理は dpuorch/midplaneorch に委譲 | 本テーブルへの影響なし |
