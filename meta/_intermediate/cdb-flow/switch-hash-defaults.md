# SWITCH_HASH — Phase A: コード由来の暗黙デフォルト 詳細トレース

生成日: 2026-05-15
対象ページ: `docs/reference/config-db/switch-hash.md`

## 訪問ファイル・関数一覧

| ファイル | 関数/セクション | 目的 |
|---------|---------------|------|
| `sonic-swss/orchagent/switch/switch_container.h` | `class SwitchHash` L12-40 | フィールドはすべて `is_set=false` 初期化（コード側ハードコードデフォルトなし） |
| `sonic-swss/orchagent/switchorch.cpp` | `SwitchOrch::SwitchOrch()` L169 | コンストラクタで `querySwitchHashDefaults()` を呼び初期化時に SAI の既定 OID を取得 |
| `sonic-swss/orchagent/switchorch.cpp` | `SwitchOrch::querySwitchHashDefaults()` L2030-2043 | `SAI_SWITCH_ATTR_ECMP_HASH` / `SAI_SWITCH_ATTR_LAG_HASH` の OID を取得しキャッシュ |
| `sonic-swss/orchagent/switchorch.cpp` | `SwitchOrch::getSwitchHashOidSai()` L2013-2028 | `sai_switch_api->get_switch_attribute()` でデフォルト hash OID を取得（失敗時は warn のみ） |
| `sonic-swss/orchagent/switchorch.cpp` | `SwitchOrch::setSwitchHash()` L782-940 | capability 不在時 (`isSwitchEcmpHashSupported() == false`) は `LOG_WARN("...is not supported: skipping ...")` で SET をスキップし続行 |
| `sonic-swss/orchagent/switch/switch_capabilities.cpp` | `validateSwitchHashFieldCap()` L191 | 設定された hash-field 集合が SAI capability 集合に含まれるか検証 |

## field 別 fallback 詳細

### `ecmp_hash` / `lag_hash` field set — コード側デフォルトなし（SAI/ASIC 依存）

- `SwitchHash` 構造体 (`switch_container.h:18-26`):

  ```cpp
  struct {
      std::set<sai_native_hash_field_t> value;
      bool is_set = false;
  } ecmp_hash;
  // lag_hash も同形
  ```

- CONFIG_DB の `SWITCH_HASH|GLOBAL` エントリに `ecmp_hash` / `lag_hash` フィールドが**含まれない場合**、`SwitchHelper::parseSwHash()` は対応する `is_set` を `false` のままにする。
- `setSwitchHash()` は `hash.ecmp_hash.is_set == false` の経路 (L815-822) で **SAI set を呼ばず、既存 SAI 設定を変更しない**。
- すなわち SONiC orchagent 自身は IPv4 / IPv6 別の field 集合をハードコードしておらず、**初期の有効 hash field 集合は SAI vendor 実装 / ASIC のデフォルト**（`SAI_SWITCH_ATTR_ECMP_HASH` / `SAI_SWITCH_ATTR_LAG_HASH` が指す hash オブジェクトの `SAI_HASH_ATTR_NATIVE_HASH_FIELD_LIST` 初期値）に従う。
- IPv4 / IPv6 を分離する設定経路は SWITCH_HASH には存在せず（YANG `hash-field` enum も IPv4/IPv6 を区別しない `SRC_IP` / `DST_IP` の単一集合）、`PORT.lag_hash` や `FG_NHG` 等の別テーブルでも区別はない。

### `ecmp_hash_algorithm` / `lag_hash_algorithm` — コード側デフォルトなし

- 同じく `SwitchHash::ecmp_hash_algorithm.is_set = false` 初期化。
- CONFIG_DB エントリにフィールドが無ければ SAI へは何も書かず、SAI 側のデフォルトアルゴリズム（典型的には `SAI_HASH_ALGORITHM_CRC`）がそのまま使われる。

### capability 不在時の挙動（**SET 失敗ではなく skip**）

`setSwitchHash()` の各 if ブロック L793-811 / L823-846 / L858-887 / L893-922 で次の挙動になる:

```cpp
if (swCap.isSwitchEcmpHashSupported())
{
    if (!swCap.validateSwitchHashFieldCap(hash.ecmp_hash.value)) { LOG_ERROR; return false; }
    if (!setSwitchHashFieldListSai(hash, true))                  { LOG_ERROR; return false; }
    cfgUpd = true;
}
else
{
    SWSS_LOG_WARN("Switch ECMP hash configuration is not supported: skipping ...");
}
```

つまり capability 自体が ASIC で未サポートな場合は:

- ユーザの SET は**エラーにならず**、`return false` もせず、警告ログのみで握り潰される。
- 該当 field の SAI 書き込みは行われず、CONFIG_DB と SAI が異なる状態になる（`setSwitchHash()` 全体としては `cfgUpd=false` のままさらに `swHlpr.setSwHash(hash)` も呼ばれないので、内部キャッシュは旧値を維持）。
- 同じ動作が `ecmp_hash_algorithm` / `lag_hash_algorithm` にもある。

これに対し capability は対応しているが**指定 field 集合 / アルゴリズムが capability セットに含まれない**場合は `LOG_ERROR("Failed to validate switch ECMP hash: capability is not supported")` で `setSwitchHash()` が `return false` し、上位の `doCfgSwitchHashTableTask()` が `LOG_ERROR("Failed to set switch hash: ASIC and CONFIG DB are diverged")` を出す（既存 page の "例外条件" 節に記載）。

### 初期化時の `querySwitchHashDefaults()` の意味

- `SwitchOrch` コンストラクタ L169 で `querySwitchHashDefaults()` を呼ぶ。
- `m_switchHashDefaults.ecmpHash.oid` / `m_switchHashDefaults.lagHash.oid` に SAI 既定 hash OID を**キャッシュするだけ**で、SONiC が SAI に向かって新規 set はしない。
- 失敗時は `LOG_WARN("Failed to get switch ECMP/LAG hash OID")` のみ。OID 取得に失敗しても起動は継続。

### DEL 不可（再掲）

`hash.X.is_set == false` かつ `hObj.X.is_set == true` の経路で `LOG_ERROR("Failed to remove switch ECMP/LAG hash ... operation is not supported")` で `return false`。つまり **CONFIG_DB エントリからフィールドを削除しても "削除されない"** — 一度設定すると、orchagent 内部キャッシュに残った値が "未消去" として扱われる。

## YANG との対比

`sonic-hash.yang` の `ecmp_hash` / `lag_hash` leaf-list および `*_algorithm` leaf には **`default` 文が無い**。`hash-field` enum と `hash-algorithm` enum の宣言のみで、未指定時のデフォルト集合は YANG レベルで規定されていない。よって SAI/ASIC のベンダー実装に委ねられる。

## トレース証跡サマリ

- 訪問ファイル: 3 ファイル (`switchorch.cpp` / `switch_container.h` / `switch_capabilities.cpp`)
- 訪問関数: 6 関数
- 検出 fallback: 5 件
  - `ecmp_hash` / `lag_hash` field set: コード側デフォルトなし（SAI 依存）
  - `ecmp_hash_algorithm` / `lag_hash_algorithm`: コード側デフォルトなし
  - capability 未サポート時: `LOG_WARN` で skip（SET 失敗にはならない）
  - capability 対応だが値が cap 外: `LOG_ERROR` で `return false`
  - 初期化 `querySwitchHashDefaults()` は OID キャッシュのみで SET なし
- IPv4 / IPv6 を分離する hash-field 集合の概念は SWITCH_HASH の orchagent 経路には存在しない（YANG enum も統合）
