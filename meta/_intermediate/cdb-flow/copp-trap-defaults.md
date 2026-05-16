# COPP_TRAP Phase A — フィールド暗黙デフォルト調査

## 対象フィールド

YANG `sonic-copp` で定義される `COPP_TRAP` フィールド:
1. `trap_ids` (mandatory true, no default)
2. `trap_group` (optional leafref, no default)
3. `always_enabled` (optional boolean, no default)

---

## フィールドごとの暗黙デフォルト分析

### `trap_ids`

- **YANG**: `mandatory true`。YANG レベルでデフォルト値なし。
- **coppmgr 初期化時**: `m_coppTrapInitCfg` から読み込み。`copp_cfg.json` (/etc/sonic/copp_cfg.json, ビルド時 `copp_cfg.j2` から生成) に各トラップ名ごとの値が定義されている。ユーザー CONFIG_DB の値が存在すれば上書き（init 値 < user 値）。
- **doCoppTrapTask SET**: `trap_ids.empty()` かつ `trap_group.empty()` の場合は処理スキップ（incomplete configuration）。つまり `trap_ids` が欠如した SET は実質 no-op。
- **暗黙デフォルト**: なし。ただし `copp_cfg.json` 由来の init cfg がフォールバック値として機能し、ユーザー DELETE 後も init 値が自動復元される（coppmgr.cpp L773-805）。
- **種別**: `silent fallback to init cfg` + `暗黙 reset on DEL`

### `trap_group`

- **YANG**: optional、leafref。デフォルト値なし。
- **coppmgr 初期化時**: `copp_cfg.json` の init cfg に必ず存在する（bgp → queue4_group1 等）。
- **doCoppTrapTask SET**: `trap_group.empty()` の場合、`is_always_enabled` のみの更新ロジックに分岐。両方空なら処理スキップ。
- **trap_group が存在しない GROUP を参照した場合**: `checkTrapGroupPending()` が true → APPL_DB への書き込みが保留 (`task_need_retry` 相当)。copporch.cpp L584 参照。
- **暗黙デフォルト**: なし（init cfg での事前定義に依存）。GROUP 未作成時の silent 保留がある。
- **種別**: `前提条件依存 (GROUP 到着待ち)` + `暗黙 reset on DEL`

### `always_enabled`

- **YANG**: optional boolean、デフォルト値なし。
- **coppmgr 初期化時**: フィールドが存在しない場合、`is_always_enabled = "false"` として扱う（coppmgr.cpp L340: `string is_always_enabled = "false";` + L354-357 でフィールド存在時のみ上書き）。
- **DELETE 後の復元時**: `is_always_enabled.empty()` なら `"false"` に設定（coppmgr.cpp L792-795）。
- **意味的挙動**:
  - 未設定 / 空文字列 → `"false"` として扱われ、feature が enabled のときのみトラップをインストール。
  - `"true"` → feature 状態に関わらず常時インストール。
  - `setFeatureTrapIdsStatus()` では `always_enabled == "true"` を文字列比較（coppmgr.cpp L90）。
- **大文字小文字制約**: 文字列 `"true"` と完全一致が必要。YANG boolean 型だが実装は文字列比較のため `"True"` / `"TRUE"` は不一致（`"false"` 扱い）。
- **種別**: `暗黙デフォルト値 "false"` + `大文字小文字制約` + `暗黙 reset on DEL`

---

## コード由来デフォルト一覧表

| フィールド | YANG default | 実装上の暗黙デフォルト | 種別 | evidence |
|---|---|---|---|---|
| `trap_ids` | なし (mandatory) | init cfg (`copp_cfg.json`) からの自動復元。DEL 後は init 値に reset | silent fallback / 暗黙 reset on DEL | coppmgr.cpp L773-805 |
| `trap_group` | なし | init cfg からの自動復元。DEL 後は init 値に reset。GROUP 未到着時は書き込み保留 | 前提条件依存 / 暗黙 reset on DEL | coppmgr.cpp L773-805, L62-79 |
| `always_enabled` | なし | 未設定・空文字列 → コード内で `"false"` として扱う | 暗黙デフォルト `"false"` / 大文字小文字制約 | coppmgr.cpp L340, L792-795, L90 |

---

## 追加判明事項

### init cfg 自動復元（暗黙 reset on DEL）

ユーザーが `COPP_TRAP|bgp` を CONFIG_DB から削除した場合、coppmgr は `m_coppTrapInitCfg` に `bgp` が存在するかチェックし、存在すれば init cfg の値でトラップを再登録する（coppmgr.cpp L773-805）。これは全フィールドに適用される。ユーザー DEL が「削除」でなく「init 値へのリセット」として機能する点は重要な実装意図。

### マージ優先度（書き込み順依存）

`mergeConfig()` は init cfg を基底として、user cfg のフィールドで上書きする（coppmgr.cpp L196-258）。同一フィールドが user cfg に存在すれば user 値優先。user cfg に存在しないフィールドのみ init 値が補完される。`NULL` フィールドが存在する key は init cfg 側もスキップ（無効化）。

### 有効な trap_id 文字列（ハードコード固定値）

`trap_id_map`（copporch.cpp L55-100）に定義された 41 種の文字列のみが有効。未定義文字列は `map.at()` で `std::out_of_range` 例外 → `task_invalid_entry` → サイレント削除（ログは ERROR レベル）。

### NAT trap_id のプラットフォーム依存

`src_nat_miss` / `dest_nat_miss` は `gIsNatSupported == false` のプラットフォームでは個別スキップ。他の trap_id は継続適用（partial success）。

---

## 証跡ファイル

- `/home/coder/sonic-unofficial-docs/.cache/sonic-sources/sonic-swss/cfgmgr/coppmgr.cpp`
- `/home/coder/sonic-unofficial-docs/.cache/sonic-sources/sonic-swss/cfgmgr/coppmgr.h`
- `/home/coder/sonic-unofficial-docs/.cache/sonic-sources/sonic-swss/orchagent/copporch.cpp`
- `/home/coder/sonic-unofficial-docs/.cache/sonic-sources/sonic-buildimage/files/image_config/copp/copp_cfg.j2`
- `/home/coder/sonic-unofficial-docs/.cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-copp.yang`
