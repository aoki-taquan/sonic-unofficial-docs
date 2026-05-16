# BGP_ALLOWED_PREFIXES — Phase A: コード由来の暗黙デフォルト調査

## 対象フィールド

YANG で定義されたデータフィールドは以下の 3 つ（全 4 list 共通）:
- `default_action`
- `prefixes_v4`
- `prefixes_v6`

キーフィールド (`deployment`, `id`, `neighbor`, `neighbor_type`, `community`) には YANG default なし。

---

## フィールド別: 書き込み時デフォルト vs 実行時 fallback

### 1. `default_action`

**YANG default**: なし（mandatory ではないが default 節なし）

**書き込み時デフォルト (SET)**:
- `set_handler` → `__get_default_action_community(data)` を呼ぶ
- `data` に `"default_action"` キーが **存在する** 場合: 値 `"permit"` / `"deny"` を検証してそのまま使用
- `data` に `"default_action"` キーが **存在しない** 場合（省略時）:
  1. `constants["bgp"]["allow_list"]["default_action"]` があればその値を使用
  2. constants にもなければ → 暗黙 fallback: **`drop_community`** (= `"permit"` 相当)
  - 実装: `managers_allow_list.py:779-785`

**実行時 fallback (DEL 後の残置ルール)**:
- `__remove_policy` が呼ばれる際も `__get_default_action_community()` を `data=None` で呼び出す
- `data=None` → constants の `default_action` を参照 → なければ `drop_community` を返す
- つまり DEL 後も route-map の seq 65535 には **drop_community** (permit 系) が残る

**constants.yml の実値**:
```yaml
allow_list:
  enabled: true
  default_action: "permit"
  drop_community: 5060:12345
```
→ 省略時の実運用 community = `"5060:12345"`

**書き込み時 vs 実行時の乖離**:
- SET 時に `default_action` 省略 → constants に従う → `"permit"` → `drop_community = "5060:12345"` を付与
- DEL 時 → 同じ constants 参照 → `"5060:12345"` のまま残存
- **乖離なし**。ただし constants を変更した場合、既存ルールは再 SET しない限り古い値のまま

---

### 2. `prefixes_v4`

**YANG default**: なし（leaf-list、ordered-by user、必須制約なし）

**書き込み時デフォルト (SET)**:
- `set_handler` 内: `prefixes_v4 = []` を初期化 (`managers_allow_list.py:70`)
- `"prefixes_v4" in data` が False の場合 → `prefixes_v4` は空リスト `[]` のまま
- `__set_handler_validate` では `prefixes_v4` と `prefixes_v6` が**両方空**だと `log_err` + `return False` (validate 失敗)
  - つまり `prefixes_v4` 単独省略は `prefixes_v6` がある限り許容される

**実行時 fallback (prefix-list 生成)**:
- `__update_prefix_list` が呼ばれると `__get_constant_list("v4")` が prepend される
  - `constants["bgp"]["allow_list"]["default_pl_rules"]["v4"]` の内容
  - 実値: `["deny 0.0.0.0/0 le 17", "permit 127.0.0.1/32"]`
  - → `prefixes_v4` が空リストでも、**constants 由来の 2 エントリ** がデフォルトで prefix-list に挿入される
  - 実装: `managers_allow_list.py:265-266`, `__load_constant_lists:709-724`

**書き込み時 vs 実行時の乖離**:
- CONFIG_DB には空リスト（または省略）が書かれていても、FRR の実 prefix-list には constants 分が必ず入る
- **乖離あり**: DB 上 `prefixes_v4` が空 → FRR 上は `deny 0.0.0.0/0 le 17; permit 127.0.0.1/32` が有効

**`__to_prefix_list` 内の暗黙補完**:
- prefix にマスク長が `/32` (v4) または `/128` (v6) 以外で `le`/`ge` 修飾子がない場合:
  - 自動で `le 32` (v4) / `le 128` (v6) を付与してホスト範囲まで許可する
  - 例: `10.0.0.0/8` → FRR 内では `permit 10.0.0.0/8 le 32` として展開
  - 実装: `managers_allow_list.py:744-753`

---

### 3. `prefixes_v6`

**YANG default**: なし（leaf-list、ordered-by user）

**書き込み時デフォルト (SET)**:
- `prefixes_v6 = []` を初期化 (`managers_allow_list.py:71`)
- `"prefixes_v6" in data` が False → 空リスト
- `prefixes_v4` と両方空なら validate 失敗（上記同様）

**実行時 fallback (prefix-list 生成)**:
- constants 由来の v6 デフォルト:
  - `["deny 0::/0 le 59", "deny 0::/0 ge 65"]`
  - → `/60`〜`/64` 以外を deny する（典型的なリンクローカル / 短すぎる / 長すぎるプレフィクス排除）
  - 実装: `managers_allow_list.py:720-724`
- IPv6 アドレスは `__normalize_ipnetwork` で正規化される (例: `2001:cdba:0:0::/64` → `2001:cdba::/64`)

**書き込み時 vs 実行時の乖離**:
- `prefixes_v4` と同様、DB 上の空リストでも FRR には constants 分が入る
- **乖離あり**: DB 上 `prefixes_v6` 省略 → FRR 上は `deny 0::/0 le 59; deny 0::/0 ge 65` が有効

---

## キーフィールドの暗黙デフォルト

### `community_value` (key の一部)

- key に `|` が 1 つしかない場合（community 部分なし）:
  - `community_value = BGPAllowListMgr.EMPTY_COMMUNITY = "empty"` が自動設定される
  - 実装: `managers_allow_list.py:64,67`
- `EMPTY_COMMUNITY` の場合、コミュニティリストは作成されない（prefix-list のみ生成）

### `neighbor_type` (key の一部)

- `NEIGHBOR_TYPE` を含まない key の場合:
  - `neighbor_type = ''` (空文字) が自動設定される
  - 実装: `managers_allow_list.py:68`

### `prefix_match_tag`

- `constants["bgp"]["allow_list"]["prefix_match_tag"]` が定義されていない場合:
  - `self.prefix_match_tag = None` (`managers_allow_list.py:657`)
  - route-map の `set tag` 行は生成されない（`__update_allow_route_map_entry:434-435`）

---

## enabled フラグ

- `constants["bgp"]["allow_list"]["enabled"]` が `False` or 存在しない場合:
  - SET/DEL 両方ともに warn log のみで `return True`（消化扱い）
  - **テーブル自体の処理が完全スキップ**される
  - 実装: `managers_allow_list.py:699-707`

---

## 証拠ソース

| 項目 | ファイル:行 |
|------|-----------|
| `EMPTY_COMMUNITY = "empty"` | `managers_allow_list.py:15` |
| `prefixes_v4/v6 = []` 初期化 | `managers_allow_list.py:70-71` |
| `__get_default_action_community` fallback | `managers_allow_list.py:764-785` |
| `__load_constant_lists` | `managers_allow_list.py:709-724` |
| `__to_prefix_list` (le/ge 自動付与) | `managers_allow_list.py:736-754` |
| `__get_routemap_tag` | `managers_allow_list.py:652-664` |
| `constants.yml` 実値 | `files/image_config/constants/constants.yml:31-41` |
| `enabled` チェック | `managers_allow_list.py:699-707` |
