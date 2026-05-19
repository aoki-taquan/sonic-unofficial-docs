# queue-counter Phase H — プラットフォーム差分

調査日: 2026-05-19
対象ファイル: docs/reference/config-db/queue-counter.md
ソース: sonic-swss/orchagent/portsorch.cpp (ref:4305596156d7)

## 発見された主なプラットフォーム差異

### 1. VOQ シャーシ — voq_stat_ids の自動追加 + VOQ 専用 NAME_MAP

`gMySwitchType == "voq"` の場合:
- `addQueueFlexCountersPerPortPerQueueIndex()` (voq=true) が `voq_stat_ids`
  (`SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS`) を通常の `queue_stat_ids` に追加する
  (portsorch.cpp:8601-8614)
- `COUNTERS_QUEUE_NAME_MAP` の代わりに `COUNTERS_VOQ_NAME_MAP` (`m_voqTable`) を使用
  (portsorch.cpp:8518-8521)
- VoQ カウンタは FlexCounter の enable/disable フラグに関わらず常時有効化される
  (portsorch.cpp:8484: `gMySwitchType != "voq"` の場合のみ `isQueueCounterEnabled()` チェック)
- `Port::SYSTEM` タイプのポートはシステムポート = VoQ シャーシ向けであり、
  通常 BOX スイッチには存在しない (portsorch.cpp:8431-8440)

### 2. WRED ケイパビリティ — ASIC 依存の動的検出

`initCounterCapabilities()` (portsorch.cpp:1850-1921) が `sai_query_stats_capability()` で
プラットフォームの WRED 統計サポートを問い合わせる:
- サポートする ASIC: `WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` 等が `isSupported=true` になり、
  WRED_ECN_QUEUE グループへの `wred_queue_stat_manager.setCounterIdList()` が実行される
- サポートしない ASIC / SAI クエリ失敗: 全フラグが `isSupported=false` のまま、
  WRED 統計は `COUNTERS:<oid>` に書き込まれない (silent 非追加)
- `STATE_DB / QUEUE_COUNTER_CAPABILITIES` テーブルにサポート状態が記録されるため、
  `wredstat` や `counterpoll wred-ecn-queue` はこのテーブルを参照して動作する

### 3. DPU — キュー ID 未初期化でのスキップ

`gMySwitchType == "dpu"` の場合:
- `postPortInit()` で `initializePortBufferMaximumParameters()` をスキップ (portsorch.cpp:6449)
- portsorch.cpp:6454 コメント: "We have to test the size of m_queue_ids here since it isn't
  initialized on some platforms (like DPU)"
- DPU ではキュー ID が初期化されないため、`queue_stat_ids` のカウンタポーリング登録も
  実質的に実行されない

### 4. MLNX (Mellanox) — OBJECT_TYPE_LIST クエリ不対応

`PortsOrch::PortsOrch()` コンストラクタ (portsorch.cpp:686-700) で `gMySwitchType` が
"voq" でない場合のみ MLNX_PLATFORM_SUBSTRING チェックが走る箇所がある。
`OBJECT_TYPE_LIST` は Mellanox プラットフォームで取得不可のため SWSS_LOG_INFO でスキップ
(portsorch.cpp:611)。キューカウンタ本体への直接影響はないが、ASIC 属性取得の
一部で Mellanox 専用パスが存在する。

### 5. Packet Trimming フィールド — 全 ASIC で COUNTER_ID_LIST に含まれるが値が 0

`SAI_QUEUE_STAT_TRIM_PACKETS` / `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS` /
`SAI_QUEUE_STAT_TX_TRIM_PACKETS` は Trimming 機能の有効・無効に関わらず
`queue_stat_ids` (portsorch.cpp:389-398) に静的に含まれる。
Trimming 非対応 ASIC ではカウンタ値が 0 または SAI が NOT_SUPPORTED を返す。

## 結論

COUNTERS_DB QUEUE カウンタのプラットフォーム差は以下の 3 軸で現れる:
1. **VOQ シャーシ** — 追加の voq_stat_ids と VOQ_NAME_MAP (非 BOX 専用)
2. **WRED ケイパビリティ** — SAI クエリで動的に決定、ASIC 依存
3. **DPU** — キュー ID 未初期化でカウンタポーリング自体が不成立
