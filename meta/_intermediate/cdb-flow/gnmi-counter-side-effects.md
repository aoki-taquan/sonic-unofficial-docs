# gnmi-counter — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-19
ソース: `sonic-gnmi/gnmi_server/connection_manager.go`, `sonic-gnmi/gnmi_server/client_subscribe.go`, `sonic-gnmi/gnmi_server/server.go`

---

## 概要

gNMI カウンタ本体は SysV 共有メモリに格納されるため CONFIG_DB / STATE_DB への直接書込はない。
ただし `telemetryd` が gRPC Subscribe セッションを管理する際、`ConnectionManager` が **STATE_DB の `TELEMETRY_CONNECTIONS`** テーブルを副次的に読み書きする。

---

## 1. STATE_DB — `TELEMETRY_CONNECTIONS`

| 操作 | Redis コマンド | タイミング | 書込元 | evidence |
|------|--------------|-----------|--------|----------|
| 起動時クリア | `HGetAll` → 全フィールドを `HDel` | `setConnectionManager()` → `PrepareRedis()` 実行時（最初の Subscribe RPC 時に 1 回） | `connection_manager.go:52-60` | |
| 接続確立 | `HSet(TELEMETRY_CONNECTIONS, key, "active")` | Subscribe セッション受け入れ時（`connectionManager.Add()`） | `connection_manager.go:116`, `client_subscribe.go:179` | |
| 接続切断 | `HDel(TELEMETRY_CONNECTIONS, key)` | Subscribe セッション終了時（`connectionManager.Remove()`、defer で保証） | `connection_manager.go:127`, `client_subscribe.go:183` | |

### キー形式

```
<client-ip:port>|<target-or-element-from-query>|...|<RFC3339-timestamp>
```

例: `192.0.2.1:51234|COUNTERS_DB|2026-05-19T00:00:00Z`

`createKey()` の正規表現 `(?:target|element):"([a-zA-Z0-9-_*]*)"` でクエリ文字列からターゲット名を抽出し、`|` 区切りで連結する（`connection_manager.go:94-109`）。

---

## 2. カウンタ共有メモリへの副次書込（non-DB）

SysV 共有メモリ（key=`7749`）への書込自体が「副作用」であるが、これは DB テーブルではない。
`IncCounter()` → `SetMemCounters()` (`context.go:180-183`) が各 RPC 受信・DBus 呼び出しごとに実行される。

---

## 3. 副次書込のないテーブル（スコープ外）

| テーブル | 理由 |
|---------|------|
| CONFIG_DB (全テーブル) | カウンタはメモリのみ。Set RPC の書込先は配下の DB だがカウンタロジックからの副次書込はなし |
| APPL_DB | 書込なし |
| COUNTERS_DB | telemetryd はカウンタデータの**読み取り元**として使用するが、`IncCounter` 経路での書込はなし |
| FLEX_COUNTER_DB | telemetryd は書込まない（orchagent 管轄） |

---

## 副次書込フロー

```
gRPC Subscribe RPC 受信
  └─ Client.Run() (client_subscribe.go:179)
       └─ connectionManager.Add(addr, query)
            ├─ (初回のみ) PrepareRedis()
            │    └─ HGetAll + HDel → STATE_DB/TELEMETRY_CONNECTIONS (旧エントリクリア)
            └─ storeKeyRedis(key)
                 └─ HSet → STATE_DB/TELEMETRY_CONNECTIONS/<key>=active

セッション終了（defer）
  └─ connectionManager.Remove(key)
       └─ deleteKeyRedis(key)
            └─ HDel → STATE_DB/TELEMETRY_CONNECTIONS/<key>
```

---

## 注意点

- `rclient == nil` の場合（`PrepareRedis` が失敗した場合）、`storeKeyRedis` / `deleteKeyRedis` はログのみ出力してリターンする（`connection_manager.go:112-115, 122-124`）。副次書込に失敗しても Subscribe セッション自体は継続される。
- `TELEMETRY_CONNECTIONS` は CONFIG_DB ではなく **STATE_DB (DB 6)** に格納される。`show gnmi client-history` コマンドの情報源となる。
- **Get / Set RPC は `TELEMETRY_CONNECTIONS` を更新しない**。ConnectionManager は Subscribe セッション専用。
