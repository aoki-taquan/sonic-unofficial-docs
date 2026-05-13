# ACL_TABLE enum 値別深掘り grep 証跡 (v2)

生成日: 2026-05-13
対象ファイル: sonic-swss/orchagent/aclorch.h, aclorch.cpp, acltable.h
          sonic-mgmt-common/models/yang/sonic/sonic-acl.yang

---

## フィールド: type (4 値 — YANG 定義, 実装は 14 値)

YANG (sonic-acl.yang:58-65): `MIRROR/MIRRORV6/L3/L3V6` の 4 値のみ。
実装 (acltable.h:26-42): `L3/L3V6/L3V4V6/MIRROR/MIRRORV6/MIRROR_DSCP/PFCWD/CTRLPLANE/DTEL_FLOW_WATCHLIST/MCLAG/MUX/DROP/MARK_META/MARK_METAV6/EGR_SET_DSCP/UNDERLAY_SET_DSCP/UNDERLAY_SET_DSCPV6` 多数。

### MIRROR
- grep hit: `acltable.h:29` `#define TABLE_TYPE_MIRROR "MIRROR"`
- grep hit: `aclorch.cpp:260` MIRROR テーブル定義 with `SAI_ACL_ACTION_TYPE_MIRROR_INGRESS`
- grep hit: `aclorch.cpp:3502` `{ TABLE_TYPE_MIRROR, true }` — capability に登録
- grep hit: `aclorch.cpp:3671` mirror capability state_db 書き込み
- 挙動: MIRROR_INGRESS_ACTION 専用。SAI capability 照会後に能力がなければ reject

### MIRRORV6
- grep hit: `acltable.h:30` `#define TABLE_TYPE_MIRRORV6 "MIRRORV6"`
- grep hit: `aclorch.cpp:279` MIRRORV6 テーブル定義
- grep hit: `aclorch.cpp:3503` `{ TABLE_TYPE_MIRRORV6, true }`, `aclorch.cpp:3510,3511` — ASIC により false も有り
- grep hit: `aclorch.cpp:5811` `m_isCombinedMirrorV6Table` 判定で MIRROR テーブルと統合されることがある
- 挙動: IPv6 ミラー。一部 ASIC では MIRROR と同一テーブルに統合

### L3
- grep hit: `acltable.h:26` `#define TABLE_TYPE_L3 "L3"`
- grep hit: `aclorch.cpp:200` L3 テーブル定義 (INGRESS/EGRESS 両対応)
- grep hit: `aclorch.cpp:454` INGRESS match フィールド群, `aclorch.cpp:471` L3V6 match
- 挙動: 通常 IPv4 L3 ACL。INGRESS/EGRESS 両 stage で使用可

### L3V6
- grep hit: `acltable.h:27` `#define TABLE_TYPE_L3V6 "L3V6"`
- grep hit: `aclorch.cpp:220` L3V6 テーブル定義
- grep hit: `aclorch.cpp:1231` `IP_PROTOCOL on IPv6 tables` 使用で WARN ログ (将来削除)
- 挙動: IPv6 L3 ACL。IP_PROTOCOL は非推奨、NEXT_HEADER を使うべき

### 追加実装値 (YANG 外)
- `L3V4V6` (`acltable.h:28`): デュアルスタック。`isAclL3V4V6TableSupported()` 確認 (`aclorch.cpp:2737`)
- `MIRROR_DSCP` (`acltable.h:31`): DSCP 値でミラー先決定 (`aclorch.cpp:298`)
- `PFCWD` (`acltable.h:32`): PFC Watchdog 専用。BRCM DNX は `SAI_ACL_BIND_POINT_TYPE_SWITCH` (`aclorch.cpp:3815`)
- `CTRLPLANE` (`acltable.h:33`): SAI テーブル作成なし (`aclorch.cpp:2727`)
- `MCLAG` (`acltable.h:35`): MCLAG 制御用 (`aclorch.cpp:334`)
- `MUX` (`acltable.h:36`): dual-ToR mux (`aclorch.cpp:352`)
- `DROP` (`acltable.h:37`): drop 専用最適化 (`aclorch.cpp:370`)
- `MARK_META` (`acltable.h:38`): metadata マーキング IPv4 (`aclorch.cpp:388`)
- `MARK_METAV6` (`acltable.h:39`): metadata マーキング IPv6 (`aclorch.cpp:400`)
- `EGR_SET_DSCP` (`acltable.h:40`): egress DSCP 書き換え (`aclorch.cpp:412,489`)
- `UNDERLAY_SET_DSCP` (`acltable.h:41`): 内部で `MARK_META` に変換 (`aclorch.cpp:121` 相当)
- `UNDERLAY_SET_DSCPV6` (`acltable.h:42`): 内部で `MARK_METAV6` に変換

---

## フィールド: stage (2 値)

### INGRESS (既定)
- grep hit: `aclorch.cpp:166` `{STAGE_INGRESS, ACL_STAGE_INGRESS}`
- grep hit: `aclorch.cpp:173` INGRESS stage で `SAI_ACL_ACTION_TYPE_MIRROR_INGRESS`
- grep hit: `aclorch.cpp:263-266` MIRROR/MIRRORV6 テーブルの INGRESS 定義
- SAI: `SAI_ACL_STAGE_INGRESS` (`aclorch.cpp:164`)
- 挙動: 受信ポートでパケット評価。MIRROR_INGRESS_ACTION が有効

### EGRESS
- grep hit: `aclorch.cpp:167` `{STAGE_EGRESS, ACL_STAGE_EGRESS}`
- grep hit: `aclorch.cpp:185` EGRESS stage
- grep hit: `aclorch.cpp:270-272` EGRESS では `SAI_ACL_ACTION_TYPE_MIRROR_EGRESS` のみ
- SAI: `SAI_ACL_STAGE_EGRESS`
- 挙動: 送信ポートでパケット評価。MIRROR_EGRESS_ACTION のみ有効

### 複合条件
- `type=CTRLPLANE` → stage 無視、SAI テーブル不作成 (`aclorch.cpp:2727`)
- `type=EGR_SET_DSCP` → EGRESS stage 固定 (`aclorch.h:412,489`)
- `type=L3V4V6` + EGRESS → `m_L3V4V6Capability[ACL_STAGE_EGRESS]` が false の場合拒否 (`aclorch.cpp:3541-3543`)

---

## フィールド: ETHER_TYPE, IP_TYPE, PACKET_ACTION (ACL_TABLE では使用なし)

ACL_TABLE テーブル自体にこれらのフィールドはない。`ACL_TABLE_TYPE` サブテーブルの `MATCHES` フィールドで許可する match キーとして指定する文字列として間接参照される。

---

## 値別 grep カバレッジサマリ

| フィールド | 値 | hit数 | 主要証跡 |
|---|---|---|---|
| type | MIRROR | 4 | acltable.h:29, cpp:260,3502,3671 |
| type | MIRRORV6 | 5 | acltable.h:30, cpp:279,3503,3510,5811 |
| type | L3 | 3 | acltable.h:26, cpp:200,454 |
| type | L3V6 | 3 | acltable.h:27, cpp:220,1231 |
| stage | INGRESS | 4 | cpp:166,173,263,265 |
| stage | EGRESS | 3 | cpp:167,185,270 |

ETHER_TYPE: ACL_TABLE に直接フィールドなし — 0 hit (非適用)
IP_TYPE: ACL_TABLE に直接フィールドなし — 0 hit (非適用)
PACKET_ACTION: ACL_TABLE に直接フィールドなし — 0 hit (非適用)

## 複合条件発見数: 4

1. `type=CTRLPLANE` → stage 無視、SAI テーブル不作成 (`aclorch.cpp:2727`)
2. `type=L3V4V6` → ASIC capability 確認 `isAclL3V4V6TableSupported()` (`aclorch.cpp:2737`)
3. `type=MIRROR/MIRRORV6` → 起動時 ASIC capability query、なければ reject (`aclorch.cpp:3502-3541`)
4. `type=EGR_SET_DSCP` → stage=EGRESS 固定。ingress で指定しても egress 動作 (`aclorch.h:489`)
