---
title: APPL_DB VRF_TABLE (VRFOrch)
description: "APPL_DB VRF_TABLE — vrfmgrd が CONFIG_DB VRF テーブルを転写し VRFOrch が SAI Virtual Router を生成するパイプライン。フィールドのコード由来デフォルトと orchagent 内部挙動を記述する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/vrforch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/vrforch.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: cfgmgr/vrfmgr.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - VRF
    - MGMT_VRF_CONFIG
    - INTERFACE
  cli:
    - config vrf
  yang:
    - sonic-vrf
---

# APPL_DB VRF_TABLE (VRFOrch)

## 概要

`APPL_DB VRF_TABLE` は [VRF](../../reference/glossary.md#term-vrf) インスタンスの実効設定を保持する [APPL_DB](../../reference/glossary.md#term-appl_db) テーブル。テーブル名は `"VRF_TABLE"` (`schema.h:80`)。

パイプラインは 2 段構成:

1. **vrfmgrd** — `CONFIG_DB VRF` を購読し、Linux `ip link add ... type vrf table <id>` で VRF デバイスを作成した後、`kfvFieldsValues(t)` をそのまま `APP_VRF_TABLE` へ書き込む（デフォルト補完なし）
2. **VRFOrch** — `APP_VRF_TABLE` を購読し、フィールドを SAI 属性に変換して `sai_virtual_router_api->create_virtual_router()` を呼ぶ

```mermaid
flowchart LR
  CDB[("CONFIG_DB\nVRF")]
  MGMT[("CONFIG_DB\nMGMT_VRF_CONFIG")]
  VRFMGR["vrfmgrd\n(Linux VRF 作成)"]
  APPDB[("APPL_DB\nVRF_TABLE")]
  ORCH["VRFOrch\n(orchagent)"]
  SAI["SAI\nsai_virtual_router_api"]
  STATE[("STATE_DB\nVRF_OBJECT_TABLE")]
  CDB --> VRFMGR --> APPDB --> ORCH --> SAI
  MGMT --> VRFMGR
  ORCH --> STATE
```

## key 構造

```text
VRF_TABLE:<vrf_name>
```

`<vrf_name>` は CONFIG_DB `VRF` テーブルの key と同一。`Vrf` プレフィクス付きが通常（例: `VRF_TABLE:VrfRed`）。`mgmt` は例外として固定テーブル ID `6000` を使用。

## フィールド一覧

| フィールド | 型 | SAI 属性 | デフォルト | 説明 |
|-----------|----|---------|-----------|------|
| `v4` | boolean | `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE` | SAI 依存 ※1 | IPv4 管理状態 |
| `v6` | boolean | `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE` | SAI 依存 ※1 | IPv6 管理状態 |
| `src_mac` | MAC アドレス | `SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS` | SAI 依存 ※1 | 送信元 MAC |
| `ttl_action` | packet_action | `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION` | SAI 依存 ※1 | TTL=1 パケット処理 |
| `ip_opt_action` | packet_action | `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION` | SAI 依存 ※1 | IP オプション違反処理 |
| `l3_mc_action` | packet_action | `SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION` | SAI 依存 ※1 | 未知 L3 マルチキャスト処理 |
| `vni` | uint32 | SAI 非直接 ※2 | `0` | L3 VNI マッピング |
| `fallback` | boolean | なし ※3 | (dead) | フォールバック（未実装） |
| `mgmtVrfEnabled` | boolean | なし ※4 | (ignored) | mgmt VRF 有効フラグ |
| `in_band_mgmt_enabled` | boolean | なし ※4 | (ignored) | in-band mgmt 有効フラグ |

- ※1 フィールド省略時は SAI `create_virtual_router()` の attrs リストに含まれない → SAI / ASIC 側デフォルト値が適用される
- ※2 `vni` は SAI 属性に直接マップされず `updateVrfVNIMap()` 経由で VXLAN VRF マップに書く (vrforch.cpp:114)
- ※3 `fallback` は `vrforch.h` の `request_description` に宣言のみ、`addOperation` にハンドラなし → `SWSS_LOG_ERROR("Logic error: Unknown attribute")` で破棄 (dead field)
- ※4 `mgmtVrfEnabled` / `in_band_mgmt_enabled` は `SWSS_LOG_INFO("MGMT VRF field: %s ignored")` で明示的に無視 (vrforch.cpp:74-78)

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動 (Phase A)

> 調査日 2026-05-15。ソース: `sonic-swss/orchagent/vrforch.cpp`, `sonic-swss/orchagent/vrforch.h`, `sonic-swss/cfgmgr/vrfmgr.cpp`, `sonic-swss-common/common/schema.h`

### v4 / v6 — SAI attrs 省略による ASIC 依存デフォルト

`v4`/`v6` フィールドが `APP_VRF_TABLE` に存在しない場合、VRFOrch は `attrs` ベクタに追加しない。`create_virtual_router()` 呼び出し時に `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE` / `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE` が省略される → SAI の実装依存デフォルト（多くの実装で `true`）が適用される。

```cpp
// vrforch.cpp:39-47
if (name == "v4")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE;
    attr.value.booldata = request.getAttrBool("v4");
}
else if (name == "v6")
{
    attr.id = SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE;
    attr.value.booldata = request.getAttrBool("v6");
}
```

これらフィールドは CONFIG_DB `sonic-vrf.yang` に定義がなく、通常の `config vrf add` では APP_VRF_TABLE に書かれない。VNETOrch が APP_DB に直接書き込む経路でのみ到達可能。

### vni — 実装デフォルト 0 (VNI なし)

```cpp
// vrforch.cpp:30
uint32_t vni = 0;
// vrforch.cpp:69-73
else if (name == "vni")
{
    vni = static_cast<uint32_t>(request.getAttrUint(name));
    continue;  // SAI attrs には追加しない
}
```

省略時は `vni = 0` のまま。`updateVrfVNIMap()` が `vni != 0` の場合のみ VXLAN マッピングを実行する (vrforch.cpp:111-119)。これは CONFIG_DB `sonic-vrf.yang` の `default 0` と一致する。

### fallback — dead field (silent discard)

`vrforch.h:34` で `{ "fallback", REQ_T_BOOL }` として `request_description` に宣言されているが、`vrforch.cpp::addOperation` に対応する分岐が存在しない。`else` ブランチに落ちて `SWSS_LOG_ERROR("Logic error: Unknown attribute: %s", name.c_str())` が出力され、フィールドは破棄される。

- SAI への影響: なし
- カーネルへの影響: なし（VRFOrch は Linux ルーティングを直接操作しない）
- **`fallback=true` に設定しても実際のフォールバック動作は発生しない**

### mgmtVrfEnabled / in_band_mgmt_enabled — 明示的 ignore

```cpp
// vrforch.cpp:74-78
else if ((name == "mgmtVrfEnabled") || (name == "in_band_mgmt_enabled"))
{
    SWSS_LOG_INFO("MGMT VRF field: %s ignored", name.c_str());
    continue;
}
```

SAI 処理に一切渡されない。mgmt VRF の SAI 表現は `gVirtualRouterId`（デフォルトルータ OID）で代用される。

### Linux ルーティングテーブル ID — CONFIG_DB 非表現のハードコード

vrfmgrd が管理するテーブル ID 割り当てルール（CONFIG_DB `VRF` テーブルのフィールドには出現しない）:

| 定数 | 値 | 意味 |
|------|----|------|
| `VRF_TABLE_START` | `1001` | 通常 VRF テーブル ID 開始 (vrfmgr.cpp:12) |
| `VRF_TABLE_END` | `5097` | 通常 VRF テーブル ID 終端 (vrfmgr.cpp:13) |
| `TABLE_LOCAL_PREF` | `1001` | `ip rule` local テーブル移動先 preference (vrfmgr.cpp:14) |
| `MGMT_VRF_TABLE_ID` | `6000` | `mgmt` VRF 専用固定テーブル ID (vrfmgr.cpp:15) |

最大同時 VRF 数は **4096** (5097 − 1001)。プール枯渇時は `getFreeTable()` が `0` を返し `ip link add` が失敗する。

### mgmt VRF 特例

`vrfName == "mgmt"` の場合:

- `ip link add mgmt type vrf table ...` は実行しない（hostcfgd 側で初期化済み前提）
- テーブル ID は `MGMT_VRF_TABLE_ID = 6000` を固定使用 (vrfmgr.cpp:180-183)
- APP_VRF_TABLE への書き込みは通常 VRF と同様に行われ、VRFOrch が SAI VR を作成する

### STATE_DB 書き戻し (orchagent → vrfmgrd 連携)

VRFOrch は VRF 作成/更新成功後に `STATE_VRF_OBJECT_TABLE|<vrf_name>` に `"state"="ok"` を書く (vrforch.cpp:120, 150)。削除時は `m_stateVrfObjectTable.del(vrf_name)` (vrforch.cpp:193)。vrfmgrd は `isVrfObjExist()` でこのフラグを参照し、VRF 削除の遅延タイミングを制御する。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`vrfmgrd` (`sonic-swss/cfgmgr/vrfmgr.cpp`) および `VRFOrch::addOperation` / `VRFOrch::delOperation` (`sonic-swss/orchagent/vrforch.cpp`) を精読した結果、以下の順序依存・タイミング依存を検出した。

### SET（VRF 追加）の先行必須条件

| # | 先行条件 | 方向 | 違反時の挙動 |
|---|----------|------|-------------|
| 1 | Linux VRF デバイス作成（vrfmgrd `setLink()`） | **強制先行** | VRF プールが空 (`getFreeTable()` → `0`) の場合 `ip link add` が失敗しエントリが APPL_DB に書かれない (`vrfmgr.cpp:185-188`) |
| 2 | EVPN VTEP（`VXLAN_EVPN_NVO` テーブル）— `vni` フィールドが非ゼロの VRF のみ | **強制先行** | `updateVrfVNIMap()` が `evpn_orch->getEVPNVtep()` null を検出して `false` を返し、`addOperation` が `false` でリターン → Consumer がエントリを `m_toSync` に残して次ループで再試行 (`vrforch.cpp:225-230`) |
| 3 | APPL_DB VRF_TABLE エントリ到着（VRFOrch の前提）— vrfmgrd が先に書いていること | 自然順（vrfmgrd → APPL_DB → VRFOrch） | `VRFOrch::addOperation` は APPL_DB の Consumer イベントで駆動されるため、vrfmgrd が `m_appVrfTableProducer.set()` を呼ぶまで SAI 作成は発生しない (`vrfmgr.cpp:303`) |

**推奨書込み順序（VNI 付き VRF の場合）**:

```text
# 1. VXLAN NVO/VTEP を先に作成
SET CONFIG_DB VXLAN_EVPN_NVO|nvo1  ...
# 2. VRF を追加（vrfmgrd が Linux link 作成 → APPL_DB 書込み → VRFOrch が SAI VR 作成）
SET CONFIG_DB VRF|VrfRed  vni=10000
# 3. VRFOrch が STATE_VRF_OBJECT_TABLE|VrfRed  state=ok を書く
```

VNI なし VRF は手順 1 が不要。

### DEL（VRF 削除）の先行必須条件

| # | 先行条件 | 方向 | 違反時の挙動 |
|---|----------|------|-------------|
| 1 | VRF を参照する INTERFACE / ROUTE の削除 | **強制先行** | `VRFOrch::delOperation` は `vrf_table_[vrf_name].ref_count != 0` を検出して `false` をリターン → Consumer が再キューし、参照カウントが 0 になるまで無限ポーリング (`vrforch.cpp:169-170`) |
| 2 | VRFOrch による `STATE_VRF_OBJECT_TABLE` エントリ削除 | **強制先行** | vrfmgrd DEL ハンドラは `isVrfObjExist()` が真の間、`it++; continue` で DEL を保留し続ける。VRFOrch が SAI `remove_virtual_router()` 成功後に `m_stateVrfObjectTable.del()` を呼んだ後にのみ `ip link del` が実行される (`vrfmgr.cpp:331-346`, `vrforch.cpp:193`) |

**安全な削除手順**:

```text
# 1. VRF 配下の全 INTERFACE を削除（ref_count のデクリメント）
DEL CONFIG_DB INTERFACE|Ethernet0|10.0.0.1/31  (VRFOrch が decreaseVrfRefCount を呼ぶまで待機)
# 2. VRF を削除
DEL CONFIG_DB VRF|VrfRed
# → vrfmgrd が APPL_DB DEL → VRFOrch が SAI DEL → STATE_VRF_OBJECT_TABLE クリア → vrfmgrd が ip link del
```

### 自動調停の仕組み

- **VNI 解決待ち（doTask 再試行）**: `addOperation` が `false` を返すと `Orch2::doTask()` が `m_toSync` にエントリを残したまま次ループへ。EVPN VTEP 作成後の次スケジュールで自動再評価される。
- **ref_count ガード（delOperation 再試行）**: `delOperation` が `false` を返した場合も同様。参照 Orch（RouteOrch / IntfsOrch 等）が `decreaseVrfRefCount()` を呼び ref_count が 0 になるまでポーリングを繰り返す。
- **VNI マップ整合性**: VNI 変更 (SET) 時は `updateVrfVNIMap()` が新旧 VNI を比較し差分のみ更新するため、同一 VNI での再投入は冪等 (`vrforch.cpp:212`)。

<!-- /ordering -->

## 例外条件・特殊挙動

- **VRF 削除タイミング**: VRFOrch が STATE_VRF_OBJECT_TABLE のエントリを削除するまで vrfmgrd は `ip link del` を遅延する。INTERFACE / ROUTE テーブルが VRF を参照中の場合は `ref_count` が非ゼロで `delOperation` が `false` を返して再キュー。
- **VXLAN EVPN 未設定時の VNI**: `evpn_orch->getEVPNVtep()` が null を返す場合 `updateVrfVNIMap()` は `false` を返して VRF 作成を中断する (vrforch.cpp:228-230)。VNI 付き VRF は EVPN VTEP が先に設定されている必要がある。
- **VNI の SAI 非直接性**: VNI は `sai_virtual_router_api` には渡されない。VXLAN Tunnel Orch が VNI-VRF マッピングを別途管理する。

## 関連ページ

- [CONFIG_DB VRF テーブル](./vrf.md)
- [CONFIG_DB MGMT_VRF_CONFIG](./mgmt-vrf-config.md)
- [CONFIG_DB STATE_VRF](./state-vrf.md)
- [YANG: sonic-vrf](../yang/sonic-vrf.md)
- [CLI: config vrf](../cli/config-vrf.md)

## 引用元

[^1]: `sonic-swss/orchagent/vrforch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/vrforch.cpp>
[^2]: `sonic-swss/orchagent/vrforch.h` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/vrforch.h>
[^3]: `sonic-swss/cfgmgr/vrfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vrfmgr.cpp>
[^4]: `sonic-swss-common/common/schema.h` <https://github.com/sonic-net/sonic-swss-common/blob/master/common/schema.h>
