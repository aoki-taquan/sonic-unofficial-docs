# Phase A デフォルト調査: APPL_DB FIXED_MIRROR_SESSION_TABLE

## 対象ページ

`docs/reference/config-db/appl-mirror.md`

## 調査ソース

- `sonic-swss/orchagent/p4orch/mirror_session_manager.h` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/p4orch/mirror_session_manager.cpp` (同上)
- `sonic-swss/orchagent/p4orch/p4orch_util.h` (同上)

## grep エントリ (1 回限定)

```
grep -rn "MIRROR_SESSION_TABLE|APP_MIRROR_SESSION" /cache/sonic-sources/sonic-swss/orchagent/ --include="*.cpp" --include="*.h"
```

ヒット箇所: `p4orch/mirror_session_manager.cpp` / `p4orch/p4orch.cpp` / `p4orch/p4orch.h` / `orchdaemon.cpp`

## 定数・デフォルト一覧

| 定数 | 値 | 定義箇所 |
|------|-----|---------|
| `MIRROR_SESSION_DEFAULT_IP_HDR_VER` | `4` | `mirror_session_manager.h:20` |
| `GRE_PROTOCOL_ERSPAN` | `0x88be` | `mirror_session_manager.h:21` |
| `SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE` | — | `prepareSaiAttrs()` ハードコード |
| `SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL` | — | `prepareSaiAttrs()` ハードコード |

## P4MirrorSessionAppDbEntry 必須フィールド

`processAddRequest()` L345 の条件式:
```cpp
app_db_entry.has_port && app_db_entry.has_src_ip && app_db_entry.has_dst_ip &&
app_db_entry.has_src_mac && app_db_entry.has_dst_mac && app_db_entry.has_ttl && app_db_entry.has_tos
```
7 フィールドすべて必須。欠けると `SWSS_RC_INVALID_PARAM`。

## discrepancy 一覧

1. **IP ヘッダバージョン固定 = 4**: IPv6 アドレスを設定しても SAI には IPv4 バージョンが設定される。IPv6 outer ヘッダ不可。
2. **GRE type ハードコード = 0x88be**: APP_DB に gre_type フィールドなし。CONFIG_DB MIRROR_SESSION と異なり Mellanox 分岐 (0x8949) もない。
3. **TOS/TTL 省略不可**: struct 初期値は `0` だが `has_*=false` のまま ADD すると失敗。
4. **セッションタイプ ERSPAN 固定**: SPAN セッションは P4RT 経由では作成不可。

## CONFIG_DB MIRROR_SESSION との主な差異

| 観点 | CONFIG_DB MIRROR_SESSION | APPL_DB FIXED_MIRROR_SESSION_TABLE |
|------|--------------------------|-------------------------------------|
| 書き込み元 | CLI / sonic-cfggen / REST | P4RT ランタイムのみ |
| セッションタイプ | SPAN / ERSPAN | ERSPAN 固定 |
| GRE type | 設定可 (default 0x88be, Mellanox 0x8949) | ハードコード 0x88be |
| MAC アドレス指定 | 不要 (nexthop 解決) | src_mac / dst_mac 必須 |
| nexthop 解決 | RouteOrch に委譲 | 不要 (MAC を直接指定) |
| IP ヘッダバージョン | IPv4 / IPv6 両対応 | IPv4 のみ |
