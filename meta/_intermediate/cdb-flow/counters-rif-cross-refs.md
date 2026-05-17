# COUNTERS_DB RIF カウンタ — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/counters-rif.md`
解析日: 2026-05-17
根拠ソース: `sonic-swss/orchagent/intfsorch.cpp`, `sonic-swss/orchagent/flexcounterorch.cpp`, `sonic-swss/orchagent/orchdaemon.cpp`

---

## 目的

`IntfsOrch` が `INTERFACE` テーブルを処理して RIF を作成し、COUNTERS_DB に RIF カウンタを登録する際に
暗黙的に参照・依存する他テーブルのキー / フィールドを網羅する。
YANG の leafref として定義されたものはなく、コードのみで表現された依存関係である。

---

## 1. PORT (PortsOrch) — 全ポート Ready ガード

### 参照箇所

`IntfsOrch::doTask(Consumer)` — `intfsorch.cpp:665-668`

```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

### 依存内容

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `doTask(Consumer)` の INTERFACE 処理 | `PORT` (APP_PORT_TABLE 経由) | `APP_PORT_TABLE\|<port_name>` | `allPortsReady()` が true になるまで INTERFACE の SET/DEL 処理を完全ブロック。PortsOrch が全ポートの SAI OID を取得して ready を宣言する前に IntfsOrch は何もしない | `intfsorch.cpp:665-668` |

---

## 2. VRF_TABLE — vrf_name が指定された場合の先行依存

### 参照箇所

`IntfsOrch::doTask(Consumer)` — `intfsorch.cpp:824-831`

```cpp
if (!vrf_name.empty())
{
    if (!m_vrfOrch->isVRFexists(vrf_name))
    {
        it++;
        continue;  // VRF が存在しない間はキューに留まりリトライ
    }
    vrf_id = m_vrfOrch->getVRFid(vrf_name);
}
```

### 依存内容

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `doTask(Consumer)` の RIF 作成判断 | [`VRF_TABLE`](vrf.md) | `VRF_TABLE\|<vrf_name>` | `INTERFACE` エントリに `vrf_name` フィールドがある場合、VRFOrch に当該 VRF が存在しない間は Consumer キューに留まってリトライし、RIF を作成しない。VRF なし（デフォルト VRF）の場合は依存なし | `intfsorch.cpp:824-831` |

---

## 3. FLEX_COUNTER_TABLE|RIF — FlexCounter ポーリング制御

### 参照箇所

`FlexCounterOrch::doTask()` — `flexcounterorch.cpp:283-286`

```cpp
if(gIntfsOrch && (key == RIF_KEY) && (value == "enable"))
{
    gIntfsOrch->generateInterfaceMap();
}
```

### 依存内容

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `generateInterfaceMap()` の呼び出しトリガ | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|RIF` フィールド `FLEX_COUNTER_STATUS` | `enable` になると `generateInterfaceMap()` → タイマーキック → `addRifToFlexCounter()` の連鎖が起動。`disable` のままでは `COUNTERS_RIF_NAME_MAP` / `COUNTERS_RIF_TYPE_MAP` へのマッピングは書かれるが syncd の SAI ポーリングは開始されず `COUNTERS:<oid>` は更新されない | `flexcounterorch.cpp:283-286`, `intfsorch.cpp:1576-1578` |

---

## 4. ASIC_DB VIDTORID — Traditional FlexCounter モード待機

### 参照箇所

`IntfsOrch::doTask(SelectableTimer)` — `intfsorch.cpp:1627-1636`

```cpp
if (!gTraditionalFlexCounter || m_vidToRidTable->hget("", id, value))
{
    addRifToFlexCounter(id, it->m_alias, type);
    it = m_rifsToAdd.erase(it);
}
else
{
    ++it;  // VID→RID が未登録ならキューに留めてリトライ
}
```

### 依存内容

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `addRifToFlexCounter()` の実行条件 | `ASIC_DB VIDTORID` | `VIDTORID\|<oid>` | `gTraditionalFlexCounter=true` の場合、syncd が SAI create_router_interface 応答を受けて ASIC_DB の `VIDTORID` に OID を書き込むまで `addRifToFlexCounter()` を呼ばない（最大 1 秒タイマーの次 tick でリトライ）。新規 FlexCounter モード (`gTraditionalFlexCounter=false`) では即座に登録 | `intfsorch.cpp:1627-1636` |

---

## 5. cross-refs ブロック（最終形）

以下を `docs/reference/config-db/counters-rif.md` の `<!-- /ordering -->` 直後に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: sonic-swss/orchagent/intfsorch.cpp (doTask Consumer, doTask SelectableTimer,
     addRifToFlexCounter, addRouterIntfs),
     sonic-swss/orchagent/flexcounterorch.cpp (doTask, generateInterfaceMap 呼出し),
     sonic-swss/orchagent/orchdaemon.cpp (初期化順序) -->

`IntfsOrch` が INTERFACE テーブルを処理して RIF を生成し、COUNTERS_DB に RIF カウンタを登録する際に
暗黙的に参照する他テーブルを示す。YANG の leafref として定義されたものはなく、コードのみで表現された依存関係である。

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---|---|---|---|---|
| `doTask(Consumer)` の INTERFACE 処理全体 | `PORT` | `APP_PORT_TABLE\|<port_name>` | `allPortsReady()` が false の間は INTERFACE の SET/DEL をすべてブロック。PortsOrch が全ポートの SAI OID 取得完了を宣言するまで RIF 作成も削除も行われない | `intfsorch.cpp:665-668` |
| `doTask(Consumer)` の RIF 作成判断 | [`VRF_TABLE`](vrf.md) | `VRF_TABLE\|<vrf_name>` | `INTERFACE` に `vrf_name` フィールドがある場合、VRFOrch に当該 VRF が登録済みでないと Consumer キューに留まりリトライ。VRF なし（デフォルト VRF）なら依存なし | `intfsorch.cpp:824-831` |
| `generateInterfaceMap()` のトリガ | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|RIF` フィールド `FLEX_COUNTER_STATUS` | `enable` 受信時に `generateInterfaceMap()` → タイマーキック → `addRifToFlexCounter()` の連鎖が起動する。`disable` のままでも COUNTERS_RIF_NAME_MAP / COUNTERS_RIF_TYPE_MAP への書き込みは行われるが、syncd の SAI ポーリングは開始されず `COUNTERS:<oid>` は更新されない | `flexcounterorch.cpp:283-286`, `intfsorch.cpp:1576-1578` |
| `addRifToFlexCounter()` の実行条件 | `ASIC_DB VIDTORID` | `VIDTORID\|<oid>` | `gTraditionalFlexCounter=true` の場合、syncd が SAI `create_router_interface` 応答後に `VIDTORID` へ OID を書くまで登録を保留（最大 1 秒間隔でリトライ）。新規 FlexCounter モード (`false`) では即時登録 | `intfsorch.cpp:1627-1636` |

### 解決タイミング

- **PORT**: `allPortsReady()` による自動待機。PortsOrch が初期化完了後に IntfsOrch の INTERFACE 処理がアンブロックされる。
- **VRF_TABLE**: `doTask` ループの `continue` でリトライ。VRF が後から追加されると次の Consumer イベント処理時に解決する。
- **FLEX_COUNTER_TABLE**: `FlexCounterOrch::doTask()` が即時評価。`enable` 書込み時点でタイマーがキックされ、最大 1 秒後に登録が完了する。
- **ASIC_DB VIDTORID**: `doTask(SelectableTimer)` の 1 秒タイマーでリトライ。通常は RIF 作成後 1 秒以内に syncd が書き込む。
<!-- /cross-refs -->
```
