---
title: MGMT_INTERFACE テーブル
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mgmt_interface.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - MGMT_INTERFACE
    - MGMT_PORT
    - MGMT_VRF_CONFIG
  cli:
    - config interface
  yang:
    - sonic-mgmt_interface
---

# MGMT_INTERFACE テーブル

## 概要

帯域外管理 IF (`eth0`) に対する IP / gateway / forced routes を保持する[^1]。`hostcfgd` がこのテーブルから `/etc/network/interfaces` の `mgmt-` セクションを再生成する。`MGMT_VRF_CONFIG.mgmtVrfEnabled = true` のとき forced routes は mgmt VRF テーブルに追加される。

## key 構造

```
MGMT_INTERFACE|<name>|<ip_prefix>
```

`<name>` は `MGMT_PORT.name` への leafref。`<ip_prefix>` は v4/v6 prefix。

## フィールド一覧

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `name` (key) | leafref `MGMT_PORT.name` | ✅ | 管理ポート名 |
| `ip_prefix` (key) | `sonic-ip-prefix` | ✅ | IP/プレフィクス |
| `gwaddr` | ip-address | - | デフォルトゲートウェイ |
| `forced_mgmt_routes` | leaf-list (prefix or address) | - | mgmt VRF / default VRF に追加する経路 |

## 制約 (must)

- `ip_prefix` と `gwaddr` は同じ IP family でなければならない（両方とも `:` を含むか、両方とも `.` を含む）

## 購読者

- `hostcfgd`: Linux ネットワーク設定の更新
- `interfaces.j2` テンプレート: `forced_mgmt_routes` 展開

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `MGMT_PORT`、`MGMT_VRF_CONFIG`
- 関連 CLI: `config interface ip add eth0 ...`
- 関連 YANG: `sonic-mgmt_interface`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: `sonic-mgmt_interface`
- CLI: [`config interface`](../cli/config-interface.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-mgmt_interface.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-mgmt_interface.yang>
