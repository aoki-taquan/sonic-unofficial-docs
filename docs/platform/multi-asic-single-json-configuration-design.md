---
title: Multi-ASIC Single JSON Configuration（Golden Config に namespace layer）
area: platform
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/golden_config/Multi-Asic_Single_JSON_Configuration_Design.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli:
    - config reload
    - config override-config-table
    - config apply-patch
    - config save
    - show runningconfiguration all
  yang: []
---

!!! note "裏取りステータス: code-verified"
    `sonic-utilities/show/main.py` の `runningconfiguration all` は multi-ASIC で `output['localhost'] = ...` + `for ns in ns_list: output[ns] = ...` の Golden Config 形式で出力する実装を確認。`config/main.py` に `apply-patch` コマンドと `override-config-table` の呼び出し（`load_minigraph --override_config`）が存在。namespace ごとのループ展開と YANG validate は generic_config_updater 側で扱われる。

# Multi-ASIC Single JSON Configuration（Golden Config に namespace layer）

## 概要

minigraph 廃止後の **Golden Config**（NDM 生成、HwProxy 経由で push）を multi-ASIC 機にも適用するための JSON スキーマ拡張[^1]。従来 multi-ASIC では host 用 `config_db.json` + ASIC 数だけの `config_db<N>.json` を別ファイルで持っていた。本提案は **1 ファイル**で host と全 ASIC を表現するため、トップに `localhost` / `asic0` / `asic1` ... の **名前空間 layer を 1 段追加**する。CLI 群（`config reload / save / override / apply-patch`、`show runningconfiguration all`）も同形式を読み書きできるよう拡張する。

## 動作仕様

### スキーマ

```json
{
  "localhost": {
    "FEATURE":   {...},
    "ACL_TABLE": {...}
  },
  "asic0": { "FEATURE": {...}, "ACL_TABLE": {...} },
  "asic1": { ... }
}
```

CLI 互換のため **single-ASIC 機ではこれまでどおり flat な ConfigDB JSON を扱う** こともできる[^1]。

### CLI 拡張

| CLI | 既存挙動 | 追加挙動 |
|-----|----------|----------|
| `config reload` | デフォルト `/etc/sonic/config_db.json` | 単一 `<file>` で全 ASIC を reload（key で振分け）|
| `config reload <a.json,b0.json,...>` | カンマ区切りで N 個指定 | 維持（後方互換）|
| `config override-config-table` | single-ASIC のみ | multi-ASIC 対応（[sonic-utilities #2738]）|
| `config apply-patch` | multi-ASIC 非対応 | path に `/asicN/<TABLE>/...` を含む JsonPatch を **ループ展開**[^1] |
| `show runningconfiguration all` | host のみ表示 | Golden Config 形式で全 ASIC 表示 |
| `config save` | N 個の file 生成 | 単一 `<file>` 保存に対応（key で集約）|

### apply-patch の例

```json
[
  { "op": "replace", "path": "/asic1/MACSEC_PROFILE/entry/k", "value": "value" },
  { "op": "replace", "path": "/asic0/MACSEC_PROFILE/entry/k", "value": "value" }
]
```

CLI は patch を per-namespace ループで分割し、各 namespace の Generic Config Update flow に流す[^1]。JsonPatch (RFC 6902) は変更しない。

### Reload / Save シナリオ

```mermaid
flowchart LR
  GC["Golden Config JSON<br/>(localhost/asic0/asic1...)"]
  GC --> RELOAD[config reload &lt;file&gt;]
  RELOAD --> NS{namespace 分割}
  NS --> H[host ConfigDB]
  NS --> A0[asic0 ConfigDB]
  NS --> A1[asic1 ConfigDB]
  SAVE[config save &lt;file&gt;] --> AGG[host + 全 asic を集約]
  AGG --> GC
```

### YANG Validation

Top に namespace layer が増えたままでは既存 YANG モデルで検証できないが、**namespace 単位（host / 各 asic）に分割して既存 YANG で validate** すれば良いという整理[^1]。新フィールドは不要。

### Pros / Cons（HLD まとめ）

| | 内容 |
|---|------|
| Pros | namespace 1 layer 追加だけで実装可、既存 YANG を流用、minigraph 廃止 → Golden Config Override への移行が素直 |
| Cons | YANG を全体に対しては当てられない（分割必要）、namespace 間で重複した table が冗長 |

<!-- evidence:
source: sonic-net/SONiC/doc/golden_config/Multi-Asic_Single_JSON_Configuration_Design.md#L83-L97 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  This design provides another layer of Host and ASIC as keys ...
  "localhost": { ... }, "asic0": { ... }, "asic1": { ... }
reasoning: namespace layer 1 段追加でスキーマ拡張する設計の根拠。
-->

## 制限事項

- 全体 YANG validate 不可。namespace 単位での validate に留まる
- 各 ASIC で重複しがちな table は NDM 側でも冗長記述が必要
- minigraph 廃止前提のため、minigraph 併用時の挙動はスコープ外

## 干渉する機能

- **Generic Config Update / Rollback**: `config apply-patch` がループ呼び出しで本機能と連動
- **NDM / HwProxy / Golden Config 生成**: 単一 file 前提
- **YANG validation**: namespace ごとに分割適用
- **multi-asic ConfigDB redis instance**: namespace ごとに別インスタンス

[sonic-utilities #2738]: https://github.com/sonic-net/sonic-utilities/pull/2738

## 引用元

[^1]: `sonic-net/SONiC` `doc/golden_config/Multi-Asic_Single_JSON_Configuration_Design.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- evidence (verifier-batch-19):
- sonic-utilities `show/main.py` `runningconfiguration all`: multi-ASIC 時 `output['localhost']` + `for ns in ns_list: output[ns] = get_config_json_by_namespace(ns)` で Golden Config 形式を出力
- sonic-utilities `config/main.py` line 1917 に `@config.command('apply-patch')` 定義、`apply_patch_from_file as _gcu_apply_patch_from_file` を import
- `load_minigraph --override_config` (l.2345) で `override_config_by(golden_config_path)` → `config override-config-table <path>` を呼び出し
-->

<!-- concerns hint:
- sonic-utilities config_main の reload / save / override で localhost / asicN 階層対応の取り込み確認 → show / override 経路は取り込み済
- apply-patch の patch ループ展開実装の sonic-utilities 取り込み確認 → apply-patch 取り込み済（namespace ループは generic_config_updater 側）
- show runningconfiguration all の出力 schema 切替の実装確認 → 確認済
- YANG validation を namespace 単位に分割する helper 実装確認 → generic_config_updater で分担
- minigraph 廃止フェーズの進捗と Golden Config 採用の現行スコープ確認 → load_minigraph に override_config オプションが残存（共存フェーズ）
-->
