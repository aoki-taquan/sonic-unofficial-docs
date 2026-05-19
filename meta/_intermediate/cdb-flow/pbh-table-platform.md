# pbh-table — Phase H プラットフォーム差異

## 調査証跡

- `sonic-swss/orchagent/pbh/pbhcap.cpp` — `PbhCapabilities::parsePbhAsicVendor()`, `PbhGenericFieldCapabilities`, `PbhMellanoxFieldCapabilities`
- `sonic-swss/orchagent/pbh/pbhcap.h` — `PbhAsicVendor` enum, `PbhVendorFieldCapabilities`
- `sonic-swss/orchagent/pbhorch.cpp` — `updatePbhTable()`, `updatePbhRule()` (Mellanox W/A L839-880)

## プラットフォーム識別方法

`PbhCapabilities::parsePbhAsicVendor()` が環境変数 `ASIC_VENDOR` を読み取る (`pbhcap.cpp:22-24, 176-197`)。

```c
const char *envVar = std::getenv("ASIC_VENDOR");
if (platform == PBH_PLATFORM_MELLANOX) → PbhAsicVendor::MELLANOX
else                                   → PbhAsicVendor::GENERIC
```

認識するベンダー:
- `"mellanox"` → MELLANOX
- それ以外（broadcom, barefoot, cisco-8000 等）→ GENERIC
- 環境変数未設定 → GENERIC (fallback, SWSS_LOG_WARN)

## プラットフォーム別フィールド操作可否

`PbhCapabilities` は起動時に vendor capabilities を決定し、STATE_DB `PBH_CAPABILITIES_TABLE` に書き出す。

### PBH_TABLE テーブル

| フィールド | GENERIC | MELLANOX |
|-----------|---------|----------|
| `interface_list` | **UPDATE** のみ | **UPDATE** のみ |
| `description` | **UPDATE** のみ | **UPDATE** のみ |

両 vendor とも **ADD/REMOVE は不可**（`interface_list`/`description` は UPDATE のみサポート）。

### PBH_HASH テーブル

| フィールド | GENERIC | MELLANOX |
|-----------|---------|----------|
| `hash_field_list` | **UPDATE** のみ | **なし（空集合）** |

**MELLANOX では `hash_field_list` の UPDATE が不可能**（`PbhMellanoxFieldCapabilities` が `hash_field_list` を一切設定しない — `pbhcap.cpp:126-141`）。

### PBH_RULE テーブル

| フィールド | GENERIC | MELLANOX |
|-----------|---------|----------|
| `gre_key`, `ether_type`, `ip_protocol`, `ipv6_next_header`, `l4_dst_port`, `inner_ether_type`, `packet_action`, `flow_counter` | ADD/UPDATE/REMOVE | ADD/UPDATE/REMOVE |
| `priority` | UPDATE のみ | UPDATE のみ |
| `hash` | UPDATE のみ | UPDATE のみ |

### PBH_HASH_FIELD テーブル

| フィールド | GENERIC | MELLANOX |
|-----------|---------|----------|
| `hash_field`, `ip_mask`, `sequence_id` | ※未設定（空集合） | ※未設定（空集合） |

`PbhHashFieldCapabilities` の `hashField` は両 vendor とも `setPbhDefaults` 未呼び出しのため空集合。実際の検証は未使用と推測される。

## Mellanox W/A (update PBH_RULE)

`updatePbhRule()` において `hash` または `packet_action` フィールドが更新対象に含まれる場合、Mellanox ASIC では SAI 上で action を無効化してから更新する回避策が必要 (`pbhorch.cpp:839-880`):

```
if (pbhCap.getAsicVendor() == PbhAsicVendor::MELLANOX) {
    if (hash or packet_action is in uFields) {
        pbhRulePtr->disableAction()   // 一時的に action を SAI 上で無効化
        aclOrch->updateAclRule(...)
        pbhRulePtr->enableAction()    // action を再有効化
    }
}
```

Generic ASIC では SAI 上で action を無効化せずに直接 `updateAclRule()` を呼び出す。

## VM・Virtual Switch

`ASIC_VENDOR=vs` (または未設定) の場合は GENERIC 動作。PBH TABLE ACL は SAI 経由で ASIC_DB に書かれるが、syncd は VS で mock 実行されるため実際のハードウェアへの降りはない。VM 環境でも `PbhCapabilities` の初期化・STATE_DB 書き込みは正常に行われる。

## サマリ

| プラットフォーム | `hash_field_list` UPDATE | PBH_RULE hash/packet_action UPDATE |
|----------------|--------------------------|-------------------------------------|
| GENERIC (broadcom 等) | 可 | 直接 updateAclRule |
| MELLANOX | **不可** | disableAction → update → enableAction |
