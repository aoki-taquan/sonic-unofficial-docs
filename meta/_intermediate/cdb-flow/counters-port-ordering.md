# COUNTERS_DB PORT カウンタ — Phase B 書込み順依存スキャンノート

対象: `COUNTERS_DB COUNTERS:<oid>` / `COUNTERS_PORT_NAME_MAP`
Consumer: `flexcounterorch` + `portsorch` (sonic-swss/orchagent/)
スキャン範囲: flexcounterorch.cpp 全行、portsorch.cpp の generatePortCounterMap() 周辺・port 作成経路精読

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード — PortInitDone が先行必須

`FlexCounterOrch::doTask()` は冒頭で `gPortsOrch->allPortsReady()` を確認し、`false` の場合は処理を即リターンする (flexcounterorch.cpp:164-166)。

```cpp
if (gPortsOrch && !gPortsOrch->allPortsReady())
{
    return;
}
```

`allPortsReady()` は `m_initDone && m_pendingPortSet.empty()` (portsorch.cpp:1685-1687) で、`m_initDone` は `portsyncd` が `APP_DB:PORT_TABLE|PortInitDone` を書き込んで初めて `true` になる (portsorch.cpp:4613-4622)。

**順序依存**: `FLEX_COUNTER_TABLE|PORT` への `FLEX_COUNTER_STATUS=enable` 書き込みを `PortInitDone` 発行**前**に行っても、`flexcounterorch` は何もしない（ただしエントリは `m_toSync` に保持され、`PortInitDone` 後に次の Consumer tick で処理される）。

### 2. FLEX_COUNTER_STATUS=enable 受信時の generatePortCounterMap() 呼び出し

`FLEX_COUNTER_TABLE|PORT` に `FLEX_COUNTER_STATUS=enable` が SET されると、`flexcounterorch` は `gPortsOrch->generatePortCounterMap()` を呼ぶ (flexcounterorch.cpp:237-240)。

`generatePortCounterMap()` は `m_portList` をイテレートし、`m_type == Port::Type::PHY` のポートのみ `port_stat_manager.setCounterIdList()` を呼んで `COUNTERS_DB` に `COUNTER_ID_LIST` を登録する (portsorch.cpp:9109-9128)。

- LAG / VLAN / CPU ポートは `m_portList` に存在するがスキップされる。
- `m_isPortCounterMapGenerated = true` が立った後は再呼び出しが noop になる（冪等）。

### 3. 新規ポート追加時の即時登録（counterpoll enable 済み時）

`portsorch` が新規ポートを作成する際、`flex_counters_orch->getPortCountersState()` が `true`（既に enable 済み）であれば、その場で `port_stat_manager.setCounterIdList()` を呼ぶ (portsorch.cpp:4143-4148)。

**順序依存**: enable 後に動的追加されたポートは `generatePortCounterMap()` を経由せず直接登録される。enable 前に存在したポートは `generatePortCounterMap()` でまとめて登録される。

### 4. Warm Start 時の 60 秒遅延

Warm Start の場合、`FlexCounterOrch` ctor が `FLEX_COUNTER_DELAY_SEC = 60` 秒の `SelectableTimer` を起動し、タイマ満了まで `doTask()` が全リターンする (flexcounterorch.cpp:127-136, 155-158)。

通常起動時は `m_delayTimerExpired = true` が即設定されるため遅延なし (flexcounterorch.cpp:137)。

**タイミング依存**: Warm Start 環境では `FLEX_COUNTER_TABLE|PORT` への書き込みが `PortInitDone` 後であっても 60 秒間は反映されない。

### 5. COUNTERS_PORT_NAME_MAP の書き込みタイミング

`portsorch` が SAI ポートを作成した直後、`m_counterNameMapUpdater->setCounterNameMap(p.m_alias, p.m_port_id)` を呼んで `COUNTERS_DB:COUNTERS_PORT_NAME_MAP` に `<port_alias>:<OID>` を書き込む (portsorch.cpp:4118)。

この書き込みは `FLEX_COUNTER_STATUS` の enable/disable に関係なくポート作成時に常に行われる。`portstat` はこのマップを読んで名前→OID 変換をするため、counterpoll が disable 状態でもマップは存在する。

### 6. DEL 時の挙動（counterpoll disable）

`FLEX_COUNTER_TABLE|PORT` に `FLEX_COUNTER_STATUS=disable` が SET されると (flexcounterorch.cpp:SET_COMMAND 分岐)、`setFlexCounterGroupOperation` で syncd に disable 操作が伝わり、syncd はポーリングを停止する。`COUNTERS_DB:COUNTERS:<oid>` のハッシュは**削除されず**、最後の値が残る。

ポート削除時は `m_counterNameMapUpdater->delCounterNameMap(alias)` で `COUNTERS_PORT_NAME_MAP` から当該エントリが削除される (portsorch.cpp:4312)。

### 7. PORT テーブルとの依存関係まとめ

| 先行必須テーブル/イベント | 理由 | ソース |
|---|---|---|
| `APP_DB:PORT_TABLE\|PortInitDone` | `allPortsReady()` が false の間 flexcounterorch は全リターン | `flexcounterorch.cpp:164-166`, `portsorch.cpp:1685-1687` |
| `CONFIG_DB:FLEX_COUNTER_TABLE\|PORT` (`FLEX_COUNTER_STATUS=enable`) | enable 前は `generatePortCounterMap()` が呼ばれず COUNTER_ID_LIST が syncd に渡らない | `flexcounterorch.cpp:235-240` |
| SAI ポート作成（portsorch による PHY ポート登録） | `m_portList` に PHY ポートが存在しないと `generatePortCounterMap()` でスキップされる | `portsorch.cpp:9112-9117` |

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `PortInitDone` → `FLEX_COUNTER_TABLE\|PORT enable` 処理 | 先行必須（欠如時は m_toSync 保留、自動リトライ） | 次 tick で自動処理される |
| 2 | `generatePortCounterMap()` → syncd COUNTER_ID_LIST → COUNTERS_DB | 一度限り冪等呼び出し（m_isPortCounterMapGenerated） | enable 後追加ポートは即時登録 |
| 3 | counterpoll enable 前ポート vs 後ポートの登録経路差 | 設計上の分岐（どちらも最終的に登録される） | なし |
| 4 | Warm Start 時の 60 秒遅延 | タイミング依存（非エラー） | 遅延後に自動処理 |
| 5 | ポート作成 → COUNTERS_PORT_NAME_MAP 書き込み | counterpoll 状態に依存しない（常時実行） | なし |
| 6 | counterpoll disable → COUNTERS_DB 値は残留 | DEL は noop（最後の値が保持される） | 明示的なクリアは不要 |
