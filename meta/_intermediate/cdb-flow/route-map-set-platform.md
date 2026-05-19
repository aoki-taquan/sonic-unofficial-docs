# route-map-set platform 調査証跡

調査日: 2026-05-19

## 調査対象

`ROUTE_MAP_SET` テーブルのプラットフォーム差分・SAI Capability 依存の有無。

## 調査手順

### 1. j2 テンプレート grep

```
grep -r "ROUTE_MAP_SET" .cache/sonic-sources/ --include="*.j2"
→ 出力なし
```

ビルド時の j2 テンプレートによる注入は行われない。

### 2. Python grep (frrcfgd / bgpcfgd / orchagent)

```
grep -r "ROUTE_MAP_SET" .cache/sonic-sources/ --include="*.py" -l
→ 出力なし（YANG ファイルを除く）
```

いずれのデーモンも ROUTE_MAP_SET を参照しない。

### 3. SAI 呼び出し調査

orchagent 全体 grep でも `ROUTE_MAP_SET` の出現なし。SAI への経路を経由しない設計のため、ASIC/SAI Capability の差分は生じない。

### 4. sonic-cfggen / platform_config テンプレート調査

```
grep -r "ROUTE_MAP_SET" .cache/sonic-sources/ --include="*.j2" --include="*.json"
→ 出力なし
```

platform_config.json や device profile からの注入も確認されない。

## 結論

- `ROUTE_MAP_SET` は純粋な YANG leafref 整合性検証レジストリであり、SAI API・ASIC Capability・プラットフォーム固有テンプレートに依存しない。
- どのプラットフォームでも動作は同一（購読なし・SAI 投入なし）。
- ビルド時の自動注入もなく、手動 `sonic-db-cli` による設定のみが適用経路。
