# MGMT_VRF_CONFIG — Phase E ハードコード定数調査

生成日: 2026-05-16
ソース: sonic-swss/cfgmgr/vrfmgr.cpp

## 抽出した定数

### コンパイル時定数 (`#define`)

| 定数名 | 値 | 定義場所 |
|--------|----|----|
| `VRF_TABLE_START` | `1001` | `vrfmgr.cpp` L12 |
| `VRF_TABLE_END` | `5097` | `vrfmgr.cpp` L13 |
| `TABLE_LOCAL_PREF` | `1001` | `vrfmgr.cpp` L14 (l3mdev-table の後) |
| `MGMT_VRF_TABLE_ID` | `6000` | `vrfmgr.cpp` L15 |
| `MGMT_VRF` | `"mgmt"` | `vrfmgr.cpp` L16 |

### C++ ローカル変数デフォルト値

| 変数名 | 型 | 初期値 | 定義場所 | 意味 |
|--------|-----|--------|---------|------|
| `mgmt_vrf_enabled` | `bool` | `false` | `vrfmgr.cpp` L234 | `mgmtVrfEnabled` フィールド不在時の fallback |
| `in_band_mgmt_enabled` | `bool` | `false` | `vrfmgr.cpp` L246 | `in_band_mgmt_enabled` フィールド不在時の fallback |

### mgmtVrfEnabled の二値

| 値 | 意味 |
|----|------|
| `true` | mgmt VRF 有効。Linux に `mgmt` VRF netdev (table ID 6000) を作成。eth0 を mgmt VRF に所属。 |
| `false` (デフォルト) | mgmt VRF 無効。eth0 はデフォルト netns（グローバル netns）に所属。 |

### mgmt VRF 名

- コード内では `MGMT_VRF = "mgmt"` としてハードコード。
- ユーザーが CONFIG_DB に書くフィールドではなく、vrfmgr.cpp が Linux に渡す netdev 名として固定。
- `setLink("mgmt")` / `delLink("mgmt")` の分岐判定に使用 (`vrfName == MGMT_VRF`)。

### kernel netns デフォルト

- vrfmgr は Linux network namespace (netns) を直接操作しない。
- `mgmtVrfEnabled=false` 時: eth0 はグローバル netns（デフォルト netns、名前なし）に所属。
- `mgmtVrfEnabled=true` 時: hostcfgd が `interfaces-config` restart を通じて eth0 を mgmt VRF に所属させる（VRF は netns ではなく VRF netdev + ルーティングテーブル分離）。
- table ID 6000 で分離されるのはルーティングテーブルであり、netns とは異なる概念。ただし管理トラフィックは他のデータプレーン VRF から論理的に分離される。

## 証跡

```
sonic-swss/cfgmgr/vrfmgr.cpp:
  L12: #define VRF_TABLE_START 1001
  L13: #define VRF_TABLE_END 5097
  L14: #define TABLE_LOCAL_PREF 1001
  L15: #define MGMT_VRF_TABLE_ID 6000
  L16: #define MGMT_VRF          "mgmt"
  L234: bool mgmt_vrf_enabled = false;
  L246: bool in_band_mgmt_enabled = false;
  L257: if ((mgmt_vrf_enabled == false) || (in_band_mgmt_enabled == false)) op = DEL_COMMAND
```
