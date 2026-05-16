---
title: TELEMETRY_CLIENT Subscription / DestinationGroup フィールド詳細
description: "TELEMETRY_CLIENT テーブルの Subscription・DestinationGroup エントリにおけるフィールド仕様・コード由来デフォルト・実装乖離の詳細リファレンス。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-telemetry_client.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-gnmi
    path: dialout/dialout_client/dialout_client.go
    ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
related:
  config_db:
    - TELEMETRY_CLIENT
    - TELEMETRY
  yang:
    - sonic-telemetry_client
  _no_related_cli: true
hard: 0
---

# TELEMETRY_CLIENT Subscription / DestinationGroup フィールド詳細

## 概要

`TELEMETRY_CLIENT` テーブルの `Subscription` および `DestinationGroup` エントリ、ならびに `Global` セクションのフィールド仕様を、YANG 定義とコード実装の両面から詳細に記述する。

概要・key 構造の全体像は [`TELEMETRY_CLIENT テーブル`](telemetry-client.md) を参照。本ページは **コード由来デフォルト・実装乖離 (discrepancy)** に焦点を当てる。

<!-- defaults -->
## 暗黙デフォルトとコード由来挙動

<!-- evidence: meta/_intermediate/cdb-flow/subscription-config-defaults.md -->

### 1. `report_interval` — YANG・実装ともに 5000 ms

**YANG 定義** (`sonic-telemetry_client.yang:134`):

```yang
leaf report_interval {
    type uint64;
    description "report_interval unit ms";
    default 5000;
}
```

**Go 実装** (`dialout_client.go:582`):

```go
cs := clientSubscription{
    interval: 5000, // default to 5000 milliseconds
    name:     name,
    cancel:   cancel,
}
```

YANG と実装が一致。`report_interval` を CONFIG_DB に書かない場合、dial-out クライアントは **5000 ms (5 秒) 周期** で報告する。

---

### 2. `unidirectional` — 実装は常に `true` に固定 (YANG との discrepancy)

**YANG 定義** (`sonic-telemetry_client.yang:88`):

```yang
leaf unidirectional {
    type boolean;
    default true;
}
```

**Go 実装** (`dialout_client.go:503`):

```go
case "unidirectional":
    // No PublishResponse supported yet
    clientCfg.Unidirectional = true
```

!!! warning "YANG-実装 discrepancy"
    CONFIG_DB に `unidirectional = false` を設定しても、実装は常に `true` を代入する (コメント: "No PublishResponse supported yet")。双方向 RPC は現在未サポート。

---

### 3. `encoding` — 実装は常に `JSON_IETF` に固定 (YANG との discrepancy)

**YANG 定義** (`sonic-telemetry_client.yang:45`): enum `JSON_IETF` / `ASCII` / `BYTES` / `PROTO`

**Go 実装** (`dialout_client.go:500`):

```go
case "encoding":
    //Flexible encoding Not supported yet
    clientCfg.Encoding = gpb.Encoding_JSON_IETF
```

!!! warning "YANG-実装 discrepancy"
    `ASCII` / `BYTES` / `PROTO` を CONFIG_DB に設定しても、実装は常に `JSON_IETF` を使用する (コメント: "Flexible encoding Not supported yet")。

---

### 4. `retry_interval` — YANG optional・実装初期値 0 (要注意)

YANG に `default` 宣言なし。Go 構造体 `ClientConfig.RetryInterval` (`time.Duration`) はゼロ値 (`0`)。

ゼロ値のまま `newClient` を呼び出すと `context.WithTimeout(ctx, 0)` となり、**接続開始直後にタイムアウト** する可能性がある。実用上は `retry_interval` を明示設定する必要がある (例: `30` 秒)。

証跡: `dialout_client.go:260`

---

### 5. `path_target` — 省略時はエラー (実質 mandatory)

`path_target` を省略すると `cs.prefix.GetTarget()` が空文字列を返し、以下のエラーで Subscription が起動しない:

```go
if target == "" {
    return fmt.Errorf("Empty target data not supported yet")
}
```

YANG 上は optional だが、実装上は **事実上 mandatory**。

証跡: `dialout_client.go:187-189`

---

### 6. `dst_group` 省略時 — Subscription をサイレントに無効化

`dst_group` が空の Subscription エントリは登録されずに無視される:

```go
if cs.destGroupName == "" {
    // not destination configured, just return
    return nil
}
```

エラーは返さないため、`dst_group` の設定漏れは**気づきにくい**。

証跡: `dialout_client.go:622-625`

---

### デフォルト・挙動サマリ

| フィールド | スコープ | YANG default | コード実装値 | 備考 |
|-----------|---------|-------------|------------|------|
| `report_interval` | Subscription | `5000` ms | `5000` ms | YANG・実装一致 |
| `unidirectional` | Global | `true` | 常に `true` | discrepancy: `false` は無視 |
| `encoding` | Global | なし | 常に `JSON_IETF` | discrepancy: 他 enum は無視 |
| `retry_interval` | Global | なし | ゼロ値 (0) | 未設定時は即タイムアウト可能性 |
| `report_type` | Subscription | なし | ゼロ値 (未定義) | 省略時動作は未定義・実質必須 |
| `path_target` | Subscription | なし | 空値 → エラー | 実質 mandatory |
| `dst_group` | Subscription | なし | 空値 → サイレント無効 | エラーなし |
| `dst_addr` | DestinationGroup | なし | 必須 (空なら拒否) | `Destination.Addrs is empty` |

<!-- /defaults -->

## フィールド仕様

### `TELEMETRY_CLIENT|Global`

| フィールド | 型 | デフォルト | 実装値 | 説明 |
|-----------|----|-----------|--------|------|
| `retry_interval` | uint64 (秒) | なし | 0 (要設定) | 再接続リトライ間隔。未設定時は 0 秒でタイムアウト |
| `src_ip` | `inet:ip-address` | なし | なし | dial-out 送信元 IP アドレス |
| `encoding` | enum | なし | 常に `JSON_IETF` | テレメトリエンコーディング (他値は現状無視) |
| `unidirectional` | boolean | `true` | 常に `true` | 単方向ストリーム (現状 `false` は未サポート) |

### `TELEMETRY_CLIENT|DestinationGroup|<name>`

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `dst_addr` | `ipv4-port` (`host:port[,...]`) | なし (必須) | コレクタ宛先。カンマ区切りで複数指定可。空アドレスは拒否 |

### `TELEMETRY_CLIENT|Subscription|<name>`

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `dst_group` | string | なし (省略時サイレント無効) | 紐づける DestinationGroup 名 |
| `path_target` | enum `APPL_DB`/`CONFIG_DB`/`COUNTERS_DB`/`STATE_DB`/`OTHERS` | なし (実質必須) | 購読先 DB |
| `paths` | string (カンマ区切り) | なし | 購読するデータパス |
| `report_interval` | uint64 (ms) | `5000` | 報告周期 |
| `report_type` | enum `periodic`/`stream`/`once` | なし (実質必須) | 報告モード |

## 制約

- `ipv4-port` typedef: `dst_addr` は `IPv4:port` のカンマ区切りのみ許容。IPv6 リテラルは YANG で拒否
- `dst_group` は `must` 制約で同 list 内の既存 `name` との一致を要求
- `DestinationGroup` が参照中の場合、DEL 操作を拒否 (`"<name> is being used"`)
- `Global` キーへの DEL 操作は拒否 (`"Invalid delete operation"`)

## 運用ヒント

### 最小構成例 (init_cfg.json)

```json
{
  "TELEMETRY_CLIENT": {
    "Global": {
      "retry_interval": "30",
      "encoding": "JSON_IETF",
      "unidirectional": "true"
    },
    "TELEMETRY_CLIENT_LIST": [
      {
        "prefix": "DestinationGroup",
        "name": "MyCollector",
        "dst_addr": "192.0.2.10:8081"
      },
      {
        "prefix": "Subscription",
        "name": "MySubscription",
        "dst_group": "MyCollector",
        "path_target": "COUNTERS_DB",
        "paths": "COUNTERS/Ethernet*,COUNTERS_PORT_NAME_MAP",
        "report_interval": "5000",
        "report_type": "periodic"
      }
    ]
  }
}
```

### よくある誤設定

- `encoding` に `ASCII`/`BYTES`/`PROTO` を指定 → 現状は `JSON_IETF` として動作する (警告なし)
- `unidirectional = false` を設定 → 現状は `true` として動作する (警告なし)
- `retry_interval` を省略 → ゼロ値で接続タイムアウト。必ず設定すること
- `dst_group` を省略または誤字 → Subscription がサイレントに無効化される
- `path_target` を省略 → `"Empty target data not supported yet"` エラー

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'TELEMETRY_CLIENT|*'
sonic-db-cli CONFIG_DB hgetall 'TELEMETRY_CLIENT|Global'
docker logs gnmi 2>&1 | grep -i "subscription\|dialout\|clientSubscription"
```

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-telemetry_client`](../yang/sonic-telemetry_client.md)
- [CONFIG_DB: TELEMETRY_CLIENT](telemetry-client.md) (テーブル全体の概要)
- [CONFIG_DB: TELEMETRY](telemetry.md) (dial-in 側設定)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-telemetry_client.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-telemetry_client.yang>

[^2]: Go 実装: `dialout_client.go`. <https://github.com/sonic-net/sonic-gnmi/blob/eb635b7679b260c3fd0786a6d0734fc8e82c9a22/dialout/dialout_client/dialout_client.go>

## 関連ページ

- [CONFIG_DB: TELEMETRY_CLIENT](telemetry-client.md)
- [CONFIG_DB: TELEMETRY](telemetry.md)

<!-- glossary-links-injected: subscription-config -->
