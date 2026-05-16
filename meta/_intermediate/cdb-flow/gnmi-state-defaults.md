# STATE_DB GNMI 関連フィールド — 暗黙デフォルト調査 (Phase A)

調査日: 2026-05-15  
対象テーブル: STATE_DB `TELEMETRY_CONNECTIONS`  
調査 repo: `sonic-net/sonic-gnmi` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)

---

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `gnmi_server/connection_manager.go` | `TELEMETRY_CONNECTIONS` テーブルへの書き込みロジック |
| `gnmi_server/client_subscribe.go` | `ConnectionManager` 初期化、threshold 設定 |
| `gnmi_server/server.go` | `setConnectionManager(s.config.Threshold)` 呼び出し |
| `telemetry/telemetry.go` | Go CLI フラグ定義 (`threshold` デフォルト = 100) |

---

## TELEMETRY_CONNECTIONS テーブル

### 概要

STATE_DB の `TELEMETRY_CONNECTIONS` は Redis Hash 型テーブル。`telemetry` デーモン (gNMI サーバ) が各 Subscribe RPC のアクティブ接続を管理するために使用する。

### key 構造

```text
TELEMETRY_CONNECTIONS  (Hash — キーなし / シングルエントリ)
```

Redis Hash の **フィールド名** が接続識別子 (connection key) となり、**値** は固定文字列 `"active"` 。

### connection key の生成ロジック (createKey)

```go
// connection_manager.go:94-108
func createKey(addr net.Addr, query string) string {
    regexStr := "(?:target|element):\"([a-zA-Z0-9-_*]*)\""
    regex := regexp.MustCompile(regexStr)
    matches := regex.FindAllStringSubmatch(query, -1)
    // connectionKeyString will look like "10.0.0.1|OTHERS|proc|uptime|2017-07-04 00:47:20
    connectionKey := addr.String() + "|"
    for i := 0; i < len(matches); i++ {
        connectionKey += matches[i][1]
        connectionKey += "|"
    }
    connectionKey += time.Now().UTC().Format(time.RFC3339)
    return connectionKey
}
```

フォーマット: `<peer_ip:port>|<target_1>|<target_2>|...|<RFC3339_timestamp>`

### フィールドと値

| フィールド (Redis Hash field) | 型 | 値 | ソース |
|-------------------------------|----|----|--------|
| `<connection_key>` | string | `"active"` (固定) | `connection_manager.go:116` |

**`"active"` はハードコード固定値** — DB から読み出されるパラメータではなく、接続存在の表示専用。

### ライフサイクル

| タイミング | 操作 | ソース |
|-----------|------|--------|
| `ConnectionManager.PrepareRedis()` 呼び出し時 | 既存全エントリを `HDel` (起動時クリア) | `connection_manager.go:52-60` |
| Subscribe RPC 開始 (`Add()`) | `HSet(table, key, "active")` | `connection_manager.go:116` |
| Subscribe RPC 終了 (`Remove()`) | `HDel(table, key)` | `connection_manager.go:127` |

### threshold との関係

`threshold` (CONFIG_DB `GNMI|gnmi.threshold`) は `ConnectionManager.Add()` で評価されるが、STATE_DB へは threshold 値自体は書き込まれない。STATE_DB は接続数のカウンタではなく、接続 key の一覧を保持する。

```go
// connection_manager.go:65
if len(cm.connections) >= cm.threshold && cm.threshold != 0 { // 0 is defined as no threshold
    // 接続拒否 — STATE_DB には書き込まない
    return "", false
}
```

**`threshold=0` の特別意味**: 上限なし (no threshold)。STATE_DB の TELEMETRY_CONNECTIONS エントリ数は threshold 以下に制限される。

---

## コード由来デフォルト — per field

### `TELEMETRY_CONNECTIONS` — connection key (Hash field)

| 種別 | 値 | ソース |
|------|----|--------|
| デフォルト (起動時) | 空 (全エントリ削除) | `connection_manager.go:52-60` — `PrepareRedis()` が HGetAll → HDel |
| 接続開始時の書き込み値 | `"active"` (固定文字列) | `connection_manager.go:116` — `HSet(..., key, "active")` |
| 接続終了時 | エントリ削除 | `connection_manager.go:127` — `HDel(table, key)` |

**乖離なし**: CONFIG_DB の設定値がこのフィールドに影響することはない (値は常に `"active"` 固定)。

---

## threshold = 0 の意味

```go
// connection_manager.go:65 — コメント付き:
if len(cm.connections) >= cm.threshold && cm.threshold != 0 { // 0 is defined as no threshold
```

- `threshold > 0`: 接続数が閾値に達すると新規接続を拒否
- `threshold = 0`: 上限なし

STATE_DB のエントリ数はこの制御の影響を受けるが、threshold 値自体は STATE_DB に保存されない。

---

## rclient nil ガード

Redis クライアントが接続失敗した場合は STATE_DB 書き込みが silent no-op になる:

```go
// connection_manager.go:111-115 (storeKeyRedis)
if rclient == nil {
    log.V(1).Infof("Redis client is nil, cannot store connection key")
    return
}
```

STATE_DB が利用不可能な場合でも、gnmi サーバ自体は起動継続する (フォールト許容設計)。

---

## 要約

| フィールド | コード由来デフォルト | ソース |
|-----------|-------------------|--------|
| Hash field (connection_key) | 起動時: 全削除 → 接続時: `"active"` | `connection_manager.go:52-60,116` |
| Hash value | `"active"` (固定, 変更不可) | `connection_manager.go:116` |
| threshold 上限 | CONFIG_DB `GNMI|gnmi.threshold` (デフォルト 100、0=無制限) | `telemetry.go:187; connection_manager.go:65` |
| Redis 不可時 | silent no-op (サーバは継続動作) | `connection_manager.go:111-115` |
