---
title: show priority-group サブコマンド
description: "show priority-group サブコマンド — show priority-group は priority group (PG) の watermark と drop counter を表示する CLI グループ。"
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - show priority-group
  yang: []
---

# show priority-group サブコマンド

## 概要

`show priority-group` は priority group (PG) の watermark と drop counter を表示する CLI グループ。watermark は `watermarkstat`、drop counter は `pg-drop` へ委譲される[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show priority-group watermark headroom [options]` | user headroom watermark を表示 |
| `show priority-group watermark shared [options]` | user shared watermark を表示 |
| `show priority-group persistent-watermark headroom [options]` | persistent headroom watermark を表示 |
| `show priority-group persistent-watermark shared [options]` | persistent shared watermark を表示 |
| `show priority-group drop counters [--namespace <ns>]` | PG drop counter を表示 |

## watermark

**用法**:

```
show priority-group watermark headroom [--namespace <ns>|all] [--json]
show priority-group watermark shared [--namespace <ns>|all] [--json]
```

実行コマンドはそれぞれ `watermarkstat -t pg_headroom` と `watermarkstat -t pg_shared`。`--json` は `-j`、`--namespace` は `-n` に変換される。

## persistent-watermark

`persistent-watermark` は `watermarkstat -p` を追加する点だけが通常 watermark と異なる。

## drop counters

`show priority-group drop counters` は `pg-drop -c show` を実行する。namespace 指定時は `-n <namespace>` を追加する。

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `show priority-group` グループと配下 command。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L1003>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型的な利用シーン

- headroom watermark を見て lossless 設定の余裕を判定する。
- PG 別 shared / headroom 使用量の傾向監視。

### よくある落とし穴

- persistent-watermark は手動 clear するまでリセットされない。
- PG が profile 紐付けされていないと watermark は 0 のまま。

### 関連する show / debug

```bash
show priority-group watermark headroom
show priority-group persistent-watermark headroom
show buffer profile
```
<!-- /ops-hint -->
