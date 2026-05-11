---
title: CABLE_LENGTH テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-cable-length.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - CABLE_LENGTH
    - PORT
    - BUFFER_PROFILE
    - BUFFER_PG
  cli: []
  yang:
    - sonic-cable-length
---

# CABLE_LENGTH テーブル

## 概要

各 port に紐づく **ケーブル長** を格納する。lossless buffer (PFC) のしきい値計算で参照され、headroom-pool / xon-xoff の自動計算に使われる[^1]。

## key 構造

```
CABLE_LENGTH|<name>
```

`<name>` はケーブル長設定グループ名 (パターン `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`、長さ 1..32)。慣例として **単一エントリ `AZURE`** を使う運用が多い。

値部は **port 名 → ケーブル長文字列** のハッシュで、port は `sonic-port` の leafref で必ず存在する port を指す必要がある。

## 主要フィールド (entry-level)

| フィールド | 型 | 制約 | 説明 |
|-----------|----|------|------|
| `<Ethernet0>` | string | pattern `[0-9]+m` | 該当 port のケーブル長 (例 `5m`、`40m`、`300m`) |

例:

```
CABLE_LENGTH|AZURE
  Ethernet0: "5m"
  Ethernet4: "40m"
  Ethernet8: "300m"
```

## 購読者

- `buffermgrd` (sonic-swss-common 経由): lossless buffer profile を `LOSSLESS_TRAFFIC_PATTERN` と組み合わせて計算
- 直接 ASIC には書かれない (中間として `BUFFER_PG` / `BUFFER_PROFILE` を生成)

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PORT`、`BUFFER_PROFILE`、`BUFFER_PG`、`LOSSLESS_TRAFFIC_PATTERN`、`DEFAULT_LOSSLESS_BUFFER_PARAMETER`
- 関連 YANG: `sonic-cable-length`
- 関連 CLI: 専用 CLI なし。通常 minigraph / `config_db.json` で直接設定。

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`BUFFER_PROFILE`](buffer-profile.md), [`BUFFER_PG`](buffer-pg.md)
- (関連 YANG ページなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-cable-length.yang` (`revision 2021-11-11`). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-cable-length.yang>
