# MGMT_VRF_CONFIG — Phase C 暗黙参照調査

生成日: 2026-05-16

## 調査目的

`vrfmgr` / `hostcfgd` が `MGMT_VRF_CONFIG` を処理する際に、暗黙的に参照する他テーブル
（`MGMT_INTERFACE` / `DEVICE_METADATA`）を抽出し、`<!-- cross-refs -->` ブロックの素材とする。

## 1. hostcfgd: MgmtIfaceCfg クラスの同時購読

`hostcfgd` の `MgmtIfaceCfg` クラス (L1605-1694) は `MGMT_INTERFACE` と `MGMT_VRF_CONFIG` を
**一体として**ロード・subscribe する。

```python
# hostcfgd:2248-2268
mgmt_ifc = init_data.get(swsscommon.CFG_MGMT_INTERFACE_TABLE_NAME, {})
mgmt_vrf = init_data.get(swsscommon.CFG_MGMT_VRF_CONFIG_TABLE_NAME, {})
self.mgmtifacecfg.load(mgmt_ifc, mgmt_vrf)
```

起動時に両テーブルを同時ロードし、`self.iface_config_data`（MGMT_INTERFACE の内容）と
`self.mgmt_vrf_enabled`（MGMT_VRF_CONFIG.mgmtVrfEnabled）を内部キャッシュに保持。

### 1a. MGMT_INTERFACE との依存関係

| 参照箇所 | 内容 | evidence |
|---|---|---|
| `MgmtIfaceCfg.load()` L1617-1619 | 起動時に `MGMT_INTERFACE` 全エントリを `iface_config_data` へロード | hostcfgd:1617-1619 |
| `MgmtIfaceCfg.update_mgmt_iface()` L1626-1643 | `MGMT_INTERFACE` 変更時に `interfaces-config` を restart。VRF 有効状態と連動 | hostcfgd:1626-1643 |
| `mgmt_intf_handler()` L2345-2350 | `MGMT_INTERFACE` 変更を受けて `update_mgmt_iface()` を呼び出し | hostcfgd:2345-2350 |
| subscribe L2485 | `config_db.subscribe('MGMT_INTERFACE', ...)` で runtime 変更を監視 | hostcfgd:2485 |
| `get_interface_ip("eth0")` L599-600 | NTP/RADIUS の src_ip 解決で `MGMT_INTERFACE` キーを参照 | hostcfgd:599-600 |

**依存の向き**: `MGMT_VRF_CONFIG.mgmtVrfEnabled=true` になると hostcfgd が
`interfaces-config restart` を実行し、その際に `MGMT_INTERFACE` のアドレス設定が
mgmt VRF namespace に移動する。両テーブルの整合が前提。

### 1b. DEVICE_METADATA との依存関係

| 参照箇所 | 内容 | evidence |
|---|---|---|
| `devmetacfg.load(dev_meta)` L2247,2267 | 起動時に `DEVICE_METADATA|localhost` を `DeviceMetaCfg` にロード | hostcfgd:2247,2267 |
| `device_metadata_handler()` L2404-2408 | `DEVICE_METADATA` 変更時に hostname / timezone / rsyslog を更新 | hostcfgd:2404-2408 |
| `subscribe(...CFG_DEVICE_METADATA_TABLE_NAME...)` L2492-2493 | `DEVICE_METADATA` を runtime で subscribe | hostcfgd:2492-2493 |

**mgmt VRF との間接依存**: `mgmtVrfEnabled=true` 時に hostcfgd が SSH / SNMP / NTP を
VRF 名前空間内で再起動する。これらのサービス設定は `DEVICE_METADATA.hostname` /
`DEVICE_METADATA.timezone` に依存するため、DEVICE_METADATA の内容が mgmt VRF
有効化の副作用として間接的に影響する。

## 2. vrfmgr: MGMT_INTERFACE / DEVICE_METADATA の直接参照

`vrfmgr.cpp` は `MGMT_INTERFACE` / `DEVICE_METADATA` を直接参照しない。
カーネル VRF の netdev 作成/削除のみを担い、管理インタフェースの IP アドレス設定は
hostcfgd に委譲している（責務分割）。

| daemon | MGMT_INTERFACE 参照 | DEVICE_METADATA 参照 |
|---|---|---|
| vrfmgr.cpp | なし（netdev のみ） | なし |
| hostcfgd MgmtIfaceCfg | 起動時 + subscribe (eth0 アドレス管理) | 間接（hostname/timezone 連動） |

## 3. cross-refs セクション構造案

### 暗黙参照テーブル一覧

| 参照元 | 参照先テーブル | 参照タイミング | 用途 | evidence |
|---|---|---|---|---|
| hostcfgd `MgmtIfaceCfg.load()` | `MGMT_INTERFACE` | 起動時 | eth0 アドレス設定の初期値ロード | hostcfgd:2248,1617 |
| hostcfgd `update_mgmt_iface()` | `MGMT_INTERFACE` | runtime (subscribe) | eth0 IP 変更時に `interfaces-config` 再起動 | hostcfgd:1626-1637 |
| hostcfgd `get_interface_ip()` | `MGMT_INTERFACE` | 都度（NTP/RADIUS src_ip 解決時） | eth0 IP アドレスを RADIUS nas_ip / NTP source に注入 | hostcfgd:599-600 |
| hostcfgd `DeviceMetaCfg.load()` | `DEVICE_METADATA` | 起動時 | hostname / timezone の初期取得 | hostcfgd:2247,2267 |
| hostcfgd `device_metadata_handler()` | `DEVICE_METADATA` | runtime (subscribe) | hostname / timezone / rsyslog 設定の動的反映 | hostcfgd:2404-2408 |

### 暗黙依存の特記事項

1. **MGMT_INTERFACE の順序依存**: `MGMT_VRF_CONFIG.mgmtVrfEnabled` を `true` にする前に
   `MGMT_INTERFACE` に eth0 の IP アドレスを設定しておかないと、VRF 有効化後の
   `interfaces-config restart` で IP アドレスなし状態になる。CLI (`config vrf add mgmt`) は
   この順序を強制しないため、手動設定時は注意が必要。

2. **DEVICE_METADATA.hostname との連動**: mgmt VRF 有効化時に SSH デーモンが VRF 内で
   再起動され、`/etc/hostname` (DEVICE_METADATA.hostname 由来) が参照される。hostname 未設定
   または空文字の場合、SSH 接続が不安定になる可能性がある。

3. **DEVICE_METADATA の直接参照なし**: vrfmgr も hostcfgd の MgmtIfaceCfg クラスも、
   DEVICE_METADATA を直接購読して MGMT_VRF_CONFIG の動作を変えることはない。
   依存は「mgmt VRF 有効化 → サービス再起動 → サービスが DEVICE_METADATA を参照」という
   間接経路。
