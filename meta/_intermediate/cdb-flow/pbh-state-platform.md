# pbh-state platform (Phase H) — 調査ノート

## ソース

- `sonic-swss/orchagent/pbh/pbhcap.cpp` (L20-23, L107-143, L310-367)

## プラットフォーム識別

`PbhCapabilities` は起動時に `parsePbhAsicVendor()` で環境変数 `ASIC_VENDOR` を読み取る。

```
#define PBH_PLATFORM_ENV_VAR  "ASIC_VENDOR"   // pbhcap.cpp:20
#define PBH_PLATFORM_GENERIC  "generic"        // pbhcap.cpp:21
#define PBH_PLATFORM_MELLANOX "mellanox"       // pbhcap.cpp:22
```

`ASIC_VENDOR` が `"mellanox"` ならば `PbhMellanoxFieldCapabilities` を生成。
それ以外・未設定・未知値はすべて `PbhGenericFieldCapabilities` を生成し WARN ログを出す。

## Generic vs Mellanox の差異

`PbhGenericFieldCapabilities` コンストラクタ (L107-124):
- `hash.hash_field_list` に `UPDATE` を INSERT する (L123)

`PbhMellanoxFieldCapabilities` コンストラクタ (L126-141):
- `hash.hash_field_list` への INSERT が**ない**

その結果、STATE_DB に書き込まれる `PBH_CAPABILITIES|hash` の差は:

| プラットフォーム | `hash_field_list` の STATE_DB 値 |
|---|---|
| Generic (default) | `"UPDATE"` |
| Mellanox | `""` (空文字列) |

他の 3 サブキー (`table`, `rule`, `hash-field`) の値は Generic と Mellanox で同一。

## Mellanox 制約の実用的影響

`config pbh hash update` 実行時に `pbh_capabilities_query(db, "hash")` が `""` を返す。
この空値は「全操作不可」と解釈され、`config pbh hash` の UPDATE 操作が拒否される。

ログ (orchagent 側):
```
SWSS_LOG_ERROR("Failed to validate field(hash_field_list): capability(UPDATE) is not supported")
```
