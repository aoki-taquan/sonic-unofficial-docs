# pfc-wd 副次 DB 書込エビデンス (Phase F)

## 調査ソース

- `sonic-swss/orchagent/pfcwdorch.cpp`
- `sonic-swss/orchagent/pfcactionhandler.cpp`
- `sonic-swss/orchagent/pfcwdorch.h`

## PFC_WD SET (createEntry / startWdOnPort) 時の副次書込

### COUNTERS_DB / COUNTERS:<queue_oid>

`registerInWdDb()` (pfcwdorch.cpp:563-603) が lossless TC ごとに以下を書き込む:

| フィールド | 値 | 書込箇所 |
|-----------|----|---------| 
| `PFC_WD_DETECTION_TIME` | `detection_time * 1000` (マイクロ秒) | pfcwdorch.cpp:570 |
| `PFC_WD_RESTORATION_TIME` | `restoration_time * 1000` (空文字列 if 0) | pfcwdorch.cpp:572-575 |
| `PFC_WD_ACTION` | `"drop"/"forward"/"alert"` | pfcwdorch.cpp:576 |
| `PFC_STAT_HISTORY` | `"enable"/"disable"` | pfcwdorch.cpp:577 |
| `PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED` | `"0"` (累積カウンタ保持) | pfcactionhandler.cpp:190 |
| `PFC_WD_QUEUE_STATS_DEADLOCK_RESTORED` | `"0"` (累積カウンタ保持) | pfcactionhandler.cpp:191 |
| `PFC_WD_QUEUE_STATUS` | `"operational"` | pfcactionhandler.cpp:192 |

これらは `initWdCounters()` (pfcactionhandler.cpp:182-195) 経由で書き込まれる。

### FLEX_COUNTER_DB / PFC_WD グループ

`m_pfcwdFlexCounterManager->setCounterIdList()` で以下を登録:

| 対象タイプ | 内容 | 箇所 |
|-----------|------|------|
| PORT OID | `SAI_PORT_STAT_PFC_*_PAUSE_DURATION_US` 等の PFC ポートカウンタ ID リスト | pfcwdorch.cpp:560 |
| QUEUE OID | `c_queueStatIds` の SAI キューカウンタ ID リスト | pfcwdorch.cpp:587 |
| QUEUE OID (attr) | `c_queueAttrIds` の SAI キュー属性 ID リスト | pfcwdorch.cpp:593 |

### SAI / ASIC_DB

- BRCM + DLR 有効時の最初のポート登録: `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_PFC_DLR_PACKET_ACTION)` (pfcwdorch.cpp:247)
- `startWdOnPort()` 経由でプラットフォーム固有 SAI アクション (drop/forward/alert)

## storm 検出時の副次書込 (ランタイム)

storm 検出イベント受信時 (pfcwdorch.cpp:984-1041):

| DB | テーブル / キー | 書込内容 | 箇所 |
|----|---------------|---------|------|
| APPL_DB | `PFC_WD_TABLE_INSTORM\|<port-alias>` | `field=<queue_index>`, `value="storm"` | pfcwdorch.cpp:1000 |
| COUNTERS_DB | `COUNTERS:<queue_oid>` | デッドロックカウンタ更新、状態フィールド更新 | pfcwdorch.cpp:996,1013,1030 |

storm 復帰時 (pfcwdorch.cpp:1043-1059):

| DB | テーブル / キー | 操作 | 箇所 |
|----|---------------|------|------|
| APPL_DB | `PFC_WD_TABLE_INSTORM\|<port-alias>` | `hdel <queue_index>` (storm フラグ削除) | pfcwdorch.cpp:1058 |

## PFC_WD DEL (deleteEntry / stopWdOnPort) 時の副次書込

`stopWdOnPort()` (pfcwdorch.cpp:643-671):

| 対象 | 操作 | 箇所 |
|------|------|------|
| FLEX_COUNTER_DB PORT OID | `clearCounterIdList` | pfcwdorch.cpp:652 |
| FLEX_COUNTER_DB QUEUE OID | `clearCounterIdList` × lossless TC 数 | pfcwdorch.cpp:657 |
| COUNTERS_DB `COUNTERS:<queue_oid>` | `hdel` (PFC_WD 設定フィールド削除) | pfcwdorch.cpp:668 |

## GLOBAL POLL_INTERVAL 変更時

`PFC_WD|GLOBAL` の `POLL_INTERVAL` 変更受信時 (pfcwdorch.cpp:352-360):

| 副次効果 | 箇所 |
|---------|------|
| `m_pfcwdFlexCounterManager->updateGroupPollingInterval()` — FLEX_COUNTER_DB の PFC_WD グループポーリング間隔を更新 | pfcwdorch.cpp:356 |
