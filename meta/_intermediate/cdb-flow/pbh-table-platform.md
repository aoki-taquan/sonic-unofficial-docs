# pbh-table — Phase H platform 調査ノート

## 調査対象ファイル

- `sonic-swss/orchagent/pbh/pbhcap.h` (PbhAsicVendor, PbhVendorFieldCapabilities クラス定義)
- `sonic-swss/orchagent/pbh/pbhcap.cpp` (PbhCapabilities, PbhGenericFieldCapabilities, PbhMellanoxFieldCapabilities)
- `sonic-swss/orchagent/pbhorch.cpp` (Mellanox W/A at line 839)
- `sonic-swss-common/common/schema.h` (STATE_PBH_CAPABILITIES_TABLE_NAME)

## プラットフォーム識別方法

`PbhCapabilities::parsePbhAsicVendor()` (pbhcap.cpp:310-335) が起動時に環境変数 `ASIC_VENDOR` を読み取る。

```cpp
#define PBH_PLATFORM_ENV_VAR  "ASIC_VENDOR"
#define PBH_PLATFORM_MELLANOX "mellanox"
#define PBH_PLATFORM_GENERIC  "generic"
```

- `ASIC_VENDOR == "mellanox"` → `PbhAsicVendor::MELLANOX`
- その他 / 未設定 → `PbhAsicVendor::GENERIC`

未設定時は `SWSS_LOG_WARN("Failed to detect ASIC vendor: ... fallback to generic")` が出る。

## ベンダー別フィールド capability

### Generic (非 Mellanox) — PbhGenericFieldCapabilities (pbhcap.cpp:107-124)

| エンティティ | フィールド | 対応 capability |
|---|---|---|
| PBH_TABLE | interface_list | UPDATE のみ |
| PBH_TABLE | description | UPDATE のみ |
| PBH_RULE | priority | UPDATE のみ |
| PBH_RULE | gre_key / ether_type / ip_protocol / ipv6_next_header / l4_dst_port / inner_ether_type | ADD + UPDATE + REMOVE |
| PBH_RULE | hash | UPDATE のみ |
| PBH_RULE | packet_action / flow_counter | ADD + UPDATE + REMOVE |
| PBH_HASH | hash_field_list | UPDATE のみ |
| PBH_HASH_FIELD | hash_field / ip_mask / sequence_id | **空（なし）** — setPbhDefaults 未呼び出し |

注意: `PBH_HASH_FIELD` の hashField.* フィールドは Generic でも空セット。`setPbhDefaults` が呼ばれていないため ADD/UPDATE/REMOVE すべて不可として validate される。ただし実際の Hash Field 作成は `createPbhHashField()` 内で直接 SAI を呼ぶため、capability チェックは pbhorch.cpp の `validatePbhHashFieldCap()` 呼び出し (pbhorch.cpp:1410-1422) でのみ検証される。

### Mellanox — PbhMellanoxFieldCapabilities (pbhcap.cpp:126-141)

Generic との差分:

| エンティティ | フィールド | Generic | Mellanox |
|---|---|---|---|
| PBH_HASH | hash_field_list | UPDATE のみ | **空（なし）** — setPbhDefaults 未呼び出し |
| PBH_RULE | packet_action / flow_counter | ADD+UPDATE+REMOVE | ADD+UPDATE+REMOVE (同じ) |

つまり Mellanox では `PBH_HASH.hash_field_list` の UPDATE が非対応。

## Mellanox W/A (pbhorch.cpp:839-863)

`updatePbhRule()` 内、`hash` フィールドまたは `packet_action` フィールドを UPDATE する場合に実行される。

```cpp
// pbhorch.cpp:839-863
if (this->pbhCap.getAsicVendor() == PbhAsicVendor::MELLANOX)
{
    if (cond1 || cond2)  // hash or packet_action in uFields
    {
        auto pbhRulePtr = dynamic_cast<AclRulePbh*>(...);
        if (!pbhRulePtr->disableAction()) { return false; }
    }
}
```

Mellanox では `hash` / `packet_action` フィールドの更新前に SAI レベルで rule の action を一時無効化する必要がある。この W/A がない場合、SAI が attribute update を拒否する可能性がある。

## STATE_DB への capabilities 書き出し

`PbhCapabilities::writePbhVendorCapabilitiesToDb()` (pbhcap.cpp:442-452) が orchagent 起動時に STATE_DB `PBH_CAPABILITIES` テーブル (`STATE_PBH_CAPABILITIES_TABLE_NAME`) に書き込む。

```
STATE_DB:PBH_CAPABILITIES|table    → interface_list, description の capability 文字列
STATE_DB:PBH_CAPABILITIES|rule     → priority, gre_key, ... の capability 文字列
STATE_DB:PBH_CAPABILITIES|hash     → hash_field_list の capability 文字列
STATE_DB:PBH_CAPABILITIES|hash-field → hash_field, ip_mask, sequence_id の capability 文字列
```

capability 文字列は `"ADD,UPDATE,REMOVE"` / `"UPDATE"` / `""` (空) の組み合わせ。

## まとめ

`PBH_TABLE` 自体のフィールド (`interface_list` / `description`) は両プラットフォームとも UPDATE のみ対応（ADD は暗黙許可、REMOVE は DEL で対応）。実質的なプラットフォーム差異は `PBH_HASH.hash_field_list` の UPDATE 不可 (Mellanox) と `PBH_RULE.hash`/`packet_action` の UPDATE 時 W/A の 2 点。`PBH_TABLE` 固有としては両プラットフォームで同一動作。
