# BUFFER_PROFILE — Phase A: コード由来の暗黙デフォルト調査結果

対象ページ: `docs/reference/config-db/buffer-profile.md`
調査日: 2026-05-14
調査対象ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` (dynamic buffer model)
- `sonic-swss/cfgmgr/buffermgr.cpp` (static buffer model passthrough)
- `sonic-swss/orchagent/bufferorch.cpp` (APPL_DB → SAI)
- `sonic-swss/cfgmgr/buffermgrdyn.h` (buffer_profile_t struct)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-buffer-profile.yang`
- `sonic-buildimage/files/build_templates/buffers_config.j2`
- `sonic-buildimage/device/mellanox/.../buffers_defaults_objects.j2`

---

## フィールド別デフォルト・暗黙挙動

### `xon` (uint64, YANG default 0)

- YANG default: `0`
- **コード実装**: `buffer_profile_t.xon` は文字列型で、初期値は空文字 `""`
- `updateBufferProfileToDb()` L905: `xon` は `profile.lossless == true` のときのみ APPL_DB に書かれる
- **lossless=false (lossy profile) のとき xon は APPL_DB に書かれない** (silently omitted)
- SAI attr: `SAI_BUFFER_PROFILE_ATTR_XON_TH`
- 乖離: YANG は `default 0` と宣言しているが、lossy プロファイルでは SAI へ渡されない。SAI のデフォルトはプラットフォーム依存。

### `xon_offset` (uint64, YANG default 0)

- YANG default: `0`
- **コード実装**: L906-908 `if (!profile.xon_offset.empty())` のときのみ APPL_DB に書かれる
- **フィールド未設定時は APPL_DB に含まれない** (silent drop)
- SAI attr: `SAI_BUFFER_PROFILE_ATTR_XON_OFFSET_TH`
- 乖離: YANG は `default 0` と宣言しているが、未設定なら SAI へ送られない。SAI が独自デフォルトを使う。

### `xoff` (uint64, YANG default 0)

- YANG default: `0`
- **コード実装**: `xoff` フィールドに値が設定されると `profileApp.lossless = true` がセットされる (buffermgrdyn.cpp L2755)
- `updateBufferProfileToDb()` L909: `xoff` は `profile.lossless == true` のときのみ APPL_DB に書かれる
- **xoff=0 を明示してもlossless=trueになり xon/xoff が SAI に送られる**
- **xoff 未設定なら lossy 扱いで xon/xoff とも APPL_DB/SAI に送られない**
- 乖離: YANG default 0 だが、実装では xoff フィールドの「存在」が lossless 判定のトリガー

### `headroom_type` (enum static/dynamic, YANG default static)

- YANG default: `static`
- **コード実装**: L2786-2795: `profileApp.dynamic_calculated = (value == "dynamic")`
- フィールド不在の場合、新規プロファイル初期化時 L2692 で `dynamic_calculated = false` に設定される → static 扱い
- `headroom_type=dynamic` セット時の副作用:
  - `profileApp.lossless = true` (自動セット)
  - `profileApp.direction = BUFFER_INGRESS` (自動セット)
  - プロファイルは **ポート参照まで APPL_DB に書かれない** (L2820-2822)
- static model (`buffermgr.cpp`) では `headroom_type` フィールドを無視してそのまま passthrough

### `packet_discard_action` (enum drop/trim, YANG default なし)

- YANG: no default
- **コード実装**: L911 `if (!profile.packet_discard_action.empty())` のときのみ APPL_DB に書かれる
- **未設定なら APPL_DB/SAI に attr が送られない** → SAI プラットフォームデフォルト (通常 drop)
- SAI attr: `SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION`
- trim 設定時の制約: ingress PG、ingress profile list、egress profile list への適用が task_failed (trim は egress shared buffer のみ有効)
- 乖離: trim を egress shared buffer に使う場合のみ有効。YANG に制約記述なし。

### `static_th` / `dynamic_th` (threshold_mode: コード内部管理)

- YANG: どちらも optional (no default)
- **コード実装 (dynamic model)**:
  - L2767-2784: `threshold_mode` が空のとき = pool の mode から `dynamic_th` または `static_th` に決定
  - **どちらも未設定かつ pool も未確認の場合、`threshold_mode` が空のまま**
  - L901: `threshold_mode.empty()` のとき `getPgPoolMode() + "_th"` を使用 → pool の mode を参照
  - L917: 常に `mode` フィールドと `profile.threshold` を APPL_DB に書く。`profile.threshold` が空文字の場合、**空文字が APPL_DB に書かれる** → SAI parse エラーのリスク
  - pool の threshold mode と profile の threshold field が不一致 → `task_failed` (L2726-2735)
- **Static model (buffermgr.cpp)**: フィールドを passthrough、バリデーションなし

### `size` (uint64, mandatory)

- YANG: mandatory
- コード: 明示必須。省略時 YANG validation でリジェクト。
- dynamic headroom model では lua plugin が size を計算して上書き

### `pool` (leafref, mandatory)

- YANG: mandatory
- コード: L2707-2715: pool 未到着 → `task_need_retry`。空値 → `task_failed`。
- pool の `mode` が profile の threshold field と不一致 → `task_failed`

---

## 検出された暗黙デフォルト・挙動

| 種別 | フィールド | 内容 | ソース |
|------|-----------|------|--------|
| silent omit | `xon` | lossy プロファイルでは APPL_DB/SAI に送られない | `buffermgrdyn.cpp:903` |
| silent omit | `xon_offset` | 未設定時 APPL_DB/SAI に送られない | `buffermgrdyn.cpp:906` |
| silent omit | `xoff` | lossy プロファイルでは APPL_DB/SAI に送られない | `buffermgrdyn.cpp:909` |
| silent omit | `packet_discard_action` | 未設定時 APPL_DB/SAI に送られない、SAI platform default が適用 | `buffermgrdyn.cpp:911` |
| flag derivation | `lossless` | xoff 設定 or headroom_type=dynamic で自動 true | `buffermgrdyn.cpp:2755,2793` |
| flag derivation | `direction=INGRESS` | headroom_type=dynamic で自動設定 | `buffermgrdyn.cpp:2794` |
| APPL_DB defer | (profile 全体) | headroom_type=dynamic ではポート参照まで APPL_DB に書かれない | `buffermgrdyn.cpp:2820` |
| threshold fallback | `dynamic_th`/`static_th` | 未設定時は pool の mode を threshold_mode に採用 | `buffermgrdyn.cpp:901` |
| empty-string write | `threshold` | th フィールド未設定かつ pool 未確認時、空文字が APPL_DB に書かれる可能性 | `buffermgrdyn.cpp:917` |
| YANG-impl乖離 | `xon`,`xon_offset`,`xoff` | YANG default 0 だが lossy では SAI に送らない | YANG vs impl |
| platform dependency | `xon` | Mellanox 8-lane ポートは xon が 2 倍計算 | `buffermgrdyn.cpp:510-520` |
| dead consumer | `headroom_type` in static model | `buffermgr.cpp` では解釈されず passthrough | `buffermgr.cpp:487-489` |
| APPL_DB defer | (lossless profile) | pool 未準備時 APPL_DB 書き込みを skip + pending フラグ | `buffermgrdyn.cpp:892-896` |
