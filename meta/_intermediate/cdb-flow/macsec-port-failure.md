# macsec-port — Phase D 失敗挙動 調査メモ

**対象**: `PORT` テーブルの `macsec` フィールド
**ソース**: `sonic-swss/cfgmgr/macsecmgr.cpp`

## enableMACsec() の失敗パス

### 1. プロファイル未ロード
`m_profiles.find(profile_name) == m_profiles.end()`
→ `SWSS_LOG_DEBUG("The MACsec profile '%s' for the port '%s' isn't ready")`
→ `task_need_retry` (無制限再試行)
証跡: `macsecmgr.cpp:488-495`

### 2. ポート未 ready
`isPortStateOk(port_name)` が false
→ `SWSS_LOG_DEBUG("The port '%s' isn't ready")`
→ `task_need_retry` (無制限再試行)
証跡: `macsecmgr.cpp:500-503`

### 3. wpa_supplicant fork 失敗 (pid < 0)
`startWPASupplicant()` が負値を返す
→ `SWSS_LOG_WARN("Cannot start the wpa_supplicant of the port '%s' : %s")`
→ `m_macsec_ports.erase(port.first)`
→ `task_need_retry`
証跡: `macsecmgr.cpp:544-550`

### 4. wpa_supplicant execl 失敗 (pid == 0)
`startWPASupplicant()` が 0 を返す (exec 失敗)
→ `SWSS_LOG_WARN("Cannot start the wpa_supplicant of the port '%s' : %s")`
→ `m_macsec_ports.erase(port.first)`
→ `task_failed` (再試行なし)
証跡: `macsecmgr.cpp:552-558`

### 5. wpa_supplicant ソケット接続タイムアウト
`startWPASupplicant()` ポーリングが RETRY_TIME 回失敗
→ `stopWPASupplicant()`
→ `SWSS_LOG_WARN("Cannot connect to wpa_supplicant.")`
→ pid=0 を返す → 上記 #4 と同じ `task_failed`
証跡: `macsecmgr.cpp:635-678`

### 6. configureMACsec() 失敗
`configureMACsec()` が false を返す
→ `SWSS_LOG_WARN("The MACsec profile '%s' on the port '%s' loading fail")`
→ `disableMACsec()` を呼び出してロールバック
→ `disableMACsec()` の戻り値を上位に返す
証跡: `macsecmgr.cpp:562-568`

## disableMACsec() の失敗パス

### 7. unconfigureMACsec() 失敗 (wpa_cli コマンドエラー)
→ `SWSS_LOG_WARN("Cannot stop MKA session on the port '%s'")`
→ `ret = task_failed`
証跡: `macsecmgr.cpp:590-595`

### 8. stopWPASupplicant() 失敗
→ `SWSS_LOG_WARN("Cannot stop WPA_SUPPLICANT process of the port '%s'")`
→ `ret = task_failed`
→ `m_macsec_ports.erase(itr)` (エントリは消去される)
証跡: `macsecmgr.cpp:597-602`

## 失敗後の STATE_DB/syslog 記録

- `task_need_retry`: Consumer がエントリを再キューし次のイベントループで再試行
- `task_failed`: Consumer がエントリを破棄。CONFIG_DB のフィールドは残る
- syslog (`SWSS_LOG_WARN`) のみ。STATE_DB への失敗記録は PORT.macsec 単独ではなし
  - ただし `MACsecOrch` の SAI POST 失敗は `STATE_DB.MACSEC_POST|switch` に記録
