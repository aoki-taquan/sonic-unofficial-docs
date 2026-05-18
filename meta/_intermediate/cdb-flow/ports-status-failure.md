# ports-status Phase D 調査ノート — 失敗挙動

## 調査対象

`docs/reference/config-db/ports-status.md` の Phase D (失敗挙動) セクション用中間ファイル。

## 書込み主体別の失敗パス

### portsyncd/linksync 側

**ソース**: `sonic-swss/portsyncd/linksync.cpp`

1. **非フロントパネル IF のスキップ** (`linksync.cpp:193-212`):
   - `m_portTable.get(key, temp)` が false を返す場合 → `m_statePortTable.set()` を呼ばない
   - `SWSS_LOG_NOTICE("Cannot find %s in port table", key.c_str())` のみ

2. **古い ifindex のスキップ** (`linksync.cpp:170-178`):
   - `m_ifindexOldNameMap.find(ifindex) != end()` → 即 return
   - swss restart 直後の過去の netlink イベントを無視するための安全策

3. **RTM_DELLINK + master あり** (`linksync.cpp:157-161`):
   - `master && nlmsg_type == RTM_DELLINK` → 即 return
   - VLAN bridge / LAG メンバーのポートは DEL でエントリを保持する

### PortsOrch 側

**ソース**: `sonic-swss/orchagent/portsorch.cpp`

4. **`initPortSupportedSpeeds()` SAI BUFFER_OVERFLOW** (`portsorch.cpp:3134-3140`):
   ```cpp
   SWSS_LOG_ERROR("Failed to get supported speed list for port %s id=%" PRIx64 ". Not enough container size", ...);
   supported_speeds.clear(); // return empty
   ```
   その後 `supported_speeds_str = swss::join(',', ...)` が空文字列になり STATE_DB に書く

5. **`initPortSupportedSpeeds()` 属性非サポート** (`portsorch.cpp:3141-3148`):
   ```cpp
   SWSS_LOG_WARN("Unable to validate speed for port %s id=%" PRIx64 ". Not supported by platform", ...);
   supported_speeds.clear();
   ```
   同様に空文字列を STATE_DB に書く

6. **`updateDbPortOperSpeed()` + `getPortOperSpeed()` 失敗** (`portsorch.cpp:9972-9988`):
   - SAI エラー: `SWSS_LOG_ERROR("Failed to get oper speed for %s", ...)` → `return false`
   - 呼び出し元 (`portsorch.cpp:9912-9916`) では失敗時に `updateDbPortOperSpeed(port, 0)` を呼ぶ
   - `speed=0` → `speedStr = "N/A"` が STATE_DB に書かれる
   - `speed=0` (up 直後の race): WARN ログ → `return false` → 呼び出し元で `updateDbPortOperSpeed(port, 0)` = `"N/A"` 書込み

7. **`getPortOperFec()` 失敗** (`portsorch.cpp:10009-10012`):
   ```cpp
   SWSS_LOG_NOTICE("Failed to get oper fec for %s", port.m_alias.c_str());
   return false;
   ```
   呼び出し元で `fec_str = "N/A"` を書く

8. **`host_tx_ready` SAI クエリ失敗** (`portsorch.cpp:6715-6718`):
   ```cpp
   SWSS_LOG_ERROR("Failed to get host_tx_ready value from SAI to Port %" PRIx64 , port.m_port_id);
   ```
   `hostTxReady = false` のままなので `"false"` が書かれる

## 結論

- すべての失敗は best-effort — `"N/A"`, `"false"`, 空文字列のフォールバック値を書くか書込みをスキップ
- orchagent クラッシュ / Consumer 停止なし
- linksync は pure best-effort (netlink を受け取れば書く、受け取れなければ書かない)
- STATE_DB エントリが stale 値を持つことがある（特に DOWN 時の `speed`, `fec`）
