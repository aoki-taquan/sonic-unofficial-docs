# DOT1X / PAC — Phase E ハードコード定数調査

調査対象: `sonic-buildimage/src/sonic-pac/pacmgr/pacmgr.h`, `pacmgr.cpp`, `hostapdmgr/hostapdmgr.cpp`

## 1. インタフェース名プレフィックス定数

### pacmgr.cpp:59

```cpp
const string INTFS_PREFIX = "E";
```

`PAC_PORT_CONFIG_TABLE` のキー（ポート名）先頭が `"E"` でなければ `SWSS_LOG_NOTICE("Invalid key format. No 'E' prefix: ...")` を出力して `continue` でスキップする（`pacmgr.cpp:166-170`）。これは Ethernet ポートのみ有効を意味する。

### hostapdmgr.cpp:37

```cpp
const string INTFS_PREFIX = "E";
```

hostapdmgrd 側でも同一の `"E"` プレフィックスチェックがある。

### pacmgr.cpp (VLAN_PREFIX)

`STATE_VLAN_TABLE` および `STATE_VLAN_MEMBER_TABLE` のキー処理では `strncmp(key.c_str(), VLAN_PREFIX, 4)` でプレフィックスチェック（`pacmgr.cpp:705,775,884,955`）。`VLAN_PREFIX` は swss ライブラリ経由で `"Vlan"` に解決される。

## 2. method_list / priority_list の最大要素数

```cpp
#define PRIORITY_METHOD_MAX 2   // pacmgr.h:40
#define INDEX_0 0               // pacmgr.h:38
#define INDEX_1 1               // pacmgr.h:39
```

`method_list` / `priority_list` はインデックス 0 と 1 の 2 要素固定。3 要素以上が CONFIG_DB に入っても [2] 以降は読み取られない。

## 3. MAX_PACKET_SIZE と PACMGR_IFNAME_SIZE

```cpp
#define MAX_PACKET_SIZE       8192   // pacmgr.h:36
#define PACMGR_IFNAME_SIZE    60     // pacmgr.h:55 — NIM_IFNAME_SIZE
```

`PACMGR_IFNAME_SIZE=60` はプラットフォームインタフェース名の最大長。`fpGetIntIfNumFromHostIfName()` の内部バッファに影響する。

## 4. hostapdmgr — hostapd 起動待機定数

```cpp
int count = 10;          // waitForHostapdInit() L1261
usleep(100*1000);        // 100ms 間隔 L1267
```

hostapd 起動後 PID ファイル (`/etc/hostapd/hostapdPid`) の存在確認を 10 回 × 100ms = 最大 1 秒待機。超過時は `return -1`（起動失敗判定）。

## 5. hostapdmgr — JSON ファイルパス定数

```cpp
const string HOSTAPD_PID_FILE = "/etc/hostapd/hostapdPid";  // hostapdmgr.cpp:38
// 設定 JSON: "/etc/hostapd/hostapd_config.json"             // hostapdmgr.cpp:977
```

これらのパスはハードコードで、CONFIG_DB / YANG / CLI から変更不可。

## 6. hostapdmgr — JSON ファイル削除待機定数

```cpp
unsigned int cnt = 10;  // hostapdmgr.cpp:975
sleep(1);               // 1 秒間隔       hostapdmgr.cpp:985
```

hostapd 再起動時に既存 JSON ファイルが消えるまで最大 10 秒待機。タイムアウト時は hostapd へのシグナル送信をスキップ。

## 7. STATEDB_KEY_SEPARATOR

```cpp
#define STATEDB_KEY_SEPARATOR "|"   // pacmgr.h:35
```

STATE_DB エントリのキーセパレータ。SONiC 共通規約 `"|"` と一致。
