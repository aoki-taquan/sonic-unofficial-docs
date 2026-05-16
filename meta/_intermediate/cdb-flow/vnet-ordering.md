# VNET / VNET_ROUTE — Phase B 書込み順依存スキャンノート

対象テーブル: `VNET|<name>`, `VNET_ROUTE|<vnet_name>|<prefix>`, `VNET_ROUTE_TUNNEL|<vnet_name>|<prefix>`
Consumer (cfgmgr): `VxlanMgr` (`sonic-swss/cfgmgr/vxlanmgr.cpp`)
Consumer (orchagent): `VNetOrch` (`sonic-swss/orchagent/vnetorch.cpp`), `VNetCfgRouteOrch` (`sonic-swss/orchagent/vnetorch.cpp`)
スキャン範囲: `doVxlanCreateTask()` L287-376, `addOperation()` L434-558, `VNetCfgRouteOrch::doTask()` L3577-3611

---

## 検出した順序依存・タイミング依存

### 1. VXLAN_TUNNEL が先行必須（VxlanMgr 経路）

- `doVxlanCreateTask()` L319-324: `m_vxlanTunnelCache.find(info.m_vxlanTunnel)` が end() を返すと `return false`（処理保留、次ループで再試行）。
- VNET エントリの SET が届いても参照先 `VXLAN_TUNNEL|<name>` がキャッシュに存在しない場合、VxlanMgr はカーネル VXLAN デバイスを作成せずに待機し続ける。
- orchagent 側も `addOperation()` L498-503: `vxlan_orch->isTunnelExists(tunnel)` が false なら `return false`。
- **推奨**: `VXLAN_TUNNEL|<name>` SET → `VNET|<name>` SET の順で書き込む。
- evidence: `vxlanmgr.cpp:319-324`, `vnetorch.cpp:498-503`

### 2. STATE_DB VRF が ready になるまで待機（VxlanMgr 経路）

- `doVxlanCreateTask()` L327-333: `isVrfStateOk(info.m_vnet)` が false の場合 `return false` で保留。
- `isVrfStateOk()` L738-751: `STATE_VRF_TABLE` に当該 VRF 名が存在するかを確認。
- VRFOrch が VRF の SAI オブジェクトを作成し STATE_DB に書き込んだ後でなければカーネル VXLAN デバイス作成に進まない。
- VNetOrch 自身が VRF を生成する経路では orchdaemon の初期化順序（`vnet_orch` L276 → `VRFOrch` L283）により自動解消されることが多い。
- evidence: `vxlanmgr.cpp:327-333`, `vxlanmgr.cpp:738-751`

### 3. ルータ MAC アドレスが取得済みであること（VxlanMgr 経路）

- `doVxlanCreateTask()` L335-342: `getVxlanRouterMacAddress()` が false を返すと `return false` で保留。
- DEVICE_METADATA の `mac` フィールドが設定されていなければ MAC 取得に失敗し、VXLAN デバイスは作成されない。
- 通常は起動時に `sonic-cfggen` が DEVICE_METADATA を書き込むため問題にならないが、テスト環境や手動ロードでは注意。
- evidence: `vxlanmgr.cpp:335-342`

### 4. VNET 本体 SET → VNET_ROUTE / VNET_ROUTE_TUNNEL SET

- `VNetCfgRouteOrch::doVnetRouteTask()` L3638 / `doVnetTunnelRouteTask()` L3613: 即時 APPL_DB に転記するのみで VNET 存在チェックなし。
- ただし orchagent 側 `VNetRouteOrch` が APPL_DB `VNET_ROUTE_TABLE` / `VNET_ROUTE_TUNNEL_TABLE` を処理する際に `VNetOrch::isVnetExists()` を呼ぶ（`addOperation()` 内）。
- VNET_ROUTE を先に書くと APPL_DB には即転記されるが、orchagent が SAI に反映するタイミングが VNET 作成完了後になる。失われはしないが SAI 反映が遅延する。
- **推奨**: `VNET|<name>` SET → `VNET_ROUTE|<name>|<prefix>` SET の順で書き込む。
- evidence: `vnetorch.cpp:3613-3635`, `vnetorch.cpp:3638-3660`

### 5. orchdaemon 内での初期化順序

- orchdaemon.cpp L276: `VNetOrch` (APP_VNET_TABLE)
- orchdaemon.cpp L279: `VNetCfgRouteOrch` (CFG_VNET_RT / CFG_VNET_RT_TUNNEL)
- orchdaemon.cpp L281: `VNetRouteOrch` (APP_VNET_RT / APP_VNET_RT_TUNNEL)
- orchdaemon.cpp L283: `VRFOrch` (APP_VRF_TABLE)
- orchdaemon.cpp L350: `VxlanTunnelOrch` (APP_VXLAN_TUNNEL)
- orchList への追加順: `vxlan_vrf_orch` → `cfg_vnet_rt_orch` → `vnet_orch` → `vnet_rt_orch` (L590-593)
- VNetOrch が `gDirectory.get<VxlanTunnelOrch*>()` でランタイム参照するため、起動シーケンスが完了するまで VNET の SET 処理が VxlanTunnelOrch の存在前提に失敗することはない（gDirectory は set が呼ばれた後に get 可能）。
- evidence: `orchdaemon.cpp:265-293`, `orchdaemon.cpp:350-351`, `orchdaemon.cpp:590-593`

---

## SET 操作の推奨順序

```
# 1. DEVICE_METADATA mac が設定済みであること（起動時に自動）

# 2. VXLAN Tunnel を先に定義
SET VXLAN_TUNNEL|<tunnel_name>  src_ip=<vtep_ip>

# 3. VNET 本体
SET VNET|<vnet_name>  vxlan_tunnel=<tunnel_name> vni=<l3_vni>

# 4. VNET_ROUTE（ルート追加）
SET VNET_ROUTE|<vnet_name>|<prefix>  nexthop=<nh_ip> ifname=<ifname>
SET VNET_ROUTE_TUNNEL|<vnet_name>|<prefix>  endpoint=<vtep_ip>
```

## DEL 操作の推奨順序

```
# 1. ルートを先に削除
DEL VNET_ROUTE|<vnet_name>|<prefix>
DEL VNET_ROUTE_TUNNEL|<vnet_name>|<prefix>

# 2. VNET 本体を削除（関連 VRF・VXLAN tunnel map が自動削除される）
DEL VNET|<vnet_name>

# 3. 参照 VXLAN_TUNNEL は他 VNET が存在しない場合のみ削除可
DEL VXLAN_TUNNEL|<tunnel_name>
```

| 依存関係 | 方向 | 緩和策 |
|----------|------|--------|
| VXLAN_TUNNEL SET → VNET SET | 強制先行 | `return false` で自動保留・再試行 |
| STATE_DB VRF ready → VNET 処理 | 強制先行 | `return false` で自動保留・再試行 |
| DEVICE_METADATA mac 設定 → VNET 処理 | 強制先行 | `return false` で自動保留・再試行 |
| VNET SET → VNET_ROUTE SAI 反映 | 論理的先行 | APPL_DB への転記は即時、SAI 反映は遅延 |
| VNET_ROUTE DEL → VNET DEL | 推奨 | DEL 時に orchagent が内部でルートを自動削除するが明示削除が安全 |

> **スキャン証跡**: `vxlanmgr.cpp:doVxlanCreateTask()` L287-376 全行精読、`vnetorch.cpp:addOperation()` L434-558、`vnetorch.cpp:VNetCfgRouteOrch::doTask()` L3577-3611、`orchdaemon.cpp:265-293`, L350-354, L590-593 参照。
