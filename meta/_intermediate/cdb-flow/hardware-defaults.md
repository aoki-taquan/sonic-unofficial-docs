# HARDWARE — Phase A コード由来の暗黙デフォルト (grep 証跡)

## 探索対象 field 一覧

`HARDWARE|ACCESS_LIST` のフィールド: `COUNTER_MODE`, `LOOKUP_MODE`, `TCAM_SHARING`

---

## entry grep (1 回限り)

```
grep -rln '"HARDWARE"' .cache/sonic-sources/
→ 0 件 (引用符付き完全一致では無し)

grep -rn 'HARDWARE|' .cache/sonic-sources/
→ sonic-mgmt-common/tools/test/dbinit.py:88:  db_hmset(ConfigDB, "HARDWARE|ACCESS_LIST", {...})
→ sonic-gnmi/testdata/db_dump.json:5426: "HARDWARE|ACCESS_LIST":{...}
→ sonic-gnmi/testdata/db_dump.json:7101: "HARDWARE_TABLE|ACCESS_LIST":{...}
```

**consumer 探索 (orchagent / swss)**:
```
grep -rn 'COUNTER_MODE|LOOKUP_MODE|TCAM_SHARING|ACCESS_LIST' sonic-swss/
→ 0 件 (orchagent は HARDWARE テーブルを購読しない)

grep -rn 'COUNTER_MODE|LOOKUP_MODE|TCAM_SHARING' sonic-swss-common/
→ 0 件

grep -rn 'COUNTER_MODE|LOOKUP_MODE|TCAM_SHARING' sonic-utilities/
→ 0 件
```

**YANG 探索**:
```
ls sonic-buildimage/src/sonic-yang-models/yang-models/ | grep hardware
→ 0 件 (HARDWARE テーブルの YANG モジュールは存在しない)
```

---

## field: COUNTER_MODE

**観測値**:
- `sonic-mgmt-common/tools/test/dbinit.py:89`: `"COUNTER_MODE": "per-rule"`
- `sonic-gnmi/testdata/db_dump.json:5426`: `"COUNTER_MODE":"per-rule"`
- `sonic-gnmi/testdata/db_dump.json:7101` (HARDWARE_TABLE 名前空間): `"COUNTER_MODE":"PER-RULE"`

**コード consumer**:
```
grep -rn 'COUNTER_MODE' sonic-swss/ → 0 件
grep -rn 'COUNTER_MODE' sonic-utilities/ → 0 件
```

**YANG**: なし（sonic-yang-models に HARDWARE モジュール未存在）

**code fallback**: community sonic-swss は `COUNTER_MODE` を読み取らない。**dead consumer** — 値を書き込んでも orchagent に影響なし。

値は大文字小文字の揺れあり (`per-rule` vs `PER-RULE`)。大文字小文字制約は不明（consumer 不在のため強制なし）。

---

## field: LOOKUP_MODE

**観測値**:
- `sonic-mgmt-common/tools/test/dbinit.py:90`: `"LOOKUP_MODE": "optimized"`
- `sonic-gnmi/testdata/db_dump.json:5426`: `"LOOKUP_MODE":"advanced"`
- `sonic-gnmi/testdata/db_dump.json:7101` (HARDWARE_TABLE 名前空間): `"LOOKUP_MODE":"LEGACY"`

値のバリアント: `optimized`, `advanced`, `LEGACY`

**コード consumer**:
```
grep -rn 'LOOKUP_MODE' sonic-swss/ → 0 件
grep -rn 'LOOKUP_MODE' sonic-utilities/ → 0 件
grep -rn 'LOOKUP_MODE' sonic-swss-common/ → 0 件
```

**YANG**: なし

**code fallback**: community sonic-swss は `LOOKUP_MODE` を読み取らない。**dead consumer**。

プラットフォーム依存フィールド: Dell gNMI/translib スタック（community code 外）でのみ消費される可能性。

---

## field: TCAM_SHARING

**観測値**:
- `sonic-gnmi/testdata/db_dump.json:5426`: `"TCAM_SHARING@":""`  
  - `@` サフィックスは leaf-list 型を示す Redis エンコーディング規約。空リスト。
  - `sonic-mgmt-common/tools/test/dbinit.py` には `TCAM_SHARING` なし（`optimized`/`per-rule` の2フィールドのみ）。

**コード consumer**:
```
grep -rn 'TCAM_SHARING' sonic-swss/ → 0 件
grep -rn 'TCAM_SHARING' sonic-utilities/ → 0 件
```

**YANG**: なし

**code fallback**: community sonic-swss は `TCAM_SHARING` を読み取らない。**dead consumer**。

`@` サフィックス付きのフィールド名は sonic Redis 規約では leaf-list を示す。空リストはデフォルト状態を意味する。

---

## テーブル名の揺れ

`sonic-gnmi/testdata/db_dump.json` に 2 種類のキー名が並存:
1. `HARDWARE|ACCESS_LIST` (行 5426, CONFIG_DB)
2. `HARDWARE_TABLE|ACCESS_LIST` (行 7101)

`HARDWARE_TABLE` は別のデータ空間（例: APP_DB や旧形式スキーマ）の可能性あり。community sonic-swss はどちらも購読しない。

---

## YANG-コード 乖離サマリ

| フィールド | YANG default | コード fallback | 乖離種類 |
|---|---|---|---|
| `COUNTER_MODE` | なし (YANG 未定義) | なし (dead consumer) | **dead consumer** |
| `LOOKUP_MODE` | なし (YANG 未定義) | なし (dead consumer) | **dead consumer** |
| `TCAM_SHARING` | なし (YANG 未定義) | なし (dead consumer) | **dead consumer** + 大文字小文字不定 |

---

## 0-hit フィールド (fallback なし)

| フィールド | 探索 | 0-hit 理由 |
|---|---|---|
| `COUNTER_MODE` | sonic-swss/orchagent 全ファイル | consumer 不在 |
| `LOOKUP_MODE` | sonic-swss/orchagent 全ファイル | consumer 不在 |
| `TCAM_SHARING` | sonic-swss/orchagent 全ファイル | consumer 不在 |

---

## 補足: スコープ

- `HARDWARE|ACCESS_LIST` は community sonic-swss/orchagent では**未消費**。
- sonic-mgmt-common (Dell gNMI Management Framework) 系の translib/transformer で消費されると推定されるが、該当コードは本 cache に存在しない。
- YANG 検証スキーマ (CVL) も未定義のため、不正値の書き込みも排除されない。
