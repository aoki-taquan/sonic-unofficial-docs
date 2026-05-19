# PBH_RULE — Phase H platform 調査メモ

## 調査対象ソース

- `sonic-swss/orchagent/pbh/pbhcap.cpp` (lines 107-141, 286-452)
- `sonic-swss/orchagent/pbhorch.cpp` (lines 839-863)
- `sonic-swss-common/common/schema.h` (line 419)

## プラットフォーム検出

`PbhCapabilities::initPbhCapabilities()` が `std::getenv("ASIC_VENDOR")` を参照。
- `"mellanox"` → `PbhMellanoxFieldCapabilities`
- それ以外 / 未設定 → `PbhGenericFieldCapabilities`（WARN ログ + fallback）

## capability 差異（PBH_RULE スコープ）

`setPbhDefaults()` = ADD + UPDATE + REMOVE を挿入。`insert(UPDATE)` のみ = UPDATE 単独。

Generic と Mellanox で `PBH_RULE` フィールドの capability は同一：
- `priority`: UPDATE のみ
- `gre_key`, `ether_type`, `ip_protocol`, `ipv6_next_header`, `l4_dst_port`, `inner_ether_type`: ADD/UPDATE/REMOVE
- `hash`: UPDATE のみ
- `packet_action`, `flow_counter`: ADD/UPDATE/REMOVE

## Mellanox 専用差異

### 1. PBH_HASH.hash_field_list（間接影響）

`PbhMellanoxFieldCapabilities` コンストラクタは `hash.hash_field_list` への挿入を省略（`pbhcap.cpp:126-141`）。
→ Mellanox では `PBH_HASH` の `hash_field_list` の UPDATE / ADD / REMOVE が全て不可。
→ `PBH_RULE` の `hash` フィールドを別の HASH プロファイルへ切り替える際、Mellanox では既存 HASH を更新できないため新規 HASH を作成する必要がある。

### 2. updatePbhRule の disableAction W/A（pbhorch.cpp:839-863）

更新フィールドに `hash` または `packet_action` が含まれる場合:
1. `AclRulePbh::disableAction()` — 既存 ACL entry の action を一時クリア
2. `AclOrch::updateAclRule()` — SAI 更新

Mellanox ASIC は action がセットされた状態での hash/action 変更を拒否するため、先に action を無効化してから更新する。
`disableAction()` 失敗 → ERROR ログ + `return false` → retry loop（UPDATE 中断）。

Generic プラットフォームではこの分岐に入らない。

## STATE_DB への capability 書き込み

`writePbhVendorCapabilitiesToDb()` が orchagent 起動時に `STATE_DB PBH_CAPABILITIES|rule` を書き込む。
フィールド値は capability set の文字列表現（例: `"ADD,UPDATE,REMOVE"`、`"UPDATE"`）。
`validatePbhRuleCap()` が SET/UPDATE/DEL 時にこの capability を参照して未サポート操作を拒否。
