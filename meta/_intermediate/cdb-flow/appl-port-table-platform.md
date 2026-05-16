# APPL_DB PORT_TABLE — プラットフォーム差調査

Task F Phase H: `APPL_DB PORT_TABLE` の書き込みと運用に関するプラットフォーム/構成差を `sonic-swss/orchagent/portsorch.cpp`（および portsyncd / portmgrd）から精読した結果。

## 結論

**差分あり**。`PORT_TABLE` のフィールド集合と書き込み挙動は以下 3 つの軸でプラットフォーム/構成依存する:

1. **ASIC capability**（`sai_query_attribute_capability` / `SAI_PORT_ATTR_SUPPORTED_*`）— FEC override / oper FEC mode / supported speeds / supported FEC modes / autoneg cap の有無で書き込み内容（特に STATE_DB 側）が変わる
2. **`gMySwitchType`** = `voq` / `dpu` / 通常スイッチ — VOQ chassis は default VLAN 削除や system_lag 同期、DPU はバッファ/queue/FEC override 一連をスキップ
3. **`platform` 環境変数の Mellanox 判定** — LAG member の collection/distribution-only モードが Mellanox では未対応扱い

## 根拠

### 1. SAI attribute capability 動的照会

`portsorch.cpp:944-1006` で起動時に以下を `sai_query_attribute_capability(gSwitchId, SAI_OBJECT_TYPE_PORT, ...)` で問い合わせ:

- `SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` → `fec_override_sup` フラグ（`portsorch.cpp:989-1000`）
- `SAI_PORT_ATTR_OPER_PORT_FEC_MODE` → `oper_fec_sup` フラグ（`portsorch.cpp:1001-1010`）

両方とも `gMySwitchType != "dpu"` ガード下（`portsorch.cpp:987`）。**DPU では一切照会されず、FEC override / oper FEC mode の更新ロジックは無効**。

`SAI_STATUS_NOT_IMPLEMENTED` / `SAI_STATUS_NOT_SUPPORTED` を返す ASIC では:

- `getPortSupportedSpeeds()` (`portsorch.cpp:3140-3155`) → `supported_speeds` が空文字で STATE_DB に書かれる + `Unable to validate speed for port ... Not supported by platform` WARN
- `getPortSupportedFecModes()` (`portsorch.cpp:3245-3260`) → `m_portSupportedFecModes[port_id].supported = false`、`isFecModeSupported()` は常に true を返す（バリデーション skip）

これらは **STATE_DB `PORT_TABLE`** 側のフィールド (`supported_speeds` / `supported_fecs` / `oper_speed` / `oper_fec`) に影響し、APPL_DB `PORT_TABLE` 側の `speed` / `fec` パススルー値は変わらない（portsyncd 経由）。ただし FEC バリデーション skip により「ASIC が実サポートしないモード」を CONFIG_DB → APPL_DB → SAI に投げて SAI で失敗する経路が出る点には注意。

### 2. AN / LT capability（attribute と固定値）

- `initPortCapAutoNeg()` (`portsorch.cpp:3177-3196`) は `SAI_PORT_ATTR_SUPPORTED_AUTO_NEG_MODE` を get。**失敗時は `port.m_cap_an = 1` で互換性維持**（"To avoid breakage on the existing platforms, AN should be 1 by default"）
- `initPortCapLinkTraining()` (`portsorch.cpp:3197-3205`) は **SAI 照会なしで `m_cap_lt = 1` 固定** + `Unable to get LT support capability` WARN。LT 非対応 ASIC でも `link_training` を SAI に渡してエラーになる経路がある（TODO コメントあり）

### 3. `gMySwitchType` 分岐

`extern string gMySwitchType;` (`portsorch.cpp:69`) は `device.metadata` の `switch_type` を反映。3 系統に分岐:

| switch_type | 値 | 影響箇所 |
|-------------|----|----------|
| 通常 | `"switch"` / 既定 | フルパス |
| `"voq"` | VOQ chassis (Cisco-8000 等) | `removeDefaultVlanMembers()` + `removeDefaultBridgePorts()` (`portsorch.cpp:1496-1499`)、`system_lag_alias = gMyHostName + "|" + gMyAsicName + "|" + lag_alias` (`portsorch.cpp:7972`)、`voqSyncAddLag` / `voqSyncDelLag` / `voqSyncAddLagMember` / `voqSyncDelLagMember`、VOQ queue counter 強制 enable (`portsorch.cpp:8485, 8510`)、`SYSTEM_PORT` 経由の `SAI_SYSTEM_PORT_ATTR_QOS_NUMBER_OF_VOQS` / `QOS_VOQ_LIST` 取得 (`portsorch.cpp:6543-6580`) |
| `"dpu"` | DPU (SmartSwitch) | autoneg fec override / oper FEC capability 照会 skip (`portsorch.cpp:987`)、いくつかの初期化 skip (`portsorch.cpp:1043, 1056, 6449, 6589`)、postPortInit で `initializePortBufferMaximumParameters` skip + queue size 0 ガード (`portsorch.cpp:6449-6470`) |

VOQ chassis では:

- `gMyAsicName` (`portsorch.cpp:72`) で **asic 名前空間** を区別。LAG alias key が `"<hostname>|<asicname>|<lag>"` 形式になる
- APPL_DB `PORT_TABLE` 自体は **各 asic namespace の APPL_DB** に独立して書かれる。chassis 全体で集約された PORT_TABLE は存在しない（multi-asic の一般則）。`gIntfsOrch->voqSyncIntfState()` (`portsorch.cpp:9841`) は asic 間で intf 状態を同期するが、APPL_DB は asic ごとに分離

### 4. Mellanox 固有分岐

`isMlnxPlatform()` (`portsorch.cpp:689-704`) は `getenv("platform")` から `MLNX_PLATFORM_SUBSTRING` (`"mellanox"`) を strstr。`portsorch.cpp:6362-6379` に **LAG member の collection-only / distribution-only モードが Mellanox 非対応** というコメント分岐があり（実コードは順序制御のみ、setter 自体は呼ぶ）、APPL_DB の `LAG_MEMBER_TABLE` 更新順序に影響。`PORT_TABLE` 自体の field 集合は不変だが、port が LAG メンバーになる/外れる際の遷移挙動が変わる。

### 5. multi-asic（line-card / chassis）

- `portsorch.cpp:691-692` で `getenv("platform")` を取得しているが、これは Mellanox 判定専用
- multi-asic では各 asic namespace で **独立した PortsOrch インスタンス** が動き、独立した APPL_DB に `PORT_TABLE` を書く
- `gMySwitchType == "voq"` のみ asic 跨ぎの system_lag / system_port を同期。それ以外の multi-asic（multi-npu line card）は asic 間同期なし

### 6. Gearbox

既存 Phase A セクション（`docs/reference/config-db/appl-port-table.md` の defaults ブロック内 `system_oper_status / line_oper_status`）で扱い済み。`isGearboxEnabled()` (`portsorch.cpp:11220-11261`) が true の環境でのみ追加 2 フィールド。Gearbox 有無は `device.metadata` ではなく `gearbox_config.json` の存在で決まり、platform 固有ハードウェア（line-side PHY 搭載機）依存。

## 整理: APPL_DB PORT_TABLE フィールドのプラットフォーム依存度

| フィールド | 依存軸 | 効果 |
|-----------|--------|------|
| `admin_status` / `mtu` | なし | portmgrd ハードコード default |
| `speed` / `lanes` / `alias` / `index` / `description` | なし（パススルー） | CONFIG_DB から portsyncd 転写 |
| `fec` / `autoneg` / `link_training` / `adv_speeds` / `interface_type` | パススルー時はなし。**SAI 適用時に ASIC capability** | 非対応 ASIC では SAI 適用エラー（APPL_DB 値自体は残る） |
| `oper_status` | なし（SAI 通知ベース） | 全 ASIC 共通 |
| `flap_count` / `last_up_time` / `last_down_time` | なし | 全 ASIC 共通 |
| `system_oper_status` / `line_oper_status` | **Gearbox 有効環境のみ** | gearbox 非搭載 ASIC では書かれない |

## 検出した既知の罠

1. **LT capability が無条件 `m_cap_lt = 1`** — link_training を非対応 ASIC で設定すると SAI 適用時にエラー（TODO コメント済み、修正未実装）
2. **DPU では FEC override / oper FEC が一切照会されない** — STATE_DB の `oper_fec` / supported FEC は空のまま
3. **VOQ chassis では default VLAN が削除される** — bridge port を持たない設計のため、`PORT_TABLE` の `oper_status` UP 時に bridge port 関連の派生処理が走らない
4. **APPL_DB は asic namespace ごとに分離** — multi-asic chassis では「全 port をまとめて見る」テーブルは APPL_DB に存在しない（CHASSIS_APP_DB を別途参照）
