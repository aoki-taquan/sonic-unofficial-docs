# VRF — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/cfgmgr/vrfmgr.cpp`
- `sonic-swss/cfgmgr/vrfmgr.h`
- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/vrforch.h`

---

## 発見された定数一覧

### vrfmgr.cpp — Linux ルーティングテーブル ID 管理

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `VRF_TABLE_START` | `1001` | 通常 VRF に割り当てる Linux routing table ID の開始値 | `vrfmgr.cpp:12` |
| `VRF_TABLE_END` | `5097` | 通常 VRF に割り当てる Linux routing table ID の終端値（排他） | `vrfmgr.cpp:13` |
| `TABLE_LOCAL_PREF` | `1001` | `ip rule` で local テーブルを移動する preference 値（l3mdev-table より後） | `vrfmgr.cpp:14` |
| `MGMT_VRF_TABLE_ID` | `6000` | `mgmt` VRF 専用の固定 Linux routing table ID | `vrfmgr.cpp:15` |
| `MGMT_VRF` | `"mgmt"` | mgmt VRF を識別する固定文字列 | `vrfmgr.cpp:16` |

### vrfmgr.cpp — VNI デフォルト値

| 変数 / 初期化 | 値 | 用途 | ソース |
|--------------|-----|------|--------|
| `uint32_t vni = 0` | `0` | VNI 未設定状態を表す初期値 | `vrfmgr.cpp:418` |

### vrforch.cpp — VNI デフォルト値

| 変数 / 初期化 | 値 | 用途 | ソース |
|--------------|-----|------|--------|
| `uint32_t vni = 0` | `0` | VNI 未設定状態を表す初期値（orchagent 側） | `vrforch.cpp:30` |

### nexthopkey.h — VRF 名プレフィクス

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `VRF_PREFIX` | `"Vrf"` | VRF 名先頭識別プレフィクス。routeorch / mplsrouteorch / flowcounterrouteorch が `compare(0, strlen(VRF_PREFIX), VRF_PREFIX)` で VRF ルートを識別する | `nexthopkey.h:20` |

### vrforch.cpp — SAI virtual_router_attr マッピング

`VRFOrch::addOperation` が APP_DB フィールドを SAI 属性に変換するマッピング（VNET / APP_DB 直接書込み時のみ有効。CONFIG_DB `VRF` テーブルには存在しない）:

| APP_DB フィールド | SAI 属性 | SAI 値型 | ソース |
|-----------------|---------|---------|--------|
| `v4` | `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE` | `bool` | `vrforch.cpp:40-41` |
| `v6` | `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE` | `bool` | `vrforch.cpp:45-46` |
| `src_mac` | `SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS` | `sai_mac_t` | `vrforch.cpp:51-52` |
| `ttl_action` | `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION` | `sai_packet_action_t` | `vrforch.cpp:56-57` |
| `ip_opt_action` | `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION` | `sai_packet_action_t` | `vrforch.cpp:61-62` |
| `l3_mc_action` | `SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION` | `sai_packet_action_t` | `vrforch.cpp:66-67` |

`ttl_action` と `l3_mc_action` は `REQ_T_PACKET_ACTION` 型（`vrforch.h:31,33`）。デフォルトのハードコード値なし（SAI ベンダーデフォルト適用）。MTU に対応する SAI 属性は `vrforch.cpp` に存在しない。

---

## 導出値・上限

| 項目 | 値 | 計算根拠 |
|------|-----|---------|
| 最大同時 VRF 数 | `4096` | `VRF_TABLE_END(5097) - VRF_TABLE_START(1001) = 4096` |
| テーブル ID 使用範囲 | `1001`〜`5096` | `VRF_TABLE_START` から `VRF_TABLE_END - 1` まで（`< VRF_TABLE_END` の条件） |
| mgmt VRF テーブル ID | `6000` | 通常プールと重ならない別枠の固定値 |

---

## リトライ / タイムアウト定数

vrfmgrd にはタイムアウト定数は存在しない。VRF DEL 時のパッシブリトライは **無制限**:

- `isVrfObjExist()` が `true` を返す間、Consumer キューをスキップして次回ループで再試行
- タイムアウトなし（orchagent 側 `m_stateVrfObjectTable.del()` を待つ）

---

## テーブル上限超過時の挙動

`getFreeTable()` が `m_freeTables` を使い果たすと `0` を返す（`vrfmgr.cpp:118-120`）。
呼び出し元 `setLink()` は `table == 0` を確認して `false` を返し（`vrfmgr.cpp:185-188`）、
`doTask()` 側が `SWSS_LOG_ERROR("Failed to create vrf netdev %s")` を記録してエントリを破棄する（`vrfmgr.cpp:283-284`）。
既存 VRF を削除すると `recycleTable()` によりテーブル ID がプールに戻る（`vrfmgr.cpp:129-134`）。

---

## 特記事項

1. **CONFIG_DB 非表現**: Linux routing table ID (`VRF_TABLE_START`〜`VRF_TABLE_END`) は CONFIG_DB のいかなるフィールドにも現れない。完全に vrfmgrd 内部のリソース管理。
2. **mgmt VRF 専用プール除外**: `MGMT_VRF_TABLE_ID=6000` は通常プール（1001〜5096）と重複しない。mgmt VRF は `setLink()` で固定 ID をマップするだけで `ip link add` を実行しない。
3. **TABLE_LOCAL_PREF と VRF_TABLE_START の値が一致**: どちらも `1001` だが役割が異なる。`TABLE_LOCAL_PREF` は `ip rule` の preference (優先度) 値、`VRF_TABLE_START` は routing table ID。
4. **VNI 上限は YANG による制約**: `vni` の取りうる値 `0`〜`16777215` は YANG `type uint32` + `range "0..16777215"` による制約であり、vrfmgr.cpp 内にはマジックナンバーとして現れない。

---

## 出典

- `sonic-swss/cfgmgr/vrfmgr.cpp` lines 12-16, 28-30, 114-134, 164-201, 281-284, 418-420, 441-443, 459-463
- `sonic-swss/cfgmgr/vrfmgr.h` lines 41-43
- `sonic-swss/orchagent/vrforch.cpp` lines 30, 38-84
- `sonic-swss/orchagent/vrforch.h` lines 31-33
- `sonic-swss/orchagent/nexthopkey.h` line 20
