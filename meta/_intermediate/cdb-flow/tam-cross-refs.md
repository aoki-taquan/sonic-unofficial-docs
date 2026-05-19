# TAM テーブル群 — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/tam.md`
解析日: 2026-05-19
根拠ソース:
- `sonic-mgmt-common/cvl/testdata/schema/sonic-ifa.yang`
- `sonic-mgmt-common/cvl/cvl_leafref_test.go`
- `sonic-mgmt-common/cvl/cvl_must_test.go`

---

## 目的

`TAM_INT_IFA_FLOW_TABLE` エントリが CONFIG_DB に書かれたとき、CVL (sonic-mgmt-common) が
**YANG leafref / must** 制約として解決する他テーブルへの依存を網羅する。
`TAM_DEVICE_TABLE` と `TAM_INT_IFA_FEATURE_TABLE` は他テーブルへの leafref を持たない。

---

## 1. ACL_TABLE (leafref: acl-table-name)

### YANG 定義

`sonic-ifa.yang:56-61`

```yang
leaf acl-table-name {
    mandatory true;
    type leafref {
        path "/acl:sonic-acl/acl:ACL_TABLE/acl:ACL_TABLE_LIST/acl:aclname";
    }
}
```

### 依存内容

| 参照元フィールド | 参照先テーブル | 参照先キー | 制約種別 | 根拠 |
|---|---|---|---|---|
| `TAM_INT_IFA_FLOW_TABLE.acl-table-name` | `ACL_TABLE` | `ACL_TABLE\|<aclname>` | YANG leafref (mandatory) | `sonic-ifa.yang:58-60` |

### 特記事項

- `mandatory true` のため、`acl-table-name` を省略した場合も CVL がエラーを返す。
- 参照先 `ACL_TABLE|<aclname>` が存在しない場合、CVL は `CVL_SEMANTIC_DEPENDENT_DATA_MISSING`
  エラーを返す（`cvl_leafref_test.go:247-254`）。

---

## 2. ACL_RULE (leafref: acl-rule-name)

### YANG 定義

`sonic-ifa.yang:63-68`

```yang
leaf acl-rule-name {
    mandatory true;
    type leafref {
        path "/acl:sonic-acl/acl:ACL_RULE/acl:ACL_RULE_LIST[acl:aclname=current()/../acl-table-name]/acl:rulename";
    }
}
```

### 依存内容

| 参照元フィールド | 参照先テーブル | 参照先キー | 制約種別 | 根拠 |
|---|---|---|---|---|
| `TAM_INT_IFA_FLOW_TABLE.acl-rule-name` | `ACL_RULE` | `ACL_RULE\|<aclname>\|<rulename>` | YANG leafref (mandatory, 連鎖キー) | `sonic-ifa.yang:65-67` |

### 特記事項

- leafref パスが `acl-table-name` を current() 参照でフィルタする連鎖形式。
  すなわち `ACL_RULE|<acl-table-name>|<acl-rule-name>` のエントリが存在していなければならない。
- 同一 `acl-table-name` に属しない rulename を指定しても CVL が `instance-required` エラーを返す
  （`cvl_leafref_test.go:212-255`）。

---

## 3. TAM_COLLECTOR_TABLE (string 参照: collector-name)

### YANG 定義と must テスト

`sonic-ifa.yang:78-83`

```yang
leaf collector-name {
    type string {
        pattern '[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,32})';
        length 1..32;
    }
}
```

`cvl_must_test.go:449-461` でコレクタ名の存在チェックが CVL must 制約として検証されている。

### 依存内容

| 参照元フィールド | 参照先テーブル | 参照先キー | 制約種別 | 根拠 |
|---|---|---|---|---|
| `TAM_INT_IFA_FLOW_TABLE.collector-name` | `TAM_COLLECTOR_TABLE` | `TAM_COLLECTOR_TABLE\|<name>` | CVL must 制約 (string 型, 実質 leafref 相当) | `cvl_must_test.go:449-461` |

### 特記事項

- YANG 型上は string だが、CVL must 制約が `TAM_COLLECTOR_TABLE` 内のエントリ存在を検証する。
  sonic-db-cli で直接書き込む場合は CVL をバイパスするため、存在しないコレクタ名を設定可能
  （ただし IFA 機能は orchagent 非実装のため実害なし）。
- `collector-name` は `optional` のため、省略した場合は参照チェックは走らない。

---

## 4. sonic-db-cli 直接書き込み時の注意

すべての cross-refs は **CVL 経由の制約**であり、GNMI/REST（Management Framework）経由の
設定変更でのみ強制される。`sonic-db-cli CONFIG_DB hmset ...` で直接書き込む場合は
これらの制約がバイパスされる（ただし orchagent 側に TAM テーブルのハンドラが存在しないため
実際の SAI 設定変更には影響しない）。

---

## 5. cross-refs ブロック (最終形)

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`TAM_INT_IFA_FLOW_TABLE` の各フィールドは YANG leafref および CVL must 制約によって
以下のテーブルのエントリを**参照**する。CVL (sonic-mgmt-common) が GNMI/REST 経由の
設定適用時にこれらの制約を強制する。

| 参照元フィールド | 参照先テーブル | 参照先キー形式 | 制約種別 | 根拠 |
|---|---|---|---|---|
| `acl-table-name` | `ACL_TABLE` | `ACL_TABLE\|<aclname>` | YANG leafref (mandatory) | `sonic-ifa.yang:58-60` |
| `acl-rule-name` | `ACL_RULE` | `ACL_RULE\|<aclname>\|<rulename>` | YANG leafref (mandatory, 連鎖キー) | `sonic-ifa.yang:65-67` |
| `collector-name` | `TAM_COLLECTOR_TABLE` | `TAM_COLLECTOR_TABLE\|<name>` | CVL must 制約 (string 型) | `cvl_must_test.go:449-461` |

### 解決タイミング

- すべての参照チェックは **CVL バリデーション** (Management Framework が呼び出す) で行われる。
  `sonic-db-cli` の直接書き込み時は CVL をバイパスするため制約は適用されない。
- `acl-rule-name` の leafref は `current()/../acl-table-name` でフィルタされた連鎖 leafref のため、
  `ACL_RULE|<acl-table-name>|<acl-rule-name>` の組み合わせが正確に一致している必要がある。
- `collector-name` は optional のため、省略時は参照チェックが走らない。

### 依存なしのテーブル

- `TAM_DEVICE_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` — 他テーブルへの leafref 参照を持たない。
  任意の順序で書き込み可能。
<!-- /cross-refs -->
```
