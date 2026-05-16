# NTP — Phase G: 通信メカニズム (pubsub) 中間調査

## 調査対象

- ソース: `sonic-net/sonic-host-services` `scripts/hostcfgd`
- テーブル: `NTP` / `NTP_SERVER` / `NTP_KEY` / `LOOPBACK_INTERFACE` (間接)

## CONFIG_DB Subscribe 登録

### NTP 専用サブスクライブ (hostcfgd:2511-2517)

```python
# Handle NTP, NTP_SERVER, and NTP_KEY updates
self.config_db.subscribe(swsscommon.CFG_NTP_GLOBAL_TABLE_NAME,
                         make_callback(self.ntp_global_handler))
self.config_db.subscribe(swsscommon.CFG_NTP_SERVER_TABLE_NAME,
                         make_callback(self.ntp_srv_key_handler))
self.config_db.subscribe(swsscommon.CFG_NTP_KEY_TABLE_NAME,
                         make_callback(self.ntp_srv_key_handler))
```

- `NTP` テーブル変更 → `ntp_global_handler` → `NtpCfg.ntp_global_update()`
- `NTP_SERVER` テーブル変更 → `ntp_srv_key_handler` → `NtpCfg.ntp_srv_key_update()`
- `NTP_KEY` テーブル変更 → `ntp_srv_key_handler` → `NtpCfg.ntp_srv_key_update()`

NTP_SERVER と NTP_KEY は **共通ハンドラ** (`ntp_srv_key_handler`) に集約されており、
どちらが変化してもその時点の両テーブル全件を再取得して chrony を再起動する。

### 間接サブスクライブ — src_intf 変化の連動

```python
self.config_db.subscribe('LOOPBACK_INTERFACE', make_callback(self.lpbk_handler))
```

`lpbk_handler` は `NtpCfg.handle_ntp_source_intf_chg(lpbk_name)` を呼び出す。
NTP_SERVER が未設定なら即 return、設定済みかつ `src_intf` と一致する場合のみ chrony を再起動する。

同様の `handle_ntp_source_intf_chg` 呼び出しは他のインタフェースタイプ (INTERFACE, VLAN_INTERFACE 等) には **無い**。LOOPBACK_INTERFACE のみ。

## chrony 制御

### CHRONY_RESTART コマンド (hostcfgd:1280)

```python
CHRONY_RESTART = ['systemctl', 'restart', 'chrony']
```

すべての NTP イベント (global/server/key/src_intf) は `systemctl restart chrony` で制御する。
SIGHUP / reload は一切使用しない。

### 各ハンドラの chrony 制御フロー

| ハンドラ | トリガー | chrony 制御 | キャッシュ更新 |
|---------|---------|------------|-------------|
| `ntp_global_update` | `NTP` テーブル変更 | `systemctl restart chrony` | 成功時のみ `self.cache[key]=data` |
| `ntp_srv_key_update` | `NTP_SERVER` / `NTP_KEY` 変更 | `systemctl restart chrony` | 成功時のみ `self.cache['servers']` / `self.cache['keys']` |
| `handle_ntp_source_intf_chg` | `LOOPBACK_INTERFACE` 変更 | `systemctl restart chrony` | キャッシュ更新なし |

### 差分チェック (キャッシュガード)

- `ntp_global_update`: `self.cache.get('global', {}) == data` が True なら **no-op**。
- `ntp_srv_key_update`: `cache['servers'] == ntp_servers and cache['keys'] == ntp_keys` が True なら **no-op**。
- `handle_ntp_source_intf_chg`: 差分チェックなし（該当インタフェース名が `src_intf` に含まれれば再起動）。

## SIGHUP の扱い

hostcfgd 自体は `signal.SIGHUP` を登録しているが **何もしない** (L111-112):

```python
def signal_handler(sig, frame):
    if sig == signal.SIGHUP:
        syslog.syslog(syslog.LOG_INFO, "HostCfgd: signal 'SIGHUP' is caught and ignoring..")
```

chrony へ SIGHUP を送信するコードは NTP ハンドラには存在しない。
(他ハンドラ例: TACACS+ の `audisp-tacplus` へは SIGHUP を送信している L489-491)

NTP 設定変更は必ず `systemctl restart chrony`（フルリスタート）であり、
設定のホットリロード (SIGHUP) は採用されていない。

## config_db.listen() による pub/sub ループ (hostcfgd:2527-2528)

```python
def start(self):
    self.config_db.listen(init_data_handler=self.load)
```

`config_db.listen()` は swsscommon の SubscriberStateTable を用いた
Redis Keyspace 通知をポーリングするループ。`init_data_handler=self.load` により
ループ開始前に `NtpCfg.load()` でスナップショット一括取得を行う。

## 証跡ライン番号

| 項目 | ファイル:行 |
|-----|-----------|
| `NtpCfg` クラス定義 | hostcfgd:1272-1406 |
| `CHRONY_RESTART` 定義 | hostcfgd:1280 |
| `handle_ntp_source_intf_chg` | hostcfgd:1312-1329 |
| `ntp_global_update` | hostcfgd:1331-1364 |
| `ntp_srv_key_update` | hostcfgd:1366-1406 |
| `ntp_global_handler` | hostcfgd:2383-2385 |
| `ntp_srv_key_handler` | hostcfgd:2387-2391 |
| `lpbk_handler` → NTP連動 | hostcfgd:2355-2364 |
| subscribe 登録 (NTP/NTP_SERVER/NTP_KEY) | hostcfgd:2511-2517 |
| subscribe 登録 (LOOPBACK_INTERFACE) | hostcfgd:2483 |
| SIGHUP 無視 | hostcfgd:111-112 |
| config_db.listen() | hostcfgd:2527-2528 |
