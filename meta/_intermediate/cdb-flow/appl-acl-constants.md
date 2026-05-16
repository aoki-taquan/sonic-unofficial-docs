# APPL_DB ACL — Phase E: ハードコード定数調査

`docs/reference/config-db/appl-acl.md` 用の Phase E（ハードコード定数）一次調査メモ。APPL_DB の `ACL_TABLE_TABLE` / `ACL_TABLE_TYPE_TABLE` / `ACL_RULE_TABLE` は `AclOrch::doTask()`（`aclorch.cpp:4272-4299`）で CONFIG_DB 版と同一ハンドラに合流するため、ハードコード定数も大部分が共通する。本メモは APPL_DB 経路で実際に観測される定数のみを抽出する。

## 対象ファイル

- `sonic-swss/orchagent/aclorch.h`
- `sonic-swss/orchagent/aclorch.cpp`
- `sonic-swss/orchagent/acltable.h`
- `sonic-swss/orchagent/tunneltermhelper.h` (vnetorch が参照する派生定数)

---

## 1. SAI priority range（起動時動的取得 + フォールバック）

`AclRule` クラスの static メンバとして `m_minPriority` / `m_maxPriority` を持つ（`aclorch.h:376-377`）。初期値は **`0` / `0`**（`aclorch.cpp:22-23`）で、`AclOrch::init()` から `SAI_SWITCH_ATTR_ACL_ENTRY_MINIMUM_PRIORITY` / `MAXIMUM_PRIORITY` を取得して上書きする（`aclorch.cpp:3687-3699`）。

| 定数 / 属性 | 値 | 用途 | ソース |
|---|---|---|---|
| `AclRule::m_minPriority` 初期値 | `0` (static) | DPU / 取得失敗時のフォールバック | `aclorch.cpp:22` |
| `AclRule::m_maxPriority` 初期値 | `0` (static) | 同上 | `aclorch.cpp:23` |
| `SAI_SWITCH_ATTR_ACL_ENTRY_MINIMUM_PRIORITY` | ASIC 依存 (動的取得) | `m_minPriority` 上書き | `aclorch.cpp:3689,3697` |
| `SAI_SWITCH_ATTR_ACL_ENTRY_MAXIMUM_PRIORITY` | ASIC 依存 (動的取得) | `m_maxPriority` 上書き | `aclorch.cpp:3690,3697` |
| DPU 分岐ガード | `gMySwitchType != "dpu"` | DPU では priority 範囲取得をスキップ → 0/0 のまま | `aclorch.cpp:3686` |

`setPriority()` の範囲チェック（`aclorch.cpp:1654-1661`）:

```cpp
if (!(value >= m_minPriority && value <= m_maxPriority))
{
    SWSS_LOG_ERROR("Priority value %d is not in range [%d, %d]",
        value, m_minPriority, m_maxPriority);
    return false;
}
```

DPU 側 orchagent では SAI 取得が走らないため、`m_minPriority = m_maxPriority = 0` のままとなり、`PRIORITY != 0` を全て弾く挙動になる（Phase H と整合）。

---

## 2. STAGE 文字列リテラル / enum 値

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `STAGE_INGRESS` | `"INGRESS"` | `ACL_TABLE.stage` 入力文字列 | `acltable.h:22` |
| `STAGE_EGRESS` | `"EGRESS"` | 同上 | `acltable.h:23` |
| `STAGE_PRE_INGRESS` | `"PRE_INGRESS"` | 同上 | `acltable.h:24` |
| `ACL_STAGE_INGRESS` | enum 値 (`acl_stage_type_t`) | C++ 内表現 | `aclorch.h` |
| `AclTable::stage` 初期値 | `ACL_STAGE_INGRESS` | `STAGE` 未指定時の C++ default | `aclorch.h:543` |

`aclStageLookUp` テーブル（`aclorch.cpp:165-168`）は文字列 → enum マッピングを定義し、`STAGE_INGRESS` / `STAGE_EGRESS` の 2 つのみを登録する（`STAGE_PRE_INGRESS` は別経路）。APPL_DB 書込み元はいずれも `STAGE_INGRESS` 固定または stage 省略（C++ default に依存）。

---

## 3. PACKET_ACTION 文字列リテラル

`aclorch.h:83-89` に `#define` で定義される。`aclPacketActionLookup`（`aclorch.cpp:144-148`）が SAI enum へマッピングするのは 3 種のみ。

| 定数 | 値 | SAI マッピング | ソース |
|---|---|---|---|
| `PACKET_ACTION_FORWARD` | `"FORWARD"` | `SAI_PACKET_ACTION_FORWARD` | `aclorch.h:83` / `aclorch.cpp:145` |
| `PACKET_ACTION_DROP` | `"DROP"` | `SAI_PACKET_ACTION_DROP` | `aclorch.h:84` / `aclorch.cpp:146` |
| `PACKET_ACTION_COPY` | `"COPY"` | `SAI_PACKET_ACTION_COPY` | `aclorch.h:85` / `aclorch.cpp:147` |
| `PACKET_ACTION_REDIRECT` | `"REDIRECT"` | (別経路で `ACTION_REDIRECT_ACTION` 経由処理) | `aclorch.h:86` |
| `PACKET_ACTION_DO_NOT_NAT` | `"DO_NOT_NAT"` | (NAT orch 連携) | `aclorch.h:87` |
| `PACKET_ACTION_DISABLE_TRIM` | `"DISABLE_TRIM"` | (Trim 連携) | `aclorch.h:88` |

mclagsyncd は `PACKET_ACTION_DROP` を文字列リテラル `"DROP"` で書き込む（`mclaglink.cpp:343-372`）。APPL_DB に `PACKET_ACTION` 自体のコード由来 default は無く、書き込み側が明示指定する必要がある（指定しない場合は SAI ACL entry が action 無しで作られ、リソース枯渇等の二次失敗の原因になる）。

---

## 4. TCP プロトコル番号（自動補完用ハードコード）

`aclorch.cpp:54`:

```cpp
const int TCP_PROTOCOL_NUM = 6; // TCP protocol number
```

`TCP_FLAGS` match が指定されていて `IP_PROTOCOL` / `NEXT_HEADER` が未指定のとき、orchagent が `MATCH_IP_PROTOCOL` (IPv4) または `MATCH_NEXT_HEADER` (IPv6) に **`"6"`** を自動補完する（`aclorch.cpp:5632-5654`）。APPL_DB / CONFIG_DB 双方で発火する。

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `TCP_PROTOCOL_NUM` | `6` | TCP_FLAGS 指定時の IP_PROTOCOL / NEXT_HEADER 自動補完値 | `aclorch.cpp:54,5645` |

---

## 5. vnetorch 由来の固定 PRIORITY（書込み側ハードコード）

vnetorch は VNET tunnel termination ACL rule の `PRIORITY` を固定値で APPL_DB に書き込む。

| 定数 | 値 | 用途 | ソース |
|---|---|---|---|
| `VNET_TUNNEL_TERM_ACL_BASE_PRIORITY` | `9998` | vnetorch の `ACL_RULE_TABLE.PRIORITY` 固定書込み値 | `tunneltermhelper.h:14` / `vnetorch.cpp:3827` |
| `VNET_TUNNEL_TERM_ACL_TABLE` | `"VNET_LOCAL_ENDPOINT"` | vnetorch の `ACL_TABLE_TABLE` key 固定値 | `tunneltermhelper.h:13` / `vnetorch.cpp:3797` |

`9998` は SAI から取得される `m_minPriority` / `m_maxPriority` 範囲内であることを暗黙前提とする。一般的な Broadcom XGS / Marvell では `[0, 999999]` 等のレンジ内に収まるが、DPU では `0/0` フォールバックのため範囲外となる（Phase H 既掲）。

---

## 6. 書込み側 STAGE 固定リテラル

vnetorch / dashenifwdorch は `ACL_TABLE_STAGE` フィールドに **`STAGE_INGRESS` = `"INGRESS"`** を固定で書き込む。

| 書込み元 | 書込み値 | ソース |
|---|---|---|
| vnetorch | `STAGE_INGRESS` | `vnetorch.cpp:3793` |
| dashenifwdorch | `STAGE_INGRESS` | `dashenifwdorch.cpp:637` |
| mclagsyncd | （書き込まず C++ default `ACL_STAGE_INGRESS` に依存） | `mclaglink.cpp:325-336` |

APPL_DB 書込み元のいずれも `STAGE_EGRESS` / `STAGE_PRE_INGRESS` を出さないため、egress / pre-ingress 経路は APPL_DB では発火しない。

---

## 7. mclagsyncd 由来の文字列リテラル（APPL_DB ACL）

mclagsyncd フォールバック ACL（`mclaglink.cpp:325-373`）で APPL_DB へ書き込まれる固定文字列。

| 文字列 | 用途 | ソース |
|---|---|---|
| `"L3"` | `ACL_TABLE_TABLE.type` 固定値 | `mclaglink.cpp:327` |
| `"ANY"` | `ACL_RULE_TABLE.IP_TYPE` 固定値 (`IP_TYPE_ANY`) | `mclaglink.cpp:343` |
| `"DROP"` | `ACL_RULE_TABLE.PACKET_ACTION` 固定値 (`PACKET_ACTION_DROP`) | `mclaglink.cpp:347` |
| `"Mclag egress port isolate acl"` | `ACL_TABLE_TABLE.policy_desc` 固定説明 | `mclaglink.cpp:325` |

---

## 8. テーブル名定数（schema.h）

`sonic-swss-common/common/schema.h:94-96`:

| 定数 | 値 | 用途 |
|---|---|---|
| `APP_ACL_TABLE_TABLE_NAME` | `"ACL_TABLE_TABLE"` | APPL_DB テーブル名 |
| `APP_ACL_TABLE_TYPE_TABLE_NAME` | `"ACL_TABLE_TYPE_TABLE"` | 同上 |
| `APP_ACL_RULE_TABLE_NAME` | `"ACL_RULE_TABLE"` | 同上 |

`AclOrch::doTask()` は CONFIG_DB 側定数（`CFG_ACL_TABLE_TABLE_NAME` 等）と OR で分岐し同一ハンドラへ流す（`aclorch.cpp:4283-4293`）。

---

## 特記事項

1. **priority 範囲は ASIC 動的取得 + DPU フォールバック `0/0`**: 静的なハードコード上下限は存在せず、起動時に SAI から取得する。DPU 側（`gMySwitchType == "dpu"`）はその取得自体がスキップされ初期値の `0/0` のまま動作する。
2. **TCP_FLAGS 自動補完値 `6` はリテラルハードコード**: `TCP_PROTOCOL_NUM = 6`（`aclorch.cpp:54`）。L4 プロトコル番号としては正規だが、APPL_DB 経路でも同じく自動付与される。
3. **APPL_DB 経路は INGRESS のみ**: 全書込み元（vnetorch / mclagsyncd / dashenifwdorch）が INGRESS 固定。EGRESS / PRE_INGRESS リテラルは APPL_DB 経路では実発火しない。
4. **`PACKET_ACTION` の APPL_DB default はなし**: 書込み側が `"DROP"` / `"FORWARD"` 等を明示指定する。指定漏れは SAI action 無しエントリとなり実害になる。
5. **vnetorch の `9998` 固定 priority** が SAI 範囲を超えれば rule 不採用となる（DPU 等で発火）。

---

## 出典

- `sonic-swss/orchagent/aclorch.h` lines 26-45, 83-89, 321-322, 376-377, 543
- `sonic-swss/orchagent/aclorch.cpp` lines 22-23, 54, 144-168, 1654-1661, 3686-3710, 5632-5654
- `sonic-swss/orchagent/acltable.h` lines 22-24
- `sonic-swss/orchagent/tunneltermhelper.h` lines 13-14
- `sonic-swss/orchagent/vnetorch.cpp` lines 3793, 3797, 3827
- `sonic-swss/mclagsyncd/mclaglink.cpp` lines 325-372
- `sonic-swss/orchagent/dash/dashenifwdorch.cpp` line 637
- `sonic-swss-common/common/schema.h` lines 94-96
