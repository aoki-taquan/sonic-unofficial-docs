# appl-mirror — Phase E: ハードコード定数スキャンノート

対象: `docs/reference/config-db/appl-mirror.md` (APPL_DB `FIXED_MIRROR_SESSION_TABLE` / P4RT)

ソース:

- `sonic-swss/orchagent/p4orch/mirror_session_manager.h` (ref `4305596156d70e9797e8a881b3d19b46de0bce0d`)
- `sonic-swss/orchagent/p4orch/mirror_session_manager.cpp` (同 ref)
- `sonic-swss/orchagent/mirrororch.cpp` (同 ref、比較用)

## 1. P4RT 経路 (`mirror_session_manager.{h,cpp}`) のハードコード定数

| 定数 | 値 | 用途 | 箇所 | 上書き可否 |
|------|----|------|------|-----------|
| `MIRROR_SESSION_DEFAULT_IP_HDR_VER` | `4` | `SAI_MIRROR_SESSION_ATTR_IPHDR_VERSION` に固定セット | `mirror_session_manager.h:20` / `.cpp:153-155` | 不可 (APP_DB スキーマにフィールドなし) |
| `GRE_PROTOCOL_ERSPAN` | `0x88be` | `SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE` に固定セット | `mirror_session_manager.h:21` / `.cpp:183-185` | 不可 (platform 分岐なし、APP_DB フィールドなし) |
| (リテラル) `SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE` | enum | session type を ERSPAN に固定 | `.cpp:144-146` | 不可 |
| (リテラル) `SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL` | enum | encap type を L3 GRE に固定 | `.cpp:148-150` | 不可 |
| `"mirror_as_ipv4_erspan"` | string | 受け付ける action 識別子 (固定) | `.cpp:307-313` (deserialize) | 不可 (他値は `SWSS_RC_INVALID_PARAM`) |
| `"FIXED_MIRROR_SESSION_TABLE"` | string | APP_P4RT テーブル名 | `sonic-swss-common/common/schema.h:70` (`APP_P4RT_MIRROR_SESSION_TABLE_NAME`) | 不可 |
| TOS / TTL parse base | `16` (`std::stoul(value, 0, 16)`) | hex 文字列としてのみ受理 | `.cpp:281-305` | 不可 (10 進・接頭辞なしは parse 失敗) |

### policer / UDP port / DSCP 既定について

- **policer 識別子**: P4RT 経路には **存在しない**。`P4MirrorSessionAppDbEntry` (`p4orch_util.h:253-279`) は ttl/tos/src_ip/dst_ip/src_mac/dst_mac/port のみ。`prepareSaiAttrs()` も `SAI_MIRROR_SESSION_ATTR_POLICER` を一切セットしない。
- **UDP port**: ERSPAN over GRE のため UDP は使用しない。SFLOW (UDP/6343) / VXLAN-ERSPAN (UDP/4789) 系のハードコードは `mirror_session_manager.{h,cpp}` には**存在しない**。
- **DSCP 既定**: P4RT 経路では `param/tos` (TOS バイト全体 = DSCP+ECN) を APP_DB の**必須フィールド**として受け取り、内部で DSCP 単独に分解しない。`prepareSaiAttrs()` は `SAI_MIRROR_SESSION_ATTR_TOS` に `mirror_session_entry.tos` をそのまま設定 (`.cpp:157-159`)。
  - 既定値は struct 初期値の `0` だが、`has_tos=false` のまま ADD すると `SWSS_RC_INVALID_PARAM` で蹴られるため**実質的にデフォルトは効かない**。

## 2. CONFIG_DB 経路 (`mirrororch.cpp`) との対比 (参考)

| 定数/識別子 | 値 | 用途 | 箇所 |
|------------|----|------|------|
| `MirrorEntry::greType` (Mellanox) | `0x8949` | platform 分岐: Mellanox Spectrum 用 GRE type | `mirrororch.cpp:65-68` |
| `MirrorEntry::greType` (それ以外) | `0x88be` | 標準 ERSPAN GRE type | `mirrororch.cpp:69-72` |
| `MirrorEntry::dscp` 初期値 | `8` | DSCP デフォルト (CS1) | `mirrororch.cpp:59` |
| `MirrorEntry::ttl` 初期値 | `255` | TTL デフォルト | `mirrororch.cpp:60` |
| `MIRROR_SESSION_DSCP_MIN` / `_MAX` | `0` / `63` | DSCP 範囲 | `mirrororch.cpp:40-42` |
| `MIRROR_SESSION_DEFAULT_NUM_TC` | `255` | TC 上限不明時のフォールバック | `mirrororch.cpp:45` |
| `MIRROR_SESSION_POLICER` | `"policer"` | policer フィールド名 | `mirrororch.cpp:29` |
| MLNX 分岐キー | `platform == MLNX_PLATFORM_SUBSTRING` | `getenv("platform")` 結果と比較 | `mirrororch.cpp:65` |

P4RT 経路はこの platform 分岐を**持たない**ため、Mellanox Spectrum 上で P4RT ERSPAN を使うと SAI に `0x88be` が渡り、CONFIG_DB 経路の `0x8949` と乖離する。

## 3. ページ追記方針

`appl-mirror.md` 既存ブロック (`<!-- defaults -->`, `<!-- ordering -->`, `<!-- platform -->`, `<!-- pubsub -->`, `<!-- failure -->`) はそのまま保持し、**`<!-- constants -->` 新規ブロック** を追加する。`defaults` / `platform` と内容が一部重複するが、Phase E では「ハードコード定数を上書き不可と明示的に列挙する」観点で再整理する。
