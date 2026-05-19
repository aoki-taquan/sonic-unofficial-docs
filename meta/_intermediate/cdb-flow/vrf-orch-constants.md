# vrf-orch Phase E — ハードコード定数

調査対象: `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-swss-common/common/schema.h`
調査日: 2026-05-19

## vrfmgr.cpp 数値定数 (L12-15)

| 定数名 | 値 | 用途 |
|---|---|---|
| `VRF_TABLE_START` | `1001` | 通常 VRF へ割り当てるルーティングテーブル ID の開始値 |
| `VRF_TABLE_END` | `5097` | 通常 VRF ルーティングテーブル ID の終端値 (exclusive)。最大同時 VRF 数 = 4096 |
| `TABLE_LOCAL_PREF` | `1001` | `ip rule add pref 1001 table local` で置き換えるときに使う preference 値。`ip rule del pref 0` とペアで実行し local テーブルルールを再配置 |
| `MGMT_VRF_TABLE_ID` | `6000` | mgmt VRF 専用固定テーブル ID。`vrfName == "mgmt"` のとき `getFreeTable()` を呼ばず直接使用 |

## schema.h テーブル名定数

| マクロ名 | 文字列値 | DB | ソース |
|---|---|---|---|
| `APP_VRF_TABLE_NAME` | `"VRF_TABLE"` | APPL_DB | `schema.h:80` |
| `APP_VXLAN_VRF_TABLE_NAME` | `"VXLAN_VRF_TABLE"` | APPL_DB | `schema.h:84` |
| `STATE_VRF_TABLE_NAME` | `"VRF_TABLE"` | STATE_DB | `schema.h:429` |
| `STATE_VRF_OBJECT_TABLE_NAME` | `"VRF_OBJECT_TABLE"` | STATE_DB | `schema.h:430` |

## 補足

- ルーティングテーブル ID プール (`1001`〜`5096`) は `vrfmgr.cpp:28` の for ループで `m_freeTables` キューに積まれる
- プール枯渇時 (`getFreeTable()` → `0`) は `setLink()` が `false` を返すが STATE_DB.set / APPL_DB.set は継続実行されるため中間状態が生じうる (`vrfmgr.cpp:282-303`)
- `TABLE_LOCAL_PREF = 1001` と `VRF_TABLE_START = 1001` が同値であるのは偶然ではない。`l3mdev-table` モジュールが pref 0 の local テーブルを使用するため、VRF テーブル ID と同じ 1001 番に移動させる設計
