# APPL_DB VLAN_TABLE / VLAN_MEMBER_TABLE — Phase E: ハードコード定数調査

APPL_DB の `VLAN_TABLE` / `VLAN_MEMBER_TABLE` 書込み元 (`cfgmgr/vlanmgr.cpp`) と購読側 (`orchagent/portsorch.cpp` VLAN 経路) に存在するハードコード定数を列挙する。`vlan-constants.md`（CONFIG_DB 版）と共通する内容は重複するが、本ファイルは **APPL_DB 経路で実発火する** 定数に絞る。

## 対象ファイル

- `sonic-swss/cfgmgr/vlanmgr.cpp`（書込み）
- `sonic-swss/orchagent/portsorch.cpp`（VLAN 経路: `doVlanTask` / `doVlanMemberTask` / `addVlan` / `addVlanMember`）
- `sonic-swss-common/common/schema.h`（テーブル名定数）

---

## テーブル名定数（schema.h）

| 定数 | 値 | ソース |
|---|---|---|
| `APP_VLAN_TABLE_NAME` | `"VLAN_TABLE"` | `schema.h:41` |
| `APP_VLAN_MEMBER_TABLE_NAME` | `"VLAN_MEMBER_TABLE"` | `schema.h:42` |

vlanmgrd が ProducerStateTable として書込み、PortsOrch が ConsumerStateTable として購読する両端のテーブル名はここで固定。

---

## vlanmgr.cpp（#define ハードコード）

| 定数名 | 値 | 用途 / 発火箇所 | ソース |
|--------|-----|----|----|
| `DOT1Q_BRIDGE_NAME` | `"Bridge"` | Linux dot1q ブリッジデバイス名（vlanmgrd 起動時に `ip link add Bridge ... type bridge` で生成） | `vlanmgr.cpp:15,94-104` |
| `VLAN_PREFIX` | `"Vlan"` | VLAN ホストインタフェース名プレフィクス。`VLAN_TABLE` key の `<vlan_name>` 必須プレフィクス | `vlanmgr.cpp:16,128-130` |
| `LAG_PREFIX` | `"PortChannel"` | LAG ポート判定用プレフィクス（`VLAN_MEMBER` の port_alias 区別） | `vlanmgr.cpp:17` |
| `DEFAULT_VLAN_ID` | `"1"` (文字列) | Bridge 初期化時に `bridge vlan del vid 1 dev Bridge self` で IEEE 802.1Q デフォルト VLAN を削除 | `vlanmgr.cpp:18,98` |
| `DEFAULT_MTU_STR` | `"9100"` | `VLAN_TABLE.mtu` 省略時の APPL_DB 注入値。Bridge MTU 初期値にも使用 | `vlanmgr.cpp:19,96,357,428` |
| `VLAN_HLEN` | `4` | IEEE 802.1Q VLAN ヘッダ長（バイト）— 定義のみで参照箇所なし（dead define） | `vlanmgr.cpp:20` |

### Linux bridge 設定リテラル（コマンド組立文字列）

| リテラル | 値 | ソース |
|---|---|---|
| bridge vlan_filtering | `"... type bridge vlan_filtering 1"` | `vlanmgr.cpp:110` |
| bridge no_linklocal_learn | `"... type bridge no_linklocal_learn 1"` | `vlanmgr.cpp:114` |
| arp_evict_nocarrier off | `"echo 0 > /proc/sys/net/ipv4/conf/Vlan<id>/arp_evict_nocarrier"` | `vlanmgr.cpp:139` |

`vlan_filtering=1` / `no_linklocal_learn=1` / `arp_evict_nocarrier=0` は VLAN 作成時に常時設定され、ASIC ベンダー非依存・全プラットフォーム共通。

---

## portsorch.cpp（#define ハードコード — VLAN 経路）

| 定数名 | 値 | 用途 / 発火箇所 | ソース |
|--------|-----|----|----|
| `VLAN_PREFIX` | `"Vlan"` | VLAN_TABLE key プレフィクス検査 (`strncmp(key, "Vlan", 4)`) と vlan_alias 組立 | `portsorch.cpp:80,5744,5755,5869,5893,10331` |
| `DEFAULT_VLAN_ID` | `1` (int) | デフォルト VLAN ID（vlanmgr の文字列版とは別定義） | `portsorch.cpp:81` |
| `MAX_VALID_VLAN_ID` | `4094` | サブインタフェース VLAN ID 上限チェック (`if (vlan_id > MAX_VALID_VLAN_ID) ...`) | `portsorch.cpp:82,2016` |

`VLAN_PREFIX = "Vlan"` の長さ 4 を `strncmp(key, VLAN_PREFIX, 4)` で検査する箇所が `doVlanTask()` / `doVlanMemberTask()` の両入口に存在し、プレフィクスなしの key は無視される（vlanmgrd 側でも同じく破棄）。

---

## SAI 関連定数（portsorch.cpp — addVlan / addVlanMember）

### create_vlan 時の VLAN 属性デフォルト

| SAI 属性 | デフォルト値 | 用途 | ソース |
|---|---|---|---|
| `SAI_VLAN_ATTR_VLAN_ID` | key から抽出した `vlan_id` | `create_vlan()` 必須引数 | `portsorch.cpp:7389` |
| `vlan.m_vlan_info.uuc_flood_type` 初期値 | `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` | `addVlan()` 内 PortsOrch 内部状態初期化 | `portsorch.cpp:7409` |
| `vlan.m_vlan_info.bc_flood_type` 初期値 | `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` | 同上 | `portsorch.cpp:7410` |
| UUC flood control フォールバック | `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` | SAI capability 未対応時に `COMBINED` 切替を抑止 | `portsorch.cpp:7800,7814` |
| BC flood control フォールバック | `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` | 同上 | `portsorch.cpp:7835,7849` |

### create_vlan_member 時の tagging_mode マッピング

| 文字列 → SAI enum | 値 | ソース |
|---|---|---|
| 初期化値（fallback） | `SAI_VLAN_TAGGING_MODE_TAGGED` | `portsorch.cpp:7540` |
| `"untagged"` | `SAI_VLAN_TAGGING_MODE_UNTAGGED` | `portsorch.cpp:7543` |
| `"tagged"` | `SAI_VLAN_TAGGING_MODE_TAGGED` | `portsorch.cpp:7545` |
| `"priority_tagged"` | `SAI_VLAN_TAGGING_MODE_PRIORITY_TAGGED` | `portsorch.cpp:7547` |

注: `addVlanMember()` の **文字列 fallback** は同関数内 (`portsorch.cpp:5916`) で `"untagged"` だが、その後の **SAI enum 初期値** は `SAI_VLAN_TAGGING_MODE_TAGGED`（L7540）と非対称。ただし fallback パスでは文字列 `"untagged"` が先に確定するため実害なし。

### switch 起動時の default VLAN 参照

| 定数 | 用途 | ソース |
|---|---|---|
| `SAI_SWITCH_ATTR_DEFAULT_VLAN_ID` | switch 初期化時に SAI のデフォルト VLAN OID を取得 | `portsorch.cpp:1019` |

`SAI_SWITCH_ATTR_DEFAULT_VLAN_ID` で取得した VLAN は通常 VLAN 1 で、ASIC ベンダー実装依存。portsorch はこの OID を `m_defaultVlan_ObjId` に保持し、`removeDefaultVlanMembers()` 経由で member を全削除する（VLAN_TABLE / VLAN_MEMBER_TABLE には書き出さない）。

---

## VLAN ID 範囲（YANG ↔ コード）

| 制約 | 値 | 出典 |
|---|---|---|
| YANG `VLAN.vlanid` range | `2..4094` | `sonic-vlan.yang` |
| YANG `VLAN.name` pattern | `Vlan(2..4095)` 形式 | `sonic-vlan.yang` |
| portsorch サブ IF 上限 | `MAX_VALID_VLAN_ID = 4094` | `portsorch.cpp:82,2016` |
| vlanmgr 下限 | (明示チェックなし — `Vlan` プレフィクス検査と `to_string(vlan_id)` のみ) | `vlanmgr.cpp:128-130` |

YANG では `2..4094`（VLAN 1 と 4095 を除外）だが、コード側に下限 2 / 上限 4095 の数値チェックは vlanmgr に存在せず、上限 4094 のみ portsorch サブインタフェース経路で検査される。`Vlan1` は YANG pattern で弾かれ、その手前で CONFIG_DB に到達できない設計。

---

## タイミング・sleep 定数

- **vlanmgr / portsorch VLAN 経路に sleep / usleep / タイムアウト定数なし**。
- member port/LAG 未 ready 時は `task_need_retry` を返し、次 select サイクルで再試行（待機時間定数なし）。
- warm-restart 復元は `addExistingData(APP_VLAN_TABLE_NAME)` / `addExistingData(APP_VLAN_MEMBER_TABLE_NAME)` で初期化時 1 回のみ、待機定数なし。

---

## 定数サマリ

| カテゴリ | 定数 | 値 | 種別 |
|---|---|---|---|
| テーブル名 | `APP_VLAN_TABLE_NAME` / `APP_VLAN_MEMBER_TABLE_NAME` | `"VLAN_TABLE"` / `"VLAN_MEMBER_TABLE"` | `#define` (schema.h) |
| name prefix | `VLAN_PREFIX` | `"Vlan"` | `#define` (vlanmgr / portsorch 両方) |
| Linux bridge 名 | `DOT1Q_BRIDGE_NAME` | `"Bridge"` | `#define` (vlanmgr) |
| LAG 判定 prefix | `LAG_PREFIX` | `"PortChannel"` | `#define` (vlanmgr) |
| デフォルト VLAN | `DEFAULT_VLAN_ID` | `"1"` (文字列) / `1` (int) | `#define` (vlanmgr / portsorch で別定義) |
| VLAN ID 上限 | `MAX_VALID_VLAN_ID` | `4094` | `#define` (portsorch) |
| MTU default | `DEFAULT_MTU_STR` | `"9100"` | `#define` (vlanmgr) |
| 未使用 | `VLAN_HLEN` | `4` | `#define` (vlanmgr — dead) |
| SAI flood default | `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` | enum | SAI 初期化値 / フォールバック |
| SAI tagging fallback | `SAI_VLAN_TAGGING_MODE_TAGGED` | enum | C++ 変数初期化 |
| SAI switch attr | `SAI_SWITCH_ATTR_DEFAULT_VLAN_ID` | OID 取得 | switch 起動時 |

### 二重定義と非対称

1. **`DEFAULT_VLAN_ID` の二重定義**: vlanmgr `"1"` (string) と portsorch `1` (int)。用途が異なる（前者は Linux bridge コマンドリテラル、後者はサブ IF 比較）ため実害なし。
2. **`VLAN_PREFIX` の重複定義**: vlanmgr / portsorch でそれぞれ `"Vlan"` を `#define`。`strncmp(key, VLAN_PREFIX, 4)` の長さ 4 がリテラルに依存している点に注意（プレフィクスを 5 文字以上に変更すると検査ロジックが破綻）。
3. **`tagging_mode` fallback の文字列/enum 非対称**: 文字列 fallback は `"untagged"`（vlanmgr / portsorch とも）、SAI enum 初期化は `SAI_VLAN_TAGGING_MODE_TAGGED`。ただし文字列確定→enum マッピングの順序で上書きされるため実発火上は不整合なし。
4. **`DEFAULT_MTU_STR = "9100"` と YANG `mtu range 1..9216`**: コード default 9100 は YANG 範囲内。Jumbo frame 最大値 9216 までは設定可能だが、デフォルト動作は 9100 で固定。
5. **`SAI_VLAN_FLOOD_CONTROL_TYPE_ALL` の 3 箇所 fallback**: 初期化 (L7409-7410) と UUC / BC capability 不在時 (L7800,7835) と内部状態同期 (L7814,7849) で計 6 箇所登場し、未対応 ASIC では `COMBINED` への切替が抑止される。

---

## 出典

- `sonic-swss/cfgmgr/vlanmgr.cpp` lines 15-20, 94-139, 357, 428
- `sonic-swss/orchagent/portsorch.cpp` lines 80-82, 1019, 2016, 5744-5893, 7389-7849, 10331
- `sonic-swss-common/common/schema.h` lines 41-42
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang`（YANG VLAN ID 範囲）
