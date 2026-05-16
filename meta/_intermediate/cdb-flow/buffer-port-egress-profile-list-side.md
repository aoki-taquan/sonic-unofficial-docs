# buffer-port-egress-profile-list — Phase F 副次 DB 書込調査

## 調査対象

- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`

## 調査結果: 副次書込なし

### STATE_DB

`handleSingleBufferPortProfileListEntry` / `handleBufferPortEgressProfileListTable` の処理経路に STATE_DB への書込は存在しない。

STATE_DB への参照は存在する（MMU サイズ読み取り: L133、最大 PG/Queue 数読み取り: L261, L1277 等）が、これらは **読み取りのみ** であり書込ではない。

### COUNTERS_DB

`processEgressBufferProfileList` / `processEgressBufferProfileListPost` / `processEgressBufferProfileListBulk` の経路に COUNTERS_DB への書込は存在しない。

`bufferorch.cpp` で COUNTERS_DB コネクションを保持しているが（L56: `m_countersDb`）、これは buffer pool ウォーターマーク用 Lua スクリプト (L240) に限定されており、egress profile list の処理経路では一切使用されない。

### APPL_STATE_DB

egress profile list の処理経路に APPL_STATE_DB への書込は存在しない。

### FLEX_COUNTER_DB

egress profile list の処理経路に FLEX_COUNTER_DB への書込は存在しない。

FLEX_COUNTER_DB 参照は `bufferorch.cpp:1135`（Port Queue counter）に存在するが、これは VOQ スイッチ判定の文脈であり BUFFER_PORT_EGRESS_PROFILE_LIST 処理とは無関係。

## 根拠まとめ

| DB | 書込有無 | 根拠 |
|----|---------|------|
| STATE_DB | **なし** | buffermgrdyn.cpp の egress handler 経路に書込コードなし。STATE_DB は読み取り（MMU サイズ・PG/Queue 最大値）にのみ使用 |
| COUNTERS_DB | **なし** | bufferorch.cpp:L56 で接続保持するが egress profile list handler では未使用。buffer pool watermark 専用 |
| APPL_STATE_DB | **なし** | 両ファイルの egress profile list 処理経路に該当コードなし |
| FLEX_COUNTER_DB | **なし** | bufferorch.cpp:L1135 は VOQ Port Queue counter 用で本テーブルと無関係 |

## grep 証跡

```
buffermgrdyn.cpp: STATE_DB / COUNTERS_DB / APPL_STATE_DB / FLEX_COUNTER — 0 件 (egress profile list handler 経路)
bufferorch.cpp: processEgressBufferProfileList / processEgressBufferProfileListPost / processEgressBufferProfileListBulk — 副次 DB 書込コードなし
```
