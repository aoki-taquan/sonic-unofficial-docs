# stp-iccp — Phase H プラットフォーム差異調査

## 調査対象

STP/ICCP 連携（iccpd + mclagsyncd）におけるプラットフォーム固有の挙動差異。

## コード根拠

### 1. mclagsyncd: `setPortIsolate()` の 2 経路分岐 (`mclaglink.cpp:190-282`)

iccpd から `MCLAG_MSG_TYPE_SET_PORT_ISOLATE` を受信した mclagsyncd は、`getenv("platform")` 文字列を以下のホワイトリストと照合する:

```cpp
// mclaglink.h:54-59
#define BRCM_PLATFORM_SUBSTRING  "broadcom"
#define BFN_PLATFORM_SUBSTRING   "barefoot"
#define CTC_PLATFORM_SUBSTRING   "centec"
#define CLX_PLATFORM_SUBSTRING   "clounix"
#define MRVL_PRST_PLATFORM_SUBSTRING "marvell-prestera"
#define MRVL_TL_PLATFORM_SUBSTRING   "marvell-teralynx"

// mclaglink.cpp:192-202
static const unordered_set<string> supported {
    BRCM_PLATFORM_SUBSTRING,
    BFN_PLATFORM_SUBSTRING,
    CTC_PLATFORM_SUBSTRING,
    CLX_PLATFORM_SUBSTRING,
    MRVL_PRST_PLATFORM_SUBSTRING,
    MRVL_TL_PLATFORM_SUBSTRING
};
const char *platform = getenv("platform");
if (platform != nullptr && supported.find(string(platform)) != supported.end())
{
    // 経路 A: Isolation Group (APPL_DB ISOLATION_GROUP_TABLE)
    ...
    p_iso_grp_tbl->set("MCLAG_ISO_GRP", fvts);
}
else
{
    // 経路 B: ACL ベース (APPL_DB ACL_TABLE / ACL_RULE_TABLE)
    ...
    p_acl_table_tbl->set(acl_name, acl_attrs);
}
```

#### 経路 A: Isolation Group 方式（Broadcom / Barefoot / Centec / Clounix / Marvell）

- `APPL_DB ISOLATION_GROUP_TABLE|MCLAG_ISO_GRP` にエントリを SET/DEL
- フィールド: `DESCRIPTION`, `TYPE`=`"bridge-port"`, `PORTS`（src PortChannel）, `MEMBERS`（dst ports カンマ区切り）
- `isolate_dst_port` から `Ethernet` プレフィックスのインターフェースは **除外** (`mclaglink.cpp:258-261`)
  → PortChannel のみを members に含める
- dst が空（全リモートリンクダウン）の場合は `del("MCLAG_ISO_GRP")` で削除

#### 経路 B: ACL 方式（Mellanox / VS / その他）

- `APPL_DB ACL_TABLE_TABLE|mclag` + `APPL_DB ACL_RULE_TABLE|mclag:mclag` にエントリを SET/DEL
- ACL テーブルは最初の SET 時のみ作成 (`acl_table_is_added` フラグ)
- isolate_dst_port が空の場合: ACL テーブルごと DEL (`p_acl_table_tbl->del(acl_name)`)
- ACL を経由してトラフィック分離を実装

### 2. iccpd 自体のプラットフォーム差異

`iccpd` (`docker-iccpd`) のコアロジック (`iccp_csm.c`, `mlacp_fsm.c`, `mlacp_link_handler.c`, `scheduler.c`) には `#ifdef` や `getenv("platform")` によるプラットフォーム分岐は存在しない。

- STP ロール決定アルゴリズム (`iccp_csm_stp_role_count()`) は全プラットフォーム共通
- Standby ノードの MAC 書き換え (`mlacp_fix_bridge_mac()`) は全プラットフォーム共通
- `TLV_T_MLACP_STP_INFO` 未サポートは全プラットフォーム共通

### 3. SmartSwitch / DPU 環境

`docker-iccpd` コンテナ自体が SmartSwitch DPU 上では起動しないため、STP/ICCP 連携機能は DPU では非適用。SmartSwitch NPU 側では通常の MCLAG として動作可能。

### 4. VS（仮想スイッチ）環境

- platform 文字列が supported セットに含まれないため **ACL 方式** にフォールバック
- `mlacp_fix_bridge_mac()` の `iccp_netlink_if_hwaddr_set()` は VS でも呼ばれるが、
  VS ではソフトウェア MAC 変更のみで実際のハードウェア操作はなし
- STP ロール決定ロジック自体は物理 ASIC と同一

## 順序制約への影響

platform による分岐は `MCLAG_MSG_TYPE_SET_PORT_ISOLATE` 受信後の DB 書き込み先のみに影響し、
STP ロール決定 (`iccp_csm_stp_role_count()`) の順序依存 (Phase B) には影響しない。

## ソース参照

- `mclaglink.cpp:190-282` — `setPortIsolate()` 2 経路分岐
- `mclaglink.h:54-59` — プラットフォームサブストリング定義
- `iccp_csm.c:845-871` — `iccp_csm_stp_role_count()` (プラットフォーム非依存)
- `iccp_netlink.c:643-676` — `mlacp_fix_bridge_mac()` (プラットフォーム非依存)
