# STATE_DB PBH_CAPABILITIES — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-19
ソース: sonic-swss/orchagent/pbh/pbhcap.cpp

## Phase F: 副次 DB 書込 (Side-Effects)

### 概要

`PbhCapabilities` クラスが書き込む `STATE_DB.PBH_CAPABILITIES` 自体は副次書込の起点であり、
STATE_DB 以外の DB への書き込みは発生しない。

書き込まれる STATE_DB エントリは `pbhcap.cpp:381,405,420,437` の 4 `Table::set()` 呼び出しのみ。

### 副次書込サマリ

| 副次書込先 DB | 書込内容 | 証跡 |
|---|---|---|
| STATE_DB | `PBH_CAPABILITIES|table` / `|rule` / `|hash` / `|hash-field` の 4 エントリ (主書込) | `pbhcap.cpp:381,405,420,437` |
| CONFIG_DB | **なし** | — |
| APPL_DB | **なし** | — |
| COUNTERS_DB | **なし** | — |
| FLEX_COUNTER_DB | **なし** | — |
| ASIC_DB | **なし** | — |

`PbhCapabilities::writePbhVendorCapabilitiesToDb()` は `Table::set()` のみを呼ぶ。
SAI API 呼び出しなし、notify/publish なし、他 Orch への通知なし。

### sonic-utilities 側の参照 (読み取り副作用)

`config pbh` コマンドが STATE_DB `PBH_CAPABILITIES` を読み取ることで操作可否チェックを行う。
これは読み取り専用であり、追加の DB 書き込みは発生しない。

### スコープ外 (書き込まない DB)

- **CONFIG_DB**: `PbhCapabilities` は設定変更を一切行わない。read-once write。
- **APPL_DB**: PBH の APPL_DB エントリは `PbhOrch`（PBH_TABLE/PBH_RULE/PBH_HASH 処理）が管理する。
  `PbhCapabilities` は APPL_DB に触れない。
- **COUNTERS_DB / FLEX_COUNTER_DB**: flow_counter 関連の書込は `PbhOrch → AclOrch` 経路
  (`pbh-side-effects.md` 参照)。`PbhCapabilities` は counter 管理に関与しない。
- **ASIC_DB**: SAI API 呼び出しなし。syncd 経由の間接書込も発生しない。
