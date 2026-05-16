# VLAN_SUB_INTERFACE — Phase B 書込み順依存 証跡

生成日: 2026-05-16
対象ページ: `docs/reference/config-db/vlan-sub-interface.md`
調査コミット: sonic-swss/cfgmgr/intfmgr.cpp, sonic-swss/orchagent/intfsorch.cpp

---

## 1. 書込み経路（入り口）

| 経路 | 呼び出し | キー |
|------|---------|------|
| CLI `config interface ip add/remove <Eth....<vlan>>` | `set_entry('VLAN_SUB_INTERFACE', ...)` | `<parent>.<vlanId>` |
| minigraph / sonic-cfggen | `minigraph.py` が生成して投入 | `<parent>.<vlanId>` |
| REST / gNMI | 未実装 | — |
| db_migrator | マイグレーションなし | — |

---

## 2. intfmgrd における処理順序

```
CONFIG_DB: VLAN_SUB_INTERFACE set
  │
  ├─ [1] isIntfStateOk(parentAlias)                   # STATE_PORT / STATE_LAG 確認
  │    └─ false → return false (retry)
  │
  ├─ [2] VRF 先行チェック (vrf_name != empty)
  │    └─ !isIntfStateOk(vrf_name) → return false (retry)
  │
  ├─ [3] vlanId チェック (short-name 形式)
  │    └─ vlanId == "0" または空 → return false (retry)
  │
  ├─ [4] addHostSubIntf(parentAlias, alias, vlanId)    # ip link add ... type vlan id
  │    └─ runtime_error → return false (retry)
  │
  ├─ [5] setHostSubIntfMtu(alias, mtu, parentMtu)      # 親 MTU を上限にクランプ
  │
  └─ [6] setHostSubIntfAdminStatus(alias, admin, parentAdmin)  # 親 admin と合成
```

evidence: `sonic-swss/cfgmgr/intfmgr.cpp:833-999`

---

## 3. orchagent (intfsorch) における処理順序

```
APPL_DB: INTF_TABLE set (sub-interface)
  │
  ├─ [1] VRF 存在チェック
  │    └─ !m_vrfOrch->isVRFexists(vrf_name) → it++ (retry)
  │
  ├─ [2] gPortsOrch->getPort(alias, port) — sub-port エントリ確認
  │    └─ 未登録 → gPortsOrch->addSubPort(port, alias, vlan, adminUp, mtu)
  │         └─ 失敗 → it++ (retry)
  │
  └─ [3] addRouterIntf() で SAI 属性を順に push
       ├─ SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID  (VRF OID)
       ├─ SAI_ROUTER_INTERFACE_ATTR_TYPE               (SAI_ROUTER_INTERFACE_TYPE_SUB_PORT)
       ├─ SAI_ROUTER_INTERFACE_ATTR_PORT_ID            (親ポート OID: port.m_parent_port_id)
       ├─ SAI_ROUTER_INTERFACE_ATTR_OUTER_VLAN_ID      (port.m_vlan_info.vlan_id)
       ├─ SAI_ROUTER_INTERFACE_ATTR_ADMIN_V4_STATE
       ├─ SAI_ROUTER_INTERFACE_ATTR_ADMIN_V6_STATE
       └─ SAI_ROUTER_INTERFACE_ATTR_MTU
```

evidence: `sonic-swss/orchagent/intfsorch.cpp:823-831, 905-918, 1183-1280`

---

## 4. 書込み順依存の要点

### 4-1. PORT (親ポート) 先行必須

`intfmgrd` は `intfmgr.cpp:833` で `isIntfStateOk(parentAlias)` を呼び、`STATE_PORT_TABLE` (Ethernet 系) または `STATE_LAG_TABLE` (PortChannel 系) に親ポートの状態エントリが存在しない場合は `return false` でリトライ待ちとなる。

すなわち `PORT` または `PORTCHANNEL` テーブルへの書き込みが先行し、かつ `portmgrd` / `teammgrd` が `STATE_DB` に `STATE_PORT_TABLE` / `STATE_LAG_TABLE` のエントリを書き終えていなければ sub-interface は処理されない。

evidence: `intfmgr.cpp:833-836`

### 4-2. VLAN tag (encapsulation VLAN ID) の順序

short-name 形式 (`Po1.10` / `Eth0.100`) では `vlan` フィールドが CONFIG_DB に書き込まれる前に VLAN_SUB_INTERFACE エントリが処理された場合、`intfmgr.cpp:936-940` の `vlanId == "0" || vlanId.empty()` チェックで `return false` となりリトライ待ちになる。

long-name 形式 (`Ethernet0.100` / `PortChannel10.100`) では `subIntf::subIntfIdx()` が名前のドット後 ID を自動採用するため `vlan` フィールドが省略可能であり、このタイミング依存は発生しない。

evidence: `intfmgr.cpp:936-940, 763-767`

### 4-3. SAI sub-port RIF 生成順序

`orchagent/intfsorch.cpp:1250-1257` で SAI sub-port RIF 生成時の属性 push 順序は固定されており、以下の 2 属性は常に対で設定される:

1. `SAI_ROUTER_INTERFACE_ATTR_PORT_ID` — 親ポートの SAI OID (`port.m_parent_port_id`)
2. `SAI_ROUTER_INTERFACE_ATTR_OUTER_VLAN_ID` — VLAN tag ID (`port.m_vlan_info.vlan_id`)

この 2 属性はサブポート RIF を一意に識別するため、どちらか一方が未設定のまま `create_router_interface()` が呼ばれることはない。また `SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID` (VRF OID) は全 RIF タイプで必須の先頭属性として push される (`intfsorch.cpp:1183-1196`)。

evidence: `intfsorch.cpp:1183-1196, 1250-1258`

### 4-4. VRF 先行必須

`intfmgrd` は `intfmgr.cpp:839-842` で `vrf_name` が空でない場合 `isIntfStateOk(vrf_name)` を確認し、VRF が `STATE_DB` に存在しなければリトライ待ちになる。

`intfsorch` は `intfsorch.cpp:826-831` で `m_vrfOrch->isVRFexists(vrf_name)` を確認し、VRF OID が未登録の場合はリトライ(`it++`)する。

VRF を使用する場合は `VRF` テーブルへの書き込み → vrfmgrd/VRFOrch 処理完了 → VLAN_SUB_INTERFACE 書き込みの順が必須。

evidence: `intfmgr.cpp:839-842`, `intfsorch.cpp:823-831`

### 4-5. 親 admin_status との合成

`intfmgr.cpp:512-525` の `setHostSubIntfAdminStatus()` は親 IF の admin_status (`getIntfAdminStatus()`) と sub-interface の admin_status を合成する: 親が `"down"` の場合は sub-IF が `"up"` 設定でも実効 `"down"` になる。

この処理は `STATE_PORT_TABLE` / `STATE_LAG_TABLE` から `admin_status` を読み取るため、親ポートの状態が先行取得されていることが前提となる（依存 #1 と連動）。

evidence: `intfmgr.cpp:512-525, 985-999`

---

## 5. フィールドごとの書込み先と依存関係

| フィールド | 書込み先 | 依存関係 |
|-----------|---------|---------|
| `<name>` (key, long-name) | APPL_DB INTF_TABLE → SAI SAI_ROUTER_INTERFACE_TYPE_SUB_PORT | 親 PORT/PORTCHANNEL 先行必須 |
| `<name>` (key, short-name) | 同上 | 親 PORT/PORTCHANNEL + `vlan` フィールド 先行必須 |
| `vlan` | カーネル sub-IF の vlan type id + SAI OUTER_VLAN_ID | short-name 形式では必須、省略でリトライ待ち |
| `admin_status` | `ip link set <sub-if> up/down` + SAI ADMIN_V4/V6_STATE | 親 admin_status と合成（親 down → sub も down） |
| `mtu` | `ip link set <sub-if> mtu <val>` | 親 MTU を上限としてクランプ (`setHostSubIntfMtu`) |
| `vrf_name` | SAI SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID | `VRF` テーブル + vrfmgrd 処理完了が先行必須 |
| `vnet_name` | APPL_DB INTF_TABLE vnet_name | VNET テーブル先行必須 |
| `loopback_action` | APPL_DB INTF_TABLE loopback_action | なし |

---

## 6. evidence

- `sonic-swss/cfgmgr/intfmgr.cpp` — `addHostSubIntf`, `isIntfStateOk`, `setHostSubIntfAdminStatus`, `setHostSubIntfMtu` 全関数
  <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
- `sonic-swss/orchagent/intfsorch.cpp` — `doTask`, `addRouterIntf`, `isVRFexists`, `getPort`, `addSubPort`
  <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/intfsorch.cpp>
