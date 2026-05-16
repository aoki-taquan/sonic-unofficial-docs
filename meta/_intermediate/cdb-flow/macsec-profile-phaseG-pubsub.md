# MACSEC_PROFILE — Phase G 通信メカニズム中間ファイル

生成日: 2026-05-16

ソース:
- `sonic-swss/cfgmgr/macsecmgr.cpp`
- `sonic-swss/orchagent/macsecorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

<!-- pubsub -->
## Phase G: CONFIG_DB Subscribe 機構

### MACsecMgr — CONFIG_DB Consumer 登録

`MACsecMgr::MACsecMgr(cfgDb, stateDb, tables)` が `Orch(cfgDb, tables)` に次のテーブルを渡し Consumer 登録する:

| テーブル名 | DB | 目的 |
|---|---|---|
| `CFG_MACSEC_PROFILE_TABLE_NAME` ("MACSEC_PROFILE") | CONFIG_DB | MKA プロファイル設定 (CAK/CKN/cipher_suite/policy 等) |
| `CFG_PORT_TABLE_NAME` ("PORT") | CONFIG_DB | ポートの `macsec` フィールドでプロファイル名参照 |

```cpp
// macsecmgr.cpp L269-276
MACsecMgr::MACsecMgr(
    DBConnector *cfgDb,
    DBConnector *stateDb,
    const vector<std::string> &tables) :
        Orch(cfgDb, tables),
        m_statePortTable(stateDb, STATE_PORT_TABLE_NAME)
```

`doTask()` の TaskMap で `(テーブル名, op)` をメソッドにディスパッチ:

```cpp
// macsecmgr.cpp L295-300
const static std::map<TaskType, TaskFunc> TaskMap = {
    { { CFG_MACSEC_PROFILE_TABLE_NAME, SET_COMMAND }, &MACsecMgr::loadProfile   },
    { { CFG_MACSEC_PROFILE_TABLE_NAME, DEL_COMMAND }, &MACsecMgr::removeProfile },
    { { CFG_PORT_TABLE_NAME,           SET_COMMAND }, &MACsecMgr::enableMACsec  },
    { { CFG_PORT_TABLE_NAME,           DEL_COMMAND }, &MACsecMgr::disableMACsec },
};
```

### wpa_supplicant 経路 (macsecmgrd → MKA)

CONFIG_DB の MACSEC_PROFILE / PORT 変化を受けた `MACsecMgr::enableMACsec()` が
`startWPASupplicant()` を呼び出して per-port の `wpa_supplicant` プロセスを `fork/exec`:

```cpp
// macsecmgr.cpp L639-644
pid_t wpa_supplicant_pid = fork();
if (wpa_supplicant_pid == 0)
{
    execl(WPA_SUPPLICANT_CMD, WPA_SUPPLICANT_CMD, ...);
    // WPA_SUPPLICANT_CMD = "/sbin/wpa_supplicant"
    // socket: SOCK_DIR + port_name  (/var/run/<port>)
}
```

`wpa_supplicant` 起動後、`wpa_cli` コマンド群 (`/sbin/wpa_cli`) でネットワーク設定を投入:

```cpp
// macsecmgr.cpp L244-266
wpa_cli_exec_and_check(sock, port_name, network_id,
    "set_network", "key_mgmt",   "NONE");
wpa_cli_exec_and_check(sock, port_name, network_id,
    "set_network", "eapol_flags", "0");
// CAK/CKN, cipher_suite, rekey_period, macsec_replay_protect 等を投入
```

### APP_DB Publish (macsecmgrd → MACsecOrch)

`MACsecMgr` が `wpa_supplicant` から MKA ネゴシエーション完了通知を受信後、
`ProducerStateTable` 相当の仕組みで APP_DB の MACsec テーブルに書き込む。

`MACsecOrch` は APP_DB 側の Consumer として orchdaemon に登録される:

```cpp
// orchdaemon.cpp L480-488
vector<string> macsec_app_tables = {
    APP_MACSEC_PORT_TABLE_NAME,
    APP_MACSEC_EGRESS_SC_TABLE_NAME,
    APP_MACSEC_INGRESS_SC_TABLE_NAME,
    APP_MACSEC_EGRESS_SA_TABLE_NAME,
    APP_MACSEC_INGRESS_SA_TABLE_NAME,
};
gMacsecOrch = new MACsecOrch(m_applDb, m_stateDb, macsec_app_tables, gPortsOrch);
```

`MACsecOrch::doTask()` の TaskMap:

| テーブル | op | メソッド |
|---|---|---|
| `APP_MACSEC_PORT_TABLE_NAME` | SET | `taskUpdateMACsecPort` |
| `APP_MACSEC_PORT_TABLE_NAME` | DEL | `taskDisableMACsecPort` |
| `APP_MACSEC_EGRESS_SC_TABLE_NAME` | SET | `taskUpdateEgressSC` |
| `APP_MACSEC_EGRESS_SC_TABLE_NAME` | DEL | `taskDeleteEgressSC` |
| `APP_MACSEC_INGRESS_SC_TABLE_NAME` | SET | `taskUpdateIngressSC` |
| `APP_MACSEC_INGRESS_SC_TABLE_NAME` | DEL | `taskDeleteIngressSC` |
| `APP_MACSEC_EGRESS_SA_TABLE_NAME` | SET | `taskUpdateEgressSA` |
| `APP_MACSEC_EGRESS_SA_TABLE_NAME` | DEL | `taskDeleteEgressSA` |
| `APP_MACSEC_INGRESS_SA_TABLE_NAME` | SET | `taskUpdateIngressSA` |
| `APP_MACSEC_INGRESS_SA_TABLE_NAME` | DEL | `taskDeleteIngressSA` |

### SAI macsec_api 呼び出し (MACsecOrch)

| SAI API | 操作 | 対応メソッド |
|---|---|---|
| `sai_macsec_api->create_macsec()` | ingress/egress MACsec オブジェクト作成 | `createMACsecObject()` (L1253, L1285) |
| `sai_macsec_api->remove_macsec()` | MACsec オブジェクト削除 | `removeMACsecObject()` (L1364, L1371) |
| `sai_macsec_api->create_macsec_port()` | ポート SA の作成 | `createMACsecPort()` (L1558) |
| `sai_macsec_api->remove_macsec_port()` | ポート SA の削除 | `removeMACsecPort()` (L1799) |
| `sai_macsec_api->create_macsec_flow()` | フロー作成 | `createMACsecFlow()` (L1829) |
| `sai_macsec_api->remove_macsec_flow()` | フロー削除 | `removeMACsecFlow()` (L1847) |
| `sai_macsec_api->create_macsec_sc()` | SC (Secure Channel) 作成 | `createMACsecSC()` (L2084) |
| `sai_macsec_api->remove_macsec_sc()` | SC 削除 | `removeMACsecSC()` (L2175) |
| `sai_macsec_api->create_macsec_sa()` | SA (Secure Association) 作成 | `createMACsecSA()` (L2504) |
| `sai_macsec_api->remove_macsec_sa()` | SA 削除 | `removeMACsecSA()` (L2524) |
| `sai_macsec_api->set_macsec_port_attribute()` | ポート属性変更 | `updateMACsecAttr()` (L2195) |
| `sai_macsec_api->set_macsec_sc_attribute()` | SC 属性変更 | `updateMACsecAttr()` (L2199) |
| `sai_macsec_api->set_macsec_sa_attribute()` | SA 属性変更 | `updateMACsecAttr()` (L2203) |

### POST 完了通知 (ASIC_DB Notification)

MACsecOrch は ASIC_DB の `NOTIFICATIONS` チャネルを `NotificationConsumer` で購読し、
POST (Power-On Self Test) 完了を受け取って MACsec 初期化シーケンスを継続する:

```cpp
// macsecorch.cpp L690-692
m_postCompletionNotificationConsumer = new swss::NotificationConsumer(
    m_notificationsDb.get(), "NOTIFICATIONS");
auto postCompletionNotificatier = new Notifier(
    m_postCompletionNotificationConsumer, this, "POST_COMPLETION__NOTIFICATIONS");
Orch::addExecutor(postCompletionNotificatier);
```

### 通信フロー全体図

```
CONFIG_DB MACSEC_PROFILE|<name> (SET/DEL)
  └─ [docker-swss] macsecmgrd
       │  MACsecMgr::doTask() → loadProfile() / removeProfile()
       │  Consumer: CFG_MACSEC_PROFILE_TABLE_NAME
       │
CONFIG_DB PORT|<port> (macsec フィールド変更)
  └─ [docker-swss] macsecmgrd
       │  MACsecMgr::doTask() → enableMACsec() / disableMACsec()
       │  Consumer: CFG_PORT_TABLE_NAME
       │
       ├─ fork/exec /sbin/wpa_supplicant -s /var/run/<port>
       │    │  wpa_cli set_network で CAK/CKN/cipher_suite 投入
       │    └─ MKA ネゴシエーション → SA 確立
       │
       └─ APP_DB APP_MACSEC_PORT_TABLE / APP_MACSEC_*SC_TABLE / APP_MACSEC_*SA_TABLE
            │  (ProducerStateTable)
            ▼
       [docker-swss] orchagent
            │  MACsecOrch::doTask()
            │  Consumer: APP_MACSEC_PORT/SC/SA テーブル
            ▼
       SAI sai_macsec_api
            ├─ create_macsec() / remove_macsec()
            ├─ create_macsec_port() / remove_macsec_port()
            ├─ create_macsec_flow() / remove_macsec_flow()
            ├─ create_macsec_sc() / remove_macsec_sc()
            └─ create_macsec_sa() / remove_macsec_sa()

ASIC_DB NOTIFICATIONS チャネル (POST 完了)
  └─ MACsecOrch::doTask(NotificationConsumer &)
       └─ handleNotification() → POST 完了後に MACsec 初期化継続
```

<!-- /pubsub -->
