# LOOPBACK_INTERFACE — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-swss/cfgmgr/intfmgr.cpp` L22-29, L201, L696, L772
- `sonic-swss/orchagent/intfsorch.cpp` L43-47, L1148-1165, L1167-1196, L1210-1228
- `sonic-swss/orchagent/routeorch.h` L28

調査日: 2026-05-16

---

## 1. intfmgrd — ループバック識別・MTU ハードコード (intfmgr.cpp L22-29)

| 定数名 | 値 | 型 | 定義場所 | 説明 |
|--------|----|----|---------|------|
| `LOOPBACK_PREFIX` | `"Loopback"` | `#define` | `intfmgr.cpp` L22 | ループバックインターフェース名のプレフィクス。`alias.compare(0, strlen(LOOPBACK_PREFIX), LOOPBACK_PREFIX)` で一致判定し `is_lo = true` を設定する |
| `LOOPBACK_DEFAULT_MTU_STR` | `"65536"` | `#define` (文字列) | `intfmgr.cpp` L28 | Linux dummy デバイス作成時の固定 MTU 値。`ip link add <name> mtu 65536 type dummy` として使用（L201）。CONFIG_DB に `mtu` フィールドは存在せず、この値は変更不可 |
| `DEFAULT_MTU_STR` | `9100` | `#define` (整数) | `intfmgr.cpp` L29 | 一般インターフェースのデフォルト MTU。Loopback には使用されず、Ethernet/PortChannel/VLAN 系のフォールバックとして使用 |

---

## 2. orchagent IntfsOrch — SAI 属性・タスク優先度 (intfsorch.cpp L43-47)

| 定数名 | 値 | 型 | 定義場所 | 説明 |
|--------|----|----|---------|------|
| `intfsorch_pri` | `35` | `const int` | `intfsorch.cpp` L43 | `IntfsOrch` のタスク優先度。`Orch` 基底クラスに渡され、orchagent 内の複数 Orch が同時にイベントを持つ場合の処理順序を決定する |
| `UPDATE_MAPS_SEC` | `1` | `#define` (秒) | `intfsorch.cpp` L45 | 統計マップ更新インターバル。`timespec { .tv_sec = UPDATE_MAPS_SEC }` として `addTimer` に登録される（L78）。Loopback IF の RIF 統計も同インターバルで収集される |
| `MGMT_VRF` | `"mgmt"` | `#define` (文字列) | `intfsorch.cpp` L47 | mgmt VRF 名のハードコード定数。`intfsorch` は mgmt VRF に属するインターフェースを通常ループバックと同扱いしない特殊分岐には使用しないが、同ファイル内で参照可能な定数として存在する |

---

## 3. orchagent IntfsOrch — loopback_action マッピング (intfsorch.cpp L1148-1165)

`getSaiLoopbackAction()` 内で定義される固定マップ:

| CONFIG_DB 値 | SAI 列挙値 | 説明 |
|-------------|-----------|------|
| `"drop"` | `SAI_PACKET_ACTION_DROP` | ループバックパケットをドロップ |
| `"forward"` | `SAI_PACKET_ACTION_FORWARD` | ループバックパケットを転送（デフォルト動作） |

- マップに存在しない値（例: `"punt"`）は `SWSS_LOG_WARN("Unsupported loopback action [%s]", actionStr.c_str())` を出力して `false` を返す。SAI 属性は設定されない。
- SAI 属性: `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION`

---

## 4. orchagent IntfsOrch — SAI ルータ IF タイプ (intfsorch.cpp L1210-1228)

`addRouterIntfs()` における `SAI_ROUTER_INTERFACE_ATTR_TYPE` の固定マッピング:

| Port type | SAI 値 | 説明 |
|-----------|--------|------|
| `Port::PHY` / `Port::LAG` / `Port::SYSTEM` | `SAI_ROUTER_INTERFACE_TYPE_PORT` | 物理/LAG/SYSTEM ポート |
| `Port::VLAN` | `SAI_ROUTER_INTERFACE_TYPE_VLAN` | VLAN インターフェース |
| `Port::SUBPORT` | `SAI_ROUTER_INTERFACE_TYPE_SUB_PORT` | サブインターフェース |
| その他（Loopback 相当） | — | `SWSS_LOG_ERROR("Unsupported port type: %d")` → SAI RIF 未作成 |

> **注意**: `SAI_ROUTER_INTERFACE_TYPE_LOOPBACK` は `intfsorch.cpp` 内では使用されない。SONiC の Loopback デバイスはカーネル上の Linux dummy デバイスとして実装されており、SAI RIF は Port::PHY 等のポートタイプで通常インターフェースとして作成される。`is_lo` フラグは `intfsorch` ではポートタイプ判定に直接使われない（`intfmgrd` 側の判定）。

---

## 5. sonic-utilities — CLI バリデーション定数 (config/main.py L104-108)

| 定数名 | 値 | 説明 |
|--------|-----|------|
| `CFG_LOOPBACK_PREFIX` | `"Loopback"` | CLI バリデーション用プレフィクス文字列 |
| `CFG_LOOPBACK_PREFIX_LEN` | `len("Loopback")` = 8 | プレフィクス長チェック用 |
| `CFG_LOOPBACK_NAME_TOTAL_LEN_MAX` | `11` | `Loopback<N>` の最大文字列長（`Loopback999` = 11 文字） |
| `CFG_LOOPBACK_ID_MAX_VAL` | `999` | `<N>` の最大値（0〜999） |
| `CFG_LOOPBACK_NO` | `"<0-999>"` | CLI ヘルプ表示用文字列 |

---

## 特記事項

1. **`LOOPBACK_DEFAULT_MTU_STR = "65536"` は変更不可**: CONFIG_DB の `LOOPBACK_INTERFACE` テーブルに `mtu` フィールドは存在せず、YANG モデルにも定義がない。カーネル dummy デバイスの MTU は常に 65536 で固定される。
2. **`SAI_ROUTER_INTERFACE_TYPE_LOOPBACK` は使用されない**: SONiC community 版の `intfsorch` は Loopback 専用 SAI RIF タイプを作成しない。ループバックパケットの動作制御は `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` 属性で行う。
3. **`loopback_action` のデフォルト**: CONFIG_DB に `loopback_action` が未設定の場合、SAI 属性は設定されず、SAI 実装依存のデフォルト（通常 `forward`）が維持される。

---

## 出典

- `sonic-net/sonic-swss/cfgmgr/intfmgr.cpp` L22-29, L201, L696, L772
- `sonic-net/sonic-swss/orchagent/intfsorch.cpp` L43-47, L1148-1165, L1210-1228
- `sonic-net/sonic-swss/orchagent/routeorch.h` L28
- `sonic-net/sonic-utilities/config/main.py` L104-108
