# PASSW_HARDENING フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `PASSW_HARDENING`

## 調査対象ファイル

- `sonic-buildimage/files/build_templates/init_cfg.json.j2` (ビルド時初期値)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-passwh.yang` (YANG スキーマ)
- `sonic-host-services/scripts/hostcfgd` (PasswHardening クラス)
- `sonic-host-services/tests/hostcfgd/test_passwh_vectors.py` (テストベクタ)

---

## フィールド別 暗黙デフォルト

テーブル: `PASSW_HARDENING`、key: `POLICIES`

### `state`

**YANG default**: `"disabled"`

```yang
# sonic-passwh.yang:28-29
leaf state {
    type feature_state;
    default "disabled";
}
```

**init_cfg.json.j2 初期値**: `"disabled"`

```json
"PASSW_HARDENING": {
    "POLICIES": {
        "state": "disabled",
        ...
    }
}
```

**コード fallback (DB なし)**: `PasswHardening.passw_policies_default = {}` → `passw_policies` も `{}` → `set_passw_hardening_policies({})` に `None`/空 dict が渡る → `if passw_policies:` が偽 → expiration は `LINUX_DEFAULT_PASS_MAX_DAYS` (99999) / `LINUX_DEFAULT_PASS_WARN_AGE` (7) のままで PAM policy 無効扱い

---

### `expiration`

**YANG default**: なし（`default` 文なし）

**init_cfg.json.j2 初期値**: `"180"` (days)

**コード fallback**: DB エントリに `expiration` がない場合、`passw_policies.get('expiration', -1)` → `-1`（パスワード有効期限なし）。ただし `state` が `disabled` の場合は `LINUX_DEFAULT_PASS_MAX_DAYS = 99999` を使用。

```python
# hostcfgd:943
curr_expiration = int(passw_policies.get('expiration', -1))
```

---

### `expiration_warning`

**YANG default**: なし

**init_cfg.json.j2 初期値**: `"15"` (days)

**コード fallback**: `passw_policies.get('expiration_warning', -1)` → `-1`（警告なし）。`state` が `disabled` の場合は `LINUX_DEFAULT_PASS_WARN_AGE = 7` を使用。

```python
# hostcfgd:944
curr_expiration_warning = int(passw_policies.get('expiration_warning', -1))
```

---

### `history_cnt`

**YANG default**: なし（range: 1..100）

**init_cfg.json.j2 初期値**: `"10"`

**コード fallback**: PAM `pam_pwhistory.so` テンプレートに渡されるが、`passw_policies` が空の場合はテンプレートが hardening なしで生成されるため history 制限なし。

---

### `len_min`

**YANG default**: なし（range: 1..32）

**init_cfg.json.j2 初期値**: `"8"`

**コード fallback**: `passw_policies` が空/`state=disabled` の場合は `pam_cracklib.so` / `pam_pwquality.so` に渡されず、OS デフォルト（通常 6 文字）が適用。

---

### `reject_user_passw_match`

**YANG default**: なし（boolean）

**init_cfg.json.j2 初期値**: `"true"`

**コード fallback**: `is_true()` 変換を通じて `True`/`False` に正規化される。DB なし時は PAM 設定に含まれない（チェックなし）。

---

### `lower_class`

**YANG default**: なし（boolean）

**init_cfg.json.j2 初期値**: `"true"`

**コード fallback**: DB なし時は PAM 設定に含まれない（クラス要件なし）。

---

### `upper_class`

**YANG default**: なし（boolean）

**init_cfg.json.j2 初期値**: `"true"`

**コード fallback**: 同上。

---

### `digits_class`

**YANG default**: なし（boolean）

**init_cfg.json.j2 初期値**: `"true"`

**コード fallback**: 同上。

---

### `special_class`

**YANG default**: なし（boolean）

**init_cfg.json.j2 初期値**: `"true"`

**コード fallback**: 同上。

---

## まとめ

| フィールド | YANG default | init_cfg.json.j2 | コード fallback (DB なし/disabled) |
|-----------|-------------|-----------------|----------------------------------|
| `state` | `"disabled"` | `"disabled"` | passw_policies={} → PAM hardening 無効 |
| `expiration` | なし | `"180"` | `get('expiration', -1)` → -1 (disabled時: 99999) |
| `expiration_warning` | なし | `"15"` | `get('expiration_warning', -1)` → -1 (disabled時: 7) |
| `history_cnt` | なし | `"10"` | policies={} → PAM history なし |
| `len_min` | なし | `"8"` | policies={} → OS デフォルト |
| `reject_user_passw_match` | なし | `"true"` | policies={} → チェックなし |
| `lower_class` | なし | `"true"` | policies={} → 要件なし |
| `upper_class` | なし | `"true"` | policies={} → 要件なし |
| `digits_class` | なし | `"true"` | policies={} → 要件なし |
| `special_class` | なし | `"true"` | policies={} → 要件なし |

**コード根拠**:
- `hostcfgd` `PasswHardening` クラス: `sonic-host-services/scripts/hostcfgd:873-958`
- `LINUX_DEFAULT_PASS_MAX_DAYS = 99999`: `sonic-host-services/scripts/hostcfgd:57`
- `LINUX_DEFAULT_PASS_WARN_AGE = 7`: `sonic-host-services/scripts/hostcfgd:58`
- `init_cfg.json.j2`: `sonic-buildimage/files/build_templates/init_cfg.json.j2` (PASSW_HARDENING セクション)
- YANG スキーマ: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-passwh.yang:25-73`
- テストベクタ: `sonic-host-services/tests/hostcfgd/test_passwh_vectors.py:8-23`
