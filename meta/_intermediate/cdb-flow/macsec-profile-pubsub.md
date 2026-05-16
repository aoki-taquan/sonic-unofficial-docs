# macsec-profile — Phase G: 通信メカニズム

<!-- source: sonic-swss/cfgmgr/macsecmgr.cpp, sonic-swss/cfgmgr/macsecmgrd.cpp -->

## 1. CONFIG_DB Subscribe パターン

`macsecmgrd` は起動時に `swss::DBConnector("CONFIG_DB", 0)` で CONFIG_DB に接続し、`Orch` 基底クラスの `Consumer`（内部は `SubscriberStateTable`）を介して以下の 2 テーブルを購読する。

```
macsecmgrd
  └─ Orch(cfgDb, tables)
       ├─ SubscriberStateTable: CFG_MACSEC_PROFILE_TABLE_NAME  ("MACSEC_PROFILE")
       └─ SubscriberStateTable: CFG_PORT_TABLE_NAME             ("PORT")
```

イベントループは `swss::Select::select(&sel, SELECT_TIMEOUT=1000ms)` でポーリングし、タイムアウト時は `macsecmgr.doTask()` を呼んで未処理タスクを消化する。FIPS MACSec POST state（STATE_DB の `MACSEC_POST_STATE`）が `"pass"` または `"disabled"` になるまでは全 CONFIG 処理をブロックする。

### doTask ディスパッチテーブル

| テーブル名 | コマンド | ハンドラ |
|-----------|---------|---------|
| `MACSEC_PROFILE` | `SET` | `MACsecMgr::loadProfile()` |
| `MACSEC_PROFILE` | `DEL` | `MACsecMgr::removeProfile()` |
| `PORT` | `SET` | `MACsecMgr::enableMACsec()` |
| `PORT` | `DEL` | `MACsecMgr::disableMACsec()` |

## 2. wpa_supplicant Unix Domain Socket 通信

### ソケットパス

MACsec が有効化されるポートごとに Unix Domain Socket が生成される:

```
/var/run/<port_name>
```

例: `Ethernet0` → `/var/run/Ethernet0`

### wpa_supplicant 子プロセス起動

`enableMACsec()` は `startWPASupplicant(sock)` を呼び出し、`fork()` + `execl()` で以下のコマンドを実行する:

```
/sbin/wpa_supplicant -s -D macsec_sonic -g /var/run/<port_name>
```

- `-s`: syslog 出力
- `-D macsec_sonic`: SONiC 向け MACsec ドライバ
- `-g <sock>`: グローバル制御ソケット（UDS）

### wpa_cli によるパラメータ注入

`configureMACsec()` は `/sbin/wpa_cli -g <sock> ...` で以下の順序でパラメータを設定する:

```
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> add_network
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> key_mgmt NONE
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> mka_cak <primary_cak>
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> mka_ckn <primary_ckn>
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> mka_priority <priority>
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> macsec_policy <0|1>
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> macsec_integ_only <0|1>
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> macsec_replay_protect <0|1>
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> macsec_replay_window <N>  # enable_replay_protect=true 時のみ
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> macsec_include_sci <0|1>
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> macsec_ciphersuite <suite>
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> set_network <id> mka_rekey_period <N>  # rekey_period>0 時のみ
wpa_cli -g /var/run/<port_name> IFNAME=<port_name> enable_network <id>
```

各コマンドの応答が `"OK"` で始まらない場合、`wpa_cli_exec_and_check()` は `std::runtime_error` を送出し MACsec 有効化は失敗する。

## 3. APPL_DB MACSEC 経路

`macsecmgrd` 自体は APPL_DB に直接書き込まない。wpa_supplicant が MKA セッション確立後、`MACsecOrch`（orchagent 内）が以下の APPL_DB テーブルを Subscribe して SAI 操作を行う:

| APPL_DB テーブル | 方向 | 説明 |
|----------------|------|------|
| `APP_MACSEC_PORT_TABLE_NAME` | MACsecOrch が Subscribe | ポートレベル MACsec 設定 |
| `APP_MACSEC_EGRESS_SC_TABLE_NAME` | MACsecOrch が Subscribe | 送信 Secure Channel |
| `APP_MACSEC_INGRESS_SC_TABLE_NAME` | MACsecOrch が Subscribe | 受信 Secure Channel |
| `APP_MACSEC_EGRESS_SA_TABLE_NAME` | MACsecOrch が Subscribe | 送信 Secure Association |
| `APP_MACSEC_INGRESS_SA_TABLE_NAME` | MACsecOrch が Subscribe | 受信 Secure Association |

`MACsecOrch` はこれらのテーブルに書き込まれた SC/SA 情報を `sai_macsec_api` で SAI に変換する。

### 全体通信フロー

```
CONFIG_DB:MACSEC_PROFILE (SET)
  │ SubscriberStateTable
  ▼
macsecmgrd::MACsecMgr::loadProfile()
  │ プロファイルをメモリにキャッシュ

CONFIG_DB:PORT.macsec (SET → profile_name)
  │ SubscriberStateTable
  ▼
macsecmgrd::MACsecMgr::enableMACsec()
  │ STATE_DB:PORT_TABLE で port state/oper_status 確認
  │ task_need_retry (port not ready) or proceed
  │
  ├─ fork() + execl(wpa_supplicant, -g /var/run/<port>)
  │     Unix Domain Socket: /var/run/<port_name>
  │
  └─ configureMACsec()
        wpa_cli -g /var/run/<port> set_network ... (MACSEC_PROFILE fields)
        │ MKA セッション確立 (EAP-MKA over MACsec peer)
        ▼
       wpa_supplicant → SAK 配布 (802.1X/MKA)
        │ SC/SA 生成通知
        ▼
       APPL_DB: APP_MACSEC_PORT/EGRESS_SC/INGRESS_SC/EGRESS_SA/INGRESS_SA
        │ SubscriberStateTable (MACsecOrch in orchagent)
        ▼
       MACsecOrch → sai_macsec_api → ASIC/HW
```

## 引用元

- `sonic-swss/cfgmgr/macsecmgr.cpp`
- `sonic-swss/cfgmgr/macsecmgrd.cpp`
- `sonic-swss/orchagent/macsecorch.cpp`
- `sonic-swss/tests/test_macsec.py`
