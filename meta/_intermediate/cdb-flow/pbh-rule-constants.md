# PBH_RULE — Phase E ハードコード定数

ソース調査日: 2026-05-19
対象ファイル:
- `sonic-swss/orchagent/pbh/pbhschema.h`
- `sonic-swss/orchagent/pbh/pbhmgr.cpp`
- `sonic-swss/orchagent/pbh/pbhrule.cpp`
- `sonic-swss/orchagent/pbh/pbhcap.cpp`

---

## 1. フィールド文字列定数 (pbhschema.h)

CONFIG_DB フィールド名として使われる文字列は `pbhschema.h` でマクロ定義されており、
YANG や sonic-db-config に文字列のソースオブジェクトはない。

```c
#define PBH_RULE_PACKET_ACTION_SET_ECMP_HASH "SET_ECMP_HASH"
#define PBH_RULE_PACKET_ACTION_SET_LAG_HASH  "SET_LAG_HASH"
#define PBH_RULE_FLOW_COUNTER_ENABLED        "ENABLED"
#define PBH_RULE_FLOW_COUNTER_DISABLED       "DISABLED"
```

---

## 2. match フィールドの暗黙 mask (pbhmgr.cpp)

`ether_type`、`ip_protocol`、`ipv6_next_header`、`l4_dst_port`、`inner_ether_type` の mask 値は
YANG に定義が存在せず、`parsePbhRule()` 内でハードコードされる。

| フィールド | mask 値 | ソース行 |
|-----------|---------|---------|
| `ether_type` | `0xFFFF` | `pbhmgr.cpp:558` |
| `ip_protocol` | `0xFF` | `pbhmgr.cpp:583` |
| `ipv6_next_header` | `0xFF` | `pbhmgr.cpp:608` |
| `l4_dst_port` | `0xFFFF` | `pbhmgr.cpp:633` |
| `inner_ether_type` | `0xFFFF` | `pbhmgr.cpp:658` |

`gre_key` のみ `value/mask` ペアをユーザーが明示指定する (`0x<value>/0x<mask>` 形式、`pbhmgr.cpp:533`)。

---

## 3. packet_action デフォルト = SET_ECMP_HASH (pbhmgr.cpp:997-1009)

`packet_action` フィールドが CONFIG_DB エントリに存在しない場合、`validatePbhRule()` が
`PBH_RULE_PACKET_ACTION_SET_ECMP_HASH` (`"SET_ECMP_HASH"`) を注入する。YANG の default 定義と一致。

---

## 4. flow_counter デフォルト = DISABLED (pbhmgr.cpp:1012-1023)

`flow_counter` フィールドが存在しない場合、`validatePbhRule()` が
`PBH_RULE_FLOW_COUNTER_DISABLED` (`"DISABLED"`) を注入する。YANG の default 定義と一致。

---

## 5. ACL ステージ固定: INGRESS (pbhorch.cpp:260)

`createPbhAclTable()` (`pbhorch.cpp:260`) は PBH ACL テーブルを常に
`ACL_STAGE_INGRESS` で作成する。EGRESS は非サポート。

---

## 6. match / action 件数バリデーション (pbhrule.cpp:84-90)

`AclRulePbh::validate()` が以下の制約をコードでのみ適用する (YANG に記述なし):
- match フィールド件数 == 0 → reject
- action 件数 != 1 → reject

---

## 7. ASIC_VENDOR 環境変数と capability フォールバック (pbhcap.cpp:20-23, 297-298)

```c
#define PBH_PLATFORM_ENV_VAR  "ASIC_VENDOR"
#define PBH_PLATFORM_GENERIC  "generic"
#define PBH_PLATFORM_MELLANOX "mellanox"
```

`ASIC_VENDOR` 未設定または未知値の場合は `PBH_PLATFORM_GENERIC` へフォールバック
(`pbhcap.cpp:297-298`)。Mellanox のみ専用 capability が存在し、
UPDATE 時に hash / packet_action フィールドの変更ステップが異なる。

---

## 8. STATE_DB 定数 (pbhcap.cpp:35-36)

```c
#define PBH_STATE_DB_NAME    "STATE_DB"
#define PBH_STATE_DB_TIMEOUT 0
```

capability テーブルを `STATE_DB:PBH_CAPABILITIES` に書き込む。
timeout = 0 は非ブロッキング (接続済みとして扱う)。

---

## 結論

- `ether_type`/`ip_protocol`/`ipv6_next_header`/`l4_dst_port`/`inner_ether_type` の mask はコードハードコード。
- ACL ステージは常に INGRESS 固定 (設定不可)。
- `packet_action`/`flow_counter` のデフォルト値はコードと YANG が一致。
- ASIC_VENDOR 未定義時は GENERIC fallback (エラーにならない)。
