# TAM テーブル Phase F: 副作用調査メモ

## 調査対象
- `sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss-common/common/schema.h`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 調査結果

### TAM テーブル群の orchagent 購読状況

orchdaemon.cpp:857-865 を確認。HFTelOrch は `CFG_HIGH_FREQUENCY_TELEMETRY_PROFILE_TABLE_NAME` (`HIGH_FREQUENCY_TELEMETRY_PROFILE`) と `CFG_HIGH_FREQUENCY_TELEMETRY_GROUP_TABLE_NAME` (`HIGH_FREQUENCY_TELEMETRY_GROUP`) のみを購読する。

`TAM_DEVICE_TABLE`, `TAM_COLLECTOR_TABLE`, `TAM_INT_IFA_FEATURE_TABLE`, `TAM_INT_IFA_FLOW_TABLE` に対応する orchagent Consumer ハンドラは存在しない。

### portsorch Path Tracing TAM の副作用

- `createAndSetPortPtTam()` (portsorch.cpp:11401): SAI TAM オブジェクトを作成し、`SAI_PORT_ATTR_TAM_OBJECT` を対象ポートに設定
- `unsetPortPtTam()` (portsorch.cpp:11448): `SAI_PORT_ATTR_TAM_OBJECT` を NULL に設定。参照カウント 0 になったら SAI TAM オブジェクトを削除
- STATE_DB / APPL_DB への書き込みはなし

### HFTelOrch STATE_DB 書き込み

- `m_state_telemetry_session` は `STATE_DB / HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE` (schema.h:509)
- `profileTableSet()` (hftelorch.cpp:308): 既存セッションエントリの `stream_status` を更新
- `groupTableDel()` (hftelorch.cpp:432): セッションエントリを削除
- `doTask(NotificationConsumer&)` (hftelorch.cpp:557): SAI TAM config change 通知受信後、完全なセッション情報（stream_status, object_names, object_ids, session_type, session_config）を書き込む

### TAM_COLLECTOR_TABLE と HFTelOrch の関係

HFTelOrch の `createTAM()` (hftelorch.cpp:766-789) は SAI TAM コレクタを固定値で作成する。`TAM_COLLECTOR_TABLE` を読まない（ローカルホスト経由のハードコード）。

## 結論

TAM テーブル群（TAM_DEVICE_TABLE / TAM_COLLECTOR_TABLE / TAM_INT_IFA_*）の CONFIG_DB 書き込みが他 DB に波及する経路は事実上なし。副作用は以下のみ:
1. portsorch Path Tracing: SAI のみ（DB 書き込みなし）
2. HFTelOrch: HIGH_FREQUENCY_TELEMETRY_PROFILE/GROUP テーブル（TAM テーブルとは別）経由で STATE_DB を更新
