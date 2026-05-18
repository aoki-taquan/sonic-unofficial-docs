# nat-app — Phase D failure 調査メモ

## 対象ファイル
`docs/reference/config-db/nat-app.md`

## 追加 Phase
Phase D: 失敗挙動マトリクス (failure)

## 調査ソース
- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/cfgmgr/natmgr.cpp`

## 主な知見

### NAT_TABLE / NAPT_TABLE
- key セグメント数不正 → `erase(it)` 恒久スキップ
- `entry_type` 不正 → `assert` abort (orchagent 停止)
- dynamic SNAT 上限超過 → `AGEOUT-SINGLE-NAT` 通知でエージアウト + エントリ破棄
- `isNatEnabled() == false` → キャッシュ保持のみ、SAI 呼ばない
- SAI create 失敗 → `it++` 次サイクルで再試行

### NAT_GLOBAL_TABLE
- key が `"Values"` 以外 → `erase(it)` 恒久スキップ
- `admin_mode` 値不正 → `assert` abort
- SAI `set_switch_attribute(NAT_ENABLE)` 失敗 → ログのみ、処理続行
- `gIsNatSupported == false` → `enableNatFeature()` で即 return、一切の SAI 操作スキップ

### NAT_DNAT_POOL_TABLE
- key セグメント数不正 → `erase(it)` 恒久スキップ
- 重複 SET → 冪等、成功扱い
- SAI create 失敗 → `it++` 再試行
