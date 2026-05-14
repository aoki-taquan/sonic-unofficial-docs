# Phase A: PBH_HASH / PBH_HASH_FIELD フィールドデフォルト調査

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/pbh.md`  
対象テーブル: `PBH_HASH`, `PBH_HASH_FIELD`

## ソース一覧

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pbh.yang` | YANG スキーマ定義・default 文 |
| `sonic-swss/orchagent/pbh/pbhmgr.cpp` | parsePbhHash / parsePbhHashField / validatePbhHash / validatePbhHashField |
| `sonic-swss/orchagent/pbh/pbhschema.h` | フィールド名定数 |
| `sonic-swss/orchagent/pbhorch.cpp` | createPbhHash / createPbhHashField SAI 呼び出し |

## PBH_HASH フィールド別デフォルト

### `hash_field_list` (leaf-list, leafref to PBH_HASH_FIELD)

- YANG: `min-elements 1`、`ordered-by user`。default 文なし。
- pbhmgr.cpp `validatePbhHash()`: `hash_field_list.is_set` が false の場合 `SWSS_LOG_ERROR` + `return false`。
- **結論: mandatory。デフォルトなし。省略は validation エラー。**

## PBH_HASH_FIELD フィールド別デフォルト

### `hash_field` (enum, mandatory)

- YANG: `mandatory true`。
- pbhmgr.cpp `validatePbhHashField()`: `hash_field.is_set` が false → `SWSS_LOG_ERROR` + `return false`。
- **結論: mandatory。デフォルトなし。**

### `ip_mask` (inet:ip-address-no-zone, conditional)

- YANG: `when` 条件 — `hash_field` が `INNER_DST_IPV4` / `INNER_SRC_IPV4` / `INNER_DST_IPV6` / `INNER_SRC_IPV6` のときのみ有効。`must` 条件 — IPv4 フィールドは `.` 含む addr、IPv6 は `:` 含む addr のみ受理。
- pbhmgr.cpp `validatePbhHashField()`: `ip_mask.is_set` の真偽はチェックするが、存在しない場合のデフォルト注入なし。non-IP フィールドで ip_mask が設定されていれば `isIpv4MaskRequired` / `isIpv6MaskRequired` で禁止。
- `parsePbhHashFieldIpMask()`: `IpAddress(value)` でパース。失敗時 `return false`。
- **結論: `hash_field` が IP アドレス系のとき必須。それ以外では設定禁止。デフォルト値なし (ユーザー提供必須)。**

### `sequence_id` (uint32, mandatory)

- YANG: `mandatory true`。
- pbhmgr.cpp `validatePbhHashField()`: `sequence_id.is_set` が false → `SWSS_LOG_ERROR` + `return false`。
- parsePbhHashFieldSequenceId: `to_uint<sai_uint32_t>(value)`、失敗時 `return false`。
- **結論: mandatory。デフォルトなし。**

## PBH_RULE のデフォルト (参考・既存記載の確認)

`validatePbhRule()` (pbhmgr.cpp:981-1027) で確認済み:

- `packet_action` 未設定時: `PBH_RULE_PACKET_ACTION_SET_ECMP_HASH` (`"SET_ECMP_HASH"`) を自動注入 (runtime default)
- `flow_counter` 未設定時: `PBH_RULE_FLOW_COUNTER_DISABLED` (`"DISABLED"`) を自動注入 (runtime default)

YANG の `default "SET_ECMP_HASH"` / `default "DISABLED"` と一致。

## サマリテーブル

| テーブル | フィールド | デフォルト | 由来 |
|---------|-----------|-----------|------|
| PBH_HASH | `hash_field_list` | なし (mandatory) | YANG min-elements 1 + validatePbhHash() |
| PBH_HASH_FIELD | `hash_field` | なし (mandatory) | YANG mandatory true + validatePbhHashField() |
| PBH_HASH_FIELD | `ip_mask` | なし (条件付き必須) | YANG when/must + isIpv4/6MaskRequired() |
| PBH_HASH_FIELD | `sequence_id` | なし (mandatory) | YANG mandatory true + validatePbhHashField() |
| PBH_RULE | `packet_action` | `SET_ECMP_HASH` | YANG default + validatePbhRule() 自動注入 |
| PBH_RULE | `flow_counter` | `DISABLED` | YANG default + validatePbhRule() 自動注入 |

## 特記事項

- `PBH_HASH_FIELD.updatePbhHashField()` は常に `return false` (更新禁止)。Hash field は作成後に変更不可。
- `ip_mask` は非 IP フィールド (`INNER_IP_PROTOCOL`, `INNER_L4_DST_PORT`, `INNER_L4_SRC_PORT`) に設定すると validation エラー。
- `sequence_id` が同じ値を複数フィールドで使用可能 (YANG に uniqueness 制約なし)。同 sequence_id のフィールドは SAI 上で associative (同じグループとして扱われる)。
