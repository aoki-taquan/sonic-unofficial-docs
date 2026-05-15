# Phase A 調査メモ: EXP_TO_FC_MAP フィールド暗黙デフォルト

## 調査日: 2026-05-14

## 対象テーブル: EXP_TO_FC_MAP

## Consumer: sonic-swss/orchagent/qosorch.cpp (ExpToFcMapHandler)

---

## field 列挙

| field | role |
|-------|------|
| `name` | outer list key (map name) |
| `exp` | inner list key (MPLS EXP bits 0-7) |
| `fc` | value (Forwarding Class) |

---

## コード由来デフォルト / 暗黙挙動一覧

### 1. EXP_MAX_VAL ハードコード

- **ソース**: `qosorch.cpp:120` — `#define EXP_MAX_VAL 7`
- **種別**: ハードコード
- **挙動**: `exp` フィールドの値が 0..7 範囲外 → エントリ全体 silent drop (`task_invalid_entry`)

### 2. FC 上限プラットフォーム依存

- **ソース**: `nhgmaporch.cpp:299-325` — `NhgMapOrch::getMaxNumFcs()`
- **種別**: プラットフォーム依存 / SAI 問い合わせ
- **挙動**: `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` を初回取得してキャッシュ (`static int max_num_fcs = -1`)。スイッチ未サポート時は `max_num_fcs=0` → 全 FC 値が invalid
- **YANG との乖離**: YANG は `[0-7]` (最大 7)、実装は SAI 返値（最大 255 等）

### 3. YANG パターン "[0-7]?" — 空文字列許容乖離

- **ソース**: `sonic-exp-fc-map.yang:54-57` — `pattern "[0-7]?"`
- **種別**: YANG-実装 discrepancy
- **挙動**: YANG `?` は空文字列を valid とするが、qosorch は `stoi()` で例外 → `task_invalid_entry`。実質空文字列は使用不可

### 4. 未定義 EXP の fallback (dead consumer pattern)

- **ソース**: 実装なし
- **種別**: dead field / ASIC 依存
- **挙動**: EXP_TO_FC_MAP にエントリがない EXP 値に対する FC は実装未定義。ASIC の挙動に依存（一般的に FC=0）

### 5. マップ未参照時の silent do-nothing

- **ソース**: `qosorch.cpp:2119-2133` — `handlePortQosMapTable`
- **種別**: 経路依存乖離
- **挙動**: EXP_TO_FC_MAP を定義しても `PORT_QOS_MAP.exp_to_fc_map` から参照されない限り SAI に反映されない

### 6. DEL 時参照保護

- **ソース**: `qosorch.cpp:181-186`
- **種別**: 書込み順依存
- **挙動**: PORT_QOS_MAP から参照中の EXP_TO_FC_MAP を DEL すると `m_pendingRemove=true` + `task_need_retry`

### 7. SAI CREATE 失敗時の task_failed

- **ソース**: `qosorch.cpp:1207-1210`
- **種別**: silent drop (orchagent 側)
- **挙動**: `sai_create_qos_map` 失敗 → `SWSS_LOG_ERROR` のみ、CONFIG_DB は汚染されたまま残る

---

## 出力ページ

`docs/reference/config-db/exp-to-fc-map.md` の `<!-- defaults -->` ブロックに反映済み。
