# mclag-domain — Phase H (プラットフォーム差) 中間調査

対象: `docs/reference/config-db/mclag-domain.md`
書込主体: `MlagOrch` (sonic-swss/orchagent/mlagorch.cpp) + `mclagsyncd` (sonic-swss/mclagsyncd/mclaglink.cpp)

## 1. MlagOrch 自体のプラットフォーム差（orchagent 側）

`mlagorch.cpp` は **platform 識別ロジックを一切持たない**。

- `getenv("platform")` / `m_platform` / ASIC 種別チェックは全行スキャンで 0 件（copyright 行の "Broadcom" 社名のみ）。
- `addIslInterface()` / `addMlagInterface()` / `doTask()` はすべて ASIC 非依存の Subject 通知だけで完結する。
- SAI API 呼び出しが無い（`sai_bridge_port_api` / `sai_lag_api` 等の直接呼び出し無し）。ASIC への反映は Subject を受けた `FdbOrch` / `PortsOrch` が担う。

evidence: `mlagorch.cpp:1-250` 全行精査（2026-05-16）

### MlagOrch から SAI への間接経路

| Subject | 受信側 Orch | 下流 SAI | platform 差 |
|---|---|---|---|
| `SUBJECT_TYPE_MLAG_ISL_CHANGE` | `FdbOrch` (ISL 判定更新) | `sai_fdb_api` (FDB flush 制御) | なし |
| `SUBJECT_TYPE_MLAG_INTF_CHANGE` | `FdbOrch` (MLAG ポートリスト更新) | `sai_fdb_api` (FDB flush スキップ) | なし |

## 2. SAI bridge_port capability と MCLAG の関係

`mclagsyncd` の `getBridgePortIdToAttrPortIdMap()` (`mclaglink.cpp:74-99`) が ASIC_DB の `SAI_OBJECT_TYPE_BRIDGE_PORT:*` を走査し、**`SAI_BRIDGE_PORT_ATTR_PORT_ID` → フォールバック `SAI_BRIDGE_PORT_ATTR_TUNNEL_ID`** の順でポート解決を試みる。

```cpp
// mclaglink.cpp:87-92
auto attr_port_id = hash.find("SAI_BRIDGE_PORT_ATTR_PORT_ID");
if (attr_port_id == hash.end())
{
    attr_port_id = hash.find("SAI_BRIDGE_PORT_ATTR_TUNNEL_ID");
    if (attr_port_id == hash.end())
        continue;
}
```

| ASIC ファミリ | bridge_port 実装 | FDB ポート解決 |
|---|---|---|
| Broadcom (Tomahawk/Trident) | `SAI_BRIDGE_PORT_ATTR_PORT_ID` を常に持つ | 一次検索で解決 |
| Mellanox Spectrum | `SAI_BRIDGE_PORT_ATTR_PORT_ID` あり | 一次検索で解決 |
| VxLAN トンネル系 | `SAI_BRIDGE_PORT_ATTR_TUNNEL_ID` を持つケース | フォールバックで解決 |
| capability 未実装 | 両 attr 不在 → `continue` でスキップ | FDB エントリが APPL_DB に伝播しない |

この差は `ASIC_DB → APPL_DB FDB_TABLE` の伝播精度に直接影響するが、CONFIG_DB の `MCLAG_DOMAIN` / `MCLAG_INTERFACE` フィールドとは独立している（フィールド値の変更で回避不能）。

## 3. port isolation 分岐（mclagsyncd 側）

`mclagsyncd::setPortIsolate()` (`mclaglink.cpp:190-378`) は **環境変数 `platform`** (`asic_type`) を基に、APPL_DB 書込先を 2 経路に分岐させる。この分岐は CONFIG_DB の `MCLAG_DOMAIN` エントリが存在する限り常に発動する。

| `platform` 値 | APPL_DB 書込先 | 除外ポート種別 |
|---|---|---|
| `broadcom` / `barefoot` / `centec` / `clounix` / `marvell-prestera` / `marvell-teralynx` | `ISOLATION_GROUP_TABLE\|MCLAG_ISO_GRP` (TYPE=bridge-port) | `Ethernet` 系を MEMBERS から除外 |
| `mellanox` / `vs` / その他未定義 | `ACL_TABLE_TABLE\|mclag` + `ACL_RULE_TABLE\|mclag:mclag` (type=L3, PACKET_ACTION=DROP) | `PortChannel` 系を OUT_PORTS から除外 |

isolation グループ削除の挙動差:

| 条件 | `broadcom` 等 (ISOLATION_GROUP 経路) | `mellanox` 等 (ACL fallback) |
|---|---|---|
| ICCP up + リモート全 MLAG I/F down | MEMBERS を空文字にしてエントリ **保持** | — |
| ICCP down | `ISOLATION_GROUP_TABLE\|MCLAG_ISO_GRP` を **DEL** | `ACL_TABLE_TABLE\|mclag` を **DEL** |
| dst port が空 (op_len==0) かつ ICCP up | MEMBERS 空で保持 (`mclaglink.cpp:235-246`) | `ACL_TABLE_TABLE\|mclag` DEL (`mclaglink.cpp:314-319`) |

evidence: `mclaglink.cpp:190-378`, `mclaglink.h:54-59`

## 4. Mellanox / Broadcom MCLAG 対応差まとめ

| 観点 | Broadcom (Tomahawk 等) | Mellanox (Spectrum 等) |
|---|---|---|
| port isolation 実装 | `SAI_OBJECT_TYPE_ISOLATION_GROUP` (SAI native) | ACL (L3 type, PACKET_ACTION=DROP) |
| APPL_DB リソース消費 | `ISOLATION_GROUP_TABLE` 1 エントリ | `ACL_TABLE_TABLE` 1 テーブル + `ACL_RULE_TABLE` 1 ルール（L3 ACL リソース消費） |
| MlagOrch / CONFIG_DB フィールド | 同一 | 同一 |
| `SAI_BRIDGE_PORT_ATTR_PORT_ID` | あり (一次解決) | あり (一次解決) |
| FDB 伝播 | 同一 | 同一 |

## 5. kernel bridge との連携差

MCLAG は `iccpd` が kernel bridge (`brX` / VLAN-aware bridge) を **直接操作しない**設計。FDB 同期は `APPL_DB FDB_TABLE` → `orchagent fdborch` → `sai_fdb_api` 経路で ASIC に書き込む。

- Mellanox Spectrum: kernel bridge FDB と SAI FDB が分離運用される。`fdbsyncd` が netlink で kernel bridge FDB を監視し `APPL_DB FDB_TABLE` に反映。MlagOrch からの `SUBJECT_TYPE_MLAG_ISL_CHANGE` が FdbOrch の ISL 判定を更新し、kernel FDB 変化の SAI 反映可否を制御する。
- Broadcom: kernel bridge と SAI FDB の整合は `fdbsyncd` が担う点は同様。差分はほぼなし。

evidence: `fdborch.cpp:1209-1212, 1665-1670`, `mlagorch.cpp:156-232`

## 6. 結論

| 観点 | platform 差 |
|---|---|
| `MlagOrch` (CONFIG_DB → orchagent) | **差なし**。ASIC 識別コードは 0 件 |
| `getBridgePortIdToAttrPortIdMap()` | `SAI_BRIDGE_PORT_ATTR_TUNNEL_ID` フォールバックあり（VxLAN トンネル系で差が出る可能性） |
| `setPortIsolate()` (port isolation 分岐) | `broadcom`/`barefoot`/`centec`/`clounix`/`marvell-*` → `ISOLATION_GROUP_TABLE`、それ以外 (`mellanox` 等) → ACL fallback |
| kernel bridge 連携 | 全プラットフォーム共通 (`fdbsyncd` 経由) |
| CONFIG_DB `MCLAG_DOMAIN` フィールド値 | 全プラットフォーム共通（platform 固有フィールドなし） |

調査範囲: `sonic-swss/orchagent/mlagorch.cpp`, `sonic-swss/mclagsyncd/mclaglink.cpp`, `sonic-swss/mclagsyncd/mclaglink.h`, `sonic-swss/orchagent/fdborch.cpp`
