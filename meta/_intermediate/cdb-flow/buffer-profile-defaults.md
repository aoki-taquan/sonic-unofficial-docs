# BUFFER_PROFILE — Phase A フィールド暗黙デフォルト調査

## 調査対象ファイル（全行精読済み）

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-buffer-profile.yang` | YANG 定義 |
| `sonic-swss/cfgmgr/buffermgrdyn.h` | `buffer_profile_t` 構造体定義 |
| `sonic-swss/cfgmgr/buffermgrdyn.cpp` L2671-2886 | `handleBufferProfileTable()` 全行 |
| `sonic-swss/cfgmgr/buffermgrdyn.cpp` L890-922 | `updateBufferProfileToDb()` 全行 |
| `sonic-swss/orchagent/bufferorch.cpp` L600-880 | `processBufferProfile()` 全行 |
| `sonic-utilities/config/main.py` L8482-8633 | CLI `buffer profile add/set` |

---

## フィールド別 暗黙デフォルト・挙動一覧

### `pool`

- **YANG**: mandatory=true、default 無し
- **書き込み経路依存乖離**:
  - CLI: `--pool` 未指定時 → `'ingress_lossless_pool'` をハードコードデフォルトとして使用 (`main.py:8564-8565`)
  - minigraph / j2 テンプレート: platform 別 `buffers_defaults_<topo>.j2` で決定（プラットフォーム依存）
  - REST/gNMI: 対応なし
- **実行時 fallback**: `buffermgrdyn` — pool が `m_bufferPoolLookup` に未存在 → `task_need_retry`（silent fallback なし、明示的リトライ）
- **orchagent 側**: pool 参照未解決 → `task_need_retry`
- **create-only**: 既存 SAI オブジェクトへの `pool` フィールド更新は **スキップ**（`bufferorch.cpp:656-659`）

### `size`

- **YANG**: mandatory=true、default 無し
- **書き込み経路依存乖離**:
  - CLI: `size` 未指定時、`headroom_type=dynamic` でなければ自動計算:
    - SHP 有効: `size = xon`
    - SHP 無効: `size = xon + xoff`
    (`main.py:8607-8612`)
  - dynamic buffer model: `buffermgrdyn` が速度・ケーブル長・MTU から自動計算して上書き
- **YANG との乖離**: YANG は mandatory だが CLI は自動計算で補完するため、ユーザーが省略できる

### `static_th`

- **YANG**: optional、default 無し
- **orchagent 挙動**: 存在する場合 `SAI_BUFFER_PROFILE_ATTR_THRESHOLD_MODE = STATIC` + `SAI_BUFFER_PROFILE_ATTR_SHARED_STATIC_TH` をセット
- **create-only**: 既存オブジェクトへの threshold mode 変更はスキップ（`bufferorch.cpp:710-714`）
- **複合必須制約**: `static_th` と `dynamic_th` は相互排他。`buffermgrdyn` の `threshold_mode` 整合チェックで不一致は `task_failed`（`buffermgrdyn.cpp:2724-2735`）

### `dynamic_th`

- **YANG**: optional、default 無し（range: -8..7）
- **書き込み経路依存乖離 (CLI)**:
  - `--dynamic_th` 未指定で static プロファイル作成時 → `DEFAULT_LOSSLESS_BUFFER_PARAMETER` テーブルの `default_dynamic_th` を参照して自動補完 (`main.py:8619-8627`)
  - 対応エントリが複数あれば `ctx.fail`
  - REST/gNMI / minigraph 経路では自動補完なし
- **create-only**: 既存 SAI オブジェクトへの threshold mode 変更はスキップ（`bufferorch.cpp:692-702`）
- **silent fallback**: CLI 経由のみ `DEFAULT_LOSSLESS_BUFFER_PARAMETER` から暗黙補完される（他経路では発生しない）

### `xon`

- **YANG**: optional、**default 0**
- **buffermgrdyn 実装**: field 存在時 `profileApp.xon = value` にセット。省略時は空文字列（初期値）のまま
- **updateBufferProfileToDb**: `profile.lossless == true` の場合のみ APPL_DB に `xon` を書き込む。lossless=false のプロファイルでは **xon は APPL_DB に出力されない**（dead field 的挙動）
- **YANG vs 実装乖離**: YANG default=0 だが、lossless=false プロファイルでは実装上 APPL_DB に送出されず SAI にも設定されない

### `xon_offset`

- **YANG**: optional、**default 0**
- **updateBufferProfileToDb**: `profile.lossless == true` かつ `!profile.xon_offset.empty()` の場合のみ APPL_DB に出力。空文字列時はスキップ（`buffermgrdyn.cpp:906-908`）
- **YANG vs 実装乖離**: YANG default=0 だが実装は「空文字列ならスキップ」で SAI には非設定

### `xoff`

- **YANG**: optional、**default 0**
- **副作用**: `xoff` フィールドが存在するとき `profileApp.lossless = true` がセットされる（`buffermgrdyn.cpp:2755`）。これにより `direction` が `BUFFER_INGRESS` 強制チェック対象になる
- **orchagent 側**: `is_lossless = true` がセットされ、lossless プロファイルとして publisher に通知される
- **lossless=false 時**: APPL_DB への xoff 書き込みなし（`updateBufferProfileToDb` の条件分岐）

### `headroom_type`

- **YANG**: optional、**default `static`**
- **実装 default**: YANG の `static` と一致。省略時 `profileApp.dynamic_calculated = false`、`lossless = false` で初期化（PROFILE_INITIALIZING 状態）
- **値 `dynamic` 時の副作用**:
  - `profileApp.dynamic_calculated = true`
  - `profileApp.lossless = true`（強制）
  - `profileApp.direction = BUFFER_INGRESS`（強制）
  - APPL_DB へは即座に書き込まず、ポートから参照されてから計算・書き込み
- **static-buffer モードでの挙動**: `DEVICE_METADATA.buffer_model=static` の場合、dynamic headroom 計算は無効化（buffermgrdyn 自体が起動しない）

### `packet_discard_action`

- **YANG**: optional、**default 無し**（enum: drop/trim）
- **実装 default**: フィールド省略時 `profileApp.packet_discard_action` は空文字列のまま → `updateBufferProfileToDb` でスキップ（`buffermgrdyn.cpp:911-913`）。APPL_DB・SAI には設定されない
- **SAI 側**: `SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION` 未設定の場合、SAI デフォルト（通常 `DROP`）が使われる（ハードコード固定値、SAI 実装依存）
- **不正値**: `drop`/`trim` 以外は `task_failed`（`bufferorch.cpp:740-743`）
- **trim 制約（複合必須制約）**:
  - ingress PG 割り当て禁止（`bufferorch.cpp:1382`）
  - ingress profile list 割り当て禁止（`bufferorch.cpp:1725`）
  - egress profile list 割り当て禁止（`bufferorch.cpp:1915`）
  - 大文字小文字: enum は小文字のみ受理（YANG enum、CLI 比較は value == "drop"/"trim" の完全一致）

---

## 書き込み経路依存乖離サマリ

| フィールド | CLI 経路 | minigraph/j2 | REST/gNMI | buffermgrd 自動 |
|-----------|----------|--------------|-----------|----------------|
| `pool` | 未指定時 `ingress_lossless_pool` に fallback | platform 依存 j2 で決定 | 非対応 | pool_name から継承 |
| `size` | `xon+xoff` or `xon` で自動計算 | j2 テンプレート値 | 非対応 | 速度・ケーブル長から計算 |
| `dynamic_th` | `DEFAULT_LOSSLESS_BUFFER_PARAMETER` から自動補完 | j2 テンプレート値 | 非対応 | 速度・ケーブル長から計算 |
| `headroom_type` | 省略時は static（`size`/`xon`/`xoff` 指定有無で判断） | 明示指定 | 非対応 | dynamic に強制（動的計算プロファイル） |

---

## dead field / silent drop

- `xon`, `xon_offset`, `xoff`: lossless=false プロファイルでは APPL_DB に出力されない（silent drop）
- `xon_offset`: 空文字列の場合 APPL_DB 出力スキップ
- `packet_discard_action`: 省略時 APPL_DB・SAI に出力されない。SAI デフォルト（DROP）が適用される（SAI 実装依存の silent fallback）

---

## ハードコード固定値

- CLI `pool` デフォルト: `'ingress_lossless_pool'` (`sonic-utilities/config/main.py:8565`)
- `headroom_type=dynamic` 時の `direction`: `BUFFER_INGRESS` 固定 (`buffermgrdyn.cpp:2794`)
- SAI `packet_discard_action` 省略時: SAI 実装依存の DROP（ASIC vendor 固有）

---

## プラットフォーム依存

- **buffer model**: `DEVICE_METADATA.buffer_model=static` では `buffermgrdyn` が起動せず dynamic headroom 計算は不可
- **j2 テンプレート**: platform/SKU ごとに `xon`/`xoff`/`size`/`dynamic_th` の具体値が異なる（Mellanox SN2700 と Arista 7050CX3 等で値差あり）
- **SAI `packet_discard_action`**: `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` 返却時は `task_ignore`（ASIC が trimming をサポートしない場合）

---

## YANG と実装の discrepancy

| フィールド | YANG | 実装 |
|-----------|------|------|
| `xon` default 0 | YANG で default=0 | lossless=false では APPL_DB に出力されない（実質 dead） |
| `xon_offset` default 0 | YANG で default=0 | 空文字列時スキップ、APPL_DB 出力なし |
| `xoff` default 0 | YANG で default=0 | lossless=false では APPL_DB 出力なし |
| `packet_discard_action` | YANG は default 無し | 省略時 SAI 実装依存の DROP（YANG に記述なし） |
| `size` mandatory | YANG mandatory=true | CLI は自動計算で補完（YANG 制約よりゆるい） |
