# SWITCH_HASH — Phase H: プラットフォーム差異

## 調査証跡

- `sonic-swss/orchagent/switch/switch_capabilities.h` (L16-99)
- `sonic-swss/orchagent/switch/switch_capabilities.cpp` (L156-614)
- `sonic-swss/orchagent/switchorch.cpp` (L782-941)
- `sonic-swss-common/common/schema.h:417` (`STATE_SWITCH_CAPABILITY_TABLE_NAME = "SWITCH_CAPABILITY"`)

## 概要

`SwitchOrch` に platform 識別文字列 (`BRCM_PLATFORM_SUBSTRING` 等) による分岐は存在しない。
プラットフォーム差異はすべて **SAI capability クエリ** 経由で実行時に決定される。
起動時に `SwitchCapabilities` コンストラクタが 6 種類のクエリを実行し、結果を STATE_DB `SWITCH_CAPABILITY|switch` に書き込む。

## SAI capability クエリの構造

`SwitchCapabilities` コンストラクタ (`switch_capabilities.cpp:156-163`) は起動時に以下を呼ぶ:

1. `queryHashCapabilities()` — `SAI_OBJECT_TYPE_HASH` / `SAI_HASH_ATTR_NATIVE_HASH_FIELD_LIST` の enum capability + attr capability をクエリ
2. `querySwitchCapabilities()` — ECMP/LAG hash・アルゴリズム各属性の attr/enum capability をクエリ

クエリ成功/失敗で `isAttrSupported` / `isEnumSupported` フラグが設定され、STATE_DB に書き込まれる。

## STATE_DB への capability 書込

`writeHashCapabilitiesToDb()` / `writeSwitchCapabilitiesToDb()` が `STATE_DB:SWITCH_CAPABILITY|switch` に以下フィールドを書き込む:

| フィールド名 | 意味 |
|---|---|
| `HASH\|NATIVE_HASH_FIELD_LIST` | ASIC がサポートする hash-field 列挙値のカンマ区切りリスト (enum 未サポートなら `"N/A"`) |
| `ECMP_HASH_CAPABLE` | `isSwitchEcmpHashSupported()` の結果 (`"true"` / `"false"`) |
| `LAG_HASH_CAPABLE` | `isSwitchLagHashSupported()` の結果 |
| `ECMP_HASH_ALGORITHM` | ECMP hash algorithm ASIC サポートリスト (enum 未サポートなら `"N/A"`) |
| `ECMP_HASH_ALGORITHM_CAPABLE` | `isSwitchEcmpHashAlgorithmSupported()` の結果 |
| `LAG_HASH_ALGORITHM` | LAG hash algorithm ASIC サポートリスト |
| `LAG_HASH_ALGORITHM_CAPABLE` | `isSwitchLagHashAlgorithmSupported()` の結果 |

## プラットフォーム別の動作差

### ECMP/LAG hash フィールドリスト

`isSwitchEcmpHashSupported()` は `nativeHashFieldList.isAttrSupported && ecmpHash.isAttrSupported` で判定。
どちらかの SAI クエリが失敗すると `false` になり、SET 受信時に `LOG_WARN("Switch ECMP hash configuration is not supported: skipping ...")` でサイレントに握り潰される。

### hash-field enum capability

`validateSwitchHashFieldCap()` は `isEnumSupported == false` の場合はバリデーションをスキップ（全 field を許可）する。
enum capability クエリが成功した ASIC では、ASIC 非サポートフィールドを含む SET を `LOG_ERROR` で拒否する。

### アルゴリズム capability

ECMP/LAG hash algorithm も同様に `isSwitchEcmpHashAlgorithmSupported()` / `isSwitchLagHashAlgorithmSupported()` で capability ゲートされる。
enum capability が取得できた場合は `validateSwitchEcmpHashAlgorithmCap()` でアルゴリズム値を検証する。

### VS (Virtual Switch)

`libsaivs` は `sai_query_attribute_capability` / `sai_query_attribute_enum_values_capability` が `SAI_STATUS_NOT_IMPLEMENTED` を返すため、全フラグが `false` のまま STATE_DB に書き込まれる。SWITCH_HASH SET はすべて `LOG_WARN` でスキップされ SAI には反映されない。

## platform 文字列分岐: なし

`switchorch.cpp` の SWITCH_HASH 処理経路に `BRCM_PLATFORM_SUBSTRING` / `MLNX_PLATFORM_SUBSTRING` 等の条件分岐は存在しない。FG_NHG (`FgNhgOrch`) / ACL など他機能と異なり、SWITCH_HASH は完全に SAI capability 動的クエリのみで機種差を吸収する。

## 確認コマンド

```bash
sonic-db-cli STATE_DB hgetall 'SWITCH_CAPABILITY|switch'
show switch-hash capabilities
```
