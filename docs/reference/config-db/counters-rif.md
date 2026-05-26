---
title: COUNTERS_DB RIF カウンタ
description: "COUNTERS_DB における RIF (Router Interface) カウンタ関連エントリ — intfsorch が SAI flex counter 経由で収集し COUNTERS_DB に格納する L3 インタフェース統計フィールドの構造・デフォルト・書き込み経路の解説。"
area: reference
verification: code-verified
last_verified: 2026-05-17
hard: 0
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/intfsorch.cpp
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss
    path: orchagent/intfsorch.h
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss
    path: orchagent/rif_rates.lua
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d
  - repo: sonic-net/sonic-utilities
    path: scripts/intfstat
    ref: 39732bceb8bd
  - repo: sonic-net/sonic-utilities
    path: counterpoll/main.py
    ref: 39732bceb8bd
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-orchagent/enable_counters.py
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/neighorch.cpp
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss
    path: orchagent/routeorch.cpp
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss
    path: orchagent/nhgorch.cpp
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss
    path: orchagent/vnetorch.cpp
    ref: 4305596156d7
related:
  config_db:
    - FLEX_COUNTER_TABLE
    - INTERFACE
  cli:
    - intfstat
    - counterpoll
---

# COUNTERS_DB RIF カウンタ

## 概要

[intfsorch](../../reference/glossary.md#term-intfsorch)（[orchagent](../../reference/glossary.md#term-orchagent) 内）が [SAI](../../reference/glossary.md#term-sai) の flex counter 機構を通じて L3 Router Interface ([RIF](../../reference/glossary.md#term-rif)) ごとに取得する統計カウンタ群[^1]。値は `COUNTERS_DB` の `COUNTERS:<oid>` に格納され、`intfstat` コマンドが読み出す。rate 統計は `RATES:<oid>` に別途格納される。

## key 構造

### RIF 名→OID マップ

```text
COUNTERS_DB / COUNTERS_RIF_NAME_MAP   (Hash)
  field: <rif_name>   (例: Ethernet0, Vlan1000, PortChannel0001)
  value: <SAI OID>    (例: oid:0x6000000000001)
```

### RIF タイプ→OID マップ

```text
COUNTERS_DB / COUNTERS_RIF_TYPE_MAP   (Hash)
  field: <SAI OID>
  value: <type>       (例: SAI_ROUTER_INTERFACE_TYPE_PORT, SAI_ROUTER_INTERFACE_TYPE_VLAN, SAI_ROUTER_INTERFACE_TYPE_SUB_PORT)
```

### カウンタハッシュ

```text
COUNTERS_DB / COUNTERS:<oid>           (Hash)
  field: <SAI_ROUTER_INTERFACE_STAT_*>
  value: <uint64 カウンタ値 (文字列)>
```

### レートハッシュ

```text
COUNTERS_DB / RATES:<oid>              (Hash)
  field: RX_BPS | RX_PPS | TX_BPS | TX_PPS
  value: <float 文字列>
```

## フィールド一覧

以下は `intfsorch.cpp` の `rifStatIds[]` に定義されている全 [SAI](../../reference/glossary.md#term-sai) カウンタ ID[^2]。

### RIF カウンタ

| [SAI](../../reference/glossary.md#term-sai) フィールド | 意味 |
|---------------|------|
| `SAI_ROUTER_INTERFACE_STAT_IN_PACKETS` | 受信パケット数 |
| `SAI_ROUTER_INTERFACE_STAT_IN_OCTETS` | 受信バイト数 |
| `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS` | 受信エラーパケット数 |
| `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS` | 受信エラーバイト数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS` | 送信パケット数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS` | 送信バイト数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS` | 送信エラーパケット数 |
| `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS` | 送信エラーバイト数 |

## RATES テーブル

[syncd](../../reference/glossary.md#term-syncd) が `rif_rates.lua` を定期実行して計算した派生レートを `RATES:<oid>` に書く[^3]。

| フィールド | 意味 |
|-----------|------|
| `RX_BPS` | 受信ビットレート (bps) |
| `RX_PPS` | 受信パケットレート (pps) |
| `TX_BPS` | 送信ビットレート (bps) |
| `TX_PPS` | 送信パケットレート (pps) |

## 書き込み経路

`COUNTERS_DB` は直接 [CONFIG_DB](../../reference/glossary.md#term-config_db) から書かれず、すべて [orchagent](../../reference/glossary.md#term-orchagent) / [syncd](../../reference/glossary.md#term-syncd) 経由で書かれる。

| 経路 | 詳細 |
|------|------|
| [intfsorch](../../reference/glossary.md#term-intfsorch) 初期化 | `COUNTERS_RIF_NAME_MAP` に [RIF](../../reference/glossary.md#term-rif) 名→OID、`COUNTERS_RIF_TYPE_MAP` に OID→タイプを書き込み |
| [syncd](../../reference/glossary.md#term-syncd) [FlexCounter](../../reference/glossary.md#term-flexcounter) | `FLEX_COUNTER_TABLE|RIF` が `enable` になった後、1 秒ごとに SAI カウンタをポーリングして `COUNTERS:<oid>` を更新 |
| syncd Lua プラグイン | `rif_rates.lua` が `RATES:<oid>` の RX_BPS / RX_PPS / TX_BPS / TX_PPS を書き込み |

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `FLEX_COUNTER_TABLE` — ポーリング有効化と間隔設定
- CLI: `intfstat`（L3 インタフェース統計表示）、`counterpoll rif enable/disable/interval`

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動 (Phase A)

<!-- evidence: sonic-swss/orchagent/intfsorch.cpp, sonic-swss/orchagent/intfsorch.h,
     sonic-swss/orchagent/rif_rates.lua,
     sonic-utilities/counterpoll/main.py,
     sonic-buildimage/dockers/docker-orchagent/enable_counters.py -->

### ポーリング間隔のコード由来デフォルト

`FLEX_COUNTER_TABLE|RIF` に `POLL_INTERVAL` が設定されていない場合、[intfsorch](../../reference/glossary.md#term-intfsorch) が **ハードコードした初期値**で syncd に投入する[^4]。

| カウンタグループ | ハードコード定数 | 値 |
|----------------|---------------|-----|
| `RIF` (通常カウンタ) | `RIF_FLEX_STAT_COUNTER_POLL_MSECS` (intfsorch.h:21) | **1000 ms** |

`counterpoll show` の表示でも RIF_STAT グループは `DEFLT_1_SEC = "default (1000)"` をフォールバック値として使用する（counterpoll/main.py:815）。

### `FLEX_COUNTER_STATUS` 未設定時の挙動

`FLEX_COUNTER_TABLE|RIF` の `FLEX_COUNTER_STATUS` が `enable` になるまで syncd は SAI ポーリングを行わない。カウンタ値は 0 のまま（または古い値）。

| 種類 | 詳細 |
|------|------|
| コード由来デフォルト | `FLEX_COUNTER_STATUS` なし → syncd 収集なし |
| CLI デフォルト | `counterpoll show` 未設定時は `disable` 扱いで表示される（counterpoll/main.py:815） |

### レートスムージングのデフォルト

`rif_rates.lua` は [COUNTERS_DB](../../reference/glossary.md#term-counters_db) の `RATES:RIF` エントリから `RIF_SMOOTH_INTERVAL` と `RIF_ALPHA` を読み取り、指数移動平均 (EMA) でレートを平滑化する[^5]。これらの値は `enable_counters.py` によって起動時に書き込まれる。

| パラメータ | デフォルト値 | 定義箇所 |
|-----------|------------|---------|
| `RIF_SMOOTH_INTERVAL` | **10**（秒） | `enable_counters.py:10` |
| `RIF_ALPHA` | **0.18**（= 2/(10+1) ≈ 0.182）| `enable_counters.py:11` |

`RIF_ALPHA` は alpha = 2/(N+1) で、N = ウィンドウ幅（秒）から導出される。デフォルト 10 秒ウィンドウで 1 秒スパイクの影響が約 10 秒で収束するよう設計されている（enable_counters.py:7-9 コメント）。

ユーザが `config rate smoothing-interval <interval> rif` を実行すると新しい alpha = 2.0/(interval+1) が計算され `RATES:RIF` に書き直される（config/main.py:9591-9598）。

!!! warning "RIF_ALPHA 未定義時の挙動"
    `rif_rates.lua` は `RIF_ALPHA` が未定義の場合 `"Alpha is not defined"` をログに残して即 return する（rif_rates.lua:21-23）。`enable_counters.py` が実行されていない場合はレート計算が一切行われず `RATES:<oid>` が空のままになる。

### 起動遅延（enable_counters.py）

`enable_counters.py` はシステム起動後にデフォルト率設定を書き込む前に意図的に sleep する[^6]。

| 起動後経過時間 | sleep 時間 |
|-------------|-----------|
| < 5 分（uptime < 300 s） | **180 秒**（3 分待機後に設定書き込み） |
| 5 分以上 | **60 秒**（1 分待機後に設定書き込み） |

これにより [orchagent](../../reference/glossary.md#term-orchagent) / syncd が完全に初期化される前に `RATES:RIF` が書かれることを防いでいる。

### RIF タイプ別登録

intfsorch は [RIF](../../reference/glossary.md#term-rif) ごとに `COUNTERS_RIF_TYPE_MAP` に OID→タイプ（`SAI_ROUTER_INTERFACE_TYPE_PORT`, `SAI_ROUTER_INTERFACE_TYPE_VLAN`, `SAI_ROUTER_INTERFACE_TYPE_SUB_PORT` 等）を書く。`COUNTERS_RIF_NAME_MAP` には RIF 名（インタフェース名）→OID のマッピングが格納され、`intfstat` がこのマップを元にカウンタを引く。

### SAI フィールド未サポート時の挙動

[ASIC](../../reference/glossary.md#term-asic) が対応していない SAI カウンタは `intfstat` の `get_counters()` で `STATUS_NA` ('N/A') として扱われ、表示に `N/A` が出る（scripts/intfstat:93-98）。

<!-- /defaults -->

<!-- ordering -->
## 処理順序と順序依存 (Phase B)

### orchdaemon 初期化順序

`orchdaemon.cpp` における Orch 生成順序は次のとおりで、`gIntfsOrch` は `FlexCounterOrch` より前に生成される[^7]。

| 順序 | 生成クラス | 依存 |
|------|-----------|------|
| 1 | `PortsOrch` | — |
| 2 | `VRFOrch` | — |
| 3 | `IntfsOrch` | VRFOrch, PortsOrch |
| 4 | `FlexCounterOrch` | gIntfsOrch (既に設定済み) |

`FlexCounterOrch::doTask()` は `gIntfsOrch != nullptr` を確認してから `generateInterfaceMap()` を呼ぶため、IntfsOrch より前に `FLEX_COUNTER_TABLE|RIF enable` が来ても安全に無視される（`gIntfsOrch` が nullptr なら分岐しない）。

### PortsOrch ガード — 全ポート Ready 前は INTERFACE 処理なし

`IntfsOrch::doTask(Consumer)` の先頭でポート初期化完了を確認する（`intfsorch.cpp:665-668`）。

```
if (!gPortsOrch->allPortsReady()) return;
```

`APP_INTF_TABLE` の SET メッセージは Consumer キューに積まれたまま保持され、`PortsOrch::allPortsReady()` が `true` を返した後に初めて処理される。したがって `INTERFACE` エントリに対応する物理ポート（`Ethernet0`、`PortChannel0001`、`Vlan1000` 等）が PortsOrch に登録済みであることが前提になる。

### RIF 作成 → タイマー駆動の非同期 FlexCounter 登録

`addRouterIntfs()` で SAI RIF 作成後、`port` を `m_rifsToAdd` リストにキューイングするのみで [FlexCounter](../../reference/glossary.md#term-flexcounter) には即時登録しない。実際の登録は `UPDATE_MAPS_SEC = 1 秒` 間隔のタイマーが発火して `doTask(SelectableTimer)` が呼ばれた後になる（`intfsorch.cpp:45, 78`）[^8]。

```
APP_INTF_TABLE SET
  → doTask(Consumer) → addRouterIntfs() → SAI RIF 作成 → m_rifsToAdd 追加
  最大 1 秒後
  → doTask(SelectableTimer) → addRifToFlexCounter()
      → COUNTERS_RIF_NAME_MAP (name→OID)
      → COUNTERS_RIF_TYPE_MAP (OID→type)
      → FLEX_COUNTER_DB: COUNTER_ID_LIST 登録
  syncd がポーリング開始 (FLEX_COUNTER_TABLE|RIF enable が前提)
      → COUNTERS:<oid> 更新
      → RATES:<oid> 更新 (rif_rates.lua)
```

この最大 1 秒の遅延の間、`COUNTERS_RIF_NAME_MAP` に当該 RIF のエントリが存在しない。`intfstat` を RIF 作成直後に実行すると表示されないことがある。

### gTraditionalFlexCounter モードでの ASIC_DB 待機

`gTraditionalFlexCounter = true`（`--use-sairedis` オプション）の場合、タイマーが発火しても [ASIC_DB](../../reference/glossary.md#term-asic_db) の `VIDTORID` テーブルに該当 OID が存在するまで `addRifToFlexCounter()` を呼ばない（`intfsorch.cpp:1629-1636`）。

`syncd` が SAI `create_router_interface` の応答を受けて `VIDTORID` を書いた後に初めて登録が完了する。新規 [FlexCounter](../../reference/glossary.md#term-flexcounter) モード (`gTraditionalFlexCounter = false`) では即座に登録する。

### FLEX_COUNTER_TABLE|RIF enable → generateInterfaceMap() 連鎖

`FlexCounterOrch::doTask()` が `FLEX_COUNTER_STATUS = enable` を受信すると（`flexcounterorch.cpp:283-285`）:

```
FlexCounterOrch::doTask()
  → gIntfsOrch->generateInterfaceMap()
      → m_updateMapsTimer->start()
          → doTask(SelectableTimer) (次回発火時)
              → m_rifsToAdd の全 RIF を addRifToFlexCounter()
```

すでに `m_rifsToAdd` に積まれた RIF が一括登録される。orchdaemon 起動直後は `FlexCounterOrch::m_delayTimerExpired = false` のため、warm-reboot 完了前に enable が来ても early return する（`flexcounterorch.cpp:157-160`）。

### 削除時の順序

`removeIntf()` → `removeRouterIntfs()` → `removeRifFromFlexCounter()` の順で処理される:

1. `COUNTERS_RIF_NAME_MAP` と `COUNTERS_RIF_TYPE_MAP` から hdel
2. `FLEX_COUNTER_DB` の COUNTER_ID_LIST を `stopFlexCounterPolling()` で削除
3. `COUNTERS:<oid>` は syncd 側が SAI の remove 応答後にクリーンアップする（IntfsOrch は直接削除しない）

`m_rifsToAdd` にまだキューイングされている RIF（`addRifToFlexCounter` 未実行）は `removeRouterIntfs()` 内でリストから除去されるだけで FlexCounter 側のクリーンアップは不要（`intfsorch.cpp:1337-1344`）。

> **コード証跡**: `intfsorch.cpp` L43 (priority 35), L45,78 (UPDATE_MAPS_SEC=1), L665-668 (PortsOrch ガード), L1296-1311 (addRouterIntfs→m_rifsToAdd), L1527-1552 (addRifToFlexCounter 書き込み順序), L1576-1578 (generateInterfaceMap), L1598-1638 (doTask Timer + gTraditionalFlexCounter 分岐), L1337-1344 (削除時クリーンアップ);
> `flexcounterorch.cpp` L157-160 (delayTimer ガード), L283-285 (RIF enable → generateInterfaceMap);
> `orchdaemon.cpp` L232, L283, L296, L625 (初期化順序)

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: sonic-swss/orchagent/intfsorch.cpp (doTask Consumer, doTask SelectableTimer,
     addRifToFlexCounter, addRouterIntfs),
     sonic-swss/orchagent/flexcounterorch.cpp (doTask, generateInterfaceMap 呼出し),
     sonic-swss/orchagent/orchdaemon.cpp (初期化順序) -->

`IntfsOrch` が INTERFACE テーブルを処理して RIF を生成し、[COUNTERS_DB](../../reference/glossary.md#term-counters_db) に RIF カウンタを登録する際に暗黙的に参照する他テーブルを示す。[YANG](../../reference/glossary.md#term-yang) の leafref として定義されたものはなく、コードのみで表現された依存関係である。

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
- **[ASIC_DB](../../reference/glossary.md#term-asic_db) VIDTORID**: `doTask(SelectableTimer)` の 1 秒タイマーでリトライ。通常は RIF 作成後 1 秒以内に syncd が書き込む。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動・retry / recovery (Phase D)

<!-- evidence: sonic-swss/orchagent/intfsorch.cpp (addRouterIntfs L1297-1305,
     removeRouterIntfs L1327-1357, doTask Consumer L665-668,
     doTask SelectableTimer L1604-1636, constructor L86-94);
     sonic-swss/orchagent/flexcounterorch.cpp (doTask L156-160) -->

### SAI `create_router_interface` 失敗 → `throw runtime_error`

`addRouterIntfs()` が SAI API を呼ぶ際、`SAI_STATUS_SUCCESS` 以外が返ると `handleSaiCreateStatus()` の結果に応じて動作が分岐する[^9]。

| `handleSaiCreateStatus` 結果 | 動作 |
|-------------------------------|------|
| `task_success` | ログ (`SWSS_LOG_ERROR`) のみで続行（`m_rifsToAdd` への追加は継続） |
| それ以外 | `throw runtime_error` → orchdaemon クラッシュ → systemd が再起動 |

[COUNTERS_DB](../../reference/glossary.md#term-counters_db) への書き込みは発生しない（`addRifToFlexCounter()` は `doTask(SelectableTimer)` で後続実行されるため）。

### SAI `remove_router_interface` 失敗 → COUNTERS_DB と SAI の乖離

`removeRouterIntfs()` は `removeRifFromFlexCounter()` を**先**に呼んでから SAI 削除を実行する（`intfsorch.cpp:1345-1355`）。

```
removeRifFromFlexCounter()
  → COUNTERS_RIF_NAME_MAP / COUNTERS_RIF_TYPE_MAP から hdel  ← 先に実行
  → FLEX_COUNTER_DB の COUNTER_ID_LIST 削除
SAI remove_router_interface  ← 後で実行 → 失敗した場合
  → throw runtime_error → orchdaemon 再起動
```

SAI 削除失敗時には COUNTERS_DB から RIF はすでに除去されているが、SAI レイヤーには RIF が残ったままになる。次回 orchdaemon 再起動時の reconcile で収束する。

### ref_count > 0 による DEL ブロック

IP プレフィックスが残っている間は RIF 削除を拒否する（`intfsorch.cpp:1327-1332`）。

```
APP_INTF_TABLE DEL → removeIntf() → ref_count > 0 → return false
```

Consumer の `it` は erase されず次回イベントでリトライされる（Consumer 標準 retry 機構）。COUNTERS_DB に変化なし。

### allPortsReady() false → INTERFACE 処理全停止

PortsOrch が初期化完了（全ポートの SAI OID 取得）を宣言するまで、`APP_INTF_TABLE` の全 SET/DEL が Consumer キューで保留される（`intfsorch.cpp:665-668`）。この間 COUNTERS_DB に変化はなく、ポート初期化完了後に自動的に処理が再開される。

### `rif_rates.lua` ロード失敗 → RATES テーブルが永続的に更新されない

コンストラクタでの Lua スクリプトロードが `runtime_error` をスローした場合、`catch` ブロックで `SWSS_LOG_WARN` を出力して続行する（`intfsorch.cpp:86-94`）[^10]。

| 状態 | 影響 |
|------|------|
| `rifRateSha` が空文字列 | syncd に Lua プラグインが登録されない |
| syncd の動作 | `COUNTERS:<oid>` のポーリングは継続するが `RATES:<oid>` は更新されない |
| `intfstat` 表示 | rate 列（RX_BPS / TX_BPS / RX_PPS / TX_PPS）が `N/A` になる |
| 回復方法 | orchdaemon 再起動のみ（ファイル復元後も自動再ロードなし） |

### `gTraditionalFlexCounter` モードで ASIC_DB VIDTORID 未到達

`gTraditionalFlexCounter=true` の環境で syncd が `VIDTORID` を書き込まない場合、`m_rifsToAdd` に RIF が残り続け、1 秒タイマーの毎発火でリトライするが COUNTERS_DB への登録は完了しない（`intfsorch.cpp:1627-1636`）。`SWSS_LOG_INFO` のみで `SWSS_LOG_ERROR` / `SWSS_LOG_WARN` は出ないため、監視が困難[^11]。

### warm-reboot 時の 60 秒遅延

warm-reboot 完了前に `FLEX_COUNTER_TABLE|RIF = enable` が届いても、`FlexCounterOrch::doTask()` は `m_delayTimerExpired = false` の間 early return する（`flexcounterorch.cpp:156-160`）。

| タイミング | 動作 |
|-----------|------|
| warm-reboot 開始〜60 秒後 | `generateInterfaceMap()` が呼ばれない → RIF カウンタ更新なし |
| 60 秒後 | `m_delayTimerExpired = true` → 自動再開 |

**永続的な障害ではなく**、最大 60 秒の遅延で自動回復する。

### 失敗パス要約

| ケース | ログ | retry/recovery | COUNTERS_DB 影響 |
|--------|------|----------------|-----------------|
| SAI create 失敗 (throw) | `SWSS_LOG_ERROR` | orchdaemon 再起動 | 書き込みなし |
| SAI remove 失敗 (throw) | `SWSS_LOG_ERROR` | orchdaemon 再起動 | NAME_MAP 削除済み (乖離) |
| ref_count > 0 で DEL | `SWSS_LOG_NOTICE` | Consumer 次イベント | 変化なし |
| allPortsReady false | なし | 起動完了後自動再開 | 変化なし |
| rif_rates.lua ロード失敗 | `SWSS_LOG_WARN` | 再起動のみ | RATES 永続的に更新なし |
| VIDTORID 未書込み | `SWSS_LOG_INFO` のみ | 1 秒タイマー自動リトライ | 登録保留（永続的な場合あり）|
| warm-reboot 60 秒遅延 | なし | 60 秒後自動回復 | 最大 60 秒遅延 |

> 中間調査詳細: `meta/_intermediate/cdb-flow/counters-rif-failure.md`
<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: sonic-swss/orchagent/intfsorch.cpp (L43-45, L96-100, L1551),
     sonic-swss/orchagent/intfsorch.h (L19-21),
     sonic-swss/orchagent/flexcounterorch.cpp (L44),
     sonic-swss-common/common/schema.h (L302, L330),
     sonic-buildimage/dockers/docker-orchagent/enable_counters.py (L10-11) -->

`IntfsOrch` と `FlexCounterOrch` に含まれる、[CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) では管理されないハードコード定数の一覧。

### FlexCounter グループ識別子

| 定数名 | 値 | 定義箇所 | 用途 |
|--------|-----|---------|------|
| `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"RIF_STAT_COUNTER"` | `intfsorch.h:19` | syncd の FlexCounter グループ名（通常カウンタ） |
| `RIF_RATE_COUNTER_FLEX_COUNTER_GROUP` | `"RIF_RATE_COUNTER"` | `intfsorch.h:20` | syncd の FlexCounter グループ名（レートカウンタ） |

これらの文字列は [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) のキープレフィックスとして使われる（例: `RIF_STAT_COUNTER:<oid>`）。

### ポーリング間隔

| 定数名 | 値 | 定義箇所 | 用途 |
|--------|-----|---------|------|
| `RIF_FLEX_STAT_COUNTER_POLL_MSECS` | `"1000"` (ms) | `intfsorch.h:21` | RIF 通常カウンタのポーリング間隔。`setFlexCounterGroupParameter()` に渡されてデフォルトの poll interval を設定する |

`counterpoll show` でも `DEFLT_1_SEC = "default (1000)"` がフォールバック値として使われる（`counterpoll/main.py:815`）。

### タイマー間隔

| 定数名 | 値 | 定義箇所 | 用途 |
|--------|-----|---------|------|
| `UPDATE_MAPS_SEC` | `1` (秒) | `intfsorch.cpp:45` | `m_updateMapsTimer` の発火間隔。`doTask(SelectableTimer)` がこの間隔で `m_rifsToAdd` を処理して `addRifToFlexCounter()` を呼ぶ |
| `FLEX_COUNTER_DELAY_SEC` | `60` (秒) | `flexcounterorch.cpp:44` | Warm-reboot 時に FlexCounterOrch が全処理を遅延させる秒数 |
| `intfsorch_pri` | `35` | `intfsorch.cpp:43` | IntfsOrch の Orch 優先度（数値が大きいほど高優先） |

### FlexCounter フィールド名

| 定数名 | 値 | 定義箇所 | 用途 |
|--------|-----|---------|------|
| `RIF_COUNTER_ID_LIST` | `"RIF_COUNTER_ID_LIST"` | `schema.h:302` | [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) に書き込む SAI カウンタ ID リストのフィールド名 |
| `RIF_PLUGIN_FIELD` | `"RIF_PLUGIN_LIST"` | `schema.h:330` | FlexCounter グループに Lua プラグイン (`rif_rates.lua`) を登録するフィールド名 |

### レートスムージング定数

| 定数名 | 値 | 定義箇所 | 用途 |
|--------|-----|---------|------|
| `DEFAULT_SMOOTH_INTERVAL` | `"10"` (秒) | `enable_counters.py:10` | `RATES:RIF` に書き込む `RIF_SMOOTH_INTERVAL` のデフォルト値。EMA ウィンドウ幅 |
| `DEFAULT_ALPHA` | `"0.18"` | `enable_counters.py:11` | `RATES:RIF` に書き込む `RIF_ALPHA` のデフォルト値。= 2/(10+1) ≈ 0.1818…（小数点 2 桁丸め） |

`RIF_ALPHA = 2 / (N + 1)` の関係で、`N = DEFAULT_SMOOTH_INTERVAL = 10` から算出される。ユーザが `config rate smoothing-interval` で変更すると、新しい alpha が再計算されて `RATES:RIF` に上書きされる。

### SAI カウンタ ID 静的配列

`intfsorch.cpp:49-59` に `rifStatIds[]` として次の 8 カウンタが列挙されており、`addRifToFlexCounter()` の実行時に全てが `RIF_COUNTER_ID_LIST` として [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) に登録される。

```text
SAI_ROUTER_INTERFACE_STAT_IN_PACKETS
SAI_ROUTER_INTERFACE_STAT_IN_OCTETS
SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS
SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS
SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS
SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS
SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS
SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS
```

この配列は定数であり、実行時や CONFIG_DB 設定で変更できない。[ASIC](../../reference/glossary.md#term-asic) が対応しないカウンタは syncd が SAI エラーを返し、`intfstat` では `N/A` として表示される。

<!-- /constants -->

<!-- side-effects -->
## 副作用・他 DB への波及 (Phase F)

<!-- evidence: sonic-swss/orchagent/intfsorch.cpp (L86-100, L1309, L1317, L1327-1330, L1363, L1370, L1537-1551, L1559-1566, L1778),
     sonic-swss/orchagent/neighorch.cpp (L349,L441,L676,L744),
     sonic-swss/orchagent/routeorch.cpp (L1362,L1384),
     sonic-swss/orchagent/nhgorch.cpp (L757,L885),
     sonic-swss/orchagent/vnetorch.cpp (L211,L235) -->

`IntfsOrch` が RIF を作成・削除するとき、`COUNTERS_DB` だけでなく複数の DB・オブジェクトに副作用書き込みを行う。

### RIF 作成時の副作用（addRifToFlexCounter）

`addRifToFlexCounter()` (intfsorch.cpp:1527-1552) は以下の 3 DB に順次書き込む[^13]:

| DB | キー | 内容 |
|----|------|------|
| COUNTERS_DB | `COUNTERS_RIF_NAME_MAP` | `hset "" <rif_name> <oid>` |
| COUNTERS_DB | `COUNTERS_RIF_TYPE_MAP` | `hset "" <oid> <type>` |
| FLEX_COUNTER_DB | `RIF_STAT_COUNTER:<oid>` | `RIF_COUNTER_ID_LIST = <8 カウンタ ID 列挙>` |

3 件の書き込みはトランザクションなしで直列実行される。FLEX_COUNTER_DB への書き込みが完了した時点で syncd が SAI ポーリングを開始し、`COUNTERS:<oid>` の更新が始まる。

### RIF 削除時の副作用（removeRifFromFlexCounter）

`removeRifFromFlexCounter()` (intfsorch.cpp:1556-1568) は作成時の逆順で削除する[^14]:

1. `COUNTERS_RIF_NAME_MAP` から `hdel "" <name>`
2. `COUNTERS_RIF_TYPE_MAP` から `hdel "" <oid>`
3. FLEX_COUNTER_DB の `RIF_STAT_COUNTER:<oid>` を `stopFlexCounterPolling()` で削除

`COUNTERS:<oid>` は IntfsOrch が直接削除せず、syncd が FlexCounter 停止後にクリーンアップする。削除後もごく短期間、古い値が COUNTERS_DB に残留する場合がある。

### PortsOrch 内部状態への副作用

RIF 作成時 (intfsorch.cpp:1309) と削除時 (intfsorch.cpp:1363) に `gPortsOrch->setPort()` が呼ばれ、PortsOrch の Port オブジェクトが更新される。

| 操作 | 変化するフィールド | 値 |
|------|-----------------|-----|
| RIF 作成後 | `port.m_rif_id`, `port.m_vr_id` | SAI OID |
| RIF 削除後 | `port.m_rif_id`, `port.m_vr_id`, `port.m_nat_zone_id`, `port.m_mpls` | 0 / false |

この更新は PortsOrch インメモリ状態のみ。APP_DB / [STATE_DB](../../reference/glossary.md#term-state_db) への書き込みは発生しない。

### ref_count による他 Orch への波及ブロック

`m_syncdIntfses[alias].ref_count` は NeighOrch・RouteOrch・NhgOrch・VnetOrch から参照カウントとして操作される:

| Orch | ref_count 増加タイミング | ref_count 減少タイミング |
|------|----------------------|----------------------|
| NeighOrch | neighbor 追加 | neighbor 削除 |
| RouteOrch | nexthop alias を持つルート追加 | ルート削除 |
| NhgOrch | nexthop group メンバ追加 | メンバ削除 |
| VnetOrch | [VNET](../../reference/glossary.md#term-vnet) nexthop 追加 | [VNET](../../reference/glossary.md#term-vnet) nexthop 削除 |

`ref_count > 0` のとき `removeRouterIntfs()` は即 `false` を返す（intfsorch.cpp:1327-1330）。SAI RIF 削除も COUNTERS_DB クリーンアップも行われず、FlexCounter 登録は残ったままになる[^15]。

### VoQ 環境: CHASSIS_APP_DB への副作用（VOQ モード限定）

`isChassisDbInUse() == true` の場合のみ、以下の副作用書き込みが発生する:

| 操作 | 対象 DB | キー | 内容 |
|------|---------|------|------|
| RIF 作成 | CHASSIS_APP_DB | `SYSTEM_INTERFACE_TABLE|<system_alias>` | `oper_status` 設定 |
| RIF 削除 | CHASSIS_APP_DB | `SYSTEM_INTERFACE_TABLE|<system_alias>` | エントリ削除 |
| ポート状態変化 | CHASSIS_APP_DB | `SYSTEM_INTERFACE_TABLE|<system_alias>` | `oper_status` 更新 |

リモートシステムポート（`SAI_SYSTEM_PORT_TYPE_REMOTE`）および他スイッチの [LAG](../../reference/glossary.md#term-lag) は sync 対象外（intfsorch.cpp:1689-1692）[^16]。

### IntfsOrch 初期化時の副作用

`IntfsOrch::IntfsOrch()` コンストラクタ (intfsorch.cpp:86-100) の実行時に以下の副作用が一度だけ発生する:

1. `rif_rates.lua` を [Redis](../../reference/glossary.md#term-redis) にロード → COUNTERS_DB に Lua スクリプト SHA が登録される
2. `setFlexCounterGroupParameter()` → FLEX_COUNTER_DB の `RIF_STAT_COUNTER` グループにポーリング間隔・stats モード・Lua プラグイン SHA が書き込まれる

これらは CONFIG_DB 変化と無関係に、orchagent 起動時に自動実行される。

> 中間調査詳細: `meta/_intermediate/cdb-flow/counters-rif-side-effects.md`
<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

> 調査証跡: `meta/_intermediate/cdb-flow/counters-rif-pubsub.md`
> 調査対象: `sonic-swss/orchagent/flexcounterorch.cpp`, `sonic-swss/orchagent/intfsorch.cpp`, `sonic-swss/orchagent/orchdaemon.cpp`, `sonic-utilities/scripts/intfstat`

### Producer/Consumer ペア

RIF カウンタの制御経路は **CONFIG_DB → FlexCounterOrch → IntfsOrch → syncd** という 4 段構成をとる。[APPL_DB](../../reference/glossary.md#term-appl_db) 中継なし。

| 区間 | 方式 | 詳細 |
|------|------|------|
| CONFIG_DB → FlexCounterOrch | `SubscriberStateTable` | `FLEX_COUNTER_TABLE\|RIF` を購読。keyspace notification で変化を検出 |
| FlexCounterOrch → IntfsOrch | 直接関数呼び出し | `gIntfsOrch->generateInterfaceMap()` → `m_updateMapsTimer->start()` |
| IntfsOrch タイマー起動後 | `SelectableTimer` 駆動 | `doTask(SelectableTimer&)` で `m_rifsToAdd` リストを処理 |
| IntfsOrch → COUNTERS_DB | 直接書き込み | `m_rifNameTable->set()` / `m_rifTypeTable->set()` |
| IntfsOrch → FLEX_COUNTER_DB | `startFlexCounterPolling()` | `RIF_STAT_COUNTER:<oid>:COUNTER_ID_LIST` を書き込む |
| syncd → [ASIC](../../reference/glossary.md#term-asic) | SAI flex counter ポーリング | 1000 ms 間隔で SAI stat API をポーリング |
| syncd → COUNTERS_DB | 直接書き込み | `COUNTERS:<oid>` Hash に各 SAI フィールドをアトミック更新 |
| syncd + rif_rates.lua | Lua プラグイン実行 | ポーリング毎に `RATES:<oid>` の RX_BPS/TX_BPS/RX_PPS/TX_PPS を指数平滑化計算 |
| COUNTERS_DB → intfstat | `SonicV2Connector.get()` 直接読み出し | `COUNTERS_RIF_NAME_MAP` で名前→OID 解決後、`COUNTERS:<oid>` を読む（pull 型） |

`FlexCounterOrch::doTask()` における RIF 経路 (flexcounterorch.cpp:283-286):

```cpp
if(gIntfsOrch && (key == RIF_KEY) && (value == "enable"))
{
    gIntfsOrch->generateInterfaceMap();
}
```

### warm-start 遅延タイマー

`FlexCounterOrch` は cold-start では即座に処理を開始するが、warm-start では **60 秒**のタイマー (`FLEX_COUNTER_DELAY_SEC = 60`) が期限切れになるまで `doTask()` 全体をブロックする (flexcounterorch.cpp:127-137, 156-158)。これは syncd の warm-start 完了前に SAI ポーリングを開始しないための設計。

```
cold-start: m_delayTimerExpired = true → 即処理可能
warm-start: SelectableTimer(60s) 起動 → 60s 間 doTask ブロック
```

### gTraditionalFlexCounter モードの非同期待機

`gTraditionalFlexCounter == true` の場合、IntfsOrch は `m_rifsToAdd` に RIF を一旦キューイングし、`doTask(SelectableTimer&)` のたびに [ASIC_DB](../../reference/glossary.md#term-asic_db) `VIDTORID` テーブルに OID が現れるまで待機する (intfsorch.cpp:1627-1636)。`gTraditionalFlexCounter == false`（新モード）では VIDTORID 未到達でも即時 `addRifToFlexCounter()` が呼ばれる。

### intfstat の読み出しパス（pull 型）

`intfstat` は COUNTERS_DB を **直接読み取る**（pull 型）。`SubscriberStateTable` / `ConsumerStateTable` / [Redis](../../reference/glossary.md#term-redis) `PSUBSCRIBE` は使用しない。コマンド実行時点の最新スナップショットを取得する。

```python
# intfstat:81-82
self.db = SonicV2Connector(use_unix_socket_path=False)
self.db.connect(self.db.COUNTERS_DB)

# intfstat:123 — 名前→OID 解決
counter_rif_name_map = self.db.get_all(self.db.COUNTERS_DB, COUNTERS_RIF_NAME_MAP)
# intfstat:96 — SAI カウンタ値取得
counter_data = self.db.get(self.db.COUNTERS_DB, full_table_id, counter_name)
# intfstat:109 — RATES テーブル読み出し
counter_data = self.db.get(self.db.COUNTERS_DB, rates_table_id, name)
```

### データフロー図

```text
CONFIG_DB[FLEX_COUNTER_TABLE|RIF]
  ↓ SubscriberStateTable (keyspace notification)
orchdaemon select() loop
  ↓ FlexCounterOrch::doTask()
      [m_delayTimerExpired チェック]
      [gPortsOrch->allPortsReady() チェック]
      gIntfsOrch->generateInterfaceMap() → m_updateMapsTimer->start()
  ↓ IntfsOrch::doTask(SelectableTimer&) → addRifToFlexCounter()
      COUNTERS_DB[COUNTERS_RIF_NAME_MAP] / [COUNTERS_RIF_TYPE_MAP]
      FLEX_COUNTER_DB[RIF_STAT_COUNTER:<oid>:COUNTER_ID_LIST]
  ↓ syncd FlexCounter スレッド (1000ms ポーリング)
      sai_router_intfs_api->get_router_interface_stats()
      COUNTERS_DB[COUNTERS:<oid>] ← SAI 統計値 (uint64 文字列)
      rif_rates.lua 実行 → COUNTERS_DB[RATES:<oid>] ← 指数平滑 BPS/PPS
  ↓ intfstat (pull 型 direct read)

APPL_DB 書き込み: なし
STATE_DB 書き込み: なし
NotificationConsumer: なし（カウンタ配信に使用せず）
```

[^17]: FlexCounterOrch RIF enable ブランチ: `sonic-swss/orchagent/flexcounterorch.cpp:283-286`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/flexcounterorch.cpp#L283>
[^18]: IntfsOrch doTask(SelectableTimer) / addRifToFlexCounter: `sonic-swss/orchagent/intfsorch.cpp:1598-1637`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L1598>
[^19]: intfstat COUNTERS_DB 直接読み出し: `sonic-utilities/scripts/intfstat:81-82,96,109,123`. <https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bd/scripts/intfstat#L81>
<!-- /pubsub -->

<!-- platform -->

## プラットフォーム / SAI Capability 差異 (Phase H)

<!-- evidence: meta/_intermediate/cdb-flow/counters-rif-platform.md -->

### VoQ シャーシ vs 非 VoQ — リモートシステムポートの扱い

VoQ シャーシ環境 (`gMySwitchType == "voq"` かつ `isChassisDbInUse()`) では `IntfsOrch` コンストラクタ起動時に `CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME` の追加 subscriber が登録される[^20]。

| 環境 | INTERFACE SET 処理 | COUNTERS_DB エントリ |
|------|--------------------|----------------------|
| 非 VoQ | `setIntf()` → `addRouterIntfs()` → `m_rifsToAdd` | 作成される |
| VoQ ローカルポート | 同上 + `voqSyncAddIntf()` で CHASSIS_APP_DB にも同期 | 作成される |
| VoQ リモートシステムポート | oper_status のみ NeighOrch 通知、RIF 作成なし | **作成されない** |

リモートシステムポートは `isRemoteSystemPortIntf()` (`intfsorch.cpp:1640-1650`) で判定され、通常の `addRouterIntfs()` パスに入らない。このため `COUNTERS_RIF_NAME_MAP` にエントリが存在せず `intfstat` でカウンタが表示されない[^21]。

### RIF タイプ別の FlexCounter 登録

`doTask(SelectableTimer&)` 内でポートタイプから RIF タイプ文字列を決定してから `addRifToFlexCounter()` を呼ぶ[^22]:

| `Port::m_type` | COUNTERS_RIF_TYPE_MAP の値 |
|----------------|---------------------------|
| PHY / [LAG](../../reference/glossary.md#term-lag) / SYSTEM | `"SAI_ROUTER_INTERFACE_TYPE_PORT"` |
| [VLAN](../../reference/glossary.md#term-vlan) | `"SAI_ROUTER_INTERFACE_TYPE_VLAN"` |
| SUBPORT | `"SAI_ROUTER_INTERFACE_TYPE_SUB_PORT"` |
| それ以外 | `""` (エラーログ) |

`SUBPORT`（[VLAN](../../reference/glossary.md#term-vlan) サブインタフェース）への統計サポートは ASIC 依存。SAI が `SAI_ROUTER_INTERFACE_TYPE_SUB_PORT` 統計を未実装の場合 `COUNTERS:<oid>` フィールドは 0 のまま更新されない。

### SAI_ROUTER_INTERFACE_STAT_* の部分サポート

`rifStatIds[]` に列挙された全フィールドが FLEX_COUNTER_DB に登録されるが (`intfsorch.cpp:49-59`)[^23]、プラットフォームによっては一部が未サポートとなる:

- `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS` / `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS` — 一部 ASIC で非実装
- 未サポートフィールドは syncd がポーリング結果を COUNTERS_DB に書かない（または常 0）
- `intfstat` はフィールドが存在しない場合に `0` と表示し、「未サポート」と「ゼロ値」を区別しない

### gTraditionalFlexCounter モードによる登録タイミング差

| モード | VIDTORID チェック | 登録タイミング |
|--------|------------------|----------------|
| `gTraditionalFlexCounter = true` (旧) | ASIC_DB `VIDTORID` にエントリが揃うまで 1 秒 tick ごと再試行 | syncd が OID を書き込むまで遅延（大規模シャーシで複数 tick） |
| `gTraditionalFlexCounter = false` (新) | スキップ | SAI RIF 作成後の次 tick（最大 1 秒）で即登録 |

### LoopBack / NAT / MPLS の特記事項

- **LoopBack インタフェース**: `is_lo` 判定で `addRouterIntfs()` が呼ばれず `m_rifsToAdd` に積まれない。`COUNTERS_RIF_NAME_MAP` エントリなし・`intfstat` 非表示はアーキテクチャ設計による（全プラットフォーム共通）。
- **[NAT](../../reference/glossary.md#term-nat) ゾーン ID**: `gIsNatSupported = false` のプラットフォームでは `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` が SAI 属性に渡されない。カウンタ収集への直接影響はない。
- **[MPLS](../../reference/glossary.md#term-mpls) 属性**: [MPLS](../../reference/glossary.md#term-mpls) 非対応 ASIC では `SAI_ROUTER_INTERFACE_ATTR_ADMIN_MPLS_STATE` を含む `create_router_interface()` がエラーを返す場合があり、RIF 作成失敗 → COUNTERS_DB エントリなしとなる[^24]。

[^20]: VoQ IntfsOrch コンストラクタ subscriber 追加: `sonic-swss/orchagent/intfsorch.cpp:102-108`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L102>
[^21]: リモートシステムポート判定 + skip: `sonic-swss/orchagent/intfsorch.cpp:881-893,1640-1666`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L881>
[^22]: RIF タイプ文字列決定ロジック: `sonic-swss/orchagent/intfsorch.cpp:1608-1626`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L1608>
[^23]: rifStatIds 全列挙: `sonic-swss/orchagent/intfsorch.cpp:49-59`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L49>
[^24]: [MPLS](../../reference/glossary.md#term-mpls) / [NAT](../../reference/glossary.md#term-nat) SAI 属性追加条件: `sonic-swss/orchagent/intfsorch.cpp:1278-1294`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L1278>

<!-- /platform -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB FLEX_COUNTER_TABLE](flex-counter-table.md)
- [CONFIG_DB COUNTERS_DB PORT カウンタ](counters-port.md)
- CLI: `intfstat`, `counterpoll`

<!-- ref-triangle:end -->

## 引用元

[^1]: intfsorch RIF カウンタ登録: `sonic-swss/orchagent/intfsorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L49>
[^2]: `rifStatIds[]` 全定義: `sonic-swss/orchagent/intfsorch.cpp:49-59`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L49>
[^3]: `rif_rates.lua` レート計算ロジック: `sonic-swss/orchagent/rif_rates.lua`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/rif_rates.lua>
[^4]: ポーリング間隔ハードコード: `sonic-swss/orchagent/intfsorch.h:21`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.h#L21>
[^5]: RIF_ALPHA/SMOOTH_INTERVAL デフォルト: `sonic-buildimage/dockers/docker-orchagent/enable_counters.py:10-11`. <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-orchagent/enable_counters.py#L10>
[^6]: 起動遅延ロジック: `sonic-buildimage/dockers/docker-orchagent/enable_counters.py:57-64`. <https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-orchagent/enable_counters.py#L57>
[^7]: orchdaemon 初期化順序: `sonic-swss/orchagent/orchdaemon.cpp:232,283,296,625`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/orchdaemon.cpp#L232>
[^8]: UPDATE_MAPS_SEC タイマー: `sonic-swss/orchagent/intfsorch.cpp:45`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L45>
[^9]: SAI create_router_interface エラーハンドリング: `sonic-swss/orchagent/intfsorch.cpp:1297-1305`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L1297>
[^10]: rif_rates.lua ロード失敗の catch: `sonic-swss/orchagent/intfsorch.cpp:86-94`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L86>
[^11]: gTraditionalFlexCounter モードでの VIDTORID 待機ループ: `sonic-swss/orchagent/intfsorch.cpp:1627-1636`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L1627>
[^12]: FlexCounter グループ識別子定数: `sonic-swss/orchagent/intfsorch.h:19-21`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.h#L19>
[^13]: addRifToFlexCounter 3 DB 書き込み: `sonic-swss/orchagent/intfsorch.cpp:1537-1551`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L1537>
[^14]: removeRifFromFlexCounter 削除シーケンス: `sonic-swss/orchagent/intfsorch.cpp:1559-1566`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L1559>
[^15]: ref_count ブロック: `sonic-swss/orchagent/intfsorch.cpp:1327-1330`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L1327>
[^16]: voqSyncAddIntf / voqSyncDelIntf: `sonic-swss/orchagent/intfsorch.cpp:1672-1748`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/intfsorch.cpp#L1672>
[^DELAY_SEC]: FLEX_COUNTER_DELAY_SEC 定数: `sonic-swss/orchagent/flexcounterorch.cpp:44`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/flexcounterorch.cpp#L44>
[^SCHEMA_CONST]: RIF_COUNTER_ID_LIST / RIF_PLUGIN_FIELD 定数: `sonic-swss-common/common/schema.h:302,330`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d/common/schema.h#L302>

<!-- glossary-links-injected: cd1a8c562425 -->
