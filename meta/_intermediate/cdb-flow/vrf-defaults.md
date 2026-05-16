# VRF フィールド暗黙デフォルト調査メモ (Phase A)

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/vrf.md`  
ソース:
- `sonic-swss/cfgmgr/vrfmgr.cpp`
- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/vrforch.h`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vrf.yang`

---

## フィールド別調査結果

### `fallback` (boolean)

- **YANG default**: `false` (sonic-vrf.yang:44)
- **vrfmgr 処理**: `fallback` フィールドは `kfvFieldsValues(t)` として APP_DB に **そのまま pass-through** される (`vrfmgr.cpp:303: m_appVrfTableProducer.set(vrfName, kfvFieldsValues(t))`)。vrfmgr 自身はこのフィールドを解釈しない。
- **VRFOrch 処理 (orchagent)**: `vrforch.h:34` で `REQ_T_BOOL` として登録されているが、`vrforch.cpp` の `addOperation` の if/else チェーンに `"fallback"` のハンドラが存在しない。未知フィールドとして `SWSS_LOG_ERROR("Logic error: Unknown attribute: %s", name.c_str())` が出力され **SAI 属性に変換されずに silent drop** される。
- **FRR / bgpcfgd**: VRF CONFIG_DB テーブルの `fallback` フィールドを参照するコードなし (bgpcfgd managers, j2 テンプレート全体検索で 0 件)。
- **実質動作**: `fallback` はどの consumer にも実装されていない **dead field**。YANG default `false` のみが有効で、値を変えても Linux カーネル・SAI・FRR への影響はない。
- **発見種別**: **dead consumer / silent drop at orchagent**

### `vni` (uint32 0..16777215)

- **YANG default**: `0` (sonic-vrf.yang:51)
- **vrfmgr 処理**: `doVrfVxlanTableCreateTask` でパース (`vrfmgr.cpp:418-433`)。`vni == 0` かつ既存マップなし → 何もしない (`vrfmgr.cpp:469-471`)。
- **暗黙デフォルト (ランタイム)**: フィールド省略時は `vni` 変数が `0` のまま (`uint32_t vni = 0;` vrfmgr.cpp:418)。YANG default `0` と一致。
- **orchagent 処理**: `vrforch.cpp:30: uint32_t vni = 0;` — フィールド省略時は `0` のまま。`vni != 0` の場合のみ `updateVrfVNIMap` 呼び出し (`vrforch.cpp:111`)。
- **VNI 再設定制約**: `old_vni != 0` の状態で別の VNI を設定しようとすると `SWSS_LOG_ERROR("vrf %s is already mapped to vni %d")` でエラーリターン。一旦 `vni=0` にリセットが必要 (vrfmgr.cpp:459-462)。
- **発見種別**: YANG default と実装デフォルトが一致。書込み順依存の制約あり。

### `name` (key: string)

- **YANG パターン制約**: `Vrf[a-zA-Z0-9_-]+` — 違反で reject。
- **mgmt VRF 特例**: `vrfName == "mgmt"` の場合は `MGMT_VRF_TABLE_ID = 6000` (ハードコード) が割り当てられ、Linux ルーティングテーブル ID の通常プール (1001-5096) を消費しない (vrfmgr.cpp:176-183)。
- **発見種別**: **ハードコード定数 + プラットフォーム依存** (MGMT_VRF 専用特例)。

---

## Linux ルーティングテーブル割り当て (暗黙挙動)

vrfmgr はコンストラクタで `VRF_TABLE_START=1001` 〜 `VRF_TABLE_END=5097` (計 4096 個) の free テーブル ID プールを作成する。VRF 追加ごとに昇順で割り当て。

- **ハードコード定数**:
  - `VRF_TABLE_START = 1001`
  - `VRF_TABLE_END = 5097`
  - `TABLE_LOCAL_PREF = 1001`
  - `MGMT_VRF_TABLE_ID = 6000`
- **最大 VRF 数**: 4096 (VRF_TABLE_END - VRF_TABLE_START)
- **発見種別**: **ハードコード / 暗黙最大数制限**。CONFIG_DB に表現されない。

---

## dead フィールド (orchagent 宣言のみ・未実装)

`vrforch.h` の `request_description` には以下のフィールドが登録されているが、**YANG sonic-vrf.yang にも CONFIG_DB VRF テーブルにも存在せず**、`addOperation` で SAI 属性への変換コードも存在しない。つまり APP_DB に書かれても orchagent で無視される。

| フィールド | orchagent 側型 | 実装状態 |
|-----------|---------------|---------|
| `v4` | REQ_T_BOOL | SAI `ADMIN_V4_STATE` に変換 (実装あり) |
| `v6` | REQ_T_BOOL | SAI `ADMIN_V6_STATE` に変換 (実装あり) |
| `src_mac` | REQ_T_MAC_ADDRESS | SAI `SRC_MAC_ADDRESS` に変換 (実装あり) |
| `ttl_action` | REQ_T_PACKET_ACTION | SAI `VIOLATION_TTL1_PACKET_ACTION` に変換 (実装あり) |
| `ip_opt_action` | REQ_T_PACKET_ACTION | SAI `VIOLATION_IP_OPTIONS_PACKET_ACTION` に変換 (実装あり) |
| `l3_mc_action` | REQ_T_PACKET_ACTION | SAI `UNKNOWN_L3_MULTICAST_PACKET_ACTION` に変換 (実装あり) |
| `fallback` | REQ_T_BOOL | **未実装 → silent drop** |
| `mgmtVrfEnabled` | REQ_T_BOOL | explicit ignore (`continue`) |
| `in_band_mgmt_enabled` | REQ_T_BOOL | explicit ignore (`continue`) |

`v4`/`v6`/`src_mac`/`ttl_action`/`ip_opt_action`/`l3_mc_action` は APP_DB 経由で orchagent に渡った場合に機能するが、**CONFIG_DB の VRF テーブル (sonic-vrf.yang) には定義されておらず**、通常の `config vrf add` では書き込まれない。これらは VNET テーブルや将来の拡張用に orchagent 側に残存している可能性がある。

---

## 書込み順依存

1. `vni` を一度設定したら `vni=0` にリセットしないと新しい VNI に変更不可。
2. VRF 削除時: orchagent の `STATE_VRF_OBJECT_TABLE` に VRF オブジェクトが残存している間 vrfmgrd は削除をリトライ待ち。所属インタフェース・ルートを先に削除すること。

---

## 要約

| 検出種別 | 対象 | 詳細 |
|---------|------|------|
| dead consumer / silent drop | `fallback` | orchagent に宣言あるが handler なし。SAI/Linux/FRR に未到達 |
| YANG default = ランタイムデフォルト一致 | `fallback=false`, `vni=0` | YANG と実装が整合 |
| ハードコード定数 | VRF ルーティングテーブル ID 1001-5096 | CONFIG_DB 非表現 |
| ハードコード + 特例 | `mgmt` VRF テーブル ID 6000 | CONFIG_DB 非表現 |
| 最大数制限 | VRF 最大 4096 個 | CONFIG_DB 非表現 |
| 書込み順依存 | `vni` 再設定 | 0 リセット必須 |
| dead consumer (YANG-実装 discrepancy) | `v4`/`v6`/`src_mac` 等 | orchagent 内部には SAI 実装あり、YANG/CONFIG_DB には未定義 |
