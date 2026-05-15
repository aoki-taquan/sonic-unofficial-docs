# ACL_TABLE ハードコード定数 (Phase E)

## ソース

- `sonic-net/sonic-swss` `orchagent/acltable.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `orchagent/aclorch.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss` `orchagent/aclorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss-common` `common/schema.h` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)

---

## フィールドキー定数 (acltable.h:12-20)

| マクロ名 | 値 (CONFIG_DB フィールド名) | 行 |
|---|---|---|
| `ACL_TABLE_DESCRIPTION` | `"POLICY_DESC"` | `acltable.h:12` |
| `ACL_TABLE_STAGE` | `"STAGE"` | `acltable.h:13` |
| `ACL_TABLE_TYPE` | `"TYPE"` | `acltable.h:14` |
| `ACL_TABLE_PORTS` | `"PORTS"` | `acltable.h:15` |
| `ACL_TABLE_SERVICES` | `"SERVICES"` | `acltable.h:16` |
| `ACL_TABLE_TYPE_MATCHES` | `"MATCHES"` | `acltable.h:18` (ACL_TABLE_TYPE サブテーブル用) |
| `ACL_TABLE_TYPE_BPOINT_TYPES` | `"BIND_POINTS"` | `acltable.h:19` (ACL_TABLE_TYPE サブテーブル用) |
| `ACL_TABLE_TYPE_ACTIONS` | `"ACTIONS"` | `acltable.h:20` (ACL_TABLE_TYPE サブテーブル用) |

---

## stage 値定数 (acltable.h:22-24)

| マクロ名 | 値 | SAI マッピング | 行 |
|---|---|---|---|
| `STAGE_INGRESS` | `"INGRESS"` | `SAI_ACL_STAGE_INGRESS` | `acltable.h:22` |
| `STAGE_EGRESS` | `"EGRESS"` | `SAI_ACL_STAGE_EGRESS` | `acltable.h:23` |
| `STAGE_PRE_INGRESS` | `"PRE_INGRESS"` | `SAI_ACL_STAGE_PRE_INGRESS` | `acltable.h:24` |

`PRE_INGRESS` は `aclStageLookup` map に含まれるが CONFIG_DB フィールド値として公式ドキュメント化されていない。`processAclTableStage()` では `INGRESS` / `EGRESS` のみ正常受理、それ以外は erase。

enum 対応: `ACL_STAGE_UNKNOWN=0`, `ACL_STAGE_INGRESS=1`, `ACL_STAGE_EGRESS=2`, `ACL_STAGE_PRE_INGRESS=3` (acltable.h:44-50)。

---

## type 値定数 (acltable.h:26-42)

| マクロ名 | 値 | 行 |
|---|---|---|
| `TABLE_TYPE_L3` | `"L3"` | `acltable.h:26` |
| `TABLE_TYPE_L3V6` | `"L3V6"` | `acltable.h:27` |
| `TABLE_TYPE_L3V4V6` | `"L3V4V6"` | `acltable.h:28` |
| `TABLE_TYPE_MIRROR` | `"MIRROR"` | `acltable.h:29` |
| `TABLE_TYPE_MIRRORV6` | `"MIRRORV6"` | `acltable.h:30` |
| `TABLE_TYPE_MIRROR_DSCP` | `"MIRROR_DSCP"` | `acltable.h:31` |
| `TABLE_TYPE_PFCWD` | `"PFCWD"` | `acltable.h:32` |
| `TABLE_TYPE_CTRLPLANE` | `"CTRLPLANE"` | `acltable.h:33` |
| `TABLE_TYPE_DTEL_FLOW_WATCHLIST` | `"DTEL_FLOW_WATCHLIST"` | `acltable.h:34` |
| `TABLE_TYPE_MCLAG` | `"MCLAG"` | `acltable.h:35` |
| `TABLE_TYPE_MUX` | `"MUX"` | `acltable.h:36` |
| `TABLE_TYPE_DROP` | `"DROP"` | `acltable.h:37` |
| `TABLE_TYPE_MARK_META` | `"MARK_META"` | `acltable.h:38` |
| `TABLE_TYPE_MARK_META_V6` | `"MARK_METAV6"` | `acltable.h:39` |
| `TABLE_TYPE_EGR_SET_DSCP` | `"EGR_SET_DSCP"` | `acltable.h:40` |
| `TABLE_TYPE_UNDERLAY_SET_DSCP` | `"UNDERLAY_SET_DSCP"` | `acltable.h:41` |
| `TABLE_TYPE_UNDERLAY_SET_DSCPV6` | `"UNDERLAY_SET_DSCPV6"` | `acltable.h:42` |

注: `DTEL_FLOW_WATCHLIST` は `TABLE_TYPE_DTEL_FLOW_WATCHLIST` として定義されているが、前ページには記載がなかった。DTelOrch が `platform==BFN|VS` のみ有効化するため、一般的ではない。

---

## バインドポイント型定数 (aclorch.h:62-63)

| マクロ名 | 値 | SAI マッピング | 行 |
|---|---|---|---|
| `BIND_POINT_TYPE_PORT` | `"PORT"` | `SAI_ACL_BIND_POINT_TYPE_PORT` | `aclorch.h:62`, `aclorch.cpp:105` |
| `BIND_POINT_TYPE_PORTCHANNEL` | `"PORTCHANNEL"` | `SAI_ACL_BIND_POINT_TYPE_LAG` | `aclorch.h:63`, `aclorch.cpp:106` |

`ACL_TABLE_TYPE.BIND_POINTS` フィールドで使われる文字列定数。`VLAN` / `SWITCH` は文字列定数マクロが存在せず、アプリケーションコードで直接 SAI 定数を使用。

---

## STATE_DB ステータス値定数 (aclorch.cpp:523-526)

| enum 値 | STATE_DB `status` 文字列 | 行 |
|---|---|---|
| `AclObjectStatus::ACTIVE` | `"Active"` | `aclorch.cpp:523` |
| `AclObjectStatus::INACTIVE` | `"Inactive"` | `aclorch.cpp:524` |
| `AclObjectStatus::PENDING_CREATION` | `"Pending creation"` | `aclorch.cpp:525` |
| `AclObjectStatus::PENDING_REMOVAL` | `"Pending removal"` | `aclorch.cpp:526` |

enum 定義: `aclorch.cpp:124`。STATUS_DB キー: `STATE_ACL_TABLE_TABLE_NAME` = `"ACL_TABLE_TABLE"` (schema.h:514)。フィールド名: ハードコード文字列 `"status"` (aclorch.cpp:6091,6105)。

---

## STATE_DB/APP_DB テーブル名定数 (schema.h)

| マクロ名 | 値 | DB | 行 |
|---|---|---|---|
| `APP_ACL_TABLE_TABLE_NAME` | `"ACL_TABLE_TABLE"` | APP_DB | `schema.h:94` |
| `APP_ACL_TABLE_TYPE_TABLE_NAME` | `"ACL_TABLE_TYPE_TABLE"` | APP_DB | `schema.h:95` |
| `STATE_ACL_TABLE_TABLE_NAME` | `"ACL_TABLE_TABLE"` | STATE_DB | `schema.h:514` |

---

## その他 STATE_DB ACTION フィールド定数 (aclorch.cpp:42-44)

| マクロ名 | 値 | 行 |
|---|---|---|
| `STATE_DB_ACL_ACTION_FIELD_IS_ACTION_LIST_MANDATORY` | `"is_action_list_mandatory"` | `aclorch.cpp:42` |
| `STATE_DB_ACL_ACTION_FIELD_ACTION_LIST` | `"action_list"` | `aclorch.cpp:43` |
| `STATE_DB_ACL_L3V4V6_SUPPORTED` | `"supported_L3V4V6"` | `aclorch.cpp:44` |

これらは ASIC capability 照会結果を STATE_DB に記録するためのフィールド名。ACL_TABLE エントリの `status` フィールドとは別テーブルに格納される。

---

## スキャン証跡

- `acltable.h:1-76` 全行精読 — フィールドキー・stage・type・enum・lookup map すべて確認
- `aclorch.h:62-63` — BIND_POINT_TYPE マクロ確認
- `aclorch.cpp:42-44, 105-106, 523-526, 6088-6105` — STATUS 値・バインドポイント lookup・STATE_DB 書込み確認
- `schema.h:94-95, 514` — APP_DB / STATE_DB テーブル名確認
