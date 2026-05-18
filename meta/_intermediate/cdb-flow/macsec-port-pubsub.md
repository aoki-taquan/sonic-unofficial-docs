# macsec-port — Phase G pubsub 調査メモ

## 調査対象

- `sonic-swss/cfgmgr/macsecmgrd.cpp`
- `sonic-swss/cfgmgr/macsecmgr.cpp`
- `sonic-swss/orchagent/macsecorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## CONFIG_DB 購読 (macsecmgrd)

`macsecmgrd.cpp:62-70` で `MACsecMgr` を初期化する際、`cfg_macsec_tables` ベクタに次の 2 テーブルを渡す:

```cpp
std::vector<std::string> cfg_macsec_tables = {
    CFG_MACSEC_PROFILE_TABLE_NAME,   // "MACSEC_PROFILE"
    CFG_PORT_TABLE_NAME,             // "PORT"
};
MACsecMgr macsecmgr(&cfgDb, &stateDb, cfg_macsec_tables);
```

`MACsecMgr` (Orch 派生) は内部で各テーブルに `SubscriberStateTable` (Consumer) を登録し、`Select` ループ (`macsecmgrd.cpp:105`) で受信する。

`doTask()` (`macsecmgr.cpp:289-349`) でディスパッチ:

| テーブル | コマンド | ハンドラ |
|---------|---------|---------|
| `CFG_MACSEC_PROFILE_TABLE_NAME` | SET | `loadProfile()` |
| `CFG_MACSEC_PROFILE_TABLE_NAME` | DEL | `removeProfile()` |
| `CFG_PORT_TABLE_NAME` | SET | `enableMACsec()` |
| `CFG_PORT_TABLE_NAME` | DEL | `disableMACsec()` |

`macsecmgrd.cpp:80-96` の POST 状態チェック: `STATE_DB` の `getMacsecPostState()` が `"pass"` または `"disabled"` を返すまで CONFIG_DB イベントを一切処理しない (`sleep(1); continue;`)。

## APPL_DB 購読 (MACsecOrch)

`orchdaemon.cpp:480-488` で MACsecOrch を APPL_DB に接続:

```cpp
vector<string> macsec_app_tables = {
    APP_MACSEC_PORT_TABLE_NAME,
    APP_MACSEC_EGRESS_SC_TABLE_NAME,
    APP_MACSEC_INGRESS_SC_TABLE_NAME,
    APP_MACSEC_EGRESS_SA_TABLE_NAME,
    APP_MACSEC_INGRESS_SA_TABLE_NAME,
};
gMacsecOrch = new MACsecOrch(m_applDb, m_stateDb, macsec_app_tables, gPortsOrch);
```

## ASIC_DB Notification 購読 (MACsecOrch — POST 完了通知)

`macsecorch.cpp:690-691` で SAI MACsec POST (Power-On Self Test) 完了通知を ASIC_DB の `"NOTIFICATIONS"` チャンネルから受信:

```cpp
m_postCompletionNotificationConsumer = new swss::NotificationConsumer(
    m_notificationsDb.get(), "NOTIFICATIONS");
auto postCompletionNotificatier = new Notifier(
    m_postCompletionNotificationConsumer, this, "POST_COMPLETION__NOTIFICATIONS");
Orch::addExecutor(postCompletionNotificatier);
```

`handleNotification()` は `op == "switch_macsec_post_status"` をハンドルし、STATE_DB の POST 状態 (`"pass"` / `"fail"`) を更新する。

## 書き込みチャンネル

- `macsecmgrd` → APPL_DB: `ProducerStateTable` 経由で `MACSEC_PORT_TABLE` / `MACSEC_EGRESS_SC_TABLE` 等へ書き込み (wpa_supplicant MKA ネゴシエーション結果を受信後に書き込む)
- `MACsecOrch` → ASIC_DB: `sai_macsec_api` で直接 SAI オブジェクトを作成
- `MACsecOrch` → STATE_DB: `m_state_macsec_port.set()` 等で MACsec 状態を書き戻し
- `MACsecOrch` → COUNTERS_DB / FLEX_COUNTER_DB: `FlexCounterManager` 経由でカウンタ登録

## 結論

- CONFIG_DB `PORT` および `MACSEC_PROFILE` は `SubscriberStateTable` ベース (Keyspace 通知経由)
- APPL_DB の 5 つの MACsec テーブルも `SubscriberStateTable` ベース
- ASIC_DB の `"NOTIFICATIONS"` チャンネルは `NotificationConsumer` ベース (POST 完了専用)
- サービス起動後に POST 状態 ready になるまで CONFIG_DB イベントは無視される (macsecmgrd 側のゲート)
