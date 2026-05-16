# flex-counter-table Phase A — implicit defaults (code-derived)

Generated: 2026-05-14  
Target doc: docs/reference/config-db/flex-counter-table.md

## Field-by-field analysis

### FLEX_COUNTER_STATUS

| 検出種類 | 詳細 |
|---------|------|
| YANG default 外 fallback | YANG に default 宣言なし。orchagent コメント「counters are disabled for polling by default」(flexcounterorch.cpp:227)。未設定時はカウンタ収集ゼロ。 |
| dead consumer | `FLOW_CNT_ROUTE` は `gFlowCounterRouteOrch->getRouteFlowCounterSupported()` が false の場合、`enable` を書いても何も起きない（SAI 未対応プラットフォームでは silent drop）。 |
| プラットフォーム依存 | `ENI` / `DASH_METER` / `HA_SET` は DPU (`switch_type == dpu`) でのみ enable_counters.py がデフォルト `enable` を注入。非 DPU ではエントリ自体なし。 |
| 書込み順依存 | `FLEX_COUNTER_STATUS = enable` を受信した時点で `gPortsOrch->allPortsReady()` が false だと `doTask` が早期 return してエントリが m_toSync に留まる。全ポート ready 後に再試行される（書込み順依存）。 |
| 暗黙 reset | warm-reboot 時: `bake()` は何もしない（intentional）。delay timer (60s) 期間中は `m_delayTimerExpired = false` のため全 SET が無視される。 |
| 経路依存乖離 | `PORT_PHY_ATTR` を enable にすると `PORT_PHY_SERDES_ATTR` も連動して enable になる（同じ counterpoll knob を共有。flexcounterorch.cpp:341-368）。CONFIG_DB には `PORT_PHY_SERDES_ATTR` キーへの直接書き込みは不要/不可能。 |
| 大文字小文字制約 | `enable`/`disable` のみ有効。大文字・空文字は `SWSS_LOG_NOTICE("Unsupported field")` で無視される。 |
| 前提条件依存 | `FLOW_CNT_TRAP` を enable にするには `gCoppOrch` が初期化済みである必要あり。null の場合 `generateHostIfTrapCounterIdList()` が呼ばれず silent drop。 |

init_cfg.json.j2 のデフォルト (`FLEX_COUNTER_STATUS: enable`):
- ACL, PORT, PORT_PHY_ATTR, RIF, QUEUE, PFCWD, PG_WATERMARK, PG_DROP, QUEUE_WATERMARK, BUFFER_POOL_WATERMARK, PORT_BUFFER_DROP

minigraph 経由 (mgmt device types = BmcMgmtToRRouter / MgmtToRRouter / MgmtTsToR) の上書き `disable`:
- BUFFER_POOL_WATERMARK, PFCWD, PG_DROP, PG_WATERMARK, PORT_BUFFER_DROP, QUEUE, QUEUE_WATERMARK

### FLEX_COUNTER_DELAY_STATUS

| 検出種類 | 詳細 |
|---------|------|
| 暗黙 reset+restore | db_migrator `migrate_config_db_flex_counter_delay_status`: fast-reboot 時に既存全エントリの `FLEX_COUNTER_DELAY_STATUS` を `true` に強制上書き。 |
| 暗黙 reset+restore (2) | db_migrator `migrate_flex_counter_delay_status_removal`: 別バージョン移行時に `FLEX_COUNTER_DELAY_STATUS` フィールドを完全削除する migration がある。フィールド有無がバージョンに依存。 |
| YANG default 外 fallback | YANG に default 宣言なし。orchagent 側での参照はなし（syncd 側の FlexCounter が参照）。未設定時は delay なし（即時ポーリング開始）。 |
| dead field | warm-reboot 専用フィールド。通常起動では `m_delayTimerExpired = true`（constructor で即セット）となるため、`FLEX_COUNTER_DELAY_STATUS` は参照されない。 |

### POLL_INTERVAL

| 検出種類 | 詳細 |
|---------|------|
| YANG default 外 fallback | YANG に default なし。CLI `counterpoll show` の fallback 表示値: |
| | PORT / RIF / WRED_ECN_PORT = `1000` ms (DEFLT_1_SEC) |
| | QUEUE / PG_DROP / ACL / TUNNEL / FLOW_CNT_TRAP / FLOW_CNT_ROUTE / WRED_ECN_QUEUE / SRV6 / ENI / HA_SET = `10000` ms (DEFLT_10_SEC) |
| | BUFFER_POOL_WATERMARK / QUEUE_WATERMARK / PG_WATERMARK / PORT_BUFFER_DROP / SWITCH = `60000` ms (DEFLT_60_SEC) |
| | ※ これらは CLI 表示のみのソフトデフォルト。orchagent / syncd にはハードコードなし |
| CLI 範囲制約 | counterpoll ごとに異なる range を IntRange で強制: |
| | PORT / QUEUE / PORT_PHY_ATTR / WRED_ECN_PORT / WRED_ECN_QUEUE / TUNNEL = 100..30000 |
| | PORT_BUFFER_DROP = 30000..300000 (CPU 負荷が高いため下限 30s) |
| | PG_DROP / ACL / FLOW_CNT_TRAP / FLOW_CNT_ROUTE / SRV6 / ENI / HA_SET = 1000..30000 |
| | watermark (QUEUE_WATERMARK / PG_WATERMARK / BUFFER_POOL_WATERMARK) = 1000..60000 |
| | SWITCH = 1000..60000 |
| YANG vs CLI 乖離 | YANG では `poll_interval` typedef が `range 100..4294967295` と定義されており CLI の per-group 制約より広い。YANG バリデーションだけでは CLI の意図した下限が守られない。 |
| ハードコード固定値 | init_cfg 内で ACL のみ `POLL_INTERVAL: 10000` が明示設定。他グループは `POLL_INTERVAL` キー自体を書かない。 |

### BULK_CHUNK_SIZE / BULK_CHUNK_SIZE_PER_PREFIX

| 検出種類 | 詳細 |
|---------|------|
| YANG default 外 fallback | YANG に default なし。未設定時は orchagent が syncd に `"NULL"` 文字列を送信（flexcounterorch.cpp:405-411）。`"NULL"` は syncd 側で chunk size 無効（上限なし）として扱われる。 |
| silent drop+fallback | 以前に BULK_CHUNK_SIZE を設定した後、両フィールドを共に削除（UPDATE で省略）すると `m_groupsWithBulkChunkSize` から erase し `"NULL","NULL"` を送信してリセット。片方だけ省略した場合は残った方のみ有効で、省略側は `"NULL"` が補完される。 |
| YANG で BULK_CHUNK_SIZE を持つグループのみ | PORT, PORT_BUFFER_DROP, QUEUE, QUEUE_WATERMARK, PG_DROP, PG_WATERMARK のみ YANG で定義。DEBUG_COUNTER / PFCWD / PORT_RATES / RIF / RIF_RATES 等は YANG にも orchagent にも BULK_CHUNK_SIZE 未定義（dead field 相当）。 |

## 書き込み経路サマリ

| 経路 | グループ | STATUS | POLL_INTERVAL |
|------|---------|--------|---------------|
| init_cfg.json.j2 | 11グループ | `enable` | ACL のみ `10000` |
| minigraph (mgmt device) | 7グループ | `disable` に上書き | 変更なし |
| enable_counters.py (DPU のみ) | ENI / DASH_METER | `enable` を注入（空の場合のみ） | なし |
| db_migrator (fast-reboot) | 全エントリ | 変更なし | 変更なし（DELAY_STATUS を true に） |
| counterpoll CLI | 各グループ | `enable`/`disable` | 設定可 |

## 検出された discrepancy / 暗黙挙動まとめ

1. **FLOW_CNT_ROUTE silent drop**: SAI 未対応プラットフォームで enable を書いても SAI 設定が行われない。ユーザーへのエラー通知なし。
2. **PORT_PHY_ATTR → PORT_PHY_SERDES_ATTR 連動**: CONFIG_DB に PORT_PHY_SERDES_ATTR キーを書かなくてもオーケストレーション内で自動 enable/disable。
3. **POLL_INTERVAL CLI 範囲 vs YANG 範囲の乖離**: YANG 100..4294967295 に対し CLI は group ごとに異なる上限（最大 300000）。
4. **BULK_CHUNK_SIZE NULL 補完**: 片フィールドのみ設定した場合の暗黙 "NULL" 補完は YANG / CLI ドキュメントに未記載。
5. **warm-reboot 60s 遅延**: FLEX_COUNTER_STATUS の書き込みが delay timer 期間中は m_toSync に蓄積し 60s 後に一括適用。
6. **FLEX_COUNTER_DELAY_STATUS の migration 削除**: バージョン cross-branch upgrade では `FLEX_COUNTER_DELAY_STATUS` が完全削除される migration が走る。
