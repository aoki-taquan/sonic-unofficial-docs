# wred-profile Phase 13 中間ファイル (Directory-sibling exhaustive scan)

## スキャン対象 enum フィールド (tier_mid)

| フィールド | 値数 | grep hit 総数 | 引用済み数 | 未引用 sibling |
|---|---|---|---|---|
| `ecn` (8 値) | 8 | 全値 hit | qosorch.cpp, sonic-wred-profile.yang | 0 |

## ディレクトリ別 sibling スキャン結果

### `orchagent/` (sonic-swss)

**引用済み**: qosorch.cpp, qosorch.h (ecn_map, WredMapHandler)  
**sibling ファイルスキャン**:
- `qosorch_ut.cpp` (テスト) — ecn_green/yellow/red/all 等の値を確認テストで使用するが、実装証跡としては qosorch.cpp が包含
- `swss-schema.md` — WRED_PROFILE の ecn フィールド名を記載するが、YANG と同一内容

grep 結果: `sonic-swss/orchagent/qosorch.h`, `sonic-swss/orchagent/qosorch.cpp` の 2 ファイルが全 ecn 値を網羅。追加 sibling なし。

### `files/build_templates/` (sonic-buildimage)

- `qos_config.j2:494` — `AZURE_LOSSLESS` WRED_PROFILE の自動生成で `ecn: ecn_all` を静的設定 — Phase 6 で既引用

### `src/sonic-yang-models/yang-models/` (sonic-buildimage)

- `sonic-wred-profile.yang` — 全 8 値を enum として定義 — Phase 6 で既引用

## 追加 row 数

**0 行** — wred-profile.md は現状で全 ecn 値の hit を網羅。
