# TAM side-effects 調査証跡 (Phase F)

## 調査対象

- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp`
- `sonic-swss/crates/countersyncd/src/actor/swss.rs`

## 方針

TAM テーブル群（TAM_DEVICE_TABLE / TAM_COLLECTOR_TABLE / TAM_INT_IFA_FEATURE_TABLE / TAM_INT_IFA_FLOW_TABLE）の
変更に対し、購読者が副次的に書き込む DB エントリを調査する。

## portsorch の TAM 操作

`portsorch.cpp` の Path Tracing TAM コード（`createPtTam()` / `setPortPtTam()` / `unsetPortPtTam()`）は
CONFIG_DB の `TAM_DEVICE_TABLE` を購読しない。SAI オブジェクト作成（`sai_tam_api->create_tam_*`）は
syncd 経由で ASIC_DB に反映されるが、STATE_DB / APPL_DB / COUNTERS_DB への直接書込みは存在しない。

```
grep: "m_state_db\|m_appl_db\|ResponsePublisher\|NotificationProducer" × portsorch createPtTam/setPortPtTam → 0 件
```

## HFTelOrch の STATE_DB 書込

`hftelorch.cpp:66` で `m_state_telemetry_session` が `STATE_HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE_NAME`
("HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE") を STATE_DB に対して保持する。

SET:
- L308: `m_state_telemetry_session.set(session_key, update_values)` — TAM 通知でストリーム状態更新
- L557: `m_state_telemetry_session.set(profile.first + "|" + type_name, values)` — プロファイルグループ ready 時

DEL:
- L432: `m_state_telemetry_session.del(profile_name + "|" + type_name)` — グループ DEL 時

`session_key` 形式: `<profile_name>|<group_type>` (例: `myprofile|port`)

書込フィールド（L557 時）:
- `stream_status` （ストリーム稼働状態）
- `session_type` = `"ipfix"` (固定値)
- `session_config` (テンプレートバイト列を string 化)

書込フィールド（L308 時）:
- `stream_status` のみ更新

## countersyncd (Rust) の COUNTERS_DB 書込

`crates/countersyncd/src/actor/swss.rs:11` の `STATE_HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE` を
読み取り、COUNTERS_DB にカウンタ名マップとカウンタ値を書き込む動作が確認できる。
ただしこの書込は TAM テーブルの直接変更ではなく STATE_DB 変化を受けたリアクション。

## 結論

| 副次 DB | テーブル名 | 書込タイミング | 根拠 |
|---|---|---|---|
| STATE_DB | `HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE` | HFTelOrch がプロファイル適用/削除時 | `hftelorch.cpp:308, 432, 557` |
| ASIC_DB | SAI route (syncd 経由) | portsorch が Path Tracing TAM を SAI に書込む際 | `portsorch.cpp:11554-11650` (syncd 経由、直接 DB 書込なし) |
| APPL_DB / COUNTERS_DB / FLEX_COUNTER_DB | なし | TAM テーブル購読者の直接書込なし | grep 0 件 |
