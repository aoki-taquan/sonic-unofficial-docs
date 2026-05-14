# MGMT_INTERFACE — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/mgmt-interface.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | `mgmt-framework` / `interfaces-config` スクリプト |
| 2. CFG→APPL 翻訳 | なし (APPL_DB 中継なし) |
| 3. APPL→SAI | なし (SAI 非経由 — Linux kernel netlink で管理インターフェースを設定) |
| 4. タイミング+副作用 | CONFIG_DB 変化を検知後、`interfaces-config` スクリプトが `ip addr add/del` 等の netlink コマンドを発行... |

## 生成ブロック

```markdown
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`mgmt-framework` / `interfaces-config` スクリプト が CONFIG_DB の `MGMT_INTERFACE` テーブルを購読する。

`MGMT_INTERFACE` の key は `<eth0>|<ip_prefix>` の形式。管理 VRF (`mgmt`) に関連付けられることが多い。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — Linux kernel netlink で管理インターフェースを設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB 変化を検知後、`interfaces-config` スクリプトが `ip addr add/del` 等の netlink コマンドを発行。即時反映。

**副作用**: 管理インターフェースの IP 変更は SSH セッションの切断を引き起こす。デフォルトルートの変更は管理トラフィックの経路に影響。
<!-- /runtime-trace -->
```
